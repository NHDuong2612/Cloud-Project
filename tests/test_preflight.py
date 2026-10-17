from unittest.mock import Mock

import pytest

from cloudhub.preflight import inspect


def session_for(account="123456789012", arn="arn:aws:iam::123456789012:user/developer"):
    session = Mock(region_name="ap-southeast-1")
    clients = {name: Mock() for name in ("sts", "service-quotas", "ec2")}
    session.client.side_effect = lambda name, **kwargs: clients[name]
    clients["sts"].get_caller_identity.return_value = {"Account": account, "Arn": arn}
    clients["service-quotas"].get_service_quota.return_value = {"Quota": {"QuotaName": "limit", "Value": 5}}
    return session, clients


def test_wrong_account_blocks_further_access():
    session, clients = session_for()
    with pytest.raises(ValueError):
        inspect(session, "999999999999")
    clients["service-quotas"].get_service_quota.assert_not_called()


def test_root_blocks_deployment():
    session, _ = session_for(arn="arn:aws:iam::123456789012:root")
    with pytest.raises(ValueError):
        inspect(session, "123456789012")


def test_network_requires_two_zones_and_labels_limits():
    session, clients = session_for()
    clients["ec2"].describe_subnets.return_value = {"Subnets": [
        {"SubnetId": "a", "AvailabilityZone": "ap-southeast-1a", "AvailableIpAddressCount": 20},
        {"SubnetId": "b", "AvailabilityZone": "ap-southeast-1b", "AvailableIpAddressCount": 20},
    ]}
    result = inspect(session, "123456789012", "vpc-example")
    assert len(result["subnets"]) == 2
    assert "remaining capacity" in result["notes"][0]
    clients["ec2"].describe_subnets.return_value["Subnets"].pop()
    with pytest.raises(ValueError):
        inspect(session, "123456789012", "vpc-example")
