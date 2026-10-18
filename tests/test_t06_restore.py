from copy import deepcopy
from unittest.mock import Mock
import json

import pytest
from cloudhub.catalog import ValidationError, validate_config
from cloudhub.settings import Settings
from cloudhub.worker import Worker
from test_worker import Store, ENV_ID, OP_ID, call


IMAGE = "123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/approved@sha256:" + "a" * 64


def restored_container():
    store = Store()
    store.env.update(template_id="T06", config=validate_config("T06", "1.0.0", {"allowed_cidr": "192.0.2.1/32", "image_alias": "notes"}), restore_job_id="restore-1", lock_owner=OP_ID)
    store.op.update(status="RUNNING", started_at=1000)
    platform = {"RecoveryBucketName": "cloudhub-recovery", "CertificateArn": "arn:aws:acm:ap-southeast-1:123456789012:certificate/aaaa-bbbb", "HostedZoneId": "Z1234", "BaseDomain": "lab.example.com", "VpcId": "vpc-123", "PublicSubnetIds": "subnet-a,subnet-b", "WorkloadBoundaryArn": "arn:aws:iam::123456789012:policy/boundary"}
    worker = Worker(store, Mock(), Mock(), Mock(), Settings("table", "arn:aws:iam::123456789012:role/deployer", platform, images={"notes": IMAGE}), clock=lambda: 1000)
    job = {"status": "APPROVED", "owner_id": "user-1", "operation_id": OP_ID, "ownership_verified": True, "template_id": "T06", "template_version": "1.0.0", "parameters": {}, "data_copy": {
        "status": "VERIFIED", "destination_bucket": "cloudhub-recovery", "destination_prefix": f"environments/{ENV_ID}/data/", "container_image": IMAGE,
        "object_count": 1, "verified_at_epoch": 900, "manifest_sha256": "c" * 64, "source_backup_id": "backup-1",
    }}
    store.other["RESTORE#restore-1"] = job
    return worker, store, job


def test_restored_prefix_is_fixed_and_survives_failed_provisioning_inventory():
    worker, store, _ = restored_container()
    worker.cfn.create_change_set.return_value = {"Id": "changeset", "StackId": "stack-id"}
    call(worker, "prepare")
    parameters = {x["ParameterKey"]: x["ParameterValue"] for x in worker.cfn.create_change_set.call_args.kwargs["Parameters"]}
    assert parameters["EnvironmentId"] == ENV_ID
    assert "RegisteredDataPrefix" not in parameters  # Never a client-controlled CFN input.
    assert store.op["restored_data"]["prefix"] == f"environments/{ENV_ID}/data/"
    assert "RootSnapshotId" not in json.dumps(parameters)


@pytest.mark.parametrize("field,value", [
    ("destination_bucket", "other-bucket"), ("destination_prefix", "environments/other/data/"),
    ("status", "COPYING"), ("object_count", True), ("object_count", -1),
    ("verified_at_epoch", 1001), ("manifest_sha256", "invalid"), ("container_image", IMAGE.replace("a" * 64, "b" * 64)),
])
def test_unverified_or_mismatched_copy_is_rejected(field, value):
    worker, store, job = restored_container()
    job["data_copy"][field] = value
    with pytest.raises(ValidationError):
        worker.restore_parameters(ENV_ID, OP_ID, store.env)
    worker.cfn.create_change_set.assert_not_called()


def test_t06_restore_rejects_cross_owner_and_infrastructure_overrides():
    worker, store, job = restored_container()
    original = deepcopy(job)
    job["owner_id"] = "other-owner"
    with pytest.raises(ValidationError):
        worker.restore_parameters(ENV_ID, OP_ID, store.env)
    job.update(original)
    job["parameters"] = {"RecoveryBucketName": "evil"}
    with pytest.raises(ValidationError):
        worker.restore_parameters(ENV_ID, OP_ID, store.env)


def test_completing_restore_records_prefix_without_recopying_or_overwriting_data():
    worker, store, _ = restored_container()
    store.op.update(stack_id="stack-id", restored_data={"bucket": "cloudhub-recovery", "prefix": f"environments/{ENV_ID}/data/"})
    call(worker, "complete")
    assert store.env["restored_data"] == store.op["restored_data"]
    assert store.env["restore_parameters"] == {}
    assert not worker.cfn.mock_calls
