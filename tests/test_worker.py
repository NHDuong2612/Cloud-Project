from copy import deepcopy
from decimal import Decimal
from unittest.mock import Mock
import json
from pathlib import Path

from botocore.exceptions import ClientError
import pytest

from cloudhub.catalog import ValidationError
from cloudhub.settings import Settings
from cloudhub.store import DynamoStore, native
from cloudhub.worker import Worker, configuration_hash
import cloudhub.worker as module


ENV_ID, OP_ID = "a" * 32, "b" * 32


class Store:
    def __init__(self, action="create"):
        self.env = {"pk": f"ENV#{ENV_ID}", "sk": "META", "owner_id": "user-1", "status": "REQUESTED" if action == "create" else "READY", "version": 1, "template_id": "T01", "template_version": "1.0.0", "config": {"instance_type": "t3.micro", "volume_gb": 16}, "duration_minutes": 60, "retention_policy": "backup"}
        self.op = {"pk": self.env["pk"], "sk": f"OP#{OP_ID}", "owner_id": "user-1", "operation_id": OP_ID, "status": "QUEUED", "action": action, "expected_version": 1, "quota_reservation_id": "server-reservation"}
        self.other = {}
        self.op["config_hash"] = configuration_hash(self.env["config"])
        self.other["QUOTA#server-reservation"] = {"owner_id": "user-1", "operation_id": OP_ID, "config_hash": self.op["config_hash"], "status": "RESERVED", "valid_until": 2000}
        self.resources = []

    def get(self, env_id, key):
        return deepcopy(self.env if key == "META" else self.other.get(key))

    def operation(self, env_id, op_id):
        return deepcopy(self.op if op_id == OP_ID else self.other.get(f"OP#{op_id}"))

    def lock(self, env, op, status, now):
        self.env.update(lock_owner=op["operation_id"], status=status)
        self.op.update(status="RUNNING", started_at=now)

    def patch_operation(self, env_id, op_id, **fields):
        self.op.update(fields)

    def finish(self, env, op, status, op_status, now, keep_lock=False, bump_version=True, **fields):
        self.env.update(status=status, **fields)
        if bump_version:
            self.env["version"] += 1
        if not keep_lock:
            self.env.pop("lock_owner", None)
        self.op["status"] = op_status

    def inventory(self, env_id, op_id, resources, now):
        self.resources.extend(resources)


@pytest.fixture
def make_worker(monkeypatch):
    monkeypatch.setattr(module, "require_available", lambda *args: None)
    def make(action="create"):
        store = Store(action)
        cfn, ssm, elb = Mock(), Mock(), Mock()
        worker = Worker(store, cfn, ssm, elb, Settings("control", "role", {}, ("T01@1.0.0",)), clock=lambda: 1000)
        return worker, store, cfn, ssm, elb
    return make


def call(worker, phase):
    return worker.run({"phase": phase, "environment_id": ENV_ID, "operation_id": OP_ID})


def stack(status="CREATE_COMPLETE"):
    return {"Stacks": [{"StackId": "stack-id", "StackStatus": status, "Tags": [{"Key": "Project", "Value": "CloudHub"}, {"Key": "CloudHubEnvironmentId", "Value": ENV_ID}]}]}


def test_competing_operation_cannot_acquire_or_unlock(make_worker):
    worker, store, cfn, _, _ = make_worker()
    store.env["lock_owner"] = "c" * 32
    with pytest.raises(ValidationError):
        call(worker, "acquire")
    assert call(worker, "recover")["outcome"] == "DONE"
    assert store.env["lock_owner"] == "c" * 32
    cfn.delete_stack.assert_not_called()


def test_stale_version_and_cross_owner_are_rejected(make_worker):
    worker, store, _, _, _ = make_worker()
    store.op["expected_version"] = 0
    with pytest.raises(ValidationError):
        call(worker, "acquire")
    store.op["owner_id"] = "other-user"
    with pytest.raises(ValidationError):
        call(worker, "acquire")


def test_delete_requires_quiesced_backup_for_same_version_and_operation(make_worker):
    worker, store, cfn, _, _ = make_worker("delete")
    with pytest.raises(ValidationError):
        call(worker, "acquire")
    store.op["backup_job_id"] = "job-1"
    store.other["BACKUP#job-1"] = {"status": "COMPLETED", "owner_id": "user-1", "source_version": 1, "source_quiesced": True, "operation_id": OP_ID, "recovery_point": "snapshot-id"}
    call(worker, "acquire")
    assert store.env["status"] == "DELETING"
    cfn.delete_stack.assert_not_called()


def test_delete_does_not_claim_final_cleanup_before_f08(make_worker):
    worker, store, _, _, _ = make_worker("delete")
    store.env.update(retention_policy="purge")
    store.op["purge_confirmed"] = True
    call(worker, "acquire")
    call(worker, "complete")
    assert store.env["status"] == "AWAITING_VERIFICATION"
    assert store.op["status"] == "WAITING_F08"
    assert store.env["lock_owner"] == OP_ID


