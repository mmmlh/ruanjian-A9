# MQTT Device Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover and bind actual MQTT-announcing devices rather than fixed catalog entries.

**Architecture:** Persist validated device hello and heartbeat announcements separately from bound devices. The discovery API returns fresh, unbound announcements; binding atomically materializes an announcement into a device row.

**Tech Stack:** FastAPI, SQLite, Paho MQTT, pytest, OpenHarmony ArkTS.

---

### Task 1: Persist MQTT announcements

**Files:**
- Modify: `cloud/backend/app/database/init_db.py`
- Modify: `cloud/backend/app/services/device_protocol.py`
- Test: `cloud/backend/tests/test_device_protocol.py`

- [ ] **Step 1: Write failing protocol tests**

```python
def test_unbound_hello_is_recorded_as_a_discoverable_device(client, db):
    on_mqtt_message("home/lab/light/hello", HELLO)
    row = db.execute("SELECT hardware_id, mqtt_topic FROM discovered_devices").fetchone()
    assert dict(row) == {"hardware_id": "lab-light-001", "mqtt_topic": "home/lab/light"}
```

- [ ] **Step 2: Run the focused test and observe failure**

Run: `pytest cloud/backend/tests/test_device_protocol.py -k discoverable -v`

- [ ] **Step 3: Add the discovery table and announcement upsert**

```python
conn.execute(
    "INSERT INTO discovered_devices (...) VALUES (...) "
    "ON CONFLICT(hardware_id) DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP"
)
```

- [ ] **Step 4: Run the focused protocol tests**

Run: `pytest cloud/backend/tests/test_device_protocol.py -k discoverable -v`

### Task 2: Expose fresh discovered devices and bind them atomically

**Files:**
- Modify: `cloud/backend/app/services/discovery_catalog.py`
- Modify: `cloud/backend/app/api/discovery.py`
- Modify: `cloud/backend/app/api/bind_device.py`
- Test: `cloud/backend/tests/test_dashboard_contract.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_discovery_returns_a_recent_unbound_mqtt_announcement(client, auth_headers):
    on_mqtt_message("home/lab/light/hello", HELLO)
    result = client.post("/api/discovery", headers=auth_headers).json()
    assert result["source"] == "mqtt_announcements"
    assert result["discovered"][0]["hardware_id"] == "lab-light-001"
```

- [ ] **Step 2: Run the focused contract tests and observe failure**

Run: `pytest cloud/backend/tests/test_dashboard_contract.py -k discovery -v`

- [ ] **Step 3: Replace catalog lookup with freshness-checked discovery lookup**

```python
candidate = get_fresh_unbound_discovery(conn, hardware_id)
if candidate is None:
    raise CandidateNotFoundError("candidate_not_found")
```

- [ ] **Step 4: Run focused contract tests**

Run: `pytest cloud/backend/tests/test_dashboard_contract.py -k discovery -v`

### Task 3: Present real discovery metadata in the client

**Files:**
- Modify: `openharmony/entry/src/main/ets/model/DeviceModel.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`
- Test: `tests/test_ui_polish_regression.py`

- [ ] **Step 1: Write failing source-regression assertions**

```python
assert "candidate.hardware_id" in source
assert "this.err = ''" in scan
```

- [ ] **Step 2: Run the focused UI test and observe failure**

Run: `pytest tests/test_ui_polish_regression.py -k discovery -v`

- [ ] **Step 3: Map and display hardware identifiers; clear stale scan state**

```typescript
Text('设备标识：' + candidate.hardware_id)
this.err = ''
```

- [ ] **Step 4: Run the focused UI test**

Run: `pytest tests/test_ui_polish_regression.py -k discovery -v`

### Task 4: Verify the complete path

**Files:**
- Test: `cloud/backend/tests/test_device_protocol.py`
- Test: `cloud/backend/tests/test_dashboard_contract.py`
- Test: `tests/test_ui_polish_regression.py`

- [ ] **Step 1: Run backend discovery and protocol tests**

Run: `pytest cloud/backend/tests/test_device_protocol.py cloud/backend/tests/test_dashboard_contract.py -v`

- [ ] **Step 2: Run UI regression tests**

Run: `pytest tests/test_ui_polish_regression.py tests/test_ui_theme_regression.py -v`

- [ ] **Step 3: Build OpenHarmony app**

Run: `openharmony/hvigorw.bat --mode module -p module=entry@default -p product=default assembleHap`

- [ ] **Step 4: Run the full Python regression suite**

Run: `pytest cloud/backend/tests tests -q`
