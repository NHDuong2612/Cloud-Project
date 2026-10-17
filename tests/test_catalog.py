import pytest

from cloudhub.catalog import TEMPLATES, ValidationError, require_available, validate_config


def test_all_ten_templates_are_discoverable_but_not_enabled_without_evidence():
    assert len(TEMPLATES) == 10
    assert all(not t.public()["available"] for t in TEMPLATES.values())
    with pytest.raises(ValidationError):
        require_available("T01", "1.0.0", [])


@pytest.mark.parametrize("config", [{"VpcId": "evil"}, {"volume_gb": True}, {"instance_type": "p5.48xlarge"}, {"volume_gb": 1000}])
def test_rejects_infrastructure_injection_and_unapproved_sizes(config):
    with pytest.raises(ValidationError):
        validate_config("T01", "1.0.0", config)


@pytest.mark.parametrize("cidr", ["0.0.0.0/0", "::/0", "10.0.0.1/24", "localhost"])
def test_web_access_is_scoped(cidr):
    with pytest.raises(ValidationError):
        validate_config("T03", "1.0.0", {"allowed_cidr": cidr})


def test_asg_and_fargate_cross_field_constraints():
    with pytest.raises(ValidationError):
        validate_config("T04", "1.0.0", {"allowed_cidr": "192.0.2.1/32", "desired_instances": 3, "max_instances": 1})
    with pytest.raises(ValidationError):
        validate_config("T06", "1.0.0", {"allowed_cidr": "192.0.2.1/32", "image_alias": "demo", "cpu": 512, "memory_mb": 512})


def test_validation_does_not_mutate_client_input_and_versions_are_pinned():
    original = {}
    assert validate_config("T01", "1.0.0", original)["volume_gb"] == 16
    assert original == {}
    with pytest.raises(ValidationError):
        validate_config("T01", "latest", {})
