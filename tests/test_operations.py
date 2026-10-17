from datetime import datetime, timezone
import json

import boto3
from botocore.stub import Stubber
import pytest

from cloudhub.catalog import ValidationError
from cloudhub.operations import start_execution


def test_start_execution_is_202_and_idempotent_with_ids_only():
    client = boto3.client("stepfunctions", region_name="ap-southeast-1", aws_access_key_id="test", aws_secret_access_key="test")
    arn = "arn:aws:states:ap-southeast-1:123456789012:stateMachine:cloudhub-dev-deployment"
    expected = {"stateMachineArn": arn, "name": "b" * 32, "input": json.dumps({"environment_id": "a" * 32, "operation_id": "b" * 32}, separators=(",", ":"))}
    with Stubber(client) as stub:
        stub.add_response("start_execution", {"executionArn": arn.replace(":stateMachine:", ":execution:") + ":" + "b" * 32, "startDate": datetime.now(timezone.utc)}, expected)
        stub.add_client_error("start_execution", service_error_code="ExecutionAlreadyExists", expected_params=expected)
        assert start_execution(client, arn, "a" * 32, "b" * 32)["status_code"] == 202
        assert start_execution(client, arn, "a" * 32, "b" * 32)["already_submitted"] is True
    with pytest.raises(ValidationError):
        start_execution(client, arn, "untrusted", "b" * 32)
