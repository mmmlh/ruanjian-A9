# 基于 OpenHarmony 的家居设备控制系统

第十五届软件杯 A9 赛题

## 项目结构

```
smart-home-A9/
├── openharmony/                  # ArkTS APP 源码 (DevEco Studio)
│   └── entry/src/main/ets/
│       ├── entryability/         # EntryAbility
│       ├── pages/                # 页面（登录/注册/仪表盘/照明/空调/门禁）
│       ├── common/               # ApiClient + MqttClient
│       └── model/                # 数据模型
├── cloud/                        # 云端服务
│   ├── backend/                  # FastAPI 后端
│   │   └── app/
│   │       ├── api/              # REST API（auth/devices/rooms/rules/data）
│   │       ├── services/         # MQTT客户端/规则引擎/AES加密/AC品牌适配
│   │       └── database/         # SQLite 建表+种子数据
│   ├── simulators/               # 虚拟设备模拟器 (Python)
│   │   ├── temperature_sensor.py # 温度传感器
│   │   ├── humidity_sensor.py    # 湿度传感器
│   │   ├── pir_sensor.py         # 人体感应传感器
│   │   ├── light_controller.py   # 智能灯控制器
│   │   ├── ac_controller.py      # 空调控制器（多品牌）
│   │   ├── door_lock.py          # 门禁控制器
│   │   └── simulator_manager.py  # 模拟器统一管理
│   ├── mosquitto/                # MQTT Broker 配置
│   ├── nginx/                    # Nginx 反向代理
│   ├── docker-compose.yml        # Docker 容器编排
│   └── deploy.sh                 # 一键部署脚本
├── docs/                         # 文档
│   ├── design/                   # 产品总体设计文档
│   └── manual/                   # 使用手册
├── ppt/                          # 产品方案介绍 PPT
└── video/                        # 演示视频
```

## 技术栈

- **APP**: DevEco Studio + ArkTS + ArkUI (Stage模型)
- **通信**: MQTT over TLS
- **后端**: Python 3.11 + FastAPI + Eclipse Mosquitto
- **安全**: JWT + AES-256-CBC + bcrypt
- **部署**: Docker Compose + Nginx

## 功能模块

1. **控制中心** — 设备总览 + 房间管理 + 联动规则
2. **照明中心** — 远程开关 + 亮度/色温调节 + 人体感应自动开关
3. **温湿度控制中心** — 实时监测 + 多品牌空调控制（格力/海尔/美的）
4. **智能门禁** — 远程开锁/上锁 + 状态监控

## 快速开始

### 前置条件

- DevEco Studio 5.0+
- OpenHarmony SDK
- Docker & Docker Compose

### 1. 启动云端服务

```bash
cd smart-home-A9/cloud
docker compose up -d
```

访问: http://localhost:8000/docs

### 2. 启动设备模拟器

模拟器随 Docker Compose 自动启动，或手动运行:

```bash
cd smart-home-A9/cloud/simulators
pip install -r requirements.txt
python simulator_manager.py
```

### 3. 编译运行 APP

用 DevEco Studio 打开 `smart-home-A9/openharmony`，连接模拟器或真机运行。

### 默认账号

- 用户名: `admin`
- 密码: `admin123`

## 时间线

- 初赛提交截止：2026年6月30日 15:00
- 出题企业：苏州未来网络研究院有限公司
