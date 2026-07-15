"""
Remote deployment script for the Smart Home A9 stack.

Usage:
  1. Set environment variables:
     SMART_HOME_SERVER=<server-ip>
     SMART_HOME_USER=root
     SMART_HOME_PASS=<password>
  2. Run:
     python deploy_remote.py
"""
import os
import sys
import time

try:
    import paramiko
except ImportError:
    print("Please install paramiko first: pip install paramiko")
    sys.exit(1)


REMOTE_DIR = "/opt/smart-home-A9"
LOCAL_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud")
DEFAULT_PUBLIC_SCHEME = os.getenv("SMART_HOME_PUBLIC_SCHEME", "https")
DEFAULT_PIP_INDEX_URL = os.getenv("SMART_HOME_PIP_INDEX_URL", "https://mirrors.aliyun.com/pypi/simple/")
DEFAULT_PIP_TRUSTED_HOST = os.getenv("SMART_HOME_PIP_TRUSTED_HOST", "mirrors.aliyun.com")
DEFAULT_PIP_TIMEOUT = os.getenv("SMART_HOME_PIP_TIMEOUT", "120")


def validate_remote_env() -> tuple[str, str, str]:
    server = os.getenv("SMART_HOME_SERVER")
    user = os.getenv("SMART_HOME_USER", "root")
    password = os.getenv("SMART_HOME_PASS")

    if not server:
        print("Error: SMART_HOME_SERVER is required")
        print("  export SMART_HOME_SERVER='your-server-ip'")
        print("  export SMART_HOME_PASS='your-password'")
        sys.exit(1)
    if not password:
        print("Error: SMART_HOME_PASS is required")
        print("  export SMART_HOME_PASS='your-password'")
        sys.exit(1)
    return server, user, password


def ssh_exec(ssh, cmd, timeout=60):
    """Execute a remote command and print its output."""
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
    """Upload a directory recursively."""
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, local_dir)
        remote_path = f"{remote_dir}/{rel}".replace("\\", "/")
        try:
            sftp.stat(remote_path)
        except FileNotFoundError:
            print(f"  mkdir {remote_path}")
            sftp.mkdir(remote_path)
        for name in files:
            local_file = os.path.join(root, name)
            remote_file = f"{remote_path}/{name}".replace("\\", "/")
            print(f"  upload {local_file} -> {remote_file}")
            sftp.put(local_file, remote_file)


def build_remote_compose(server: str) -> str:
    public_base_url = f"{DEFAULT_PUBLIC_SCHEME}://{server}"
    return f"""version: '3.8'

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
    build:
      context: ./backend
      args:
        PIP_INDEX_URL: {DEFAULT_PIP_INDEX_URL}
        PIP_TRUSTED_HOST: {DEFAULT_PIP_TRUSTED_HOST}
        PIP_DEFAULT_TIMEOUT: {DEFAULT_PIP_TIMEOUT}
    container_name: smart-home-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/smart_home.db
      - MQTT_BROKER=mqtt
      - MQTT_PORT=1883
      - MQTT_USE_TLS=false
      - MQTT_TLS_PORT=8883
      - MQTT_CA_CERTS=/certs/server.crt
      - PUBLIC_BASE_URL={public_base_url}
      - JWT_SECRET=smart-home-a9-secret-key
      - JWT_EXPIRE_HOURS=24
      - DEBUG=false
    volumes:
      - ./data:/app/data
      - ./mosquitto/certs:/certs:ro
    depends_on:
      - mqtt
    restart: unless-stopped

  simulators:
    build:
      context: ./simulators
      args:
        PIP_INDEX_URL: {DEFAULT_PIP_INDEX_URL}
        PIP_TRUSTED_HOST: {DEFAULT_PIP_TRUSTED_HOST}
        PIP_DEFAULT_TIMEOUT: {DEFAULT_PIP_TIMEOUT}
    container_name: smart-home-simulators
    environment:
      - MQTT_BROKER=mqtt
      - MQTT_PORT=1883
    depends_on:
      - mqtt
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: smart-home-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - backend
    restart: unless-stopped
"""


