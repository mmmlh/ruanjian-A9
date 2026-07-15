# Home Assistant Aligned A9 Medium Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a medium-scope A9 smart-home refactor that makes device discovery, dashboard summary, control feedback, monitoring, and rules feel like a real smart-home workflow without replacing the existing FastAPI, MQTT, and OpenHarmony architecture.

**Architecture:** Keep the existing backend and ArkTS page structure, but add one stable backend presentation layer for device/candidate/dashboard data, one lightweight activity-log layer for scenes and rules, and one consistent service-call response contract consumed by all control pages. Frontend pages should stop guessing device capabilities and instead render backend-curated fields such as `online`, `status_summary`, `last_seen_at`, and `changed_states`.

**Tech Stack:** FastAPI, SQLite, MQTT, pytest, OpenHarmony ArkTS, hvigor

---

### Task 1: Stabilize Candidate Discovery and Binding

**Files:**
- Modify: `cloud/backend/tests/test_dashboard_contract.py`
- Modify: `cloud/backend/tests/test_devices.py`
- Modify: `cloud/backend/app/services/discovery_catalog.py`
- Modify: `cloud/backend/app/api/discovery.py`
- Modify: `cloud/backend/app/api/bind_device.py`

- [ ] **Step 1: Extend the backend contract tests to lock candidate-device behavior**

Add the following tests to `cloud/backend/tests/test_dashboard_contract.py` so the new response shape is fixed before implementation:

```python
def test_discovery_returns_candidate_status_summary_and_last_seen(self, client, auth_headers, monkeypatch):
    self._restrict_discovery_to_seeded_rooms(monkeypatch)

    response = client.post("/api/discovery", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "candidate_catalog"
    assert isinstance(payload["discovered"], list)
    candidate = payload["discovered"][0]
    assert "status" in candidate
    assert "status_summary" in candidate
    assert "last_seen_at" in candidate
    assert isinstance(candidate["status_summary"], str)
    assert candidate["status_summary"].strip()

def test_bind_device_rejects_duplicate_binding(self, client, auth_headers, monkeypatch):
    self._restrict_discovery_to_seeded_rooms(monkeypatch)
    candidate = client.post("/api/discovery", headers=auth_headers).json()["discovered"][0]

    first = client.post(
        "/api/bind_device",
        json={"device_id": candidate["id"], "room_id": 1, "name": "Duplicate Guard"},
        headers=auth_headers,
    )
    assert first.status_code == 200

    second = client.post(
        "/api/bind_device",
        json={"device_id": candidate["id"], "room_id": 1, "name": "Duplicate Guard"},
        headers=auth_headers,
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "candidate_already_bound"
```

Add one detail check in `cloud/backend/tests/test_devices.py` so the binding response becomes UI-friendly:

```python
def test_bind_device_response_contains_room_name_and_status_summary(self, client, auth_headers, monkeypatch):
    from app.api import discovery as discovery_api

    monkeypatch.setattr(discovery_api, "ROOMS", ["livingroom", "bedroom", "study"])
    candidate = client.post("/api/discovery", headers=auth_headers).json()["discovered"][0]

    response = client.post(
        "/api/bind_device",
        json={"device_id": candidate["id"], "room_id": 1, "name": "Guest Lamp"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["room_name"] == "客厅"
    assert payload["device"]["status_summary"]
```

- [ ] **Step 2: Run the discovery/binding contract tests and confirm they fail**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py -v
```

Expected: FAIL because the current discovery payload does not include `status_summary` or `last_seen_at`, and the bound-device response is not yet normalized for the new UI contract.

- [ ] **Step 3: Implement candidate normalization in the discovery catalog and bind endpoint**

In `cloud/backend/app/services/discovery_catalog.py`, add a small formatter so every candidate returns stable fields:

```python
from datetime import datetime, timezone

def summarize_candidate_status(device_type: str, status: dict[str, Any]) -> str:
    if device_type == "light":
        return "Power on" if status.get("power") == "on" else "Power off"
    if device_type == "ac":
        if status.get("power") == "on":
            return f"{status.get('mode', 'cool')} {status.get('temp', 26)}C"
        return "Standby"
    if device_type == "door_lock":
        return "Locked" if status.get("locked", True) else "Unlocked"
    if device_type == "curtain":
        return f"Open {int(status.get('position', 0))}%"
    if device_type == "humidifier":
        return f"Target humidity {int(status.get('target_humidity', 60))}%"
    return json.dumps(status, ensure_ascii=False)

