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
        "CodeBucket": "cloudhub-deployment-test", "CrudBundleKey": "apps/crud/" + "a" * 64 + ".zip",
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


def test_ecr_repository_is_derived_and_data_bucket_is_required():
    config = {"CertificateArn": "arn:aws:acm:ap-southeast-1:123456789012:certificate/12345678-abcd-1234-abcd-123456789012", "HostedZoneId": "Z123ABC", "BaseDomain": "labs.example.com", "RecoveryBucketName": "cloudhub-recovery-test"}
    image = "123456789012.dkr.ecr.ap-southeast-1.amazonaws.com/team/demo@sha256:" + "a" * 64
    settings = Settings("table", "role", config, images={"demo": image})
    result = settings.parameters("T06", "a" * 32, {"image_alias": "demo"})
    assert result["ContainerRepositoryArn"] == "arn:aws:ecr:ap-southeast-1:123456789012:repository/team/demo"
    bad = Settings("table", "role", config, images={"demo": image.replace("ap-southeast-1", "us-east-1")})
    with pytest.raises(ValidationError, match="account and region"):
        bad.parameters("T06", "a" * 32, {"image_alias": "demo"})
