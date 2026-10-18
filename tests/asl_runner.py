"""Offline runner for the JSONPath ASL subset used by this repository.

Exercises checked-in transitions and Retry/Catch with virtual time. It is not
an AWS Step Functions emulator and does not prove service/IAM behavior.
"""
import json
from pathlib import Path


class AslRunner:
    def __init__(self, invoke, clock):
        self.workflow = json.loads(Path("workflow/deploy.asl.json").read_text(encoding="utf-8"))
        self.invoke, self.clock, self.trace = invoke, clock, []

    def run(self, data, max_transitions=400):
        name = self.workflow["StartAt"]
        for _ in range(max_transitions):
            state = self.workflow["States"][name]
            self.trace.append(name)
            kind = state["Type"]
            if kind in {"Succeed", "Fail"}:
                return kind == "Succeed"
            if kind == "Task":
                payload = {}
                for key, value in state["Parameters"]["Payload"].items():
                    payload[key[:-2] if key.endswith(".$") else key] = data[value[2:]] if key.endswith(".$") else value
                attempts = 0
                while True:
                    try:
                        data = self.invoke(payload)
                        name = state["Next"]
                        break
                    except Exception as exc:
                        retry = next((x for x in state.get("Retry", []) if type(exc).__name__ in x["ErrorEquals"]), None)
                        if retry and attempts < retry["MaxAttempts"]:
                            self.clock[0] += retry["IntervalSeconds"] * retry.get("BackoffRate", 1) ** attempts
                            attempts += 1
                            continue
                        catch = next((x for x in state.get("Catch", []) if "States.ALL" in x["ErrorEquals"]), None)
                        if catch is None:
                            raise
                        assert catch["ResultPath"] is None
                        name = catch["Next"]
                        break
            elif kind == "Wait":
                self.clock[0] += state["Seconds"]
                name = state["Next"]
            elif kind == "Choice":
                choice = next((x for x in state["Choices"] if data.get(x["Variable"][2:]) == x["StringEquals"]), None)
                name = choice["Next"] if choice else state["Default"]
            else:
                raise AssertionError(f"Unsupported ASL state type: {kind}")
            assert self.clock[0] - 1000 < self.workflow["TimeoutSeconds"]
        raise AssertionError("Workflow did not terminate within the transition bound")