def main():
    server, user, password = validate_remote_env()

    print("=" * 50)
    print("  Smart Home A9 Remote Deployment")
    print("=" * 50)

    print("\n[1/6] Connecting to server...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username=user, password=password, timeout=15)
    print(f"  Connected to {server}")

    sftp = ssh.open_sftp()

    print("\n[2/6] Checking server environment...")
    ssh_exec(ssh, "uname -a")
    ssh_exec(ssh, "cat /etc/os-release | head -3")

    print("\n[3/6] Checking Docker...")
    out, _ = ssh_exec(ssh, "docker --version 2>/dev/null || echo NOT_FOUND")
    if "NOT_FOUND" in out:
        print("  Installing Docker...")
        ssh_exec(ssh, "curl -fsSL https://get.docker.com | sh", timeout=120)
        ssh_exec(ssh, "systemctl enable docker && systemctl start docker")
    else:
        print(f"  Docker already installed: {out.strip()}")

    out, _ = ssh_exec(ssh, "docker compose version 2>/dev/null || echo NOT_FOUND")
    if "NOT_FOUND" in out:
        print("  Installing Docker Compose plugin...")
        ssh_exec(ssh, "apt-get update && apt-get install -y docker-compose-plugin", timeout=120)

    print("\n[4/6] Preparing remote directories...")
    ssh_exec(
        ssh,
        f"mkdir -p {REMOTE_DIR}/backend/app/api {REMOTE_DIR}/backend/app/models "
        f"{REMOTE_DIR}/backend/app/services {REMOTE_DIR}/backend/app/database "
        f"{REMOTE_DIR}/simulators {REMOTE_DIR}/mosquitto/config "
        f"{REMOTE_DIR}/mosquitto/data {REMOTE_DIR}/mosquitto/certs "
        f"{REMOTE_DIR}/nginx/certs {REMOTE_DIR}/data",
    )

    print("\n[5/6] Uploading project files...")
    upload_dir(sftp, f"{LOCAL_BASE}/backend", f"{REMOTE_DIR}/backend")
    upload_dir(sftp, f"{LOCAL_BASE}/simulators", f"{REMOTE_DIR}/simulators")

    sftp.put(
        f"{LOCAL_BASE}/mosquitto/config/mosquitto.conf",
        f"{REMOTE_DIR}/mosquitto/config/mosquitto.conf",
    )
    sftp.put(
        f"{LOCAL_BASE}/nginx/nginx.conf",
        f"{REMOTE_DIR}/nginx/nginx.conf",
    )

    nginx_cert = f"{LOCAL_BASE}/nginx/certs/server.crt"
    nginx_key = f"{LOCAL_BASE}/nginx/certs/server.key"
    if os.path.exists(nginx_cert) and os.path.exists(nginx_key):
        sftp.put(nginx_cert, f"{REMOTE_DIR}/nginx/certs/server.crt")
        sftp.put(nginx_key, f"{REMOTE_DIR}/nginx/certs/server.key")
        sftp.put(nginx_cert, f"{REMOTE_DIR}/mosquitto/certs/server.crt")
        sftp.put(nginx_key, f"{REMOTE_DIR}/mosquitto/certs/server.key")

    compose_content = build_remote_compose(server)
    with sftp.open(f"{REMOTE_DIR}/docker-compose.yml", "w") as handle:
        handle.write(compose_content)
    print("  docker-compose.yml uploaded")

    sftp.close()

    print("\n[6/6] Starting containers...")
    ssh_exec(ssh, f"cd {REMOTE_DIR} && docker compose up -d --build", timeout=300)

    print("\nWaiting for services to come up...")
    time.sleep(10)

    print("\nContainer status:")
    ssh_exec(ssh, f"cd {REMOTE_DIR} && docker compose ps")

    print("\nAPI smoke test:")
    ssh_exec(ssh, "curl -s http://localhost:8000/")
    ssh_exec(ssh, "curl -s http://localhost:8000/api/health")

    ssh.close()

    print("\n" + "=" * 50)
    print("  Deployment finished")
    print(f"  HTTPS:   https://{server}")
    print(f"  API:     https://{server}/api/health")
    print(f"  Swagger: https://{server}/docs")
    print(f"  MQTT(S): mqtts://{server}:8883")
    print("=" * 50)


if __name__ == "__main__":
    main()
