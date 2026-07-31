import json
from typing import Any

from app.services.device_command import SUPPORTED_ACTIONS_BY_DEVICE_TYPE


SUPPORTED_RULE_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "changed"}


class RulePayloadError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def parse_condition_json(raw: str) -> dict[str, Any]:
    try:
        condition = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RulePayloadError("invalid_condition_json") from exc

    if not isinstance(condition, dict):
        raise RulePayloadError("invalid_condition_json")

    _validate_condition_node(condition)
    return condition


def parse_action_json(raw: str) -> list[dict[str, Any]]:
    try:
        actions = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RulePayloadError("invalid_action_json") from exc

    if not isinstance(actions, list):
        raise RulePayloadError("invalid_action_json")

    for action in actions:
        if not isinstance(action, dict):
            raise RulePayloadError("invalid_action_json")

        device_type = action.get("device_type")
        action_name = action.get("action")
        params = action.get("params", {})

        if not isinstance(device_type, str) or not device_type.strip():
            raise RulePayloadError("invalid_action_json")
        if not isinstance(action_name, str) or not action_name.strip():
            raise RulePayloadError("invalid_action_json")
        if device_type not in SUPPORTED_ACTIONS_BY_DEVICE_TYPE:
            raise RulePayloadError("invalid_action_json")
        if action_name not in SUPPORTED_ACTIONS_BY_DEVICE_TYPE[device_type]:
            raise RulePayloadError("invalid_action_json")
        if "room_id" in action and not isinstance(action["room_id"], str):
            raise RulePayloadError("invalid_action_json")
        if "device_id" in action and not isinstance(action["device_id"], int):
            raise RulePayloadError("invalid_action_json")
        if not isinstance(params, dict):
            raise RulePayloadError("invalid_action_json")

    return actions


def normalize_condition_json(raw: str) -> str:
    condition = parse_condition_json(raw)
    return json.dumps(condition, separators=(",", ":"))


def normalize_action_json(raw: str) -> str:
    actions = parse_action_json(raw)
    return json.dumps(actions, separators=(",", ":"))


def _validate_condition_node(condition: dict[str, Any]):
    trigger = condition.get("trigger")
    field = condition.get("field")
    operator = condition.get("operator")

    if not isinstance(trigger, str) or not trigger.strip():
        raise RulePayloadError("invalid_condition_json")
    if not isinstance(field, str) or not field.strip():
        raise RulePayloadError("invalid_condition_json")
    if not isinstance(operator, str) or operator not in SUPPORTED_RULE_OPERATORS:
        raise RulePayloadError("invalid_condition_json")
    if "value" not in condition:
        raise RulePayloadError("invalid_condition_json")

    and_conditions = condition.get("and", [])
    if not isinstance(and_conditions, list):
        raise RulePayloadError("invalid_condition_json")

    for sub_condition in and_conditions:
        if not isinstance(sub_condition, dict):
            raise RulePayloadError("invalid_condition_json")
        _validate_condition_node(sub_condition)
