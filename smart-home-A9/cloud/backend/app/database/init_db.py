"""
建表 + 初始数据
"""
import sqlite3


def create_tables(conn: sqlite3.Connection):
    """创建所有表"""
    conn.executescript("""
    -- 用户表
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role        TEXT DEFAULT 'user',
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- 房间表
    CREATE TABLE IF NOT EXISTS rooms (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        floor       INTEGER DEFAULT 1,
        description TEXT,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- 设备表
    CREATE TABLE IF NOT EXISTS devices (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id     INTEGER NOT NULL REFERENCES rooms(id),
        type        TEXT NOT NULL,
        name        TEXT NOT NULL,
        brand       TEXT,
        mqtt_topic  TEXT NOT NULL,
        status_json TEXT DEFAULT '{}',
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- 传感器数据表
    CREATE TABLE IF NOT EXISTS sensor_data (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id   INTEGER NOT NULL REFERENCES devices(id),
        data_type   TEXT NOT NULL,
        value       REAL,
        extra_json  TEXT DEFAULT '{}',
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_sensor_data_device_ts
        ON sensor_data(device_id, timestamp);

    -- 设备操作日志表
    CREATE TABLE IF NOT EXISTS device_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id   INTEGER NOT NULL REFERENCES devices(id),
        action      TEXT NOT NULL,
        detail      TEXT,
        user_id     INTEGER REFERENCES users(id),
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- 场景表
    CREATE TABLE IF NOT EXISTS scenes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        icon        TEXT DEFAULT '🏠',
        description TEXT,
        actions_json TEXT NOT NULL,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- 联动规则表
    CREATE TABLE IF NOT EXISTS automation_rules (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        condition_json  TEXT NOT NULL,
        action_json     TEXT NOT NULL,
        enabled         INTEGER DEFAULT 1,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)


def seed_data(conn: sqlite3.Connection):
    """插入初始数据（仅当表为空时）"""
    count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    if count > 0:
        return

    # ── 默认用户 admin/admin123 ──
    # 密码哈希将在 auth 模块中用 bcrypt 生成
    # 这里先用占位符，首次启动时通过 API 注册
    from app.services.security import hash_password
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        ("admin", hash_password("admin123"), "admin")
    )

    # ── 客厅 ──
    conn.execute("INSERT INTO rooms (id, name, floor, description) VALUES (1, '客厅', 1, '家庭客厅区域')")
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(1, 1, 'temperature_sensor', '客厅温度', NULL, 'home/livingroom/temperature_sensor', "
        "'{\"value\":25.0,\"unit\":\"celsius\"}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(2, 1, 'humidity_sensor', '客厅湿度', NULL, 'home/livingroom/humidity_sensor', "
        "'{\"value\":55.0,\"unit\":\"percent\"}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(3, 1, 'pir_sensor', '客厅人体感应', NULL, 'home/livingroom/pir_sensor', "
        "'{\"presence\":false}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(4, 1, 'light', '客厅主灯', NULL, 'home/livingroom/light', '{\"power\":\"off\",\"brightness\":0}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(5, 1, 'ac', '客厅空调', 'gree', 'home/livingroom/ac', '{\"power\":\"off\",\"mode\":\"cool\",\"temp\":26}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(6, 1, 'door_lock', '客厅门禁', NULL, 'home/livingroom/door_lock', '{\"locked\":true}')"
    )

    # ── 卧室 ──
    conn.execute("INSERT INTO rooms (id, name, floor, description) VALUES (2, '卧室', 1, '主卧室')")
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(7, 2, 'temperature_sensor', '卧室温度', NULL, 'home/bedroom/temperature_sensor', "
        "'{\"value\":25.0,\"unit\":\"celsius\"}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(8, 2, 'humidity_sensor', '卧室湿度', NULL, 'home/bedroom/humidity_sensor', "
        "'{\"value\":55.0,\"unit\":\"percent\"}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(9, 2, 'pir_sensor', '卧室人体感应', NULL, 'home/bedroom/pir_sensor', "
        "'{\"presence\":false}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(10, 2, 'light', '卧室主灯', NULL, 'home/bedroom/light', '{\"power\":\"off\",\"brightness\":0}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(11, 2, 'ac', '卧室空调', 'haier', 'home/bedroom/ac', '{\"power\":\"off\",\"mode\":\"cool\",\"temp\":26}')"
    )

    # ── 联动规则 ──
    conn.execute(
        "INSERT INTO automation_rules (id, name, condition_json, action_json, enabled) VALUES "
        "(1, '人来开灯', "
        "'{\"trigger\":\"pir_sensor\",\"field\":\"presence\",\"operator\":\"eq\",\"value\":true,"
        "\"and\":[{\"trigger\":\"light\",\"field\":\"power\",\"operator\":\"eq\",\"value\":\"off\"]}', "
        "'[{\"device_type\":\"light\",\"action\":\"on\",\"params\":{\"brightness\":80}}]', 1)"
    )
    conn.execute(
        "INSERT INTO automation_rules (id, name, condition_json, action_json, enabled) VALUES "
        "(2, '人走关灯', "
        "'{\"trigger\":\"pir_sensor\",\"field\":\"presence\",\"operator\":\"eq\",\"value\":false,"
        "\"and\":[{\"trigger\":\"light\",\"field\":\"power\",\"operator\":\"eq\",\"value\":\"on\"}]}', "
        "'[{\"device_type\":\"light\",\"action\":\"off\",\"params\":{}}]', 1)"
    )
    conn.execute(
        "INSERT INTO automation_rules (id, name, condition_json, action_json, enabled) VALUES "
        "(3, '高温自动制冷', "
        "'{\"trigger\":\"temperature_sensor\",\"field\":\"value\",\"operator\":\"gt\",\"value\":28,"
        "\"and\":[{\"trigger\":\"ac\",\"field\":\"power\",\"operator\":\"eq\",\"value\":\"off\"}]}', "
        "'[{\"device_type\":\"ac\",\"action\":\"set\",\"params\":{\"power\":\"on\",\"mode\":\"cool\",\"temp\":26}}]', 1)"
    )
    conn.execute(
        "INSERT INTO automation_rules (id, name, condition_json, action_json, enabled) VALUES "
        "(4, '高湿自动除湿', "
        "'{\"trigger\":\"humidity_sensor\",\"field\":\"value\",\"operator\":\"gt\",\"value\":80,"
        "\"and\":[{\"trigger\":\"ac\",\"field\":\"power\",\"operator\":\"eq\",\"value\":\"off\"}]}', "
        "'[{\"device_type\":\"ac\",\"action\":\"set\",\"params\":{\"power\":\"on\",\"mode\":\"dehumidify\"}}]', 1)"
    )