def test_duration_starts_only_when_ready_and_update_preserves_expiry(make_worker):
    worker, store, _, ssm, _ = make_worker()
    call(worker, "acquire")
    assert "expires_at_epoch" not in store.env
    store.op.update(outputs={"InstanceId": "i-example"}, stack_id="stack-id")
    ssm.describe_instance_information.return_value = {"InstanceInformationList": []}
    assert call(worker, "health")["outcome"] == "WAIT"
    assert store.env["status"] == "PROVISIONING"
    call(worker, "complete")
    assert store.env["expires_at_epoch"] == 4600
    assert store.env["ready_at"] == 1000
    worker2, store2, _, _, _ = make_worker("update")
    store2.env.update(lock_owner=OP_ID, expires_at_epoch=8000)
    store2.op.update(started_at=1000, status="RUNNING", stack_id="stack-id")
    call(worker2, "complete")
    assert store2.env["expires_at_epoch"] == 8000


def test_update_failure_does_not_delete_source_stack(make_worker):
    worker, store, cfn, _, _ = make_worker("update")
    store.env["lock_owner"] = OP_ID
    store.op.update(started_at=1000, status="RUNNING")
    cfn.describe_stacks.return_value = stack("UPDATE_ROLLBACK_COMPLETE")
    cfn.get_paginator.return_value.paginate.return_value = [{"StackResourceSummaries": []}]
    call(worker, "recover")
    cfn.delete_stack.assert_not_called()
    assert store.env["status"] == "NEEDS_ATTENTION"


def test_stack_permission_errors_are_not_mistaken_for_missing_resources(make_worker):
    worker, store, cfn, _, _ = make_worker("delete")
    cfn.describe_stacks.side_effect = ClientError({"Error": {"Code": "AccessDenied", "Message": "denied"}}, "DescribeStacks")
    with pytest.raises(ClientError):
        worker.stack(ENV_ID, store.op)


def test_inventory_reads_all_pages(make_worker):
    worker, store, cfn, _, _ = make_worker()
    cfn.get_paginator.return_value.paginate.return_value = [{"StackResourceSummaries": [{"LogicalResourceId": "a"}]}, {"StackResourceSummaries": [{"LogicalResourceId": "b"}]}]
    worker.inventory(ENV_ID, OP_ID, "stack-id")
    assert len(store.resources) == 2


def test_replacement_changeset_is_blocked(make_worker):
    worker, store, cfn, _, _ = make_worker("plan_update")
    store.env["lock_owner"] = OP_ID
    store.op.update(started_at=1000, status="RUNNING", change_set_id="changeset")
    cfn.describe_change_set.return_value = {"Status": "CREATE_COMPLETE", "Changes": [{"ResourceChange": {"Replacement": "True"}}]}
    with pytest.raises(ValidationError):
        call(worker, "changeset")
    cfn.execute_change_set.assert_not_called()


def test_store_uses_consistent_reads_and_atomic_versioned_lock():
    table = Mock()
    table.get_item.return_value = {"Item": {"version": Decimal(1), "config": {"volume_gb": Decimal(16)}}}
    store = DynamoStore(table)
    assert store.get(ENV_ID, "META")["config"]["volume_gb"] == 16
    assert table.get_item.call_args.kwargs["ConsistentRead"] is True
    fixture = Store()
    store.lock(fixture.env, fixture.op, "PROVISIONING", 1000)
    transactions = table.meta.client.transact_write_items.call_args.kwargs["TransactItems"]
    assert len(transactions) == 3
    assert "#v=:version" in transactions[0]["Update"]["ConditionExpression"]
    assert "attribute_not_exists(lock_owner)" in transactions[0]["Update"]["ConditionExpression"]
    assert "config_hash=:hash" in transactions[2]["Update"]["ConditionExpression"]
    with pytest.raises(ValueError):
        native(Decimal("1.5"))


def test_handler_filters_aws_error_message(monkeypatch, make_worker):
    worker, store, _, _, _ = make_worker()
    worker.run = Mock(side_effect=ClientError({"Error": {"Code": "AccessDenied", "Message": "do-not-leak-secret"}}, "DescribeStacks"))
    monkeypatch.setattr(module, "runtime", lambda: worker)
    result = module.handler({"phase": "acquire", "environment_id": ENV_ID, "operation_id": OP_ID}, None)
    assert "do-not-leak-secret" not in json.dumps(result)
    assert result["error_code"] == "AWS_AccessDenied"


def test_workflow_is_bounded_and_all_choices_have_defaults():
    workflow = json.loads(Path("workflow/deploy.asl.json").read_text())
    assert workflow["TimeoutSeconds"] <= 10800
    for state in workflow["States"].values():
        if state["Type"] == "Task":
            assert state["TimeoutSeconds"] == 75
            assert state["Catch"]
            assert set(state["Parameters"]["Payload"]) == {"phase", "environment_id.$", "operation_id.$"}
        if state["Type"] == "Choice":
            assert "Default" in state
