"""TV2 calls this after storing the authenticated request and quota reservation."""

import json
import re

from .catalog import ValidationError


def start_execution(client, workflow_arn, environment_id, operation_id):
    if any(not isinstance(x, str) or not re.fullmatch(r"[a-f0-9]{32}", x) for x in (environment_id, operation_id)):
        raise ValidationError("Identifiers must be UUID hex strings.")
    payload = json.dumps({"environment_id": environment_id, "operation_id": operation_id}, separators=(",", ":"))
    try:
        execution = client.start_execution(stateMachineArn=workflow_arn, name=operation_id, input=payload)
    except client.exceptions.ExecutionAlreadyExists:
        return {"status_code": 202, "operation_id": operation_id, "already_submitted": True}
    return {"status_code": 202, "operation_id": operation_id, "execution_arn": execution["executionArn"]}
