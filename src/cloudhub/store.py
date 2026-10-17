"""Atomic environment/operation transitions in the shared F05 control table."""

from hashlib import sha256
from decimal import Decimal


def native(value):
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise ValueError("Non-integral control value")
        return int(value)
    if isinstance(value, dict):
        return {k: native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [native(x) for x in value]
    return value


class DynamoStore:
    def __init__(self, table):
        self.table = table
        self.client = table.meta.client

    def get(self, env_id, sort_key):
        return native(self.table.get_item(Key={"pk": f"ENV#{env_id}", "sk": sort_key}, ConsistentRead=True).get("Item"))

    def operation(self, env_id, op_id):
        return self.get(env_id, f"OP#{op_id}")

    def lock(self, env, op, status, now):
        transactions = [
            {"Update": {
                "TableName": self.table.name, "Key": {"pk": env["pk"], "sk": "META"},
                "UpdateExpression": "SET lock_owner=:op, #s=:status, updated_at=:now",
                "ConditionExpression": "#v=:version AND owner_id=:owner AND (#s=:initial OR lock_owner=:op) AND (attribute_not_exists(lock_owner) OR lock_owner=:op)",
                "ExpressionAttributeNames": {"#v": "version", "#s": "status"},
                "ExpressionAttributeValues": {":version": op["expected_version"], ":owner": op["owner_id"], ":op": op["operation_id"], ":status": status, ":initial": env["status"], ":now": now},
            }},
            {"Update": {
                "TableName": self.table.name, "Key": {"pk": env["pk"], "sk": op["sk"]},
                "UpdateExpression": "SET #s=:running, started_at=if_not_exists(started_at,:now)",
                "ConditionExpression": "owner_id=:owner AND (#s=:queued OR #s=:running)",
                "ExpressionAttributeNames": {"#s": "status"},
                "ExpressionAttributeValues": {":owner": op["owner_id"], ":queued": "QUEUED", ":running": "RUNNING", ":now": now},
            }},
        ]
        if op["action"] in {"create", "update"}:
            transactions.append({"Update": {
                "TableName": self.table.name, "Key": {"pk": env["pk"], "sk": f"QUOTA#{op['quota_reservation_id']}"},
                "UpdateExpression": "SET #s=:consumed",
                "ConditionExpression": "owner_id=:owner AND operation_id=:op AND config_hash=:hash AND ((#s=:reserved AND valid_until>:now) OR #s=:consumed)",
                "ExpressionAttributeNames": {"#s": "status"},
                "ExpressionAttributeValues": {":owner": op["owner_id"], ":op": op["operation_id"], ":hash": op["config_hash"], ":reserved": "RESERVED", ":consumed": "CONSUMED", ":now": now},
            }})
        self.client.transact_write_items(TransactItems=transactions)

    def patch_operation(self, env_id, op_id, **fields):
        names = {f"#k{i}": key for i, key in enumerate(fields)}
        values = {f":v{i}": value for i, value in enumerate(fields.values())}
        self.table.update_item(
            Key={"pk": f"ENV#{env_id}", "sk": f"OP#{op_id}"},
            UpdateExpression="SET " + ", ".join(f"#k{i}=:v{i}" for i in range(len(fields))),
            ExpressionAttributeNames=names, ExpressionAttributeValues=values,
            ConditionExpression="attribute_exists(pk)",
        )

    def finish(self, env, op, env_status, op_status, now, *, keep_lock=False, bump_version=True, **fields):
        fields = {**fields, "status": env_status, "updated_at": now}
        names = {f"#k{i}": key for i, key in enumerate(fields)}
        values = {f":v{i}": value for i, value in enumerate(fields.values())}
        values[":op"] = op["operation_id"]
        expression = "SET " + ", ".join(f"#k{i}=:v{i}" for i in range(len(fields)))
        if bump_version:
            expression += ", #version=#version+:one"
            names["#version"] = "version"
            values[":one"] = 1
        if not keep_lock:
            expression += " REMOVE lock_owner"
        self.client.transact_write_items(TransactItems=[
            {"Update": {
                "TableName": self.table.name, "Key": {"pk": env["pk"], "sk": "META"},
                "UpdateExpression": expression, "ConditionExpression": "lock_owner=:op",
                "ExpressionAttributeNames": names, "ExpressionAttributeValues": values,
            }},
            {"Update": {
                "TableName": self.table.name, "Key": {"pk": env["pk"], "sk": op["sk"]},
                "UpdateExpression": "SET #s=:status, finished_at=:now",
                "ExpressionAttributeNames": {"#s": "status"},
                "ExpressionAttributeValues": {":status": op_status, ":now": now},
            }},
        ])

    def inventory(self, env_id, op_id, resources, now):
        with self.table.batch_writer() as writer:
            for resource in resources:
                physical = resource.get("PhysicalResourceId", "")
                writer.put_item(Item={
                    "pk": f"ENV#{env_id}", "sk": "RESOURCE#" + sha256((resource["LogicalResourceId"] + physical).encode()).hexdigest(),
                    "operation_id": op_id, "logical_id": resource["LogicalResourceId"],
                    "resource_type": resource["ResourceType"], "physical_id": physical,
                    "aws_status": resource["ResourceStatus"], "observed_at": now,
                    "parent_physical_id": resource.get("ParentPhysicalId", ""),
                })
