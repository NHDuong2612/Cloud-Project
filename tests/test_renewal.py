from unittest.mock import Mock

import pytest
from cloudhub.catalog import ValidationError
from cloudhub.store import DynamoStore
from cloudhub.worker import Worker, configuration_hash
from test_worker import Store, ENV_ID, OP_ID, call


def renewal(monkeypatch):
    from cloudhub.settings import Settings
    monkeypatch.setattr("cloudhub.worker.require_available", lambda *args: None)
    store = Store("renew")
    store.env.update(ready_at=400, expires_at_epoch=4000)
    store.op.update(expected_expires_at_epoch=4000, new_expires_at_epoch=7600)
    digest = configuration_hash({"config": store.env["config"], "expires_at_epoch": 7600})
    store.op["config_hash"] = digest
    store.other["QUOTA#server-reservation"]["config_hash"] = digest
    cfn = Mock()
    return Worker(store, cfn, Mock(), Mock(), Settings("table", "role", {}), clock=lambda: 1000), store, cfn


def test_renew_is_idempotent_and_does_not_call_cloudformation(monkeypatch):
    worker, store, cfn = renewal(monkeypatch)
    call(worker, "acquire")
    assert store.env["status"] == "RENEWING"
    assert call(worker, "prepare")["outcome"] == "DONE"
    assert store.env["expires_at_epoch"] == 7600
    assert store.env["duration_minutes"] == 120 and store.env["version"] == 2
    assert call(worker, "prepare")["outcome"] == "DONE"
    assert store.env["version"] == 2
    assert not cfn.mock_calls


@pytest.mark.parametrize("change", [
    {"new_expires_at_epoch": True}, {"new_expires_at_epoch": 3000},
    {"new_expires_at_epoch": 400 + 481 * 60}, {"new_expires_at_epoch": 7601},
    {"expected_expires_at_epoch": 3999}, {"config_hash": "stale-estimate"},
])
def test_invalid_or_unpriced_renewal_is_rejected(monkeypatch, change):
    worker, store, _ = renewal(monkeypatch)
    store.op.update(change)
    with pytest.raises(ValidationError):
        call(worker, "acquire")
    assert "lock_owner" not in store.env


@pytest.mark.parametrize("changes", [{"expires_at_epoch": 1000}, {"status": "FINALIZING", "lock_owner": "c" * 32}])
def test_expired_or_finalizing_session_cannot_be_renewed(monkeypatch, changes):
    worker, store, _ = renewal(monkeypatch)
    store.env.update(changes)
    store.op["expected_expires_at_epoch"] = store.env["expires_at_epoch"]
    with pytest.raises(ValidationError):
        call(worker, "acquire")


def test_renewal_transaction_checks_expiry_and_consumes_reservation(monkeypatch):
    _, fixture, _ = renewal(monkeypatch)
    table = Mock()
    DynamoStore(table).lock(fixture.env, fixture.op, "RENEWING", 1000)
    items = table.meta.client.transact_write_items.call_args.kwargs["TransactItems"]
    assert len(items) == 3
    assert "expires_at_epoch=:expiry AND expires_at_epoch>:now" in items[0]["Update"]["ConditionExpression"]
    assert items[0]["Update"]["ExpressionAttributeValues"][":expiry"] == 4000
    assert items[2]["Update"]["ExpressionAttributeValues"][":hash"] == fixture.op["config_hash"]


def test_renewal_transaction_matches_dynamodb_sdk(monkeypatch):
    import boto3
    from botocore.stub import Stubber
    _, fixture, _ = renewal(monkeypatch)
    table = boto3.resource("dynamodb", region_name="ap-southeast-1", aws_access_key_id="test", aws_secret_access_key="test").Table("cloudhub-test")
    with Stubber(table.meta.client) as stub:
        stub.add_response("transact_write_items", {})
        DynamoStore(table).lock(fixture.env, fixture.op, "RENEWING", 1000)
        stub.assert_no_pending_responses()
