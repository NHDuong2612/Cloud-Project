from dataclasses import dataclass
import json
import os

from .catalog import ValidationError


@dataclass(frozen=True)
class Settings:
    table_name: str
    cfn_role_arn: str
    platform: dict
    verified: tuple = ()
    images: dict = None

    @classmethod
    def from_env(cls):
        return cls(
            os.environ["CONTROL_TABLE"], os.environ["CFN_ROLE_ARN"],
            json.loads(os.environ["PLATFORM_PARAMETERS"]),
            tuple(x for x in os.environ.get("VERIFIED_TEMPLATES", "").split(",") if x),
            json.loads(os.environ.get("APPROVED_IMAGES", "{}")),
        )

    def parameters(self, template_id, env_id, config):
        # A fixed mapping prevents passing role/subnet/template URL overrides.
        keys = {
            "instance_type": "InstanceType", "volume_gb": "VolumeSize", "allowed_cidr": "AllowedCidr",
            "db_instance_class": "DBInstanceClass", "db_storage_gb": "DBStorage",
            "min_instances": "MinInstances", "desired_instances": "DesiredInstances", "max_instances": "MaxInstances",
            "target_cpu": "TargetCPU", "cpu": "Cpu", "memory_mb": "Memory", "desired_tasks": "DesiredTasks",
        }
        values = {**self.platform, "EnvironmentId": env_id, **{keys[k]: str(v) for k, v in config.items() if k in keys}}
        if template_id in ("T04", "T06"):
            for key in ("CertificateArn", "HostedZoneId", "BaseDomain"):
                if not values.get(key):
                    raise ValidationError(f"Platform is missing {key}.")
            values["DomainName"] = f"{env_id}.{values.pop('BaseDomain')}"
        if template_id == "T06":
            image = (self.images or {}).get(config["image_alias"])
            if not image:
                raise ValidationError("Container image alias has not been approved.")
            import re
            if not re.fullmatch(r"\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/[a-z0-9._/-]+@sha256:[a-f0-9]{64}", image):
                raise ValidationError("Approved image must be an ECR SHA256 digest URI.")
            values["ContainerImage"] = image
        return values