def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    normalized["status_summary"] = summarize_candidate_status(candidate["type"], candidate["status"])
    normalized["last_seen_at"] = datetime.now(timezone.utc).isoformat()
    return normalized
```

Then use it from `list_unbound_candidates()`:

```python
def list_unbound_candidates(...):
    ...
    return [normalize_candidate(item) for item in _build_unbound_candidates(...)]
```

In `cloud/backend/app/api/bind_device.py`, normalize the response after `create_bound_device()` so the frontend gets the same shape it saw during scanning:

```python
from app.services.discovery_catalog import summarize_candidate_status

...
    device["status_summary"] = summarize_candidate_status(
        device["type"],
        device.get("status", {}),
    )
    device["last_seen_at"] = device.get("updated_at") or device.get("created_at")
```

In `cloud/backend/app/api/discovery.py`, keep the response intentionally non-mutating and explicit:

```python
return {
    "discovered": discovered,
    "count": len(discovered),
    "source": "candidate_catalog",
    "mutates_devices": False,
}
```

- [ ] **Step 4: Re-run the targeted backend tests**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py -v
```

Expected: PASS for the new candidate-payload and duplicate-binding assertions.

- [ ] **Step 5: Commit the discovery/binding slice**

```bash
git add cloud/backend/tests/test_dashboard_contract.py cloud/backend/tests/test_devices.py cloud/backend/app/services/discovery_catalog.py cloud/backend/app/api/discovery.py cloud/backend/app/api/bind_device.py
git commit -m "feat: stabilize discovery candidate binding flow"
```

### Task 2: Add a Shared Backend Device Presentation Layer

**Files:**
- Create: `cloud/backend/app/services/device_view.py`
- Modify: `cloud/backend/app/api/devices.py`
- Modify: `cloud/backend/app/api/dashboard.py`
- Modify: `cloud/backend/app/services/entity_state.py`
- Modify: `cloud/backend/tests/test_dashboard_contract.py`
- Modify: `cloud/backend/tests/test_devices.py`

- [ ] **Step 1: Add failing tests for online state and status summaries**

Extend `cloud/backend/tests/test_dashboard_contract.py`:

```python
def test_dashboard_summary_devices_include_online_and_status_summary(self, client, auth_headers):
    response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200
    device = response.json()["devices"][0]
    assert "online" in device
    assert "status_summary" in device
    assert "last_seen_at" in device

def test_dashboard_stats_match_device_online_flags(self, client, auth_headers):
    response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    online_count = sum(1 for item in payload["devices"] if item["online"])
    assert payload["stats"]["online_devices"] == online_count
```

Extend `cloud/backend/tests/test_devices.py`:

```python
def test_list_devices_returns_presentation_fields(self, client, auth_headers):
    response = client.get("/api/devices", headers=auth_headers)

    assert response.status_code == 200
    device = response.json()[0]
    assert "online" in device
    assert "status_summary" in device
    assert "last_seen_at" in device
```

- [ ] **Step 2: Run the dashboard and devices tests to capture the failing contract**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py -v
```

Expected: FAIL because `/api/devices` and `/api/dashboard/summary` currently return raw DB rows without presentation fields.

- [ ] **Step 3: Create a reusable `device_view` helper and wire it into list endpoints**

Create `cloud/backend/app/services/device_view.py`:

```python
from datetime import datetime, timedelta, timezone
import json

ONLINE_FRESHNESS_WINDOW = timedelta(minutes=10)

