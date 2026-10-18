import json
from types import SimpleNamespace
from unittest.mock import Mock

from botocore.exceptions import ReadTimeoutError
import pytest

from cloudhub.catalog import ValidationError
from cloudhub.settings import Settings
from cloudhub.worker import Worker, configuration_hash
import cloudhub.worker as module
from asl_runner import AslRunner
from test_worker import Store, ENV_ID, OP_ID, call, stack


def environment(monkeypatch, action="create", verified=("T01@1.0.0",)):
    store, clock = Store(action), [1000]
    cfn, ssm = Mock(), Mock()
    cfn.exceptions = SimpleNamespace(AlreadyExistsException=type("AlreadyExists", (Exception,), {}))
    cfn.create_change_set.return_value = {"Id": "changeset", "StackId": "stack-id"}
    cfn.describe_change_set.return_value = {"Status": "CREATE_COMPLETE", "ExecutionStatus": "AVAILABLE", "Changes": []}
    cfn.get_paginator.return_value.paginate.return_value = [{"StackResourceSummaries": []}]
    complete = stack("UPDATE_COMPLETE" if action == "update" else "CREATE_COMPLETE")
    complete["Stacks"][0]["Outputs"] = [{"OutputKey": "InstanceId", "OutputValue": "i-test"}]
    cfn.describe_stacks.return_value = complete
    ssm.describe_instance_information.return_value = {"InstanceInformationList": [{"PingStatus": "Online"}]}
    settings = Settings("table", "role", {"VpcId": "vpc-test", "PublicSubnetId": "subnet-test", "WorkloadBoundaryArn": "boundary"}, verified)
    instances = []
    def fresh_worker():
        worker = Worker(store, cfn, ssm, Mock(), settings, clock=lambda: clock[0])
        instances.append(worker)
        return worker
    monkeypatch.setattr(module, "runtime", fresh_worker)
    runner = AslRunner(lambda payload: module.handler(payload, None), clock)
    return runner, store, cfn, ssm, clock, instances


def inputs():
    return {"environment_id": ENV_ID, "operation_id": OP_ID}


def test_checked_in_workflow_creates_ready_session_across_worker_restarts(monkeypatch):
    runner, store, cfn, ssm, clock, workers = environment(monkeypatch)
    ssm.describe_instance_information.side_effect = [{"InstanceInformationList": []}, {"InstanceInformationList": [{"PingStatus": "Online"}]}]
    assert runner.run(inputs())
    assert store.env["status"] == "READY" and store.op["status"] == "SUCCEEDED"
    assert store.env["expires_at_epoch"] == clock[0] + 3600
    assert len(workers) >= 9
    cfn.create_change_set.assert_called_once()
    cfn.execute_change_set.assert_called_once()
    assert "WaitHealth" in runner.trace


def test_lost_changeset_response_reuses_token_and_recovers_existing_change(monkeypatch):
    runner, store, cfn, _, _, _ = environment(monkeypatch)
    class AlreadyExists(Exception):
        pass
    cfn.exceptions = SimpleNamespace(AlreadyExistsException=AlreadyExists)
    cfn.create_change_set.side_effect = [ReadTimeoutError(endpoint_url="https://cloudformation.test"), AlreadyExists()]
    cfn.describe_change_set.return_value.update(ChangeSetId="changeset", StackId="stack-id")
    assert runner.run(inputs())
    requests = cfn.create_change_set.call_args_list
    assert requests[0].kwargs == requests[1].kwargs
    cfn.execute_change_set.assert_called_once()
    assert store.env["status"] == "READY"


def test_lost_execute_response_does_not_execute_update_twice(monkeypatch):
    runner, store, cfn, _, _, _ = environment(monkeypatch, "update")
    preview_id = "c" * 32
    store.env.update(expires_at_epoch=6000, ready_at=400)
    store.op.update(config=store.env["config"], preview_operation_id=preview_id, confirmed_change_set_id="changeset")
    store.other[f"OP#{preview_id}"] = {"status": "PREVIEWED", "expected_version": 1, "owner_id": "user-1", "config": store.env["config"], "change_set_id": "changeset", "stack_id": "stack-id"}
    def execute(**kwargs):
        cfn.describe_change_set.return_value["ExecutionStatus"] = "EXECUTE_IN_PROGRESS"
        raise ReadTimeoutError(endpoint_url="https://cloudformation.test")
    cfn.execute_change_set.side_effect = execute
    assert runner.run(inputs())
    cfn.execute_change_set.assert_called_once()
    assert store.env["expires_at_epoch"] == 6000


