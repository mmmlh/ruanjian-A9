"""
设备联动规则引擎 — 监听传感器数据，条件满足时自动触发动作
"""
import json
import logging
import threading
from typing import Any

from app.database.connection import get_db
from app.services import mqtt_client

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎单例"""

    def __init__(self):
        self._rules: list[dict] = []
        self._device_states: dict[int, dict] = {}  # device_id -> status
        self._lock = threading.Lock()

    def reload_rules(self):
        """从数据库重新加载所有启用的规则"""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM automation_rules WHERE enabled = 1"
            ).fetchall()
        with self._lock:
            self._rules = [dict(r) for r in rows]
        logger.info(f"规则引擎已加载 {len(self._rules)} 条规则")

    def update_device_state(self, device_id: int, state: dict):
        """更新设备状态缓存"""
        with self._lock:
            self._device_states[device_id] = state

    def on_sensor_data(self, topic: str, payload: Any):
        """收到传感器数据时触发规则检查"""
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return

        # 从 topic 解析 room_id 和设备类型
        # topic 格式: home/{room}/{device_type} 或 home/{room}/{device_type}/sensor
        parts = topic.split("/")
        if len(parts) < 3:
            return
        room_id = parts[1]
        sensor_type = parts[2]  # 设备类型在第三段（如 temperature_sensor, pir_sensor）

        # 更新设备状态缓存
        with get_db() as conn:
            device = conn.execute(
                "SELECT id FROM devices WHERE mqtt_topic LIKE ?",
                (f"%/{room_id}/sensor/{sensor_type}",)
            ).fetchone()
            if device:
                self.update_device_state(device["id"], payload)

        # 检查所有规则
        with self._lock:
            rules = list(self._rules)

        for rule in rules:
            try:
                condition = json.loads(rule["condition_json"])
                if self._evaluate(condition, sensor_type, payload, room_id):
                    actions = json.loads(rule["action_json"])
                    self._execute_actions(actions, room_id)
                    logger.info(f"规则触发: {rule['name']}")
            except Exception as e:
                logger.error(f"规则执行异常 [{rule['name']}]: {e}")

    def _evaluate(self, condition: dict, sensor_type: str, payload: dict, room_id: str) -> bool:
        """评估规则条件"""
        trigger_type = condition.get("trigger")
        if trigger_type != sensor_type:
            return False

        field = condition.get("field")
        operator = condition.get("operator")
        expected = condition.get("value")

        actual = payload.get(field)
        if actual is None:
            return False

        # 比较
        result = self._compare(actual, operator, expected)
        if not result:
            return False

        # 检查附加条件（and）
        and_conditions = condition.get("and", [])
        for sub in and_conditions:
            sub_trigger = sub.get("trigger")
            sub_field = sub.get("field")
            sub_op = sub.get("operator")
            sub_val = sub.get("value")

            # 从设备状态缓存中查找
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
        """比较操作"""
        if operator == "eq":
            return actual == expected
        elif operator == "neq":
            return actual != expected
        elif operator == "gt":
            return float(actual) > float(expected)
        elif operator == "lt":
            return float(actual) < float(expected)
        elif operator == "gte":
            return float(actual) >= float(expected)
        elif operator == "lte":
            return float(actual) <= float(expected)
        elif operator == "changed":
            return True  # 简化：值变化即触发
        return False

    def _find_device_state(self, device_type: str, room_id: str) -> dict | None:
        """从缓存中查找指定房间、指定类型的设备状态"""
        with get_db() as conn:
            device = conn.execute(
                "SELECT id FROM devices WHERE type = ? AND mqtt_topic LIKE ?",
                (device_type, f"%/{room_id}/%")
            ).fetchone()
        if device:
            with self._lock:
                return self._device_states.get(device["id"])
        return None

    def _execute_actions(self, actions: list[dict], room_id: str):
        """执行规则动作列表"""
        for action in actions:
            device_type = action.get("device_type")
            action_name = action.get("action")
            params = action.get("params", {})
            target_room = action.get("room_id", "same")

            if target_room == "same":
                target_room = room_id

            # 构建 MQTT 主题和载荷
            topic = f"home/{target_room}/{device_type}/command"
            payload = {"action": action_name}
            payload.update(params)

            mqtt_client.publish_message(topic, json.dumps(payload))
            logger.info(f"规则动作: {topic} -> {payload}")


# 全局规则引擎实例
rule_engine = RuleEngine()
