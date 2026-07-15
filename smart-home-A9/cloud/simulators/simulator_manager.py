"""
设备模拟器管理器 — 统一启停所有设备
"""
import os
import signal
import logging
import time

from temperature_sensor import TemperatureSensor
from humidity_sensor import HumiditySensor
from pir_sensor import PIRSensor
from light_controller import LightController
from ac_controller import ACController
from door_lock import DoorLock
from curtain_controller import CurtainController
from humidifier_controller import HumidifierController

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


def create_devices() -> list:
    """创建所有模拟设备（与数据库初始数据一致）"""
    devices = []

    # ── 客厅 ──
    devices.append(TemperatureSensor(1, "livingroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(HumiditySensor(2, "livingroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(PIRSensor(3, "livingroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(LightController(4, "livingroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(ACController(5, "livingroom", brand="gree", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(DoorLock(6, "livingroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))

    # ── 卧室 ──
    devices.append(TemperatureSensor(7, "bedroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(HumiditySensor(8, "bedroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(PIRSensor(9, "bedroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(LightController(10, "bedroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(ACController(11, "bedroom", brand="haier", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))

    # ── 书房 ──
    devices.append(TemperatureSensor(12, "study", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(LightController(13, "study", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(ACController(14, "study", brand="midea", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))

    # ── 扩展设备：窗帘 ──
    devices.append(CurtainController(15, "livingroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))
    devices.append(CurtainController(16, "study", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))

    # ── 扩展设备：加湿器 ──
    devices.append(HumidifierController(17, "bedroom", mqtt_broker=MQTT_BROKER, mqtt_port=MQTT_PORT))

    return devices


def main():
    """启动所有设备模拟器"""
    devices = create_devices()

    logger.info(f"正在启动 {len(devices)} 个设备模拟器...")
    for d in devices:
        d.start()
        time.sleep(0.2)  # 错开连接

    logger.info("所有设备已启动，按 Ctrl+C 停止")

    # 优雅退出
    def shutdown(signum, frame):
        logger.info("正在停止所有设备...")
        for d in devices:
            d.stop()
        logger.info("模拟器已全部停止")
        exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 保持运行
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
