# Hardware-Free Environment Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep virtual sensor devices online and show each remote page's room temperature and humidity during a no-hardware demo.

**Architecture:** Extend `main.py`'s existing state synchronizer to process sensor MQTT messages, so the simulator's five-second readings update both sensor history and device freshness. `DeviceRemotePage` will reuse `getDevicesForUi(roomId)` to load room sensors, derive display values locally, and periodically refresh only those values.

**Tech Stack:** FastAPI, SQLite, MQTT, ArkTS/OpenHarmony, pytest, Hvigor.

---

### Task 1: Synchronize sensor readings into device state

**Files:**
- Modify: `D:\ruanjianbei\smart-home-A9\cloud\backend\tests\test_devices.py:286-306`
- Modify: `D:\ruanjianbei\smart-home-A9\cloud\backend\app\main.py:118-160`

- [ ] **Step 1: Add a failing MQTT sensor-state regression**

```python
def test_mqtt_sensor_updates_sensor_device_state_and_freshness(self, client, db):
    db.execute("UPDATE devices SET updated_at = ? WHERE id = 1", ("2000-01-01 00:00:00",))
    db.commit()

    on_mqtt_message(
        "home/livingroom/temperature_sensor/sensor",
        {"value": 26.4, "unit": "celsius", "device_id": "temp_001", "ts": 1},
    )

    row = db.execute("SELECT status_json, updated_at FROM devices WHERE id = 1").fetchone()
    assert json.loads(row["status_json"]) == {"value": 26.4, "unit": "celsius", "ts": 1}
    assert row["updated_at"] != "2000-01-01 00:00:00"
```

- [ ] **Step 2: Verify the regression fails**

Run: `python -m pytest cloud/backend/tests/test_devices.py::TestDevices::test_mqtt_sensor_updates_sensor_device_state_and_freshness -q`

Expected: FAIL because `sensor` topics are ignored by `_sync_device_status`.

- [ ] **Step 3: Accept sensor topics in the shared synchronizer**

```python
def _sync_device_status(topic: str, payload):
    """Persist device state from status, response, and sensor topics."""
    # Existing JSON parsing remains unchanged.
    parts = topic.split("/")
    if len(parts) < 4 or parts[-1] not in {"status", "response", "sensor"}:
        return
    # Keep response-state extraction for response topics only.
    # Existing status filtering and UPDATE devices ... updated_at remain unchanged.
```

The existing metadata filter removes `device_id` from sensor status while retaining `value`, `unit`, and `ts`.

- [ ] **Step 4: Verify the backend regression passes**

Run: `python -m pytest cloud/backend/tests/test_devices.py::TestDevices::test_mqtt_sensor_updates_sensor_device_state_and_freshness -q`

Expected: PASS.

### Task 2: Show room environment on every remote page

**Files:**
- Create: `D:\ruanjianbei\smart-home-A9\tests\test_remote_environment_demo_regression.py`
- Modify: `D:\ruanjianbei\smart-home-A9\openharmony\entry\src\main\ets\pages\DeviceRemotePage.ets:34-91,148-179,531-542`

- [ ] **Step 1: Add a failing remote-environment regression**

```python
def test_device_remote_page_refreshes_and_displays_room_environment():
    source = REMOTE_PAGE.read_text(encoding="utf-8")

    assert "@State roomDevices: Device[] = []" in source
    assert "async refreshRoomEnvironment(): Promise<void>" in source
    assert "await getDevicesForUi(current.room_id)" in source
    assert "private environmentTimer: number = -1" in source
    assert "setInterval(() => {" in source
    assert "this.refreshRoomEnvironment()" in source
    assert "室内温度" in source
    assert "室内湿度" in source
    assert "湿度未采集" in source
```

- [ ] **Step 2: Verify the frontend regression fails**

Run: `python -m pytest tests/test_remote_environment_demo_regression.py -q`

Expected: FAIL because the remote page has no room-sensor state, refresh timer, or environment metrics.

- [ ] **Step 3: Add room-environment state, refresh, and cleanup**

```typescript
@State roomDevices: Device[] = []
private environmentTimer: number = -1

async refreshRoomEnvironment(): Promise<void> {
  let current = this.cur()
  if (!current) return
  try {
    this.roomDevices = await getDevicesForUi(current.room_id)
  } catch (_) {
    // Preserve the last valid room readings during a transient refresh failure.
  }
}

startEnvironmentRefresh(): void {
  if (this.environmentTimer > 0) clearInterval(this.environmentTimer)
  this.environmentTimer = setInterval(() => {
    this.refreshRoomEnvironment()
  }, 5000)
}
```

Start the timer after `load()` in `aboutToAppear`, clear it in `aboutToDisappear`, and call `refreshRoomEnvironment()` after selecting a device. Add helpers that find sensor devices by type, parse `status_json`, format temperature as `value + '°C'`, format humidity as `value + '%'`, and return `湿度未采集` when the room has no humidity sensor.

- [ ] **Step 4: Add the compact environment row**

```typescript
Row() {
  MetricChip({ label: '室内温度', value: this.roomTemperature(), tone: 'accent' }).layoutWeight(1)
  Blank().width(10)
  MetricChip({ label: '室内湿度', value: this.roomHumidity(), tone: 'warning' }).layoutWeight(1)
}
.width('100%')
.margin({ top: 10 })
```

Place this row below the existing two summary metrics in `buildStatusHero`; retain the existing device metric and room-information row.

- [ ] **Step 5: Verify the frontend regression passes**

Run: `python -m pytest tests/test_remote_environment_demo_regression.py -q`

Expected: PASS.

### Task 3: Verify, package, and deploy

**Files:**
- Verify: `D:\ruanjianbei\smart-home-A9\cloud\backend\app\main.py`
- Verify: `D:\ruanjianbei\smart-home-A9\openharmony\entry\src\main\ets\pages\DeviceRemotePage.ets`

- [ ] **Step 1: Run focused regression coverage**

Run: `python -m pytest cloud/backend/tests/test_devices.py tests/test_remote_offline_guard_regression.py tests/test_remote_environment_demo_regression.py -q`

Expected: PASS.

- [ ] **Step 2: Run the repository suite and HAP build**

Run: `python -m pytest tests -q`

Run: `cd openharmony; .\hvigorw.bat assembleHap --stacktrace`

Expected: all tests pass and Hvigor reports `BUILD SUCCESSFUL`.

- [ ] **Step 3: Deploy only the backend MQTT synchronizer change**

Upload `cloud/backend/app/main.py` to `/opt/smart-home-A9/backend/app/main.py`, retain a timestamped server backup, rebuild only `backend`, restart it with `docker compose up -d --no-deps backend`, and verify `http://localhost:8000/api/health` returns success.

- [ ] **Step 4: Inspect the final change set**

Run: `git diff --check`

Expected: no whitespace errors.
