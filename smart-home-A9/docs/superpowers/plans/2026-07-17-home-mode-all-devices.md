# 回家模式全设备启用 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将预置“回家模式”设置为全部可控设备的明确到家状态，并安全更新已有数据库。

**Architecture:** 场景动作继续由既有 `execute_scene` 逐条转为 MQTT 指令，不增加新的 API。数据库初始化时用一个仅匹配未改名预置场景的修复函数，将新旧数据库的场景动作和描述统一为 10 条可控设备动作。

**Tech Stack:** Python、SQLite、FastAPI、pytest

---

### Task 1: 约束回家场景的完整动作

**Files:**
- Modify: `cloud/backend/tests/test_scenes.py:1-35`

- [ ] **Step 1: Write the failing test**

```python
import json


def test_home_scene_enables_all_controllable_devices(self, client, auth_headers):
    response = client.get("/api/scenes/1", headers=auth_headers)

    assert response.status_code == 200
    scene = response.json()
    actions = json.loads(scene["actions_json"])

    assert scene["description"] == "到家一键启用：全屋灯光、空调、窗帘和加湿器开启，门锁保持上锁"
    assert actions == [
        {"device_type": "light", "room_id": "livingroom", "action": "on", "params": {"brightness": 80}},
        {"device_type": "light", "room_id": "bedroom", "action": "on", "params": {"brightness": 80}},
        {"device_type": "light", "room_id": "study", "action": "on", "params": {"brightness": 80}},
        {"device_type": "ac", "room_id": "livingroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
        {"device_type": "ac", "room_id": "bedroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
        {"device_type": "ac", "room_id": "study", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
        {"device_type": "curtain", "room_id": "livingroom", "action": "open", "params": {}},
        {"device_type": "curtain", "room_id": "study", "action": "open", "params": {}},
        {"device_type": "humidifier", "room_id": "bedroom", "action": "on", "params": {"level": 2, "target_humidity": 60}},
        {"device_type": "door_lock", "room_id": "livingroom", "action": "lock", "params": {}},
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cloud/backend/tests/test_scenes.py::TestScenes::test_home_scene_enables_all_controllable_devices -q`

Expected: FAIL because the current scene only has three actions and an older description.

### Task 2: 更新新建与已有数据库的预置回家场景

**Files:**
- Modify: `cloud/backend/app/database/init_db.py:31-47`
- Modify: `cloud/backend/app/database/init_db.py:157-162`
- Modify: `cloud/backend/app/database/init_db.py:261-265`

- [ ] **Step 1: Add canonical constants and repair function**

```python
HOME_SCENE_DESCRIPTION = "到家一键启用：全屋灯光、空调、窗帘和加湿器开启，门锁保持上锁"
HOME_SCENE_ACTIONS_JSON = json.dumps(
    [
        {"device_type": "light", "room_id": "livingroom", "action": "on", "params": {"brightness": 80}},
        {"device_type": "light", "room_id": "bedroom", "action": "on", "params": {"brightness": 80}},
        {"device_type": "light", "room_id": "study", "action": "on", "params": {"brightness": 80}},
        {"device_type": "ac", "room_id": "livingroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
        {"device_type": "ac", "room_id": "bedroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
        {"device_type": "ac", "room_id": "study", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
        {"device_type": "curtain", "room_id": "livingroom", "action": "open", "params": {}},
        {"device_type": "curtain", "room_id": "study", "action": "open", "params": {}},
        {"device_type": "humidifier", "room_id": "bedroom", "action": "on", "params": {"level": 2, "target_humidity": 60}},
        {"device_type": "door_lock", "room_id": "livingroom", "action": "lock", "params": {}},
    ],
    separators=(",", ":"),
)
LEGACY_HOME_SCENE_ACTIONS_JSON = json.dumps(
    [
        {"device_type": "light", "room_id": "livingroom", "action": "on", "params": {"brightness": 80}},
        {"device_type": "ac", "room_id": "livingroom", "action": "set", "params": {"power": "on", "mode": "cool", "temp": 26}},
        {"device_type": "door_lock", "room_id": "livingroom", "action": "unlock", "params": {"auth_code": "scene-trigger"}},
    ],
    separators=(",", ":"),
)


def repair_home_scene_payload(conn: sqlite3.Connection):
    conn.execute(
        "UPDATE scenes SET description = ?, actions_json = ? "
        "WHERE id = ? AND name = ? AND actions_json = ?",
        (HOME_SCENE_DESCRIPTION, HOME_SCENE_ACTIONS_JSON, 1, "回家模式", LEGACY_HOME_SCENE_ACTIONS_JSON),
    )
```

- [ ] **Step 2: Invoke repair before returning for an existing database**

```python
if count > 0:
    repair_legacy_rule_payloads(conn)
    repair_home_scene_payload(conn)
    return
```

- [ ] **Step 3: Use the same constants for the new-database seed**

```python
conn.execute(
    "INSERT INTO scenes (id, name, icon, description, actions_json) VALUES (?, ?, ?, ?, ?)",
    (1, "回家模式", "🏠", HOME_SCENE_DESCRIPTION, HOME_SCENE_ACTIONS_JSON),
)
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `python -m pytest cloud/backend/tests/test_scenes.py::TestScenes::test_home_scene_enables_all_controllable_devices -q`

Expected: PASS.

### Task 3: 验证已有数据库的兼容修复

**Files:**
- Modify: `cloud/backend/tests/test_scenes.py:87-90`

- [ ] **Step 1: Write the failing migration test**

```python
from app.database import init_db
from app.database.init_db import HOME_SCENE_ACTIONS_JSON, HOME_SCENE_DESCRIPTION, LEGACY_HOME_SCENE_ACTIONS_JSON


def test_init_db_repairs_legacy_home_scene(self, db):
    db.execute(
        "UPDATE scenes SET description = ?, actions_json = ? WHERE id = 1",
        ("到家一键开启：客厅灯亮 + 空调制冷 + 门禁解锁", LEGACY_HOME_SCENE_ACTIONS_JSON),
    )
    db.commit()

    init_db()

    repaired = db.execute("SELECT description, actions_json FROM scenes WHERE id = 1").fetchone()
    assert repaired["description"] == HOME_SCENE_DESCRIPTION
    assert json.loads(repaired["actions_json"]) == json.loads(HOME_SCENE_ACTIONS_JSON)
```

- [ ] **Step 2: Run test to verify it fails before Task 2 implementation**

Run: `python -m pytest cloud/backend/tests/test_scenes.py::TestScenes::test_init_db_repairs_legacy_home_scene -q`

Expected: FAIL because the old scene payload remains unchanged.

- [ ] **Step 3: Run the focused migration test after Task 2 implementation**

Run: `python -m pytest cloud/backend/tests/test_scenes.py::TestScenes::test_init_db_repairs_legacy_home_scene -q`

Expected: PASS.

### Task 4: Run regression suite

**Files:**
- Verify: `cloud/backend/tests/test_scenes.py`
- Verify: `tests/`

- [ ] **Step 1: Run scene tests**

Run: `python -m pytest cloud/backend/tests/test_scenes.py -q`

Expected: PASS.

- [ ] **Step 2: Run repository test suite**

Run: `python -m pytest tests -q`

Expected: PASS.

- [ ] **Step 3: Inspect the final patch**

Run: `git diff --check; git diff -- cloud/backend/app/database/init_db.py cloud/backend/tests/test_scenes.py`

Expected: no whitespace errors; only the canonical home-scene payload, compatibility repair, and regression tests are changed.
