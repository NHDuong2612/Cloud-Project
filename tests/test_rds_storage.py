import json
from unittest.mock import Mock

import pytest
from cloudhub.catalog import ValidationError, validate_config
from cloudhub.settings import Settings
from cloudhub.worker import Worker, database_restore_stage
from test_worker import Store, ENV_ID, OP_ID, call


def restored_database(size=40, source=40):
    store = Store()
    config = validate_config("T03", "1.0.0", {"allowed_cidr": "192.0.2.1/32", "db_storage_gb": size})
    store.env.update(template_id="T03", config=config, restore_job_id="restore-1", lock_owner=OP_ID)
    store.op.update(status="RUNNING", started_at=1000)
    store.other["RESTORE#restore-1"] = {"status": "APPROVED", "owner_id": "user-1", "operation_id": OP_ID, "ownership_verified": True, "template_id": "T03", "template_version": "1.0.0", "source_allocated_storage_gb": source, "parameters": {"DBSnapshotIdentifier": "owned-snapshot"}}
    settings = Settings("table", "role", {"VpcId": "vpc-123", "PublicSubnetId": "subnet-a", "PrivateSubnetIds": "subnet-a,subnet-b", "WorkloadBoundaryArn": "boundary", "CodeBucket": "cloudhub-code", "CrudBundleKey": "apps/crud/" + "a" * 64 + ".zip"})
    return Worker(store, Mock(), Mock(), Mock(), settings, clock=lambda: 1000), store


@pytest.mark.parametrize("size,source", [(40, 40), (44, 40), (100, 40)])
def test_restore_explicitly_passes_quota_priced_storage(size, source):
    worker, store = restored_database(size, source)
    worker.cfn.create_change_set.return_value = {"Id": "change", "StackId": "stack"}
    call(worker, "prepare")
    request = worker.cfn.create_change_set.call_args.kwargs
    template = json.loads(request["TemplateBody"])
    assert template["Resources"]["Database"]["Properties"]["AllocatedStorage"] == {"Ref": "DBStorage"}
    assert {x["ParameterKey"]: x["ParameterValue"] for x in request["Parameters"]}["DBStorage"] == str(size)


@pytest.mark.parametrize("size,source", [(20, 40), (41, 40), (40, None), (40, True), (100, 101)])
def test_restore_rejects_shrink_small_growth_or_missing_snapshot_size(size, source):
    worker, store = restored_database(size, source)
    with pytest.raises(ValidationError):
        worker.restore_parameters(ENV_ID, OP_ID, store.env)


def test_later_update_keeps_snapshot_id_and_honors_storage_instead_of_ignoring_it():
    worker, store = restored_database()
    store.env["restore_parameters"] = {"DBSnapshotIdentifier": "owned-snapshot"}
    store.op.update(action="plan_update", config={**store.env["config"], "db_storage_gb": 44})
    worker.cfn.create_change_set.return_value = {"Id": "change", "StackId": "stack"}
    call(worker, "prepare")
    request = worker.cfn.create_change_set.call_args.kwargs
    parameters = {x["ParameterKey"]: x["ParameterValue"] for x in request["Parameters"]}
    assert parameters["DBStorage"] == "44" and parameters["DBSnapshotIdentifier"] == "owned-snapshot"
    assert json.loads(request["TemplateBody"])["Resources"]["Database"]["Properties"]["AllocatedStorage"] == {"Ref": "DBStorage"}


def test_small_growth_is_rejected_during_preview(monkeypatch):
    monkeypatch.setattr("cloudhub.worker.require_available", lambda *args: None)
    worker, store = restored_database()
    store.env.update(status="READY")
    store.env.pop("lock_owner")
    store.op.update(action="plan_update", config={**store.env["config"], "db_storage_gb": 41})
    with pytest.raises(ValidationError, match="ten percent"):
        call(worker, "acquire")
