"""
Rule engine for evaluating sensor-triggered automation rules.
"""
import json
import logging
import threading
from typing import Any

from app.database.connection import get_db
from app.services import mqtt_client
from app.services.activity_log import write_activity
from app.services.device_command import execute_device_command
from app.services.device_state_projection import device_state_projection
from app.services.rule_payloads import (
    RulePayloadError,
    parse_action_json,
    parse_condition_json,
)

logger = logging.getLogger(__name__)


def load_projection_states() -> dict[int, dict[str, Any]]:
    with get_db() as conn:
        devices = conn.execute("SELECT id, status_json FROM devices").fetchall()

    states: dict[int, dict[str, Any]] = {}
    for device in devices:
        try:
            status = json.loads(device["status_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            status = None
        if not isinstance(status, dict):
            logger.warning(
                "invalid device status_json for projection: device_id=%s",
                device["id"],
            )
            status = {}
        states[device["id"]] = status
    return states


class RuleEngine:
    """In-memory rule engine singleton."""

    def __init__(self):
        self._rules: list[dict] = []
        self._device_id_map: dict[str, int] = {}
        self._lock = threading.Lock()

    def reload_rules(self):
        """Reload enabled rules and pre-parse executable payloads."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM automation_rules WHERE enabled = 1"
            ).fetchall()
            devices = conn.execute(
                "SELECT id, type, mqtt_topic FROM devices"
            ).fetchall()

        compiled_rules: list[dict] = []
        skipped_rules = 0
        for row in rows:
            rule = dict(row)
            try:
                rule["condition"] = parse_condition_json(rule["condition_json"])
                rule["actions"] = parse_action_json(rule["action_json"])
            except RulePayloadError as exc:
                skipped_rules += 1
                logger.warning("skipped invalid rule payload [%s]: %s", rule["name"], exc.code)
                continue
            compiled_rules.append(rule)

        device_id_map: dict[str, int] = {}
        for device in devices:
            parts = device["mqtt_topic"].split("/")
            if len(parts) >= 3:
                key = f"{parts[1]}/{parts[2]}"
                device_id_map[key] = device["id"]

        with self._lock:
            self._rules = compiled_rules
            self._device_id_map = device_id_map
            device_state_projection.rebuild(load_projection_states)

        logger.info(
            "rule engine loaded %s rules, %s device indexes, skipped=%s",
            len(compiled_rules),
            len(device_id_map),
            skipped_rules,
        )

    def _get_device_id(self, room_id: str, device_type: str) -> int | None:
        key = f"{room_id}/{device_type}"
        with self._lock:
            return self._device_id_map.get(key)

    def on_sensor_data(self, topic: str, payload: Any):
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return

        parts = topic.split("/")
        if len(parts) < 3:
            return
        room_id = parts[1]
        sensor_type = parts[2]

        with self._lock:
            rules = list(self._rules)

        for rule in rules:
            try:
                condition = rule["condition"]
                if self._evaluate(condition, sensor_type, payload, room_id):
                    actions = rule["actions"]
                    self._execute_actions(actions, room_id)
                    logger.info("rule triggered: %s", rule["name"])
                    write_activity(
                        event_type="rule",
                        title=rule["name"],
                        detail=json.dumps(
                            {"room_id": room_id, "trigger": sensor_type},
                            ensure_ascii=False,
                        ),
                        source="rules.trigger",
                    )
            except Exception as exc:
                logger.error("rule execution failed [%s]: %s", rule["name"], exc)

    def _evaluate(self, condition: dict, sensor_type: str, payload: dict, room_id: str) -> bool:
        trigger_type = condition.get("trigger")
        if trigger_type != sensor_type:
            return False

        field = condition.get("field")
        operator = condition.get("operator")
        expected = condition.get("value")

        actual = payload.get(field)
        if actual is None:
            return False

        if not self._compare(actual, operator, expected):
            return False

        and_conditions = condition.get("and", [])
        for sub in and_conditions:
            sub_trigger = sub.get("trigger")
            sub_field = sub.get("field")
            sub_op = sub.get("operator")
            sub_val = sub.get("value")

            sub_state = self._find_device_state(sub_trigger, room_id)
            if sub_state is None:
                return False
            sub_actual = sub_state.get(sub_field)
            if sub_actual is None:
                return False
            if not self._compare(sub_actual, sub_op, sub_val):
                return False

        return True

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        if operator == "eq":
            return actual == expected
        if operator == "neq":
            return actual != expected
        if operator == "gt":
            return float(actual) > float(expected)
        if operator == "lt":
            return float(actual) < float(expected)
        if operator == "gte":
            return float(actual) >= float(expected)
        if operator == "lte":
            return float(actual) <= float(expected)
        if operator == "changed":
            return True
        return False

    def _find_device_state(self, device_type: str, room_id: str) -> dict | None:
        device_id = self._get_device_id(room_id, device_type)
        if device_id is not None:
            return device_state_projection.get(device_id)
        return None

    def _execute_actions(self, actions: list[dict], room_id: str):
        for action in actions:
            device_type = action.get("device_type")
            action_name = action.get("action")
            params = action.get("params", {})
            target_room = action.get("room_id", "same")

            if target_room == "same":
                target_room = room_id

            if "device_id" in action:
                explicit_device_id = action["device_id"]
                if (
                    isinstance(explicit_device_id, bool)
                    or not isinstance(explicit_device_id, int)
                    or explicit_device_id <= 0
                ):
                    raise RulePayloadError("invalid_action_json")
                device_id = explicit_device_id
            else:
                device_id = self._get_device_id(target_room, device_type)

            if device_id is not None:
                result = execute_device_command(
                    device_id,
                    action_name,
                    params,
                    user=None,
                    expected_device_type=device_type,
                )
                logger.info("rule action: %s -> %s", result["topic"], result["payload"])
                continue

            topic = f"home/{target_room}/{device_type}/command"
            payload = {"action": action_name}
            payload.update(params)

            mqtt_client.publish_message(topic, json.dumps(payload))
            logger.info("rule action: %s -> %s", topic, payload)


rule_engine = RuleEngine()
