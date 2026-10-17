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


def https_frontend(template, target_type="instance"):
    template["Parameters"].update({
        "PublicSubnetIds": {"Type": "List<AWS::EC2::Subnet::Id>"},
        "CertificateArn": {"Type": "String", "AllowedPattern": "^arn:[^:]+:acm:[a-z0-9-]+:[0-9]{12}:certificate/[a-f0-9-]+$"},
        "HostedZoneId": {"Type": "AWS::Route53::HostedZone::Id"},
        "DomainName": {"Type": "String", "AllowedPattern": "^[a-f0-9]{32}\\.[a-z0-9.-]+$"},
    })
    template["Resources"].update({
        "LoadBalancerSecurityGroup": resource("AWS::EC2::SecurityGroup", {
            "VpcId": ref("VpcId"), "GroupDescription": "HTTPS entry for approved client network",
            "SecurityGroupIngress": [{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": ref("AllowedCidr")}],
            "SecurityGroupEgress": [{"IpProtocol": "tcp", "FromPort": 8080, "ToPort": 8080, "DestinationSecurityGroupId": ref("InstanceSecurityGroup")}], "Tags": tags(),
        }, "Only HTTPS from the approved network; only application traffic to targets."),
        "WebIngress": resource("AWS::EC2::SecurityGroupIngress", {"GroupId": ref("InstanceSecurityGroup"), "IpProtocol": "tcp", "FromPort": 8080, "ToPort": 8080, "SourceSecurityGroupId": ref("LoadBalancerSecurityGroup")}, "Targets receive traffic only from their ALB."),
        "LoadBalancer": resource("AWS::ElasticLoadBalancingV2::LoadBalancer", {
            "Type": "application", "Scheme": "internet-facing", "Subnets": ref("PublicSubnetIds"), "SecurityGroups": [ref("LoadBalancerSecurityGroup")],
            "LoadBalancerAttributes": [{"Key": "routing.http.drop_invalid_header_fields.enabled", "Value": "true"}, {"Key": "routing.http.desync_mitigation_mode", "Value": "strictest"}], "Tags": tags(),
        }, "Two-AZ entry point with a certificate managed outside the session."),
        "TargetGroup": resource("AWS::ElasticLoadBalancingV2::TargetGroup", {
            "VpcId": ref("VpcId"), "Protocol": "HTTP", "Port": 8080, "TargetType": target_type,
            "HealthCheckPath": "/health", "HealthCheckIntervalSeconds": 15, "HealthCheckTimeoutSeconds": 5, "HealthyThresholdCount": 2, "UnhealthyThresholdCount": 3,
            "Matcher": {"HttpCode": "200"}, "TargetGroupAttributes": [{"Key": "deregistration_delay.timeout_seconds", "Value": "30"}], "Tags": tags(),
        }, "Application readiness includes the workload's health contract."),
        "Listener": resource("AWS::ElasticLoadBalancingV2::Listener", {
            "LoadBalancerArn": ref("LoadBalancer"), "Port": 443, "Protocol": "HTTPS", "Certificates": [{"CertificateArn": ref("CertificateArn")}],
            "SslPolicy": "ELBSecurityPolicy-TLS13-1-2-2021-06", "DefaultActions": [{"Type": "forward", "TargetGroupArn": ref("TargetGroup")}],
        }, "TLS at the entry point; no plaintext public listener."),
        "DNS": resource("AWS::Route53::RecordSet", {"HostedZoneId": ref("HostedZoneId"), "Name": ref("DomainName"), "Type": "A", "AliasTarget": {"DNSName": attr("LoadBalancer", "DNSName"), "HostedZoneId": attr("LoadBalancer", "CanonicalHostedZoneID")}}, "One hostname per session in the platform-owned zone."),
    })


def t04():
    template = base("CloudHub T04 HTTPS web fleet with bounded Auto Scaling and private RDS; persistent data stays outside the EC2 fleet.")
    template["Parameters"].pop("PublicSubnetId")
    compute_parameters(template)
    web_parameters(template)
    template["Parameters"].update({
        "MinInstances": {"Type": "Number", "Default": 1, "MinValue": 1, "MaxValue": 2},
        "DesiredInstances": {"Type": "Number", "Default": 1, "MinValue": 1, "MaxValue": 3},
        "MaxInstances": {"Type": "Number", "Default": 2, "MinValue": 2, "MaxValue": 3},
        "TargetCPU": {"Type": "Number", "Default": 50, "MinValue": 20, "MaxValue": 80},
    })
    template["Resources"]["InstanceSecurityGroup"] = resource("AWS::EC2::SecurityGroup", {
        "VpcId": ref("VpcId"), "GroupDescription": "CloudHub fleet; ALB ingress only",
        "SecurityGroupEgress": [{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"}], "Tags": tags(),
    }, "Fleet nodes have outbound TLS for bootstrap; inbound is added only from the ALB.")
    database(template)
    https_frontend(template)
    crud_runtime(template)
    template["Resources"]["InstanceRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"].append({"Effect": "Allow", "Action": "cloudformation:SignalResource", "Resource": ref("AWS::StackId")})
    bootstrap = (ROOT / "scripts/assets/bootstrap-crud.sh").read_text()
    signal = "/opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource AutoScalingGroup --region ${AWS::Region}"
    bootstrap = bootstrap.replace("set -eu\n", "set -eu\ndnf install -y aws-cfn-bootstrap\ntrap '" + signal + "' EXIT\n", 1)
    bootstrap += "\nfor attempt in $(seq 1 60); do\n  curl --fail --silent http://127.0.0.1:8080/health && break\n  sleep 5\ndone\ncurl --fail --silent http://127.0.0.1:8080/health\n"
    data = instance_properties()
    data.pop("IamInstanceProfile")
    data["IamInstanceProfile"] = {"Name": ref("InstanceProfile")}
    data["NetworkInterfaces"][0].pop("SubnetId")
    data["NetworkInterfaces"][0]["Groups"] = data["NetworkInterfaces"][0].pop("GroupSet")
    data["CreditSpecification"] = {"CpuCredits": "standard"}
    data["UserData"] = {"Fn::Base64": sub(bootstrap)}
    data.pop("Tags")
    data["TagSpecifications"] = [{"ResourceType": "instance", "Tags": tags()}, {"ResourceType": "volume", "Tags": tags()}]
    template["Resources"]["LaunchTemplate"] = resource("AWS::EC2::LaunchTemplate", {"LaunchTemplateData": data}, "A versioned launch template permits controlled rolling replacement.")
    template["Resources"]["AutoScalingGroup"] = resource("AWS::AutoScaling::AutoScalingGroup", {
        "VPCZoneIdentifier": ref("PublicSubnetIds"), "LaunchTemplate": {"LaunchTemplateId": ref("LaunchTemplate"), "Version": attr("LaunchTemplate", "LatestVersionNumber")},
        "MinSize": ref("MinInstances"), "DesiredCapacity": ref("DesiredInstances"), "MaxSize": ref("MaxInstances"),
        "HealthCheckType": "ELB", "HealthCheckGracePeriod": 240, "TargetGroupARNs": [ref("TargetGroup")],
        "Tags": [{**x, "PropagateAtLaunch": True} for x in tags()],
    }, "Fleet scales only within server-validated bounds; RDS owns durable data.", ["Use ELB health checks and signal readiness after the DB write/read probe."],
        DependsOn=["Listener", "DatabaseIngress", "AppDatabaseEgress", "WebIngress"],
        CreationPolicy={"ResourceSignal": {"Count": ref("DesiredInstances"), "Timeout": "PT15M"}},
        UpdatePolicy={"AutoScalingRollingUpdate": {"MinInstancesInService": ref("MinInstances"), "MaxBatchSize": 1, "PauseTime": "PT15M", "WaitOnResourceSignals": True}})
    template["Resources"]["ScalingPolicy"] = resource("AWS::AutoScaling::ScalingPolicy", {
        "AutoScalingGroupName": ref("AutoScalingGroup"), "PolicyType": "TargetTrackingScaling",
        "TargetTrackingConfiguration": {"PredefinedMetricSpecification": {"PredefinedMetricType": "ASGAverageCPUUtilization"}, "TargetValue": ref("TargetCPU")},
    }, "CPU target tracking operates within the ASG maximum, never unlimited scale-out.")
    template["Outputs"] = {
        "EndpointUrl": {"Description": "Per-session HTTPS hostname", "Value": sub("https://${DomainName}")},
        "TargetGroupArn": {"Description": "F04 checks healthy target count", "Value": ref("TargetGroup")},
        "AutoScalingGroupName": {"Description": "Fleet for monitoring and cleanup verification", "Value": ref("AutoScalingGroup")},
        "DatabaseIdentifier": {"Description": "Persistent data source for F06", "Value": ref("Database")},
    }
    return template


def t05():
    template = deepcopy(t01())
    template["Description"] = "CloudHub T05 Nginx website session; trusted content persists on encrypted EBS and is preserved during snapshot restore."
    web_parameters(template)
    instance_role(template, [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": sub("arn:${AWS::Partition}:s3:::${CodeBucket}/${AppBundleKey}")}])
    template["Resources"]["InstanceSecurityGroup"]["Properties"].update({
        "GroupDescription": "CloudHub website from approved client network",
        "SecurityGroupIngress": [{"IpProtocol": "tcp", "FromPort": 8080, "ToPort": 8080, "CidrIp": ref("AllowedCidr")}],
    })
    template["Resources"]["InstanceSecurityGroup"]["Metadata"]["com.aws.cloudformation.Context"] = {"why": "Website access is scoped to the client CIDR; administration uses SSM.", "must": ["No inbound SSH or unrestricted website ingress."]}
    template["Resources"]["Instance"]["Properties"]["UserData"] = {"Fn::Base64": sub((ROOT / "scripts/assets/bootstrap-website.sh").read_text())}
    template["Resources"]["Instance"]["Metadata"]["com.aws.cloudformation.Context"]["must"].append("Restored content must not be replaced by the seed website.")
    template["Outputs"]["EndpointUrl"] = {"Description": "CIDR-restricted website demo; SSM tunnel is also supported", "Value": sub("http://${Instance.PublicIp}:8080")}
    return template


def t06():
    template = base("CloudHub T06 ECS Fargate session; approved immutable image, HTTPS entry and registered per-environment S3 data prefix.")
    template["Parameters"].pop("PublicSubnetId")
    template["Parameters"].update({
        "AllowedCidr": {"Type": "String", "AllowedPattern": "^([0-9]{1,3}\\.){3}[0-9]{1,3}/(2[4-9]|3[0-2])$"},
        "ContainerImage": {"Type": "String", "AllowedPattern": "^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$"},
        "ContainerRepositoryArn": {"Type": "String", "AllowedPattern": "^arn:[^:]+:ecr:[a-z0-9-]+:[0-9]{12}:repository/.+$"},
        "RecoveryBucketName": {"Type": "String", "AllowedPattern": "^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"},
        "Cpu": {"Type": "Number", "Default": 256, "AllowedValues": [256, 512]},
        "Memory": {"Type": "Number", "Default": 512, "AllowedValues": [512, 1024, 2048]},
        "DesiredTasks": {"Type": "Number", "Default": 1, "MinValue": 1, "MaxValue": 2},
    })
    template["Rules"] = {"FargateSizing": {"Assertions": [{"Assert": {"Fn::Or": [{"Fn::Equals": [ref("Cpu"), "256"]}, {"Fn::Not": [{"Fn::Equals": [ref("Memory"), "512"]}]}]}, "AssertDescription": "512 CPU units require at least 1024 MiB."}]}}
    template["Resources"]["InstanceSecurityGroup"] = resource("AWS::EC2::SecurityGroup", {
        "VpcId": ref("VpcId"), "GroupDescription": "CloudHub task ENIs; ALB ingress only", "Tags": tags(),
        "SecurityGroupEgress": [{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"}],
    }, "Outbound TLS for ECR, S3 and CloudWatch; no direct inbound task access.")
    https_frontend(template, "ip")
    trust = {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"}, "Action": "sts:AssumeRole",
        "Condition": {"StringEquals": {"aws:SourceAccount": ref("AWS::AccountId")}, "ArnLike": {"aws:SourceArn": sub("arn:${AWS::Partition}:ecs:${AWS::Region}:${AWS::AccountId}:*")}},
    }]}
    template["Resources"]["LogGroup"] = resource("AWS::Logs::LogGroup", {"LogGroupName": sub("/cloudhub/environments/${EnvironmentId}"), "RetentionInDays": 14, "Tags": tags()}, "Retain operational logs separately from session data.", ["F08 must report this retained group and retention."], DeletionPolicy="Retain", UpdateReplacePolicy="Retain")
    for name, suffix, statements, why in [
        ("ExecutionRole", "execution", [
            {"Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*"},
            {"Effect": "Allow", "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"], "Resource": ref("ContainerRepositoryArn")},
            {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"], "Resource": attr("LogGroup", "Arn")},
        ], "Runtime pulls the approved image and writes logs; these credentials are not the application task role."),
        ("TaskRole", "task", [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"], "Resource": sub("arn:${AWS::Partition}:s3:::${RecoveryBucketName}/environments/${EnvironmentId}/data/*")}], "Application can access only its registered persistent data prefix."),
    ]:
        template["Resources"][name] = resource("AWS::IAM::Role", {"RoleName": sub("${AWS::StackName}-" + suffix), "Path": "/cloudhub/workloads/", "PermissionsBoundary": ref("WorkloadBoundaryArn"), "AssumeRolePolicyDocument": deepcopy(trust), "Policies": [{"PolicyName": "environment-runtime", "PolicyDocument": {"Version": "2012-10-17", "Statement": statements}}], "Tags": tags()}, why, ["Keep the platform boundary and environment-scoped resource policy."])
    template["Resources"]["Cluster"] = resource("AWS::ECS::Cluster", {"Tags": tags()}, "A session-local cluster keeps inventory and service ownership explicit.")
    template["Resources"]["TaskDefinition"] = resource("AWS::ECS::TaskDefinition", {
        "Family": sub("${AWS::StackName}-app"), "RequiresCompatibilities": ["FARGATE"], "NetworkMode": "awsvpc",
        "RuntimePlatform": {"CpuArchitecture": "X86_64", "OperatingSystemFamily": "LINUX"}, "Cpu": ref("Cpu"), "Memory": ref("Memory"),
        "ExecutionRoleArn": attr("ExecutionRole", "Arn"), "TaskRoleArn": attr("TaskRole", "Arn"), "Tags": tags(),
        "ContainerDefinitions": [{
            "Name": "app", "Image": ref("ContainerImage"), "Essential": True, "User": "10001:10001", "ReadonlyRootFilesystem": True,
            "LinuxParameters": {"Capabilities": {"Drop": ["ALL"]}},
            "PortMappings": [{"ContainerPort": 8080, "Protocol": "tcp"}],
            "Environment": [{"Name": "DATA_BUCKET", "Value": ref("RecoveryBucketName")}, {"Name": "DATA_PREFIX", "Value": sub("environments/${EnvironmentId}/data/")}, {"Name": "AWS_DEFAULT_REGION", "Value": ref("AWS::Region")}],
            "LogConfiguration": {"LogDriver": "awslogs", "Options": {"awslogs-group": ref("LogGroup"), "awslogs-region": ref("AWS::Region"), "awslogs-stream-prefix": "app"}},
        }],
    }, "Immutable task revisions use a non-root, read-only runtime; writable layers are not backups.")
    template["Resources"]["Service"] = resource("AWS::ECS::Service", {
        "Cluster": ref("Cluster"), "TaskDefinition": ref("TaskDefinition"), "LaunchType": "FARGATE", "PlatformVersion": "1.4.0", "DesiredCount": ref("DesiredTasks"),
        "EnableExecuteCommand": False, "EnableECSManagedTags": True, "PropagateTags": "SERVICE", "Tags": tags(),
        "HealthCheckGracePeriodSeconds": 60,
        "DeploymentConfiguration": {"DeploymentCircuitBreaker": {"Enable": True, "Rollback": True}, "MinimumHealthyPercent": 100, "MaximumPercent": 200},
        "NetworkConfiguration": {"AwsvpcConfiguration": {"AssignPublicIp": "ENABLED", "Subnets": ref("PublicSubnetIds"), "SecurityGroups": [ref("InstanceSecurityGroup")]}},
        "LoadBalancers": [{"ContainerName": "app", "ContainerPort": 8080, "TargetGroupArn": ref("TargetGroup")}],
    }, "Fargate tasks use IP targets; the circuit breaker prevents publishing a broken image.", ["Approved images must listen on 8080 and provide a meaningful /health endpoint."], DependsOn=["Listener", "WebIngress"])
    template["Outputs"] = {
        "EndpointUrl": {"Description": "HTTPS application URL", "Value": sub("https://${DomainName}")},
        "TargetGroupArn": {"Description": "Readiness probe target group", "Value": ref("TargetGroup")},
        "ClusterName": {"Description": "ECS cluster name", "Value": ref("Cluster")},
        "ServiceArn": {"Description": "ECS service inventory", "Value": ref("Service")},
        "RegisteredDataPrefix": {"Description": "Only this prefix belongs to this environment's backup scope", "Value": sub("s3://${RecoveryBucketName}/environments/${EnvironmentId}/data/")},
    }
    return template


BUILDERS = {"t01": t01, "t03": t03, "t04": t04, "t05": t05, "t06": t06}


def main():
    target = ROOT / "src" / "cloudhub" / "templates"
    target.mkdir(exist_ok=True)
    for name, builder in BUILDERS.items():
        path = target / f"{name}-1.0.0.json"
        path.write_text(json.dumps(builder(), indent=2) + "\n", encoding="utf-8")
        print(f"{path.name}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
