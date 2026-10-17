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


def web_parameters(template):
    template["Parameters"].update({
        "AllowedCidr": {"Type": "String", "AllowedPattern": "^([0-9]{1,3}\\.){3}[0-9]{1,3}/(2[4-9]|3[0-2])$"},
        "CodeBucket": {"Type": "String", "AllowedPattern": "^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"},
        "AppBundleKey": {"Type": "String", "AllowedPattern": "^apps/[a-z0-9_-]+/[a-f0-9]{64}\\.zip$"},
    })


def database(template):
    template["Parameters"].update({
        "PrivateSubnetIds": {"Type": "List<AWS::EC2::Subnet::Id>"},
        "DBInstanceClass": {"Type": "String", "Default": "db.t3.micro", "AllowedValues": ["db.t3.micro", "db.t4g.micro"]},
        "DBStorage": {"Type": "Number", "Default": 20, "MinValue": 20, "MaxValue": 100},
        "DBSnapshotIdentifier": {"Type": "String", "Default": "", "MaxLength": 256},
        "DBEngineVersion": {"Type": "String", "Default": "16.15", "AllowedPattern": "^16\\.[0-9]+$"},
    })
    template.setdefault("Conditions", {})["HasDBSnapshot"] = {"Fn::Not": [{"Fn::Equals": [ref("DBSnapshotIdentifier"), ""]}]}
    new_only = lambda value: {"Fn::If": ["HasDBSnapshot", ref("AWS::NoValue"), value]}
    template["Resources"].update({
        "DatabaseSecurityGroup": resource("AWS::EC2::SecurityGroup", {"GroupDescription": "Private CloudHub RDS; app group only", "VpcId": ref("VpcId"), "Tags": tags()}, "DB is reached only by the application's security group.", ["Never open PostgreSQL to a CIDR."]),
        "DatabaseIngress": resource("AWS::EC2::SecurityGroupIngress", {"GroupId": ref("DatabaseSecurityGroup"), "IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432, "SourceSecurityGroupId": ref("InstanceSecurityGroup")}, "Separate ingress avoids a security-group dependency cycle."),
        "AppDatabaseEgress": resource("AWS::EC2::SecurityGroupEgress", {"GroupId": ref("InstanceSecurityGroup"), "IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432, "DestinationSecurityGroupId": ref("DatabaseSecurityGroup")}, "Application DB traffic stays inside the VPC."),
        "DatabaseSubnets": resource("AWS::RDS::DBSubnetGroup", {"DBSubnetGroupDescription": "CloudHub private DB subnets across two AZs", "SubnetIds": ref("PrivateSubnetIds"), "Tags": tags()}, "RDS uses private subnets; Single-AZ DB still needs a two-AZ subnet group."),
        "DatabaseParameters": resource("AWS::RDS::DBParameterGroup", {"Description": "Require TLS for CloudHub PostgreSQL", "Family": "postgres16", "Parameters": {"rds.force_ssl": "1"}, "Tags": tags()}, "The demo requires verified TLS for DB connections."),
        "Database": resource("AWS::RDS::DBInstance", {
            "DBInstanceIdentifier": sub("${AWS::StackName}-db"), "Engine": "postgres", "EngineVersion": ref("DBEngineVersion"),
            "EngineLifecycleSupport": "open-source-rds-extended-support-disabled",
            "DBInstanceClass": ref("DBInstanceClass"), "AllocatedStorage": new_only(ref("DBStorage")), "StorageType": "gp3", "StorageEncrypted": new_only(True),
            "DBName": new_only("cloudhub"), "MasterUsername": new_only("cloudhub_admin"), "ManageMasterUserPassword": True,
            "DBSnapshotIdentifier": {"Fn::If": ["HasDBSnapshot", ref("DBSnapshotIdentifier"), ref("AWS::NoValue")]},
            "DBSubnetGroupName": ref("DatabaseSubnets"), "DBParameterGroupName": ref("DatabaseParameters"), "VPCSecurityGroups": [ref("DatabaseSecurityGroup")],
            "PubliclyAccessible": False, "MultiAZ": False, "BackupRetentionPeriod": 1, "CopyTagsToSnapshot": True, "DeletionProtection": False, "Tags": tags(),
        }, "Dedicated per-session database; credentials managed by RDS. Restore inherits source encryption.",
            ["F06 may approve only encrypted PostgreSQL 16 snapshots containing the cloudhub schema.", "F08 must inventory final snapshots and their ongoing storage charges."],
            DeletionPolicy="Snapshot", UpdateReplacePolicy="Retain"),
    })


def crud_runtime(template):
    instance_role(template, [
        {"Effect": "Allow", "Action": "s3:GetObject", "Resource": sub("arn:${AWS::Partition}:s3:::${CodeBucket}/${AppBundleKey}")},
        {"Effect": "Allow", "Action": "secretsmanager:GetSecretValue", "Resource": attr("Database", "MasterUserSecret.SecretArn")},
    ])
    return {"Fn::Base64": sub((ROOT / "scripts/assets/bootstrap-crud.sh").read_text())}


def t03():
    template = base("CloudHub T03 CRUD web and private PostgreSQL session; per-environment identity and managed DB credentials.")
    compute_parameters(template)
    web_parameters(template)
    template["Resources"]["InstanceSecurityGroup"] = resource("AWS::EC2::SecurityGroup", {
        "GroupDescription": "CloudHub web demo from approved client CIDR", "VpcId": ref("VpcId"),
        "SecurityGroupIngress": [{"IpProtocol": "tcp", "FromPort": 8080, "ToPort": 8080, "CidrIp": ref("AllowedCidr")}],
        "SecurityGroupEgress": [{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"}], "Tags": tags(),
    }, "The demo web port is scoped to the configured client network.", ["No SSH or public PostgreSQL ingress."])
    database(template)
    properties = instance_properties()
    properties["UserData"] = crud_runtime(template)
    template["Resources"]["Instance"] = resource("AWS::EC2::Instance", properties, "Stateless app code is downloaded from an immutable trusted S3 artifact.", ["No secret values in user data or logs."], DependsOn=["DatabaseIngress", "AppDatabaseEgress"], DeletionPolicy="Delete", UpdateReplacePolicy="Retain")
    template["Outputs"] = {
        "InstanceId": {"Description": "App instance and SSM probe target", "Value": ref("Instance")},
        "EndpointUrl": {"Description": "CIDR-restricted HTTP demo; use an SSM tunnel on untrusted networks", "Value": sub("http://${Instance.PublicIp}:8080")},
        "DatabaseIdentifier": {"Description": "Database for F06 snapshot/restore", "Value": ref("Database")},
    }
    return template


BUILDERS = {"t01": t01, "t03": t03}


def main():
    target = ROOT / "src" / "cloudhub" / "templates"
    target.mkdir(exist_ok=True)
    for name, builder in BUILDERS.items():
        path = target / f"{name}-1.0.0.json"
        path.write_text(json.dumps(builder(), indent=2) + "\n", encoding="utf-8")
        print(f"{path.name}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
