#!/bin/bash
# 智能家居系统一键部署脚本
# 在阿里云 ECS 上执行：bash deploy.sh

set -e

echo "========================================="
echo "  智能家居设备控制系统 — 一键部署"
echo "========================================="

# 1. 安装 Docker（如果没有）
if ! command -v docker &> /dev/null; then
    echo "[1/5] 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[1/5] Docker 已安装: $(docker --version)"
fi

# 2. 安装 Docker Compose 插件（如果没有）
if ! docker compose version &> /dev/null; then
    echo "[2/5] 安装 Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin
else
    echo "[2/5] Docker Compose 已安装: $(docker compose version)"
fi

# 3. 创建项目目录
echo "[3/5] 创建项目目录..."
mkdir -p /opt/smart-home-A9
cd /opt/smart-home-A9

# 4. 创建所有文件
echo "[4/5] 生成项目文件..."

# ── docker-compose.yml ──
cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  mqtt:
    image: eclipse-mosquitto:2
    container_name: smart-home-mqtt
    ports:
      - "1883:1883"
      - "8883:8883"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/certs:/mosquitto/certs
    restart: unless-stopped

  backend:
    image: python:3.11-slim
    container_name: smart-home-backend
    working_dir: /app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/smart_home.db
      - MQTT_BROKER=mqtt
      - MQTT_PORT=1883
      - JWT_SECRET=smart-home-a9-secret-key
      - JWT_EXPIRE_HOURS=24
      - DEBUG=false
    volumes:
      - ./backend:/app
      - ./data:/app/data
    command: bash -c "pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    depends_on:
      - mqtt
    restart: unless-stopped

  simulators:
    image: python:3.11-slim
    container_name: smart-home-simulators
    working_dir: /app
    environment:
      - MQTT_BROKER=mqtt
      - MQTT_PORT=1883
    volumes:
      - ./simulators:/app
    command: bash -c "pip install paho-mqtt==1.6.1 && python simulator_manager.py"
    depends_on:
      - mqtt
    restart: unless-stopped
COMPOSE_EOF

# ── Mosquitto 配置 ──
mkdir -p mosquitto/config mosquitto/data mosquitto/certs data
cat > mosquitto/config/mosquitto.conf << 'MQTT_EOF'
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest stdout
log_type all
MQTT_EOF

# ── 后端代码 ──
mkdir -p backend/app/api backend/app/models backend/app/services backend/app/database
mkdir -p simulators

echo "请将本地代码上传到以下目录："
echo "  后端: /opt/smart-home-A9/backend/"
echo "  模拟器: /opt/smart-home-A9/simulators/"
echo ""
echo "或者使用 scp 上传："
echo "  scp -r cloud/backend/* root@<IP>:/opt/smart-home-A9/backend/"
echo "  scp -r cloud/simulators/* root@<IP>:/opt/smart-home-A9/simulators/"
echo ""
echo "上传完成后执行："
echo "  cd /opt/smart-home-A9 && docker compose up -d"
echo ""
echo "========================================="
echo "  部署完成！访问 http://<IP>:8000/docs"
echo "========================================="
