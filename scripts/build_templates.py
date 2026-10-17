"""Build the versioned, server-owned CloudFormation template artifacts."""

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def ref(name):
    return {"Ref": name}


def sub(value):
    return {"Fn::Sub": value}


def attr(name, field):
    return {"Fn::GetAtt": [name, field]}


def resource(kind, properties, why, must=(), **extra):
    return {"Type": kind, "Metadata": {"com.aws.cloudformation.Context": {"why": why, "must": list(must)}}, "Properties": properties, **extra}


def base(description):
    return {"AWSTemplateFormatVersion": "2010-09-09", "Description": description,
            "Metadata": {"AWSToolsMetrics": {"AWSAgentToolkit": "aws-cloudformation@3"}},
            "Parameters": {
                "EnvironmentId": {"Type": "String", "AllowedPattern": "^[a-f0-9]{32}$"},
                "VpcId": {"Type": "AWS::EC2::VPC::Id"},
                "PublicSubnetId": {"Type": "AWS::EC2::Subnet::Id"},
                "WorkloadBoundaryArn": {"Type": "String", "AllowedPattern": "^arn:[^:]+:iam::[0-9]{12}:policy/.+$"},
            }, "Resources": {}, "Outputs": {}}


def tags():
    return [{"Key": "Project", "Value": "CloudHub"}, {"Key": "CloudHubEnvironmentId", "Value": ref("EnvironmentId")}]


def compute_parameters(template):
    template["Parameters"].update({
        "AmiParameter": {"Type": "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>", "Default": "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"},
        "InstanceType": {"Type": "String", "Default": "t3.micro", "AllowedValues": ["t3.micro", "t3.small"]},
        "VolumeSize": {"Type": "Number", "Default": 16, "MinValue": 8, "MaxValue": 64},
    })


def instance_role(template, statements=()):
    template["Resources"]["InstanceRole"] = resource("AWS::IAM::Role", {
        "RoleName": sub("${AWS::StackName}-instance"), "Path": "/cloudhub/workloads/", "PermissionsBoundary": ref("WorkloadBoundaryArn"),
        "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]},
        "Policies": [{"PolicyName": "environment-runtime", "PolicyDocument": {"Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Action": ["ssm:UpdateInstanceInformation", "ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], "Resource": "*"}, *statements,
        ]}}], "Tags": tags(),
    }, "Dedicated instance identity; SSM avoids inbound SSH.", ["Keep the platform boundary and environment-specific resource policies."])
    template["Resources"]["InstanceProfile"] = resource("AWS::IAM::InstanceProfile", {
        "InstanceProfileName": sub("${AWS::StackName}-profile"), "Path": "/cloudhub/workloads/", "Roles": [ref("InstanceRole")],
    }, "Attach the environment role without static credentials.")


def instance_properties():
    return {
        "ImageId": ref("AmiParameter"), "InstanceType": ref("InstanceType"), "IamInstanceProfile": ref("InstanceProfile"),
        "CreditSpecification": {"CPUCredits": "standard"},
        "MetadataOptions": {"HttpTokens": "required", "HttpEndpoint": "enabled", "HttpPutResponseHopLimit": 1},
        "NetworkInterfaces": [{"DeviceIndex": "0", "AssociatePublicIpAddress": True, "SubnetId": ref("PublicSubnetId"), "GroupSet": [ref("InstanceSecurityGroup")]}],
        "BlockDeviceMappings": [{"DeviceName": "/dev/xvda", "Ebs": {"VolumeType": "gp3", "VolumeSize": ref("VolumeSize"), "Encrypted": True, "DeleteOnTermination": True}}],
        "Tags": tags(),
    }


def snapshot_parameters(template, properties):
    template["Parameters"].update({
        "RootSnapshotId": {"Type": "String", "Default": "", "AllowedPattern": "^$|^snap-[a-f0-9]+$"},
        "SourceAmiId": {"Type": "String", "Default": "", "AllowedPattern": "^$|^ami-([a-f0-9]{8}|[a-f0-9]{17})$"},
    })
    template.setdefault("Conditions", {}).update({"HasRootSnapshot": {"Fn::Not": [{"Fn::Equals": [ref("RootSnapshotId"), ""]}]}})
    template["Conditions"]["HasSourceAmi"] = {"Fn::Not": [{"Fn::Equals": [ref("SourceAmiId"), ""]}]}
    template.setdefault("Rules", {})["SnapshotNeedsSourceAmi"] = {"Assertions": [{"Assert": {"Fn::Or": [{"Fn::Equals": [ref("RootSnapshotId"), ""]}, {"Fn::Not": [{"Fn::Equals": [ref("SourceAmiId"), ""]}]}]}, "AssertDescription": "Restore requires the recorded source AMI."}]}
    properties["ImageId"] = {"Fn::If": ["HasSourceAmi", ref("SourceAmiId"), ref("AmiParameter")]}
    properties["BlockDeviceMappings"][0]["Ebs"]["SnapshotId"] = {"Fn::If": ["HasRootSnapshot", ref("RootSnapshotId"), ref("AWS::NoValue")]}


def t01():
    template = base("CloudHub T01 Linux session; isolated EC2 role, encrypted root EBS and SSM-only access.")
    compute_parameters(template)
    instance_role(template)
    template["Resources"]["InstanceSecurityGroup"] = resource("AWS::EC2::SecurityGroup", {
        "GroupDescription": "CloudHub Linux SSM; no inbound ports", "VpcId": ref("VpcId"),
        "SecurityGroupEgress": [{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"}], "Tags": tags(),
    }, "Outbound TLS lets the SSM agent reach AWS APIs without a NAT gateway.", ["No inbound SSH or application access."])
    properties = instance_properties()
    snapshot_parameters(template, properties)
    template["Resources"]["Instance"] = resource("AWS::EC2::Instance", properties,
        "One machine per session; root data can be restored from an approved EBS snapshot.",
        ["F06 must snapshot quiesced data before deletion unless purge was confirmed.", "Use a snapshot-owned source AMI and a volume at least as large as the snapshot."],
        DeletionPolicy="Delete", UpdateReplacePolicy="Retain")
    template["Outputs"] = {
        "InstanceId": {"Description": "SSM managed instance for the owner", "Value": ref("Instance")},
        "AmiId": {"Description": "Record this with the recovery point", "Value": properties["ImageId"]},
        "RootDeviceName": {"Description": "Resolve its EBS volume with DescribeInstances", "Value": "/dev/xvda"},
    }
    return template


BUILDERS = {"t01": t01}


def main():
    target = ROOT / "src" / "cloudhub" / "templates"
    target.mkdir(exist_ok=True)
    for name, builder in BUILDERS.items():
        path = target / f"{name}-1.0.0.json"
        path.write_text(json.dumps(builder(), indent=2) + "\n", encoding="utf-8")
        print(f"{path.name}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
