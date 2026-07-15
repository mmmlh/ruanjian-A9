"""
建表 + 初始数据
"""
import json
import sqlite3


LEGACY_RULE_1_CONDITION_JSON = json.dumps(
    {
        "trigger": "pir_sensor",
        "field": "presence",
        "operator": "eq",
        "value": True,
        "and": [
            {
                "trigger": "light",
                "field": "power",
                "operator": "eq",
                "value": "off",
            }
        ],
    },
    separators=(",", ":"),
)
LEGACY_RULE_1_ACTION_JSON = json.dumps(
    [{"device_type": "light", "action": "on", "params": {"brightness": 80}}],
    separators=(",", ":"),
)


def repair_legacy_rule_payloads(conn: sqlite3.Connection):
    """Repair known malformed seed payloads in existing databases."""
    rows = conn.execute(
        "SELECT id, condition_json, action_json FROM automation_rules"
    ).fetchall()

    for row in rows:
        if row["id"] != 1 or row["action_json"] != LEGACY_RULE_1_ACTION_JSON:
            continue

        try:
            json.loads(row["condition_json"])
        except json.JSONDecodeError:
            conn.execute(
                "UPDATE automation_rules SET condition_json = ? WHERE id = ?",
                (LEGACY_RULE_1_CONDITION_JSON, row["id"]),
            )


def ensure_schema(conn: sqlite3.Connection):
    """Backfill columns for older local databases created before schema changes."""
    device_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(devices)").fetchall()
    }
    if device_columns and "updated_at" not in device_columns:
        conn.execute("ALTER TABLE devices ADD COLUMN updated_at DATETIME")
        conn.execute(
            "UPDATE devices SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)"
        )


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
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
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
    CREATE TABLE IF NOT EXISTS activity_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type  TEXT NOT NULL,
        title       TEXT NOT NULL,
        detail      TEXT,
        source      TEXT NOT NULL,
        device_id   INTEGER REFERENCES devices(id),
        user_id     INTEGER REFERENCES users(id),
        timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_activity_log_ts
        ON activity_log(timestamp);

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
    ensure_schema(conn)


def seed_data(conn: sqlite3.Connection):
    """插入初始数据（仅当表为空时）"""
    count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    if count > 0:
        repair_legacy_rule_payloads(conn)
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

    # ── 书房 ──
    conn.execute("INSERT INTO rooms (id, name, floor, description) VALUES (3, '书房', 1, '书房工作间')")
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(12, 3, 'temperature_sensor', '书房温度', NULL, 'home/study/temperature_sensor', "
        "'{\"value\":24.0,\"unit\":\"celsius\"}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(13, 3, 'light', '书房灯', NULL, 'home/study/light', '{\"power\":\"off\",\"brightness\":0}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(14, 3, 'ac', '书房空调', 'midea', 'home/study/ac', '{\"power\":\"off\",\"mode\":\"cool\",\"temp\":26}')"
    )

    # ── 扩展设备：窗帘 ──
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(15, 1, 'curtain', '客厅窗帘', NULL, 'home/livingroom/curtain', '{\"position\":0}')"
    )
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(16, 3, 'curtain', '书房窗帘', NULL, 'home/study/curtain', '{\"position\":0}')"
    )

    # ── 扩展设备：加湿器 ──
    conn.execute(
        "INSERT INTO devices (id, room_id, type, name, brand, mqtt_topic, status_json) VALUES "
        "(17, 2, 'humidifier', '卧室加湿器', NULL, 'home/bedroom/humidifier', "
        "'{\"power\":\"off\",\"level\":2,\"target_humidity\":60}')"
    )

    # ── 场景 ──
    conn.execute(
        "INSERT INTO scenes (id, name, icon, description, actions_json) VALUES "
        "(1, '回家模式', '🏠', '到家一键开启：客厅灯亮 + 空调制冷 + 门禁解锁', "
        "'[{\"device_type\":\"light\",\"room_id\":\"livingroom\",\"action\":\"on\",\"params\":{\"brightness\":80}},"
        "{\"device_type\":\"ac\",\"room_id\":\"livingroom\",\"action\":\"set\",\"params\":{\"power\":\"on\",\"mode\":\"cool\",\"temp\":26}},"
        "{\"device_type\":\"door_lock\",\"room_id\":\"livingroom\",\"action\":\"unlock\",\"params\":{\"auth_code\":\"scene-trigger\"}}]')"
    )
    conn.execute(
        "INSERT INTO scenes (id, name, icon, description, actions_json) VALUES "
        "(2, '离家模式', '🚪', '出门一键关闭：所有灯灭 + 空调关闭 + 窗帘关闭 + 门禁上锁', "
        "'[{\"device_type\":\"light\",\"room_id\":\"livingroom\",\"action\":\"off\",\"params\":{}},"
        "{\"device_type\":\"light\",\"room_id\":\"bedroom\",\"action\":\"off\",\"params\":{}},"
        "{\"device_type\":\"light\",\"room_id\":\"study\",\"action\":\"off\",\"params\":{}},"
        "{\"device_type\":\"ac\",\"room_id\":\"livingroom\",\"action\":\"off\",\"params\":{}},"
        "{\"device_type\":\"ac\",\"room_id\":\"bedroom\",\"action\":\"off\",\"params\":{}},"
        "{\"device_type\":\"ac\",\"room_id\":\"study\",\"action\":\"off\",\"params\":{}},"
        "{\"device_type\":\"curtain\",\"room_id\":\"livingroom\",\"action\":\"close\",\"params\":{}},"
        "{\"device_type\":\"curtain\",\"room_id\":\"study\",\"action\":\"close\",\"params\":{}},"
        "{\"device_type\":\"humidifier\",\"room_id\":\"bedroom\",\"action\":\"off\",\"params\":{}},"
        "{\"device_type\":\"door_lock\",\"room_id\":\"livingroom\",\"action\":\"lock\",\"params\":{}}]')"
    )
    conn.execute(
        "INSERT INTO scenes (id, name, icon, description, actions_json) VALUES "
        "(3, '睡眠模式', '🌙', '睡前设置：卧室灯暗光 + 空调设为26°C', "
        "'[{\"device_type\":\"light\",\"room_id\":\"bedroom\",\"action\":\"on\",\"params\":{\"brightness\":30,\"color\":\"warm\"}},"
        "{\"device_type\":\"ac\",\"room_id\":\"bedroom\",\"action\":\"set\",\"params\":{\"power\":\"on\",\"mode\":\"cool\",\"temp\":26,\"fan\":\"low\"}},"
        "{\"device_type\":\"light\",\"room_id\":\"livingroom\",\"action\":\"off\",\"params\":{}}]')"
    )

    # ── 联动规则 ──
    conn.execute(
        "INSERT INTO automation_rules (id, name, condition_json, action_json, enabled) VALUES "
        "(1, '人来开灯', "
        "'{\"trigger\":\"pir_sensor\",\"field\":\"presence\",\"operator\":\"eq\",\"value\":true,"
        "\"and\":[{\"trigger\":\"light\",\"field\":\"power\",\"operator\":\"eq\",\"value\":\"off\"}]}', "
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

    repair_legacy_rule_payloads(conn)
