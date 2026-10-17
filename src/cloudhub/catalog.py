"""Versioned input contracts. Infrastructure identifiers are never user inputs."""

from copy import deepcopy
from dataclasses import dataclass
from ipaddress import ip_network
from pathlib import Path
import re


class ValidationError(ValueError):
    """A safe message that may be returned through the CloudHub API."""


def integer(default, minimum, maximum, **extra):
    return {"type": "integer", "default": default, "minimum": minimum, "maximum": maximum, **extra}


def choice(default, values):
    return {"type": "string", "default": default, "enum": values}


COMPUTE = {
    "instance_type": choice("t3.micro", ["t3.micro", "t3.small"]),
    "volume_gb": integer(16, 8, 64),
}
DATABASE = {
    "db_instance_class": choice("db.t3.micro", ["db.t3.micro", "db.t4g.micro"]),
    "db_storage_gb": integer(20, 20, 100),
}
ACCESS = {"allowed_cidr": {"type": "string", "format": "ipv4-cidr", "description": "Client IPv4 network, /24 or narrower."}}


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    owner: str
    properties: dict
    required: tuple = ()
    backup_scope: str = "Pending TV4 handler"
    version: str = "1.0.0"

    @property
    def path(self):
        return Path(__file__).parent / "templates" / f"{self.id.lower()}-{self.version}.json"

    @property
    def schema(self):
        return {"type": "object", "additionalProperties": False, "properties": deepcopy(self.properties), "required": list(self.required)}

    def public(self, verified=()):
        return {
            "id": self.id, "version": self.version, "name": self.name, "owner": self.owner,
            "implemented": self.path.is_file(), "available": self.path.is_file() and f"{self.id}@{self.version}" in verified,
            "schema": self.schema, "backup_scope": self.backup_scope,
            "actions": ["create", "inspect", "plan_update", "delete"] if self.path.is_file() else [],
        }


TEMPLATES = {
    "T01": Template("T01", "Máy Linux", "TV3", COMPUTE, backup_scope="EBS root volume; snapshot and restore supplied by TV4"),
    "T02": Template("T02", "Website tĩnh", "TV4", {}),
    "T03": Template("T03", "Web và cơ sở dữ liệu", "TV3", {**COMPUTE, **DATABASE, **ACCESS}, ("allowed_cidr",), "RDS application data; TV4 snapshot/restore, application code is reproducible"),
    "T04": Template("T04", "Web chịu tải cao", "TV3", {
        **COMPUTE, **DATABASE, **ACCESS, "min_instances": integer(1, 1, 3),
        "desired_instances": integer(1, 1, 3), "max_instances": integer(2, 1, 3),
        "target_cpu": integer(50, 20, 80),
    }, ("allowed_cidr",), "RDS application data; EC2 fleet is stateless"),
    "T05": Template("T05", "Website trên máy chủ", "TV1/TV3", {**COMPUTE, **ACCESS}, ("allowed_cidr",), "EBS web content; TV4 backup/restore"),
    "T06": Template("T06", "Ứng dụng Docker", "TV3", {
        **ACCESS, "image_alias": {"type": "string", "pattern": "^[a-z][a-z0-9-]{0,31}$"},
        "cpu": integer(256, 256, 512, enum=[256, 512]),
        "memory_mb": integer(512, 512, 2048, enum=[512, 1024, 2048]),
        "desired_tasks": integer(1, 1, 2),
    }, ("allowed_cidr", "image_alias"), "Only the registered per-environment S3 prefix; container writable layers are ephemeral"),
    "T07": Template("T07", "Kho file và chia sẻ", "TV2", {}),
    "T08": Template("T08", "Ổ đĩa dùng chung", "TV4", {}),
    "T09": Template("T09", "API serverless", "TV2", {}),
    "T10": Template("T10", "Kho dữ liệu phân tích", "TV4", {}),
}


def get_template(template_id, version):
    template = TEMPLATES.get(template_id)
    if template is None or version != template.version:
        raise ValidationError("Unknown template or template version.")
    return template


def require_available(template_id, version, verified):
    template = get_template(template_id, version)
    if not template.public(verified)["available"]:
        raise ValidationError("Template is not enabled: AWS lifecycle verification is required.")
    return template


def validate_config(template_id, version, config):
    template = get_template(template_id, version)
    if not isinstance(config, dict):
        raise ValidationError("Configuration must be an object.")
    if set(config) - set(template.properties):
        raise ValidationError("Configuration contains unsupported fields.")
    result = deepcopy(config)
    for name, rule in template.properties.items():
        if name not in result and "default" in rule:
            result[name] = deepcopy(rule["default"])
        if name not in result:
            if name in template.required:
                raise ValidationError(f"Missing field: {name}.")
            continue
        value = result[name]
        if rule["type"] == "integer":
            if type(value) is not int or not rule["minimum"] <= value <= rule["maximum"]:
                raise ValidationError(f"Invalid range or type: {name}.")
        elif type(value) is not str or len(value) > 256:
            raise ValidationError(f"Invalid string: {name}.")
        if "enum" in rule and value not in rule["enum"]:
            raise ValidationError(f"Value is not approved: {name}.")
        if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
            raise ValidationError(f"Invalid format: {name}.")
        if rule.get("format") == "ipv4-cidr":
            try:
                network = ip_network(value, strict=True)
            except ValueError as exc:
                raise ValidationError("Invalid allowed_cidr.") from exc
            if network.version != 4 or network.prefixlen < 24:
                raise ValidationError("allowed_cidr must be IPv4 /24 or narrower.")
    if template_id == "T04" and not result["min_instances"] <= result["desired_instances"] <= result["max_instances"]:
        raise ValidationError("Scaling requires min <= desired <= max.")
    if template_id == "T06" and result["cpu"] == 512 and result["memory_mb"] < 1024:
        raise ValidationError("512 CPU units require at least 1024 MB memory.")
    return result
