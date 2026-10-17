import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("template_builders", ROOT / "scripts/build_templates.py")
builders = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builders)


def test_generated_templates_are_current_and_within_inline_size_limit():
    for name, builder in builders.BUILDERS.items():
        path = ROOT / "src/cloudhub/templates" / f"{name}-1.0.0.json"
        assert path.stat().st_size < 51200
        assert json.loads(path.read_text()) == builder()


def test_t01_has_no_ingress_and_requires_imdsv2_encrypted_storage():
    resources = builders.t01()["Resources"]
    assert not resources["InstanceSecurityGroup"]["Properties"].get("SecurityGroupIngress")
    instance = resources["Instance"]["Properties"]
    assert instance["MetadataOptions"]["HttpTokens"] == "required"
    assert instance["BlockDeviceMappings"][0]["Ebs"]["Encrypted"] is True
    assert instance["CreditSpecification"]["CPUCredits"] == "standard"
    assert "PermissionsBoundary" in resources["InstanceRole"]["Properties"]


def test_no_secrets_in_outputs_and_each_resource_has_context():
    for builder in builders.BUILDERS.values():
        template = builder()
        assert template["Metadata"]["AWSToolsMetrics"]["AWSAgentToolkit"] == "aws-cloudformation@3"
        assert all("secret" not in k.lower() and "password" not in k.lower() for k in template["Outputs"])
        for resource in template["Resources"].values():
            assert resource["Metadata"]["com.aws.cloudformation.Context"]["why"]


def test_t03_database_is_private_and_restore_preserves_data():
    template = builders.t03()
    database = template["Resources"]["Database"]
    assert database["Properties"]["PubliclyAccessible"] is False
    assert database["Properties"]["ManageMasterUserPassword"] is True
    assert "MasterUserPassword" not in database["Properties"]
    assert database["DeletionPolicy"] == "Snapshot"
    assert database["UpdateReplacePolicy"] == "Retain"
    ingress = template["Resources"]["DatabaseIngress"]["Properties"]
    assert "CidrIp" not in ingress and ingress["SourceSecurityGroupId"] == {"Ref": "InstanceSecurityGroup"}
