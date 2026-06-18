"""
远程部署脚本 — 通过 SSH 部署到阿里云 ECS

使用方式：
    1. 设置环境变量:
       export SMART_HOME_SERVER="your-server-ip"
       export SMART_HOME_USER="root"
       export SMART_HOME_PASS="your-password"
    2. 运行: python deploy_remote.py
"""
import os
import sys
import time

try:
    import paramiko
except ImportError:
    print("请先安装 paramiko: pip install paramiko")
    sys.exit(1)

# ── 从环境变量读取服务器配置（禁止硬编码密码！）──
SERVER = os.getenv("SMART_HOME_SERVER")
USER = os.getenv("SMART_HOME_USER", "root")
PASS = os.getenv("SMART_HOME_PASS")

if not SERVER:
    print("错误: 请设置环境变量 SMART_HOME_SERVER")
    print("  export SMART_HOME_SERVER='your-server-ip'")
    print("  export SMART_HOME_PASS='your-password'")
    sys.exit(1)
if not PASS:
    print("错误: 请设置环境变量 SMART_HOME_PASS")
    print("  export SMART_HOME_PASS='your-password'")
    sys.exit(1)

REMOTE_DIR = "/opt/smart-home-A9"
LOCAL_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud")


def ssh_exec(ssh, cmd, timeout=60):
    """执行远程命令并打印输出"""
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(f"  [stderr] {err.strip()}")
    return out, err


def upload_dir(sftp, local_dir, remote_dir):
    """递归上传目录"""
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        remote_path = f"{remote_dir}/{rel}".replace("\\", "/")
        try:
            sftp.stat(remote_path)
        except FileNotFoundError:
            print(f"  mkdir {remote_path}")
            sftp.mkdir(remote_path)
        for f in files:
            local_file = os.path.join(root, f)
            remote_file = f"{remote_path}/{f}".replace("\\", "/")
            print(f"  upload {local_file} -> {remote_file}")
            sftp.put(local_file, remote_file)


def main():
    print("=" * 50)
    print("  智能家居系统 — 远程部署")
    print("=" * 50)

    # 连接 SSH
    print("\n[1/6] 连接服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASS, timeout=15)
    print(f"  已连接 {SERVER}")

    sftp = ssh.open_sftp()

    # 检查环境
    print("\n[2/6] 检查服务器环境...")
    ssh_exec(ssh, "uname -a")
    ssh_exec(ssh, "cat /etc/os-release | head -3")

    # 安装 Docker
    print("\n[3/6] 检查/安装 Docker...")
    out, _ = ssh_exec(ssh, "docker --version 2>/dev/null || echo NOT_FOUND")
    if "NOT_FOUND" in out:
        print("  安装 Docker...")
        ssh_exec(ssh, "curl -fsSL https://get.docker.com | sh", timeout=120)
        ssh_exec(ssh, "systemctl enable docker && systemctl start docker")
    else:
        print(f"  Docker 已安装: {out.strip()}")

    out, _ = ssh_exec(ssh, "docker compose version 2>/dev/null || echo NOT_FOUND")
    if "NOT_FOUND" in out:
        print("  安装 Docker Compose...")
        ssh_exec(ssh, "apt-get update && apt-get install -y docker-compose-plugin", timeout=120)

    # 创建目录
    print("\n[4/6] 创建远程目录...")
    ssh_exec(ssh, f"mkdir -p {REMOTE_DIR}/backend/app/api {REMOTE_DIR}/backend/app/models "
                  f"{REMOTE_DIR}/backend/app/services {REMOTE_DIR}/backend/app/database "
                  f"{REMOTE_DIR}/simulators {REMOTE_DIR}/mosquitto/config "
                  f"{REMOTE_DIR}/mosquitto/data {REMOTE_DIR}/mosquitto/certs {REMOTE_DIR}/data")

    # 上传文件
    print("\n[5/6] 上传项目文件...")
    upload_dir(sftp, f"{LOCAL_BASE}/backend", f"{REMOTE_DIR}/backend")
    upload_dir(sftp, f"{LOCAL_BASE}/simulators", f"{REMOTE_DIR}/simulators")

    # 上传配置文件
    sftp.put(f"{LOCAL_BASE}/mosquitto/config/mosquitto.conf",
             f"{REMOTE_DIR}/mosquitto/config/mosquitto.conf")

    # 上传 docker-compose.yml
    compose_content = """version: '3.8'

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
"""
    with sftp.open(f"{REMOTE_DIR}/docker-compose.yml", "w") as f:
        f.write(compose_content)
    print("  docker-compose.yml 已上传")

    sftp.close()

    # 启动服务
    print("\n[6/6] 启动 Docker 容器...")
    ssh_exec(ssh, f"cd {REMOTE_DIR} && docker compose up -d --build", timeout=300)

    # 等待启动
    print("\n等待服务启动...")
    time.sleep(10)

    # 检查状态
    print("\n容器状态：")
    ssh_exec(ssh, f"cd {REMOTE_DIR} && docker compose ps")

    # 测试 API
    print("\n测试 API：")
    ssh_exec(ssh, "curl -s http://localhost:8000/")
    ssh_exec(ssh, "curl -s http://localhost:8000/api/health")

    ssh.close()

    print("\n" + "=" * 50)
    print(f"  部署完成！")
    print(f"  API 地址: http://{SERVER}:8000")
    print(f"  Swagger:  http://{SERVER}:8000/docs")
    print("=" * 50)


if __name__ == "__main__":
    main()
