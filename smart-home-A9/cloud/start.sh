#!/bin/bash
# 智能家居设备控制系统 - 一键启动 (Linux/Mac)

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   智能家居设备控制系统 - 一键启动       ║"
echo "║   Smart Home Control System v1.0         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 检查 Docker
if ! command -v docker &>/dev/null; then
    echo "[ERROR] 未检测到 Docker，请先安装 Docker"
    exit 1
fi
echo "[OK] Docker 已就绪"

cd "$(dirname "$0")"

# 检查证书
if [ ! -f "mosquitto/certs/server.crt" ]; then
    echo "[WARN] TLS 证书不存在，正在生成自签名证书..."
    mkdir -p mosquitto/certs nginx/certs
    openssl req -x509 -newkey rsa:2048 \
        -keyout mosquitto/certs/server.key \
        -out mosquitto/certs/server.crt \
        -days 365 -nodes \
        -subj "/CN=localhost"
    cp mosquitto/certs/server.crt nginx/certs/
    cp mosquitto/certs/server.key nginx/certs/
    echo "[OK] 证书已生成"
fi

# 启动服务
echo ""
echo "[INFO] 正在启动 Docker 容器..."
docker compose up -d

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  所有服务已启动！                       ║"
echo "╠══════════════════════════════════════════╣"
echo "║  HTTP API:   http://localhost:8000       ║"
echo "║  HTTPS API:  https://localhost           ║"
echo "║  Swagger:    http://localhost:8000/docs  ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  查看日志:  docker compose logs -f"
echo "  停止服务:  docker compose down"
echo "  默认账号:  admin / admin123"
echo ""
