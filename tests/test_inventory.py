from unittest.mock import Mock

from botocore.exceptions import ClientError
import pytest

from cloudhub.inventory import InventoryCollector


def test_dynamic_children_of_asg_ecs_and_efs_are_inventoried():
    ec2, scaling, ecs, efs = Mock(), Mock(), Mock(), Mock()
    scaling.get_paginator.return_value.paginate.return_value = [{"AutoScalingGroups": [{"Instances": [{"InstanceId": "i-1"}]}]}]
    ec2.describe_instances.return_value = {"Reservations": [{"Instances": [{"BlockDeviceMappings": [{"Ebs": {"VolumeId": "vol-1"}}], "NetworkInterfaces": [{"NetworkInterfaceId": "eni-ec2"}]}]}]}
    ecs.get_paginator.return_value.paginate.return_value = [{"taskArns": ["task-1"]}]
    ecs.describe_tasks.return_value = {"tasks": [{"taskArn": "task-1", "attachments": [{"details": [{"name": "networkInterfaceId", "value": "eni-ecs"}]}]}]}
    efs.get_paginator.return_value.paginate.return_value = [{"MountTargets": [{"NetworkInterfaceId": "eni-efs"}]}]
    resources = [{"LogicalResourceId": name, "ResourceType": kind, "PhysicalResourceId": value} for name, kind, value in [
        ("Fleet", "AWS::AutoScaling::AutoScalingGroup", "fleet"), ("Cluster", "AWS::ECS::Cluster", "cluster"),
        ("Service", "AWS::ECS::Service", "arn:aws:ecs:ap-southeast-1:123456789012:service/cluster/service"),
        ("Mount", "AWS::EFS::MountTarget", "fsmt-1"),
    ]]
    found = InventoryCollector(ec2, scaling, ecs, efs).expand(resources)
    assert {x["PhysicalResourceId"] for x in found} == {"i-1", "vol-1", "eni-ec2", "task-1", "eni-ecs", "eni-efs"}
    assert all(x["ParentPhysicalId"] for x in found)


def test_permission_errors_never_mean_resource_is_deleted():
    ec2 = Mock()
    ec2.describe_instances.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "DescribeInstances")
    resource = {"LogicalResourceId": "Instance", "ResourceType": "AWS::EC2::Instance", "PhysicalResourceId": "i-example"}
    with pytest.raises(ClientError):
        InventoryCollector(ec2, Mock(), Mock(), Mock()).expand([resource])
