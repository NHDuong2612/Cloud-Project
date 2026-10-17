import pytest

from cloudhub.catalog import ValidationError
from cloudhub.settings import Settings


def test_https_workloads_fail_before_aws_without_domain_configuration():
    settings = Settings("table", "role", {})
    with pytest.raises(ValidationError, match="CertificateArn"):
        settings.parameters("T04", "a" * 32, {})


def test_https_hostname_is_server_derived():
    settings = Settings("table", "role", {
        "CertificateArn": "arn:aws:acm:ap-southeast-1:123456789012:certificate/12345678-abcd-1234-abcd-123456789012",
        "HostedZoneId": "Z123ABC", "BaseDomain": "labs.example.com",
    })
    result = settings.parameters("T04", "a" * 32, {})
    assert result["DomainName"] == "a" * 32 + ".labs.example.com"
    assert "BaseDomain" not in result


def test_container_image_requires_approved_digest():
    settings = Settings("table", "role", {
        "CertificateArn": "arn:aws:acm:ap-southeast-1:123456789012:certificate/12345678-abcd-1234-abcd-123456789012",
        "HostedZoneId": "Z123ABC", "BaseDomain": "labs.example.com",
    }, images={"demo": "nginx:latest"})
    with pytest.raises(ValidationError, match="digest"):
        settings.parameters("T06", "a" * 32, {"image_alias": "demo"})