def test_failed_readiness_rolls_back_and_keeps_review_lock(monkeypatch):
    runner, store, cfn, ssm, _, _ = environment(monkeypatch)
    ssm.describe_instance_information.return_value = {"InstanceInformationList": []}
    def delete(**kwargs):
        cfn.describe_stacks.return_value = stack("DELETE_COMPLETE")
    cfn.delete_stack.side_effect = delete
    assert not runner.run(inputs())
    assert store.env["status"] == "NEEDS_ATTENTION" and store.env["lock_owner"] == OP_ID
    assert store.op["status"] == "FAILED" and "expires_at_epoch" not in store.env
    cfn.delete_stack.assert_called_once()
    assert "RollbackPoll" in runner.trace


def test_unverified_template_is_rejected_by_actual_worker_gate(monkeypatch):
    runner, store, cfn, _, _, _ = environment(monkeypatch, verified=())
    assert not runner.run(inputs())
    assert store.op["status"] == "REJECTED"
    cfn.create_change_set.assert_not_called()


def test_renewal_finished_before_lost_response_is_not_applied_twice(monkeypatch):
    runner, store, cfn, _, _, _ = environment(monkeypatch, "renew")
    store.env.update(ready_at=400, expires_at_epoch=4000)
    store.op.update(expected_expires_at_epoch=4000, new_expires_at_epoch=7600)
    digest = configuration_hash({"config": store.env["config"], "expires_at_epoch": 7600})
    store.op["config_hash"] = digest
    store.other["QUOTA#server-reservation"]["config_hash"] = digest
    original_invoke = runner.invoke
    lost = []
    def invoke(payload):
        result = original_invoke(payload)
        if payload["phase"] == "prepare" and not lost:
            lost.append(True)
            raise module.RetryableDeploymentError("Response lost after transaction committed")
        return result
    runner.invoke = invoke
    assert runner.run(inputs())
    assert store.env["version"] == 2 and store.env["expires_at_epoch"] == 7600
    assert not cfn.mock_calls


def test_transport_retry_exhaustion_enters_bounded_rollback(monkeypatch):
    runner, store, cfn, _, _, _ = environment(monkeypatch)
    cfn.create_change_set.side_effect = ReadTimeoutError(endpoint_url="https://cloudformation.test")
    cfn.delete_stack.side_effect = lambda **kwargs: setattr(cfn.describe_stacks, "return_value", stack("DELETE_COMPLETE"))
    assert not runner.run(inputs())
    assert cfn.create_change_set.call_count == 4  # initial call + three retries
    assert "Recover" in runner.trace and "RollbackPoll" in runner.trace
    assert store.env["lock_owner"] == OP_ID


def test_deadline_and_unfinished_rollback_never_unlock_environment(monkeypatch):
    _, store, cfn, _, clock, workers = environment(monkeypatch)
    worker = module.runtime()
    store.env.update(lock_owner=OP_ID, status="PROVISIONING")
    store.op.update(status="RUNNING", started_at=1000, rollback_started=1000)
    clock[0] = 8201
    with pytest.raises(ValidationError, match="deadline"):
        call(worker, "poll")
    cfn.describe_stacks.return_value = stack("DELETE_IN_PROGRESS")
    assert call(worker, "rollback_poll")["outcome"] == "DONE"
    assert store.env["lock_owner"] == OP_ID and store.env["version"] == 1


@pytest.mark.parametrize("status", ["ABORTED", "TIMED_OUT", "FAILED"])
def test_interrupted_execution_keeps_lock_and_duplicate_event_is_harmless(monkeypatch, status):
    _, store, _, _, _, _ = environment(monkeypatch, "update")
    store.env.update(lock_owner=OP_ID, status="UPDATING")
    store.op.update(status="RUNNING", started_at=1000)
    arn = "arn:aws:states:ap-southeast-1:123456789012:stateMachine:deployment"
    monkeypatch.setenv("STATE_MACHINE_ARN", arn)
    client = Mock()
    client.describe_execution.return_value = {"status": status, "stateMachineArn": arn, "input": json.dumps(inputs())}
    monkeypatch.setattr(module.boto3, "client", lambda *args, **kwargs: client)
    event = {"detail": {"stateMachineArn": arn, "executionArn": "execution", "status": status}}
    module.reconcile_handler(event, None)
    module.reconcile_handler(event, None)
    assert store.env["lock_owner"] == OP_ID and store.env["version"] == 1
    assert store.env["status"] == "NEEDS_ATTENTION" and store.op["status"] == "FAILED"


def test_stale_failure_event_cannot_override_successful_execution(monkeypatch):
    _, store, _, _, _, _ = environment(monkeypatch)
    arn = "workflow"
    monkeypatch.setenv("STATE_MACHINE_ARN", arn)
    client = Mock()
    client.describe_execution.return_value = {"status": "SUCCEEDED", "stateMachineArn": arn}
    monkeypatch.setattr(module.boto3, "client", lambda *args, **kwargs: client)
    module.reconcile_handler({"detail": {"stateMachineArn": arn, "executionArn": "execution", "status": "FAILED"}}, None)
    assert store.env["status"] == "REQUESTED"