def parse_updated_at(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed

def is_online(updated_at: str | None, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    seen_at = parse_updated_at(updated_at)
    return seen_at is not None and now - seen_at <= ONLINE_FRESHNESS_WINDOW

def summarize_status(device_type: str, status_json: str) -> str:
    status = json.loads(status_json or "{}")
    if device_type == "light":
        return f"Brightness {status.get('brightness', 0)}%" if status.get("power") == "on" else "Power off"
    if device_type == "ac":
        return f"{status.get('mode', 'cool')} {status.get('temp', 26)}C" if status.get("power") == "on" else "Standby"
    if device_type == "door_lock":
        return "Locked" if status.get("locked", True) else "Unlocked"
    if device_type == "curtain":
        return f"Open {int(status.get('position', 0))}%"
    if device_type == "humidifier":
        return f"Target humidity {int(status.get('target_humidity', 60))}%"
    if device_type in {"temperature_sensor", "humidity_sensor"}:
        return str(status.get("value", "--"))
    if device_type == "pir_sensor":
        return "Motion detected" if status.get("presence") else "Area idle"
    return "Unknown"

def present_device(row: dict, now: datetime | None = None) -> dict:
    result = dict(row)
    result["last_seen_at"] = result.get("updated_at") or result.get("created_at")
    result["online"] = is_online(result.get("updated_at"), now=now)
    result["status_summary"] = summarize_status(result["type"], result.get("status_json") or "{}")
    return result
```

Use it from `cloud/backend/app/api/devices.py`:

```python
from app.services.device_view import present_device

...
    return [present_device(dict(row)) for row in rows]
...
    result = present_device(dict(row))
    result["status"] = json.loads(result.get("status_json") or "{}")
    return result
```

Use it from `cloud/backend/app/api/dashboard.py`:

```python
from app.services.device_view import is_online, present_device

...
        devices = [present_device(dict(row), now=now) for row in ...]
...
    online_devices = sum(1 for device in devices if device["online"])
```

In `cloud/backend/app/services/entity_state.py`, mirror the same semantics in Home-Assistant-style state attributes:

```python
from app.services.device_view import is_online, summarize_status

...
    attributes["online"] = is_online(device.get("updated_at"))
    attributes["status_summary"] = summarize_status(device["type"], device.get("status_json") or "{}")
```

- [ ] **Step 4: Re-run the targeted backend contract tests**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py -v
```

Expected: PASS for presentation-field assertions and online-count consistency.

- [ ] **Step 5: Commit the backend presentation layer**

```bash
git add cloud/backend/app/services/device_view.py cloud/backend/app/api/devices.py cloud/backend/app/api/dashboard.py cloud/backend/app/services/entity_state.py cloud/backend/tests/test_dashboard_contract.py cloud/backend/tests/test_devices.py
git commit -m "feat: add shared device presentation layer"
```

### Task 3: Refactor the Dashboard and Device Management Pages Around Backend-Curated Fields

**Files:**
- Modify: `openharmony/entry/src/main/ets/model/DeviceModel.ets`
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`

- [ ] **Step 1: Extend ArkTS models so the compiler enforces the new data contract**

Update `openharmony/entry/src/main/ets/model/DeviceModel.ets`:

```ts
export class Device {
  id: number = 0
  room_id: number = 0
  type: string = ''
  name: string = ''
  brand: string = ''
  mqtt_topic: string = ''
  status_json: string = ''
  room_name: string = ''
  updated_at: string = ''
  last_seen_at: string = ''
  status_summary: string = ''
  online: boolean = false
}

export class DiscoveredDevice {
  id: string = ''
  room: string = ''
  room_hint: string = ''
  type: string = ''
  name: string = ''
  brand: string = ''
  mqtt_topic: string = ''
  status: Record<string, Object> = {}
  status_summary: string = ''
  last_seen_at: string = ''
  online: boolean = true
}
```

- [ ] **Step 2: Map the new fields in `ApiClient.ets`**

Update the device mappers in `openharmony/entry/src/main/ets/common/ApiClient.ets`:

```ts
function mapDevice(record: Record<string, Object>): Device {
  let device = new Device()
  ...
  device.updated_at = readString(record, 'updated_at')
  device.last_seen_at = readString(record, 'last_seen_at', device.updated_at)
  device.status_summary = readString(record, 'status_summary')
  device.online = readBoolean(record, 'online', false)
  return device
}

function mapDiscoveredDevice(record: Record<string, Object>): DiscoveredDevice {
  let device = new DiscoveredDevice()
  ...
  device.status_summary = readString(record, 'status_summary')
  device.last_seen_at = readString(record, 'last_seen_at')
  device.online = readBoolean(record, 'online', true)
  return device
}
```

- [ ] **Step 3: Update `DashboardPage.ets` and `DeviceManagePage.ets` to render the curated fields**

In `DashboardPage.ets`, stop recomputing every status label from `status_json` when `status_summary` is already available:

```ts
static status(device: Device): string {
  if (device.status_summary) {
    return device.status_summary
  }
  let s = parseDeviceStatus(device.status_json)
  ...
}

dotColor(device: Device): string {
  if (!device.online) {
    return '#D7DEE6'
  }
  ...
}
```

Pass both `deviceType` and `deviceId` when opening the remote page:

```ts
this.getUIContext().getRouter().pushUrl({
  url: 'pages/DeviceRemotePage',
  params: { 'deviceType': device.type, 'deviceId': device.id }
})
```

In `DeviceManagePage.ets`, surface candidate summaries and timestamps:

```ts
Text(candidate.status_summary || 'No recent state').fontSize(11).fontColor('#8C8C8C')
Text(candidate.last_seen_at ? candidate.last_seen_at.substring(5, 16) : 'Just discovered')
  .fontSize(10).fontColor('#B0B0B0').margin({ top: 4 })
```

Do the same for bound devices:

```ts
Text(device.online ? 'Online' : 'Offline')
  .fontSize(11)
  .fontColor(device.online ? '#8FBF7F' : '#D49595')
Text(device.status_summary || 'No state').fontSize(11).fontColor('#8C8C8C').margin({ top: 2 })
```

- [ ] **Step 4: Compile the OpenHarmony app and confirm the type changes are wired correctly**

Run:

```powershell
cd openharmony
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected: PASS and regenerate `openharmony/entry/build/default/outputs/default/entry-default-signed.hap`.

- [ ] **Step 5: Commit the dashboard/device-management frontend slice**

```bash
git add openharmony/entry/src/main/ets/model/DeviceModel.ets openharmony/entry/src/main/ets/common/ApiClient.ets openharmony/entry/src/main/ets/pages/DashboardPage.ets openharmony/entry/src/main/ets/pages/DeviceManagePage.ets
git commit -m "feat: align dashboard and device management with backend device views"
```

### Task 4: Unify Service Call Results and Tighten the Remote-Control Loop

**Files:**
- Modify: `cloud/backend/tests/test_devices.py`
- Modify: `cloud/backend/app/services/device_command.py`
- Modify: `cloud/backend/app/api/services.py`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`

- [ ] **Step 1: Lock the service-call response with failing backend tests**

Extend `cloud/backend/tests/test_devices.py`:

```python
def test_service_call_returns_changed_state_list(self, client, auth_headers):
    response = client.post(
        "/api/services",
        json={"entity_id": "light.device_4", "action": "on", "params": {"brightness": 75}},
        headers=auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["changed_states"], list)
    assert payload["changed_states"]
    assert payload["changed_states"][0]["entity_id"] == "light.device_4"

def test_service_call_error_payload_is_stable_when_publish_fails(self, client, auth_headers, monkeypatch):
    import app.services.device_command as device_command_service

    def fail_publish(topic: str, payload: str):
        raise RuntimeError("mqtt offline")

    monkeypatch.setattr(device_command_service, "publish_message", fail_publish)

    response = client.post(
        "/api/services",
        json={"entity_id": "light.device_4", "action": "on"},
        headers=auth_headers,
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "command_dispatch_failed"
```

- [ ] **Step 2: Run the focused service-call tests**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_devices.py -v
```

Expected: one or more tests fail if `changed_states` and device state wiring are not yet stable enough for the remote page.

- [ ] **Step 3: Normalize `execute_entity_command()` output and use it directly from `/api/services`**

In `cloud/backend/app/services/device_command.py`, make the return payload explicit and future-safe:

```python
return {
    "device_id": device_id,
    "entity_id": f"{device['type']}.device_{device_id}",
    "action": actual_action,
    "payload": payload,
    "topic": topic,
    "changed_state": build_state(dict(updated)) if updated else None,
    "message": f"{device['name']} {actual_action} command dispatched",
}
```

In `cloud/backend/app/api/services.py`, use the service result directly:

```python
@router.post("")
def call_service(req: ServiceCallRequest, user: dict = Depends(get_current_user)):
    result = execute_entity_command(req.entity_id, req.action, req.params, user)
    changed_state = result["changed_state"]
    return {
        "success": True,
        "message": result["message"],
        "entity_id": result["entity_id"],
        "action": result["action"],
        "changed_states": [changed_state] if changed_state else [],
        "service_response": {
            result["entity_id"]: {
                "topic": result["topic"],
                "action": result["action"],
                "payload": result["payload"],
            }
        },
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
```

In `DeviceRemotePage.ets`, default to the specific `deviceId` when arriving from the dashboard:

```ts
aboutToAppear(): void {
  let p = this.getUIContext().getRouter().getParams() as Record<string, Object>
  if (p && p['deviceType'] !== undefined) {
    this.dt = p['deviceType'] as string
  }
  if (p && p['deviceId'] !== undefined) {
    this.pendingDeviceId = p['deviceId'] as number
  }
  this.load()
}
```

Use the `changed_states` response before forcing a reload:

```ts
let result = await callService(eid, action, params)
this.successMessage = result.message || 'Command sent successfully'
if (result.changed_states.length > 0) {
  let updated = result.changed_states[0]
  let current = this.cur()
  if (current) {
    current.status_json = JSON.stringify(updated.attributes)
    current.updated_at = updated.last_updated
    this.sl(this.ix)
  }
}
await this.load()
```

Add a small debounce for slider-driven actions:

```ts
private sliderTimer: number = -1

queueSliderCommand(action: string, params: CommandParams): void {
  if (this.sliderTimer > 0) {
    clearTimeout(this.sliderTimer)
  }
  this.sliderTimer = setTimeout(() => {
    this.sliderTimer = -1
    this.cmdCurrent(action, params)
  }, 250)
}
```

- [ ] **Step 4: Re-run backend tests and rebuild OpenHarmony**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_devices.py -v
cd ..\..\openharmony
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected: backend tests PASS and the ArkTS build succeeds with the new route-param and state-refresh logic.

- [ ] **Step 5: Commit the unified service-call slice**

```bash
git add cloud/backend/tests/test_devices.py cloud/backend/app/services/device_command.py cloud/backend/app/api/services.py openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets
git commit -m "feat: unify service call results for remote control"
```

### Task 5: Add a Lightweight Activity Log and Upgrade the Monitor Page

**Files:**
- Modify: `cloud/backend/app/database/init_db.py`
- Create: `cloud/backend/app/services/activity_log.py`
- Modify: `cloud/backend/app/api/scenes.py`
- Modify: `cloud/backend/app/services/rule_engine.py`
- Modify: `cloud/backend/app/api/data.py`
- Modify: `cloud/backend/tests/test_data.py`
- Modify: `openharmony/entry/src/main/ets/model/DeviceModel.ets`
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`

- [ ] **Step 1: Add failing tests for activity-log records**

Extend `cloud/backend/tests/test_data.py`:

```python
def test_logs_endpoint_returns_activity_log_records(self, client, auth_headers):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO activity_log (event_type, title, detail, source, user_id) VALUES (?, ?, ?, ?, ?)",
            ("scene", "Home Mode", "Executed scene", "scenes.execute", 1),
        )

    response = client.get("/api/data/logs", headers=auth_headers)
    assert response.status_code == 200
    item = response.json()[0]
    assert "event_type" in item
    assert item["event_type"] in {"device", "scene", "rule"}
```

Add one filter assertion:

```python
def test_logs_endpoint_filters_by_event_type(self, client, auth_headers):
    response = client.get("/api/data/logs?event_type=scene", headers=auth_headers)
    assert response.status_code == 200
```

- [ ] **Step 2: Run the data tests and capture the missing-table failure**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_data.py -v
```

Expected: FAIL because `activity_log` does not exist yet and `/api/data/logs` only reads `device_log`.

- [ ] **Step 3: Introduce `activity_log` and merge it into the monitor API**

In `cloud/backend/app/database/init_db.py`, add the table:

```sql
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
```

Create `cloud/backend/app/services/activity_log.py`:

```python
from app.database.connection import get_db

def write_activity(event_type: str, title: str, detail: str, source: str, device_id: int | None = None, user_id: int | None = None) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (event_type, title, detail, source, device_id, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_type, title, detail, source, device_id, user_id),
        )
```

Log scene execution in `cloud/backend/app/api/scenes.py`:

```python
from app.services.activity_log import write_activity

...
    write_activity(
        event_type="scene",
        title=scene["name"],
        detail=json.dumps({"executed": len(executed)}, ensure_ascii=False),
        source="scenes.execute",
        user_id=int(user["sub"]),
    )
```

Log rule triggers in `cloud/backend/app/services/rule_engine.py`:

```python
from app.services.activity_log import write_activity

...
                    write_activity(
                        event_type="rule",
                        title=rule["name"],
                        detail=json.dumps({"room_id": room_id, "trigger": sensor_type}, ensure_ascii=False),
                        source="rules.trigger",
                    )
```

Merge `device_log` and `activity_log` in `cloud/backend/app/api/data.py`:

```python
@router.get("/logs")
def get_device_logs(..., event_type: Optional[str] = None, ...):
    entries = []
    with get_db() as conn:
        device_rows = conn.execute(...).fetchall()
        activity_query = "SELECT * FROM activity_log WHERE 1=1"
        activity_params = []
        if event_type:
            activity_query += " AND event_type = ?"
            activity_params.append(event_type)
        activity_query += " ORDER BY timestamp DESC LIMIT ?"
        activity_params.append(limit)
        activity_rows = conn.execute(activity_query, activity_params).fetchall()

    for row in device_rows:
        item = dict(row)
        item["event_type"] = "device"
        item["title"] = row["action"]
        entries.append(item)

    for row in activity_rows:
        entries.append(dict(row))

    entries.sort(key=lambda item: item["timestamp"], reverse=True)
    return entries[:limit]
```

In `DataMonitorPage.ets`, prefer `event_type` and `title` when present:

```ts
Text((item.title || this.al(item.action)) + ' · ' + this.tm(item.timestamp))
```

- [ ] **Step 4: Re-run tests, rebuild the app, and verify the monitor page compiles**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_data.py -v
cd ..\..\openharmony
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected: PASS for the new activity-log tests and a successful HAP build.

- [ ] **Step 5: Commit the monitoring/activity-log slice**

```bash
git add cloud/backend/app/database/init_db.py cloud/backend/app/services/activity_log.py cloud/backend/app/api/scenes.py cloud/backend/app/services/rule_engine.py cloud/backend/app/api/data.py cloud/backend/tests/test_data.py openharmony/entry/src/main/ets/model/DeviceModel.ets openharmony/entry/src/main/ets/common/ApiClient.ets openharmony/entry/src/main/ets/pages/DataMonitorPage.ets
git commit -m "feat: add activity logging for monitor workflows"
```

### Task 6: Finish the Rules Options Contract and Refactor the Rules Page Into a Stable Form Builder

**Files:**
- Modify: `cloud/backend/tests/test_rules.py`
- Modify: `cloud/backend/app/api/rules.py`
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets`

- [ ] **Step 1: Extend the rules contract tests with UI-facing expectations**

Update `cloud/backend/tests/test_rules.py`:

```python
def test_rule_options_return_labels_actions_and_room_names(self, client, auth_headers):
    response = client.get("/api/rules/options", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["triggers"]
    assert payload["targets"]
    assert payload["operators"]
    assert all("label" in item for item in payload["triggers"])
    assert all("actions" in item for item in payload["targets"])

def test_create_rule_rejects_missing_name(self, client, auth_headers):
    response = client.post(
        "/api/rules",
        json={"name": "", "condition_json": "{}", "action_json": "[]", "enabled": 1},
        headers=auth_headers,
    )
    assert response.status_code == 422 or response.status_code == 400
```

- [ ] **Step 2: Run the rules tests**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_rules.py -v
```

Expected: FAIL if the options payload is too raw or the create endpoint accepts obviously invalid requests.

- [ ] **Step 3: Tighten `/api/rules/options` and simplify the ArkTS form logic**

In `cloud/backend/app/api/rules.py`, keep the API authoritative about supported actions:

```python
operators = [
    {"label": "Equals", "value": "eq"},
    {"label": "Not equal", "value": "neq"},
    {"label": "Greater than", "value": "gt"},
    {"label": "Greater or equal", "value": "gte"},
    {"label": "Less than", "value": "lt"},
    {"label": "Less or equal", "value": "lte"},
]
```

Guard rule creation with minimal validation:

```python
if not req.name.strip():
    raise HTTPException(status_code=400, detail="rule_name_required")
```

In `RulesPage.ets`, build a readable summary instead of raw JSON echoes:

```ts
cs(r: AutomationRule): string {
  try {
    let c = JSON.parse(r.condition_json) as Record<string, Object>
    return `If ${String(c['trigger'])} ${String(c['operator'])} ${String(c['value'])}`
  } catch (e) {
    return 'Condition unavailable'
  }
}

as(r: AutomationRule): string {
  try {
    let a = JSON.parse(r.action_json) as Array<Object>
    if (a.length === 0) return 'No action'
    let f = a[0] as Record<string, Object>
    return `Then ${String(f['device_type'])} -> ${String(f['action'])}`
  } catch (e) {
    return 'Action unavailable'
  }
}
```

Reset the dialog state after successful creation:

```ts
resetDialog(): void {
  this.nm = ''
  this.vl = '28'
  this.modeValue = 'cool'
  this.tempValue = 26
  this.brightnessValue = 80
  this.targetHumidityValue = 60
  this.levelValue = 2
}

...
await createRule(...)
this.resetDialog()
this.dlg = false
```

- [ ] **Step 4: Re-run backend tests and rebuild OpenHarmony**

Run:

```powershell
cd cloud/backend
python -m pytest tests/test_rules.py -v
cd ..\..\openharmony
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected: rules tests PASS and no ArkTS compile regressions.

- [ ] **Step 5: Commit the rules-form slice**

```bash
git add cloud/backend/tests/test_rules.py cloud/backend/app/api/rules.py openharmony/entry/src/main/ets/pages/RulesPage.ets
git commit -m "feat: stabilize rules options and form flow"
```

### Task 7: Run Full Verification and Execute the Manual Acceptance Path

**Files:**
- Modify: `docs/manual` only if the verification reveals required user-facing runbook updates
- No required code creation; this task is for proof and cleanup

- [ ] **Step 1: Run the full backend suite**

Run:

```powershell
cd cloud/backend
python -m pytest tests -v
```

Expected: PASS across `test_dashboard_contract.py`, `test_devices.py`, `test_data.py`, `test_rules.py`, `test_auth.py`, `test_integration.py`, and the remaining backend suites.

- [ ] **Step 2: Build the OpenHarmony app from a clean daemon state**

Run:

```powershell
cd openharmony
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected: PASS and produce `openharmony/entry/build/default/outputs/default/entry-default-signed.hap`.

- [ ] **Step 3: Perform the manual acceptance path in this exact order**

Use this checklist:

```text
1. Open DashboardPage and confirm online counts, temperature, humidity, scenes, and recent activity render.
2. Open DeviceManagePage, run Scan, bind one candidate device to a room, and confirm it moves into the bound-device section.
3. Return to DashboardPage and confirm the newly bound device appears in the room grid.
4. Tap the new device card, land on DeviceRemotePage, run one control action, and confirm success feedback plus state refresh.
5. Open DataMonitorPage and confirm Live, History, and Logs all show meaningful data.
6. Open RulesPage, create one rule through the form, toggle it once, and delete the temporary rule.
```

- [ ] **Step 4: Capture any final drift fixes discovered during verification**

If verification reveals contract mismatches, apply only small cleanup changes such as:

```text
- label mismatch between backend operator names and RulesPage chips
- missing `online` / `status_summary` mapping in one model path
- scene or rule log entries missing from monitor sorting
- route-param mismatch for `deviceId` on DeviceRemotePage
```

Re-run only the affected test/build command after each cleanup.

- [ ] **Step 5: Commit the verified integrated result**

```bash
git add -A
git commit -m "feat: deliver home-assistant-aligned medium refactor"
```
