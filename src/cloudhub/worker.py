"""Short, idempotent CloudFormation steps driven by a Standard workflow."""

from functools import lru_cache
from hashlib import sha256
import json
import re
import time

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .catalog import ValidationError, get_template, require_available, validate_config
from .settings import Settings
from .store import DynamoStore
from .inventory import InventoryCollector


class RetryableDeploymentError(RuntimeError):
    pass


def configuration_hash(config):
    return sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


TERMINAL = {"SUCCEEDED", "PREVIEWED", "NO_CHANGES", "FAILED", "REJECTED", "WAITING_F08"}
OUTPUTS = {"InstanceId", "AmiId", "RootDeviceName", "EndpointUrl", "DatabaseIdentifier", "TargetGroupArn", "AutoScalingGroupName", "ServiceArn", "ClusterName", "RegisteredDataPrefix"}


def database_restore_stage(template):
    """PostgreSQL snapshot restore must precede enabling managed credentials."""
    from copy import deepcopy
    result = deepcopy(template)
    database_resources = {"InstanceSecurityGroup", "DatabaseSecurityGroup", "DatabaseIngress", "AppDatabaseEgress", "DatabaseSubnets", "DatabaseParameters", "Database"}
    result["Resources"] = {k: v for k, v in result["Resources"].items() if k in database_resources}
    result["Resources"]["Database"]["Properties"]["ManageMasterUserPassword"] = False
    result["Outputs"] = {"DatabaseIdentifier": template["Outputs"]["DatabaseIdentifier"]}
    result["Description"] = "CloudHub internal database-only PostgreSQL restore stage; F04 enables managed credentials before adding the application."
    used = set()
    def collect(value):
        if isinstance(value, dict):
            if "Ref" in value:
                used.add(value["Ref"])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str):
            used.update(re.findall(r"\$\{([A-Za-z0-9]+)(?:\.[^}]*)?\}", value))
    for section in ("Resources", "Outputs", "Conditions", "Rules"):
        collect(result.get(section, {}))
    result["Parameters"] = {k: v for k, v in result["Parameters"].items() if k in used}
    result["Parameters"]["DBSnapshotIdentifier"].pop("Default", None)
    result["Parameters"]["DBSnapshotIdentifier"]["MinLength"] = 1
    return result


