"""Expand CloudFormation parents into the live child IDs needed by F08."""

from botocore.exceptions import ClientError


class InventoryCollector:
    def __init__(self, ec2, autoscaling, ecs, efs):
        self.ec2, self.autoscaling, self.ecs, self.efs = ec2, autoscaling, ecs, efs

    def expand(self, resources):
        found = {}
        cluster = next((x.get("PhysicalResourceId") for x in resources if x["ResourceType"] == "AWS::ECS::Cluster"), None)
        def add(kind, identifier, parent):
            if identifier:
                found[kind, identifier] = {
                    "LogicalResourceId": parent["LogicalResourceId"] + ":child",
                    "ResourceType": kind, "PhysicalResourceId": identifier,
                    "ResourceStatus": "OBSERVED", "ParentPhysicalId": parent.get("PhysicalResourceId", ""),
                }
        def instance(identifier, parent):
            add("AWS::EC2::Instance", identifier, parent)
            try:
                response = self.ec2.describe_instances(InstanceIds=[identifier])
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                    return
                raise
            for reservation in response["Reservations"]:
                for item in reservation["Instances"]:
                    for mapping in item.get("BlockDeviceMappings", []):
                        add("AWS::EC2::Volume", mapping.get("Ebs", {}).get("VolumeId"), parent)
                    for interface in item.get("NetworkInterfaces", []):
                        add("AWS::EC2::NetworkInterface", interface["NetworkInterfaceId"], parent)
        for resource in resources:
            physical, kind = resource.get("PhysicalResourceId"), resource["ResourceType"]
            if not physical:
                continue
            if kind == "AWS::EC2::Instance":
                instance(physical, resource)
                found.pop(("AWS::EC2::Instance", physical), None)
            elif kind == "AWS::AutoScaling::AutoScalingGroup":
                for page in self.autoscaling.get_paginator("describe_auto_scaling_groups").paginate(AutoScalingGroupNames=[physical]):
                    for group in page["AutoScalingGroups"]:
                        for node in group["Instances"]:
                            instance(node["InstanceId"], resource)
            elif kind == "AWS::ECS::Service" and cluster:
                service = physical.rsplit("/", 1)[-1]
                for page in self.ecs.get_paginator("list_tasks").paginate(cluster=cluster, serviceName=service, desiredStatus="RUNNING"):
                    arns = page["taskArns"]
                    for offset in range(0, len(arns), 100):
                        response = self.ecs.describe_tasks(cluster=cluster, tasks=arns[offset:offset + 100])
                        if response.get("failures"):
                            raise ValueError("Some ECS task metadata could not be read; inventory is incomplete.")
                        for task in response["tasks"]:
                            add("AWS::ECS::Task", task["taskArn"], resource)
                            for attachment in task.get("attachments", []):
                                for detail in attachment.get("details", []):
                                    if detail["name"] == "networkInterfaceId":
                                        add("AWS::EC2::NetworkInterface", detail["value"], resource)
            elif kind == "AWS::EFS::MountTarget":
                for page in self.efs.get_paginator("describe_mount_targets").paginate(MountTargetId=physical):
                    for target in page["MountTargets"]:
                        add("AWS::EC2::NetworkInterface", target["NetworkInterfaceId"], resource)
        return list(found.values())
