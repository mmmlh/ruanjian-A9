"""
设备基类 — 所有模拟器的抽象父类
"""
import json
import time
import logging
import threading
from abc import ABC, abstractmethod

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class BaseDevice(ABC):
    """设备基类"""

    def __init__(self, device_id: int, room_id: str, device_type: str,
                 mqtt_broker: str = "localhost", mqtt_port: int = 1883):
        self.device_id = device_id
        self.room_id = room_id
        self.device_type = device_type
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.client: mqtt.Client | None = None
        self.running = False
        self._thread: threading.Thread | None = None
        self.hardware_id = f"sim-{device_type}-{device_id:03d}"
        self.protocol_version = "1.0"
        self._last_heartbeat = 0.0

        # MQTT 主题
        self.topic_base = f"home/{room_id}/{device_type}"
        self.topic_command = f"{self.topic_base}/command"
        self.topic_status = f"{self.topic_base}/status"
        self.topic_sensor = f"{self.topic_base}/sensor"
        self.topic_hello = f"{self.topic_base}/hello"
        self.topic_heartbeat = f"{self.topic_base}/heartbeat"
        self.topic_ack = f"{self.topic_base}/ack"

    def connect_mqtt(self):
        """连接 MQTT Broker"""
        self.client = mqtt.Client(
            client_id=f"sim_{self.device_type}_{self.device_id}",
            protocol=mqtt.MQTTv311,
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
        self.client.loop_start()
        logger.info(f"[{self}] MQTT 已连接: {self.mqtt_broker}:{self.mqtt_port}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(self.topic_command)
            logger.info(f"[{self}] 订阅指令主题: {self.topic_command}")
            self.publish_hello()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"[{self}] 收到指令: {payload}")
            self.handle_command(payload)
        except Exception as e:
            logger.error(f"[{self}] 指令处理异常: {e}")

    @abstractmethod
    def handle_command(self, payload: dict):
        """处理控制指令 — 子类实现"""
        pass

    @abstractmethod
    def generate_data(self) -> dict:
        """生成模拟数据 — 子类实现"""
        pass

    def publish_status(self, status: dict, command_id: str | None = None):
        """发布设备状态"""
        if self.client:
            message = dict(status)
            if isinstance(command_id, str) and command_id:
                message["command_id"] = command_id
            self.client.publish(self.topic_status, json.dumps(message), qos=1)

    def publish_sensor_data(self, data: dict):
        """发布传感器数据"""
        if self.client:
            self.client.publish(self.topic_sensor, json.dumps(data), qos=1)

    def capabilities(self) -> dict:
        return {"actions": [], "params": {}}

    def publish_hello(self):
        if self.client:
            self.client.publish(
                self.topic_hello,
                json.dumps(
                    {
                        "hardware_id": self.hardware_id,
                        "protocol_version": self.protocol_version,
                        "capabilities": self.capabilities(),
                    }
                ),
                qos=1,
                retain=True,
            )

    def publish_heartbeat(self):
        if self.client:
            # Reannounce identity so a restarted backend can re-register this device.
            self.publish_hello()
            self.client.publish(
                self.topic_heartbeat,
                json.dumps({"hardware_id": self.hardware_id, "ts": int(time.time())}),
                qos=1,
            )

    def publish_ack(self, payload: dict, success: bool, state: dict, error_code: str | None = None):
        command_id = payload.get("command_id")
        if not isinstance(command_id, str) or not command_id:
            return
        message = {"command_id": command_id, "success": success, "state": dict(state)}
        if error_code:
            message["error_code"] = error_code
        if self.client:
            self.client.publish(self.topic_ack, json.dumps(message), qos=1)

    def start(self):
        """启动设备模拟（在独立线程中）"""
        self.running = True
        self.connect_mqtt()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"[{self}] 已启动")

    def _run_loop(self):
        """模拟主循环"""
        while self.running:
            try:
                if time.time() - self._last_heartbeat >= 30:
                    self.publish_heartbeat()
                    self._last_heartbeat = time.time()
                data = self.generate_data()
                if data:
                    self.publish_sensor_data(data)
            except Exception as e:
                logger.error(f"[{self}] 模拟异常: {e}")
            self._sleep()

    def _sleep(self):
        """默认 5 秒间隔，子类可覆盖"""
        for _ in range(50):
            if not self.running:
                break
            time.sleep(0.1)

    def stop(self):
        """停止设备模拟"""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        logger.info(f"[{self}] 已停止")

    def __str__(self):
        return f"{self.device_type}#{self.device_id}({self.room_id})"