class Worker:
    def __init__(self, store, cfn, ssm, elb, settings, clock=time.time, rds=None, collector=None):
        self.store, self.cfn, self.ssm, self.elb, self.settings, self.clock = store, cfn, ssm, elb, settings, clock
        self.rds = rds
        self.collector = collector

    def records(self, event):
        env_id, op_id = event["environment_id"], event["operation_id"]
        for value in (env_id, op_id):
            if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
                raise ValidationError("Identifiers must be UUID hex strings.")
        env = self.store.get(env_id, "META")
        op = self.store.operation(env_id, op_id)
        if not env or not op or op["owner_id"] != env["owner_id"] or op["operation_id"] != op_id:
            raise ValidationError("Operation or environment ownership is invalid.")
        return env_id, op_id, env, op

    def run(self, event):
        env_id, op_id, env, op = self.records(event)
        phase = event["phase"]
        result = {"environment_id": env_id, "operation_id": op_id, "outcome": "CONTINUE"}
        if op["status"] in TERMINAL and phase != "recover":
            return {**result, "outcome": "DONE"}
        if phase not in {"acquire", "recover"} and env.get("lock_owner") != op_id:
            raise ValidationError("Operation does not own the environment lock.")
        if phase not in ("acquire", "recover", "rollback_poll") and int(self.clock()) - int(op["started_at"]) > 7200:
            raise ValidationError("Deployment deadline exceeded.")
        method = getattr(self, phase, None)
        if method is None or phase not in {"acquire", "prepare", "changeset", "execute", "poll", "post_provision", "health", "complete", "recover", "rollback_poll"}:
            raise ValidationError("Unknown worker phase.")
        return {**result, **method(env_id, op_id, env, op)}

    def acquire(self, env_id, op_id, env, op):
        action = op["action"]
        if action not in {"create", "plan_update", "update", "delete", "renew"}:
            raise ValidationError("Unsupported operation.")
        if int(env["version"]) != int(op["expected_version"]):
            raise ValidationError("Environment version has changed.")
        allowed = {"create": {"REQUESTED", "PROVISIONING"}, "plan_update": {"READY", "PLANNING"}, "update": {"READY", "UPDATING"}, "delete": {"READY", "PAUSED", "FINALIZING", "DELETING"}, "renew": {"READY", "RENEWING"}}
        if env["status"] not in allowed[action] or env.get("lock_owner") not in (None, op_id):
            raise ValidationError("Environment is busy or in an incompatible state.")
        if action != "delete":
            require_available(env["template_id"], env["template_version"], self.settings.verified)
            config = validate_config(env["template_id"], env["template_version"], op.get("config", env["config"]))
            if action == "renew":
                expiry, target, ready = env.get("expires_at_epoch"), op.get("new_expires_at_epoch"), env.get("ready_at")
                if config != env["config"] or any(type(x) is not int for x in (expiry, target, ready)) or op.get("expected_expires_at_epoch") != expiry:
                    raise ValidationError("Renewal must match the current configuration and expiry.")
                if expiry <= int(self.clock()) or not expiry < target <= ready + 480 * 60 or (target - ready) % 60:
                    raise ValidationError("Renewal requires an active session and a total duration of at most eight hours.")
            if action in {"create", "update", "renew"} and not op.get("quota_reservation_id"):
                raise ValidationError("A server-side quota reservation is required.")
            if action in {"create", "update", "renew"}:
                reservation = self.store.get(env_id, f"QUOTA#{op['quota_reservation_id']}")
                expected_hash = configuration_hash({"config": config, "expires_at_epoch": target}) if action == "renew" else configuration_hash(config)
                if not reservation or not all([
                    reservation.get("owner_id") == env["owner_id"], reservation.get("operation_id") == op_id,
                    reservation.get("config_hash") == expected_hash, op.get("config_hash") == expected_hash,
                    reservation.get("status") in {"RESERVED", "CONSUMED"},
                    reservation.get("status") == "CONSUMED" or int(reservation.get("valid_until", 0)) > int(self.clock()),
                ]):
                    raise ValidationError("Quota reservation is missing, expired or does not match configuration.")
            duration = env["duration_minutes"]
            if type(duration) is not int or not 15 <= duration <= 480:
                raise ValidationError("Duration must be 15 to 480 minutes.")
            for key in ("volume_gb", "db_storage_gb"):
                if action != "create" and config.get(key, 0) < env["config"].get(key, 0):
                    raise ValidationError("Storage shrink is not supported.")
            self.settings.parameters(env["template_id"], env_id, config)
            if action == "create":
                self.restore_parameters(env_id, op_id, env)
        else:
            self.check_delete(env_id, op_id, env, op)
        status = {"create": "PROVISIONING", "plan_update": "PLANNING", "update": "UPDATING", "delete": "DELETING", "renew": "RENEWING"}[action]
        self.store.lock(env, op, status, int(self.clock()))
        return {}

    def check_delete(self, env_id, op_id, env, op):
        if env.get("retention_policy") == "purge" and op.get("purge_confirmed") is True:
            return
        job_id = op.get("backup_job_id")
        job = self.store.get(env_id, f"BACKUP#{job_id}") if job_id else None
        if not job or not all([
            job.get("status") == "COMPLETED", job.get("owner_id") == env["owner_id"],
            job.get("source_version") == op["expected_version"], job.get("source_quiesced") is True,
            job.get("operation_id") == op_id, bool(job.get("recovery_point")),
            env.get("write_fence_operation_id") == op_id, env.get("lock_owner") == op_id,
            env.get("status") in {"FINALIZING", "DELETING"},
        ]):
            raise ValidationError("A consistent completed F06 backup is required before deletion.")

    def stack_name(self, env_id):
        return f"cloudhub-env-{env_id}"

    def restore_parameters(self, env_id, op_id, env):
        job_id = env.get("restore_job_id")
        if not job_id:
            return {}
        job = self.store.get(env_id, f"RESTORE#{job_id}")
        if not job or not all([
            job.get("status") == "APPROVED", job.get("owner_id") == env["owner_id"],
            job.get("operation_id") == op_id, job.get("ownership_verified") is True,
            job.get("template_id") == env["template_id"], job.get("template_version") == env["template_version"],
        ]):
            raise ValidationError("An owned, approved F06 restore job is required.")
        parameters = job.get("parameters", {})
        allowed = {"T01": {"RootSnapshotId", "SourceAmiId"}, "T05": {"RootSnapshotId", "SourceAmiId"}, "T03": {"DBSnapshotIdentifier"}, "T04": {"DBSnapshotIdentifier"}}.get(env["template_id"], set())
        if not parameters or set(parameters) != allowed or any(type(v) is not str or not 1 <= len(v) <= 256 for v in parameters.values()):
            raise ValidationError("Unsupported restore parameters.")
        return parameters

    def stack(self, env_id, op):
        name = op.get("stack_id", self.stack_name(env_id))
        try:
            stack = self.cfn.describe_stacks(StackName=name)["Stacks"][0]
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ValidationError" and "does not exist" in exc.response["Error"].get("Message", ""):
                return None
            raise
        tags = {x["Key"]: x["Value"] for x in stack.get("Tags", [])}
        if tags.get("CloudHubEnvironmentId") != env_id or tags.get("Project") != "CloudHub":
            raise ValidationError("Stack ownership tags do not match.")
        return stack

    def inventory(self, env_id, op_id, stack_id):
        pages = self.cfn.get_paginator("list_stack_resources").paginate(StackName=stack_id)
        resources = []
        for page in pages:
            resources.extend(page["StackResourceSummaries"])
            self.store.inventory(env_id, op_id, page["StackResourceSummaries"], int(self.clock()))
        if self.collector is not None:
            self.store.inventory(env_id, op_id, self.collector.expand(resources), int(self.clock()))

    def prepare(self, env_id, op_id, env, op):
        action = op["action"]
        if action == "renew":
            target = op["new_expires_at_epoch"]
            self.store.finish(env, op, "READY", "SUCCEEDED", int(self.clock()), expires_at_epoch=target, duration_minutes=(target - env["ready_at"]) // 60)
            return {"outcome": "DONE"}
        if action == "delete":
            stack = self.stack(env_id, op)
            if not stack:
                return {"outcome": "DELETED"}
            self.inventory(env_id, op_id, stack["StackId"])
            self.store.patch_operation(env_id, op_id, stack_id=stack["StackId"])
            self.cfn.delete_stack(StackName=stack["StackId"], RoleARN=self.settings.cfn_role_arn, ClientRequestToken=op_id)
            return {"outcome": "POLL"}
        if action == "update":
            preview = self.store.operation(env_id, op.get("preview_operation_id", ""))
            if not preview or preview.get("status") != "PREVIEWED" or preview.get("expected_version") != op["expected_version"] or preview.get("owner_id") != env["owner_id"]:
                raise ValidationError("A current, owned change-set preview is required.")
            if preview["config"] != op.get("config") or op.get("confirmed_change_set_id") != preview["change_set_id"]:
                raise ValidationError("Confirmed configuration does not match the preview.")
            self.store.patch_operation(env_id, op_id, change_set_id=preview["change_set_id"], stack_id=preview["stack_id"])
            return {}
        template = get_template(env["template_id"], env["template_version"])
        config = validate_config(template.id, template.version, op.get("config", env["config"]))
        body = template.path.read_text(encoding="utf-8")
        schema = json.loads(body)
        if action == "create" and env.get("restore_job_id") and template.id in {"T03", "T04"}:
            schema = database_restore_stage(schema)
            body = json.dumps(schema)
        parameters = self.settings.parameters(template.id, env_id, config)
        if action == "create":
            parameters.update(self.restore_parameters(env_id, op_id, env))
        else:
            parameters.update(env.get("restore_parameters", {}))
        required = {k for k, v in schema["Parameters"].items() if "Default" not in v}
        if required - set(parameters):
            raise ValidationError("Platform configuration is missing required template parameters.")
        request = {
            "StackName": self.stack_name(env_id), "ChangeSetName": f"op-{op_id}",
            "ChangeSetType": "CREATE" if action == "create" else "UPDATE", "TemplateBody": body,
            "Parameters": [{"ParameterKey": k, "ParameterValue": str(v)} for k, v in parameters.items() if k in schema["Parameters"]],
            "Capabilities": ["CAPABILITY_NAMED_IAM"], "RoleARN": self.settings.cfn_role_arn, "ClientToken": op_id,
            "Tags": [{"Key": k, "Value": v} for k, v in {"Project": "CloudHub", "CloudHubEnvironmentId": env_id, "OwnerId": env["owner_id"], "TemplateVersion": f"{template.id}@{template.version}"}.items()],
        }
        try:
            response = self.cfn.create_change_set(**request)
        except self.cfn.exceptions.AlreadyExistsException:
            response = self.cfn.describe_change_set(StackName=request["StackName"], ChangeSetName=request["ChangeSetName"])
            response = {"Id": response["ChangeSetId"], "StackId": response["StackId"]}
        self.store.patch_operation(env_id, op_id, change_set_id=response["Id"], stack_id=response["StackId"], config=config)
        return {}

    def changeset(self, env_id, op_id, env, op):
        change = self.cfn.describe_change_set(ChangeSetName=op["change_set_id"])
        status = change["Status"]
        if status in {"CREATE_PENDING", "CREATE_IN_PROGRESS"}:
            return {"outcome": "WAIT"}
        if status == "FAILED":
            reason = change.get("StatusReason", "")
            if op["action"] != "create" and ("didn't contain changes" in reason or "No updates" in reason):
                self.store.finish(env, op, "READY", "NO_CHANGES", int(self.clock()), bump_version=False)
                return {"outcome": "DONE"}
            raise ValidationError("CloudFormation change-set creation failed; review AWS events.")
        if status != "CREATE_COMPLETE":
            raise ValidationError("Change set is not executable.")
        changes = [x.get("ResourceChange", {}) for x in change.get("Changes", [])]
        if (op["action"] != "create" or op.get("deployment_stage") == "application") and any(x.get("Replacement") in {"True", "Conditional"} and x.get("ResourceType") != "AWS::ECS::TaskDefinition" for x in changes):
            raise ValidationError("Resource replacement requires a separate restore/migration workflow.")
        if op["action"] == "plan_update":
            summary = [{k: x[k] for k in ("LogicalResourceId", "ResourceType", "Action", "Replacement") if k in x} for x in changes]
            self.store.patch_operation(env_id, op_id, changes=summary)
            self.store.finish(env, op, "READY", "PREVIEWED", int(self.clock()), bump_version=False)
            return {"outcome": "DONE"}
        return {}

    def execute(self, env_id, op_id, env, op):
        change = self.cfn.describe_change_set(ChangeSetName=op["change_set_id"])
        if change.get("ExecutionStatus") not in {"EXECUTE_IN_PROGRESS", "EXECUTE_COMPLETE"}:
            self.cfn.execute_change_set(ChangeSetName=op["change_set_id"], ClientRequestToken=f"{op_id}-{op.get('deployment_stage', 'initial')}")
        return {}

    def poll(self, env_id, op_id, env, op):
        stack = self.stack(env_id, op)
        if not stack:
            if op["action"] == "delete":
                return {"outcome": "DELETED"}
            raise ValidationError("Environment stack is missing.")
        status = stack["StackStatus"]
        if status.endswith("_IN_PROGRESS") or status == "REVIEW_IN_PROGRESS":
            return {"outcome": "WAIT"}
        self.inventory(env_id, op_id, stack["StackId"])
        if op["action"] == "delete":
            if status == "DELETE_COMPLETE":
                return {"outcome": "DELETED"}
            raise ValidationError("Stack deletion failed; retained resources require review.")
        if status not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
            raise ValidationError("Stack provisioning failed; inspect CloudFormation events.")
        outputs = {x["OutputKey"]: x["OutputValue"] for x in stack.get("Outputs", []) if x["OutputKey"] in OUTPUTS}
        self.store.patch_operation(env_id, op_id, outputs=outputs)
        return {}

    def post_provision(self, env_id, op_id, env, op):
        if op["action"] != "create" or not env.get("restore_job_id") or env["template_id"] not in {"T03", "T04"} or op.get("deployment_stage") == "application":
            return {}
        identifier = op["outputs"]["DatabaseIdentifier"]
        if not op.get("password_management_requested"):
            self.rds.modify_db_instance(DBInstanceIdentifier=identifier, ManageMasterUserPassword=True, ApplyImmediately=True)
            self.store.patch_operation(env_id, op_id, password_management_requested=True)
            return {"outcome": "WAIT"}
        database = self.rds.describe_db_instances(DBInstanceIdentifier=identifier)["DBInstances"][0]
        secret_status = database.get("MasterUserSecret", {}).get("SecretStatus")
        if secret_status == "impaired":
            raise ValidationError("Restored database credential management needs review.")
        if database["DBInstanceStatus"] != "available" or secret_status != "active":
            return {"outcome": "WAIT"}
        template = get_template(env["template_id"], env["template_version"])
        schema = json.loads(template.path.read_text(encoding="utf-8"))
        parameters = self.settings.parameters(template.id, env_id, op["config"])
        parameters.update(self.restore_parameters(env_id, op_id, env))
        request = {
            "StackName": op["stack_id"], "ChangeSetName": f"op-{op_id}-app", "ChangeSetType": "UPDATE", "TemplateBody": json.dumps(schema),
            "Parameters": [{"ParameterKey": k, "ParameterValue": str(v)} for k, v in parameters.items() if k in schema["Parameters"]],
            "Capabilities": ["CAPABILITY_NAMED_IAM"], "RoleARN": self.settings.cfn_role_arn, "ClientToken": f"{op_id}-app",
        }
        try:
            response = self.cfn.create_change_set(**request)
        except self.cfn.exceptions.AlreadyExistsException:
            response = self.cfn.describe_change_set(StackName=request["StackName"], ChangeSetName=request["ChangeSetName"])
            response = {"Id": response["ChangeSetId"], "StackId": response["StackId"]}
        self.store.patch_operation(env_id, op_id, change_set_id=response["Id"], deployment_stage="application")
        return {"outcome": "CHANGESET"}

    def health(self, env_id, op_id, env, op):
        if not op.get("health_started"):
            self.store.patch_operation(env_id, op_id, health_started=int(self.clock()))
        elif int(self.clock()) - int(op["health_started"]) > 600:
            raise ValidationError("Readiness check exceeded ten minutes.")
        outputs = op.get("outputs", {})
        if "TargetGroupArn" in outputs:
            targets = self.elb.describe_target_health(TargetGroupArn=outputs["TargetGroupArn"])["TargetHealthDescriptions"]
            config = op.get("config", env["config"])
            expected = config.get("desired_instances", config.get("desired_tasks", 1))
            healthy = sum(x["TargetHealth"]["State"] == "healthy" for x in targets)
            return {"outcome": "HEALTHY" if healthy >= expected else "WAIT"}
        instance_id = outputs.get("InstanceId")
        if not instance_id:
            raise ValidationError("Template has no supported readiness probe.")
        nodes = self.ssm.describe_instance_information(Filters=[{"Key": "InstanceIds", "Values": [instance_id]}])["InstanceInformationList"]
        if not nodes or nodes[0]["PingStatus"] != "Online":
            return {"outcome": "WAIT"}
        if env["template_id"] == "T01":
            return {"outcome": "HEALTHY"}
        command_id = op.get("health_command_id")
        if not command_id:
            response = self.ssm.send_command(InstanceIds=[instance_id], DocumentName="AWS-RunShellScript", Parameters={"commands": ["curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8080/health"]}, TimeoutSeconds=30)
            self.store.patch_operation(env_id, op_id, health_command_id=response["Command"]["CommandId"])
            return {"outcome": "WAIT"}
        try:
            invocation = self.ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        except self.ssm.exceptions.InvocationDoesNotExist:
            return {"outcome": "WAIT"}
        if invocation["Status"] in {"Pending", "InProgress", "Delayed"}:
            return {"outcome": "WAIT"}
        if invocation["Status"] != "Success":
            self.store.patch_operation(env_id, op_id, health_command_id="")
            return {"outcome": "WAIT"}
        return {"outcome": "HEALTHY"}

    def complete(self, env_id, op_id, env, op):
        now = int(self.clock())
        if op["action"] == "delete":
            self.store.finish(env, op, "AWAITING_VERIFICATION", "WAITING_F08", now, keep_lock=True, bump_version=False)
        else:
            fields = {"stack_id": op["stack_id"], "outputs": op.get("outputs", {}), "config": op.get("config", env["config"])}
            if op["action"] == "create":
                fields.update(ready_at=now, expires_at_epoch=now + int(env["duration_minutes"]) * 60)
                fields["restore_parameters"] = self.restore_parameters(env_id, op_id, env)
            self.store.finish(env, op, "READY", "SUCCEEDED", now, **fields)
        return {"outcome": "DONE"}

    def recover(self, env_id, op_id, env, op):
        if env.get("lock_owner") != op_id:
            # A rejected competing request must never unlock or alter another job.
            if op["status"] not in TERMINAL:
                self.store.patch_operation(env_id, op_id, status="REJECTED", error_code="REQUEST_REJECTED")
            return {"outcome": "DONE"}
        stack = self.stack(env_id, op)
        if stack:
            self.inventory(env_id, op_id, stack["StackId"])
        if op["action"] == "create" and stack and stack["StackStatus"] != "DELETE_COMPLETE":
            self.cfn.delete_stack(StackName=stack["StackId"], RoleARN=self.settings.cfn_role_arn, ClientRequestToken=f"rollback-{op_id}")
            self.store.patch_operation(env_id, op_id, rollback_started=int(self.clock()), stack_id=stack["StackId"])
            return {"outcome": "WAIT"}
        self.store.finish(env, op, "NEEDS_ATTENTION", "FAILED", int(self.clock()))
        return {"outcome": "DONE"}

    def rollback_poll(self, env_id, op_id, env, op):
        stack = self.stack(env_id, op)
        if stack and stack["StackStatus"].endswith("_IN_PROGRESS") and int(self.clock()) - int(op.get("rollback_started", 0)) < 1800:
            return {"outcome": "WAIT"}
        if stack:
            self.inventory(env_id, op_id, stack["StackId"])
        self.store.finish(env, op, "NEEDS_ATTENTION", "FAILED", int(self.clock()))
        return {"outcome": "DONE"}


@lru_cache(maxsize=1)
def runtime():
    settings = Settings.from_env()
    config = Config(retries={"mode": "standard", "total_max_attempts": 3}, connect_timeout=5, read_timeout=20)
    session = boto3.Session()
    collector = InventoryCollector(session.client("ec2", config=config), session.client("autoscaling", config=config), session.client("ecs", config=config), session.client("efs", config=config))
    return Worker(DynamoStore(session.resource("dynamodb", config=config).Table(settings.table_name)), session.client("cloudformation", config=config), session.client("ssm", config=config), session.client("elbv2", config=config), settings, rds=session.client("rds", config=config), collector=collector)


def handler(event, context):
    worker = runtime()
    error_message = "Operation could not be completed; review its status and inventory."
    try:
        return worker.run(event)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        transient_transaction = code == "TransactionCanceledException" and any(x.get("Code") in {"TransactionConflict", "ProvisionedThroughputExceeded", "ThrottlingError"} for x in exc.response.get("CancellationReasons", []))
        if transient_transaction or code in {"Throttling", "ThrottlingException", "TooManyRequestsException", "RequestLimitExceeded", "TransactionInProgressException"}:
            raise RetryableDeploymentError("AWS_RETRYABLE") from None
        error_code = "AWS_" + re.sub(r"[^A-Za-z0-9_]", "", code)[:64]
    except ValidationError as exc:
        error_code = "INVALID_OPERATION_OR_STATE"
        error_message = str(exc)[:256]
    except (KeyError, TypeError, ValueError):
        error_code = "INVALID_OPERATION_OR_STATE"
    except BotoCoreError:
        raise RetryableDeploymentError("AWS_TRANSPORT_RETRYABLE") from None
    # Never put AWS raw messages or command output in execution history.
    if re.fullmatch(r"[a-f0-9]{32}", str(event.get("environment_id", ""))) and re.fullmatch(r"[a-f0-9]{32}", str(event.get("operation_id", ""))):
        try:
            worker.records(event)
            worker.store.patch_operation(event["environment_id"], event["operation_id"], error_code=error_code, error_message=error_message)
        except (ClientError, ValidationError, KeyError, TypeError, ValueError):
            pass
    return {"environment_id": event.get("environment_id", ""), "operation_id": event.get("operation_id", ""), "outcome": "ERROR", "error_code": error_code}


def reconcile_handler(event, context):
    """A stopped execution may leave AWS operations active: require manual review."""
    import os
    detail = event["detail"]
    if detail.get("stateMachineArn") != os.environ["STATE_MACHINE_ARN"] or detail.get("status") not in {"FAILED", "TIMED_OUT", "ABORTED"}:
        return
    execution = boto3.client("stepfunctions").describe_execution(executionArn=detail["executionArn"])
    data = json.loads(execution["input"])
    worker = runtime()
    _, _, env, op = worker.records(data)
    if op["status"] not in TERMINAL and env.get("lock_owner") == op["operation_id"]:
        worker.store.patch_operation(data["environment_id"], data["operation_id"], error_code="EXECUTION_INTERRUPTED")
        worker.store.finish(env, op, "NEEDS_ATTENTION", "FAILED", int(time.time()))
