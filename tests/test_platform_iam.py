from pathlib import Path
import re


def test_ec2_updates_are_scoped_to_owned_instances():
    source = Path("terraform/modules/platform/main.tf").read_text(encoding="utf-8")
    statement = re.search(r'Sid\s*=\s*"UpdateOwnedInstances"(.*?)\n      },', source, re.S)[1]
    assert all(action in statement for action in ("ec2:StopInstances", "ec2:StartInstances", "ec2:ModifyInstanceCreditSpecification"))
    assert ":instance/*" in statement
    assert '"ec2:ResourceTag/Project" = "CloudHub"' in statement
    assert "ssm:DescribeAssociation" in source and "ssm:ListAssociations" in source
