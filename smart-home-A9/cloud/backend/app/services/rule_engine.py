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
        self._device_id_map: dict[str, int] = {}     # "room_id/type" -> device_id
        self._lock = threading.Lock()

    def reload_rules(self):
        """从数据库重新加载所有启用的规则，并构建设备索引"""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM automation_rules WHERE enabled = 1"
            ).fetchall()
            # 构建设备 ID 索引（一次性加载全部，避免后续每条消息都查 DB）
            devices = conn.execute(
                "SELECT id, type, mqtt_topic FROM devices"
            ).fetchall()
        with self._lock:
            self._rules = [dict(r) for r in rows]
            self._device_id_map.clear()
            for d in devices:
                # mqtt_topic 格式: home/livingroom/temperature_sensor
                parts = d["mqtt_topic"].split("/")
                if len(parts) >= 3:
                    key = f"{parts[1]}/{parts[2]}"  # e.g. "livingroom/temperature_sensor"
                    self._device_id_map[key] = d["id"]
        logger.info(f"规则引擎已加载 {len(self._rules)} 条规则, {len(self._device_id_map)} 个设备索引")

    def update_device_state(self, device_id: int, state: dict):
        """更新设备状态缓存"""
        with self._lock:
            self._device_states[device_id] = state

    def _get_device_id(self, room_id: str, device_type: str) -> int | None:
        """从索引中获取 device_id（无 DB 查询）"""
        key = f"{room_id}/{device_type}"
        return self._device_id_map.get(key)

    def on_sensor_data(self, topic: str, payload: Any):
        """收到传感器数据时触发规则检查"""
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return

        # 从 topic 解析 room_id 和设备类型
        parts = topic.split("/")
        if len(parts) < 3:
            return
        room_id = parts[1]
        sensor_type = parts[2]

        # 更新设备状态缓存（使用索引，无 DB 查询）
        device_id = self._get_device_id(room_id, sensor_type)
        if device_id is not None:
            self.update_device_state(device_id, payload)

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

        if not self._compare(actual, operator, expected):
            return False

        # 检查附加条件（and）— 全部从内存缓存查找
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
            return True
        return False

    def _find_device_state(self, device_type: str, room_id: str) -> dict | None:
        """从内存缓存中查找指定房间、指定类型的设备状态"""
        device_id = self._get_device_id(room_id, device_type)
        if device_id is not None:
            with self._lock:
                return self._device_states.get(device_id)
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
