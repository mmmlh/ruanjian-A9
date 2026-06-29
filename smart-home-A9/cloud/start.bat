@echo off
chcp 65001 >nul
title 智能家居设备控制系统 - A9 Team

echo.
echo ╔══════════════════════════════════════════╗
echo ║   智能家居设备控制系统 - 一键启动       ║
echo ║   Smart Home Control System v1.0         ║
echo ╚══════════════════════════════════════════╝
echo.

:: 检查 Docker
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 未检测到 Docker，请先安装 Docker Desktop
    echo         下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker 已就绪

:: 进入 cloud 目录
cd /d "%~dp0"

:: 检查证书
if not exist "mosquitto\certs\server.crt" (
    echo [WARN] TLS 证书不存在，正在生成自签名证书...
    mkdir mosquitto\certs nginx\certs 2>nul
    openssl req -x509 -newkey rsa:2048 -keyout mosquitto\certs\server.key -out mosquitto\certs\server.crt -days 365 -nodes -subj "//CN=localhost" 2>nul
    copy mosquitto\certs\server.crt nginx\certs\ >nul
    copy mosquitto\certs\server.key nginx\certs\ >nul
    echo [OK] 证书已生成
)

:: 启动服务
echo.
echo [INFO] 正在启动 Docker 容器...
docker compose up -d

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 启动失败，请检查 Docker 状态
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════╗
echo ║  所有服务已启动！                       ║
echo ╠══════════════════════════════════════════╣
echo ║  HTTP API:   http://localhost:8000       ║
echo ║  HTTPS API:  https://localhost           ║
echo ║  Swagger:    http://localhost:8000/docs  ║
echo ║  WebSocket:  ws://localhost:8000/ws/     ║
echo ╚══════════════════════════════════════════╝
echo.
echo 按任意键打开浏览器访问控制面板...
pause >nul

start http://localhost:8000/docs

echo.
echo 提示：
echo   - 查看日志:  docker compose logs -f
echo   - 停止服务:  docker compose down
echo   - 默认账号:  admin / admin123
echo.
pause
