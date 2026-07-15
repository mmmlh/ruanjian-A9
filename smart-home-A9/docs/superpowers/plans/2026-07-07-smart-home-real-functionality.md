# Smart Home Real Functionality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shell-like device discovery, control feedback, monitoring, and rule editing flows with a real end-to-end smart-home workflow across the FastAPI backend and OpenHarmony client.

**Architecture:** First lock the new backend contract with focused pytest coverage for discovery, dashboard summary, control responses, and rule options. Then implement the backend slices that expose real candidate-device discovery and summary APIs, followed by OpenHarmony page refactors that consume those APIs and provide clear success, error, loading, and empty states. Finish by tightening the remote-control and monitoring loops and verifying both backend tests and ArkTS compilation.

**Tech Stack:** FastAPI, SQLite, pytest, OpenHarmony ArkTS, MQTT-backed device state sync, WebSocket updates

---

### Task 1: Lock The New Backend Contract With Tests

**Files:**
- Create: `cloud/backend/tests/test_dashboard_contract.py`
- Modify: `cloud/backend/tests/test_devices.py`
- Modify: `cloud/backend/tests/test_rules.py`

- [ ] **Step 1: Write the failing dashboard and discovery tests**

```python
# cloud/backend/tests/test_dashboard_contract.py
def test_dashboard_summary_returns_rooms_devices_and_recent_logs(client, auth_headers):
    resp = client.get("/api/dashboard/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "rooms" in data
    assert "devices" in data
    assert "stats" in data
    assert "scenes" in data
    assert "recent_logs" in data
    assert data["stats"]["total_devices"] >= len(data["devices"])


def test_discovery_returns_candidates_without_creating_real_devices(client, auth_headers, db):
    before = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    resp = client.post("/api/discovery", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert "discovered" in payload
    after = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    assert after == before


def test_bind_device_creates_bound_device_from_candidate(client, auth_headers):
    discovery = client.post("/api/discovery", headers=auth_headers).json()
    candidate = discovery["discovered"][0]
    resp = client.post(
        "/api/bind_device",
        json={"device_id": candidate["id"], "room_id": 1, "name": "新客厅设备"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["device"]["room_id"] == 1
    assert payload["device"]["name"] == "新客厅设备"
```

- [ ] **Step 2: Add failing control-response and rule-option tests**

```python
# cloud/backend/tests/test_devices.py
def test_service_call_returns_success_message_and_timestamp(client, auth_headers):
    resp = client.post(
        "/api/services",
        json={"entity_id": "light.device_4", "action": "on", "params": {"brightness": 75}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["message"]
    assert payload["entity_id"] == "light.device_4"
    assert payload["executed_at"]


# cloud/backend/tests/test_rules.py
def test_rule_options_endpoint_returns_supported_devices_and_actions(client, auth_headers):
    resp = client.get("/api/rules/options", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert "triggers" in payload
    assert "targets" in payload
    assert any(item["value"] == "temperature_sensor" for item in payload["triggers"])
```

- [ ] **Step 3: Run the focused tests to verify they fail**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\cloud\backend
$env:PYTHONPATH='.'
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py tests/test_rules.py -q
```

Expected:

- `404` for `/api/dashboard/summary` and `/api/rules/options`
- Discovery test fails because `/api/discovery` currently inserts real rows
- Service response test fails because `/api/services` does not yet include `success`, `message`, or `executed_at`

- [ ] **Step 4: Commit the red tests**

```bash
git add cloud/backend/tests/test_dashboard_contract.py cloud/backend/tests/test_devices.py cloud/backend/tests/test_rules.py
git commit -m "test: lock real functionality backend contract"
```

### Task 2: Implement Real Candidate Discovery, Binding, And Dashboard Summary

**Files:**
- Create: `cloud/backend/app/api/dashboard.py`
- Create: `cloud/backend/app/services/discovery_catalog.py`
- Modify: `cloud/backend/app/api/discovery.py`
- Modify: `cloud/backend/app/api/bind_device.py`
- Modify: `cloud/backend/app/api/devices.py`
- Modify: `cloud/backend/app/database/init_db.py`
- Modify: `cloud/backend/app/main.py`

- [ ] **Step 1: Write the discovery helper implementation**

```python
# cloud/backend/app/services/discovery_catalog.py
from __future__ import annotations

import json
from typing import Any

from app.database.connection import get_db


def _status_for_type(device_type: str) -> dict[str, Any]:
    defaults = {
        "light": {"power": "off", "brightness": 0},
        "ac": {"power": "off", "mode": "cool", "temp": 26},
        "door_lock": {"locked": True},
        "temperature_sensor": {"value": 24.5, "unit": "celsius"},
        "humidity_sensor": {"value": 52.0, "unit": "percent"},
        "pir_sensor": {"presence": False},
        "curtain": {"position": 0},
        "humidifier": {"power": "off", "level": 2, "target_humidity": 60},
    }
    return defaults.get(device_type, {})


def list_unbound_candidates() -> list[dict[str, Any]]:
    base_candidates = [
        {"id": "candidate-livingroom-curtain", "room_hint": "客厅", "type": "curtain", "name": "客厅窗帘扩展", "brand": "", "mqtt_topic": "home/livingroom/curtain_extra"},
        {"id": "candidate-study-light", "room_hint": "书房", "type": "light", "name": "书房氛围灯", "brand": "", "mqtt_topic": "home/study/light_extra"},
        {"id": "candidate-bedroom-humidifier", "room_hint": "卧室", "type": "humidifier", "name": "卧室备用加湿器", "brand": "", "mqtt_topic": "home/bedroom/humidifier_extra"},
    ]
    with get_db() as conn:
        existing_topics = {
            row["mqtt_topic"]
            for row in conn.execute("SELECT mqtt_topic FROM devices").fetchall()
        }
    items: list[dict[str, Any]] = []
    for candidate in base_candidates:
        if candidate["mqtt_topic"] in existing_topics:
            continue
        items.append({
            **candidate,
            "status": _status_for_type(candidate["type"]),
            "online": True,
        })
    return items


def create_bound_device(candidate_id: str, room_id: int, custom_name: str | None) -> dict[str, Any]:
    candidate = next((item for item in list_unbound_candidates() if item["id"] == candidate_id), None)
    if candidate is None:
        raise ValueError("candidate_not_found")
    name = custom_name or candidate["name"]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO devices (room_id, type, name, brand, mqtt_topic, status_json) VALUES (?, ?, ?, ?, ?, ?)",
            (room_id, candidate["type"], name, candidate["brand"], candidate["mqtt_topic"], json.dumps(candidate["status"])),
        )
        device_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = conn.execute(
            "SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id WHERE d.id = ?",
            (device_id,),
        ).fetchone()
    return dict(row)
```

- [ ] **Step 2: Rework discovery, binding, and dashboard endpoints around that helper**

```python
# cloud/backend/app/api/discovery.py
@router.post("")
def discover(user: dict = Depends(get_current_user)):
    discovered = list_unbound_candidates()
    return {"discovered": discovered, "count": len(discovered), "source": "candidate_catalog"}


# cloud/backend/app/api/bind_device.py
class BindDeviceRequest(BaseModel):
    device_id: str
    room_id: int
    name: Optional[str] = None


@router.post("")
def bind_device(req: BindDeviceRequest, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        room = conn.execute("SELECT id, name FROM rooms WHERE id = ?", (req.room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="房间不存在")
    try:
        device = create_bound_device(req.device_id, req.room_id, req.name)
    except ValueError:
        raise HTTPException(status_code=404, detail="候选设备不存在")
    return {"success": True, "device": device, "message": f"设备 '{device['name']}' 已绑定到 '{room['name']}'"}


# cloud/backend/app/api/dashboard.py
@router.get("/summary")
def dashboard_summary(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rooms = [dict(row) for row in conn.execute("SELECT r.*, COUNT(d.id) as device_count FROM rooms r LEFT JOIN devices d ON d.room_id = r.id GROUP BY r.id ORDER BY r.id").fetchall()]
        devices = [dict(row) for row in conn.execute("SELECT d.*, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id ORDER BY d.id").fetchall()]
        scenes = [dict(row) for row in conn.execute("SELECT * FROM scenes ORDER BY id").fetchall()]
        recent_logs = [dict(row) for row in conn.execute("SELECT * FROM device_log ORDER BY timestamp DESC LIMIT 8").fetchall()]
    stats = {
        "total_devices": len(devices),
        "online_devices": len(devices),
        "offline_devices": 0,
    }
    return {"rooms": rooms, "devices": devices, "scenes": scenes, "recent_logs": recent_logs, "stats": stats}
```

- [ ] **Step 3: Register the new router and keep seed data stable**

```python
# cloud/backend/app/main.py
from app.api import auth, rooms, devices, data, rules, scenes, states, login, discovery, bind_device, services, dashboard
app.include_router(dashboard.router)


# cloud/backend/app/database/init_db.py
# Do not add random discovery inserts here.
# Keep only deterministic rooms, devices, scenes, and automation rules.
```

- [ ] **Step 4: Run the backend tests to verify the new contract passes**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\cloud\backend
$env:PYTHONPATH='.'
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py tests/test_rules.py -q
```

Expected:

- Dashboard summary returns `rooms`, `devices`, `stats`, `scenes`, and `recent_logs`
- Discovery no longer changes the `devices` row count
- Binding turns a candidate into a real room-bound device

- [ ] **Step 5: Commit the backend discovery and dashboard slice**

```bash
git add cloud/backend/app/api/dashboard.py cloud/backend/app/services/discovery_catalog.py cloud/backend/app/api/discovery.py cloud/backend/app/api/bind_device.py cloud/backend/app/api/devices.py cloud/backend/app/database/init_db.py cloud/backend/app/main.py
git commit -m "feat: add real discovery and dashboard summary"
```

### Task 3: Normalize Service Responses And Rule Options For The Client

**Files:**
- Modify: `cloud/backend/app/api/services.py`
- Modify: `cloud/backend/app/api/rules.py`
- Modify: `cloud/backend/app/services/device_command.py`

- [ ] **Step 1: Add the failing rule-options and service-response assertions if any are still missing**

```python
def test_service_response_includes_changed_states_even_when_empty(client, auth_headers):
    resp = client.post(
        "/api/services",
        json={"entity_id": "door_lock.device_6", "action": "lock"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "changed_states" in payload
    assert "executed_at" in payload
```

- [ ] **Step 2: Implement richer service responses and rule options**

```python
# cloud/backend/app/api/services.py
from datetime import datetime, timezone


@router.post("")
def call_service(req: ServiceCallRequest, user: dict = Depends(get_current_user)):
    result = execute_entity_command(req.entity_id, req.action, req.params, user)
    changed_state = result["changed_state"]
    return {
        "success": True,
        "message": f"{req.entity_id} 执行 {req.action} 成功",
        "entity_id": req.entity_id,
        "action": req.action,
        "changed_states": [changed_state] if changed_state else [],
        "service_response": {
            req.entity_id: {
                "topic": result["topic"],
                "action": result["payload"]["action"],
                "payload": result["payload"],
            }
        },
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


# cloud/backend/app/api/rules.py
@router.get("/options")
def get_rule_options(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        targets = [
            {"device_id": row["id"], "label": row["name"], "type": row["type"], "room_name": row["room_name"]}
            for row in conn.execute("SELECT d.id, d.name, d.type, r.name as room_name FROM devices d JOIN rooms r ON d.room_id = r.id ORDER BY d.id").fetchall()
        ]
    return {
        "triggers": [
            {"label": "温度传感器", "value": "temperature_sensor", "field": "value"},
            {"label": "湿度传感器", "value": "humidity_sensor", "field": "value"},
            {"label": "人体传感器", "value": "pir_sensor", "field": "presence"},
        ],
        "operators": [
            {"label": "大于", "value": "gt"},
            {"label": "小于", "value": "lt"},
            {"label": "等于", "value": "eq"},
        ],
        "actions": {
            "light": ["on", "off", "set"],
            "ac": ["on", "off", "set"],
            "door_lock": ["unlock", "lock"],
            "curtain": ["open", "close", "set"],
            "humidifier": ["on", "off", "set"],
        },
        "targets": targets,
    }
```

- [ ] **Step 3: Run the tests for this slice**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\cloud\backend
$env:PYTHONPATH='.'
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py tests/test_rules.py -q
```

Expected:

- Service responses contain `success`, `message`, `entity_id`, and `executed_at`
- Rule options endpoint exposes supported triggers, operators, actions, and targets

- [ ] **Step 4: Commit the backend contract polish**

```bash
git add cloud/backend/app/api/services.py cloud/backend/app/api/rules.py cloud/backend/app/services/device_command.py
git commit -m "feat: enrich service responses and rule options"
```

### Task 4: Rebuild Device Management Around Candidate Binding

**Files:**
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Modify: `openharmony/entry/src/main/ets/model/DeviceModel.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`

- [ ] **Step 1: Add API models and methods for dashboard summary, discovery, and rule options**

```ts
// openharmony/entry/src/main/ets/model/DeviceModel.ets
export class DiscoveredDevice {
  id: string = ''
  room_hint: string = ''
  type: string = ''
  name: string = ''
  brand: string = ''
  mqtt_topic: string = ''
  status_json: string = ''
  online: boolean = true
}

export class DashboardSummary {
  rooms: Room[] = []
  devices: Device[] = []
  scenes: Scene[] = []
  recent_logs: LogItem[] = []
  stats: Record<string, number> = {}
}


// openharmony/entry/src/main/ets/common/ApiClient.ets
export async function getDashboardSummary(): Promise<DashboardSummary> { /* map /api/dashboard/summary */ }
export async function discoverDevices(): Promise<DiscoveredDevice[]> { /* map /api/discovery */ }
export async function bindDevice(deviceId: string, roomId: number, name?: string): Promise<Record<string, Object>> { /* post /api/bind_device */ }
export async function getRuleOptions(): Promise<Record<string, Object>> { /* get /api/rules/options */ }
```

- [ ] **Step 2: Refactor device management into bound vs candidate sections**

```ts
// openharmony/entry/src/main/ets/pages/DeviceManagePage.ets
@State discovered: DiscoveredDevice[] = []
@State scanning: boolean = false
@State selectedCandidateId: string = ''
@State bindingName: string = ''
@State errorMessage: string = ''
@State successMessage: string = ''

async scanCandidates(): Promise<void> {
  this.scanning = true
  this.errorMessage = ''
  try {
    this.discovered = await discoverDevices()
  } catch (err) {
    this.errorMessage = '扫描候选设备失败'
  } finally {
    this.scanning = false
  }
}

async bindSelected(device: DiscoveredDevice): Promise<void> {
  try {
    await bindDevice(device.id, this.nrm, this.bindingName || device.name)
    this.successMessage = '设备绑定成功'
    await this.ld()
    await this.scanCandidates()
  } catch (err) {
    this.errorMessage = (err as Error).message || '设备绑定失败'
  }
}
```

- [ ] **Step 3: Verify the page compiles cleanly**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
node hvigorw.js --mode module -p product=default -p module=entry assembleHap
```

Expected:

- No ArkTS type errors from `ApiClient.ets`, `DeviceModel.ets`, or `DeviceManagePage.ets`
- Device management page no longer depends on manual MQTT topic entry

- [ ] **Step 4: Commit the candidate-binding UI slice**

```bash
git add openharmony/entry/src/main/ets/common/ApiClient.ets openharmony/entry/src/main/ets/model/DeviceModel.ets openharmony/entry/src/main/ets/pages/DeviceManagePage.ets
git commit -m "feat: rebuild device management around discovery binding"
```

### Task 5: Rework Dashboard And Remote Control Into A Real Feedback Loop

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- Modify: `openharmony/entry/src/main/ets/common/MqttClient.ets`

- [ ] **Step 1: Move the dashboard to the summary API and add feedback states**

```ts
// openharmony/entry/src/main/ets/pages/DashboardPage.ets
@State loading: boolean = false
@State errorMessage: string = ''
@State successMessage: string = ''
@State recentLogs: LogItem[] = []
@State onlineCount: number = 0
@State totalCount: number = 0

async ld(): Promise<void> {
  this.loading = true
  this.errorMessage = ''
  try {
    let summary = await getDashboardSummary()
    this.rooms = summary.rooms
    this.devices = summary.devices
    this.scenes = summary.scenes
    this.recentLogs = summary.recent_logs
    this.onlineCount = Number(summary.stats['online_devices'] || 0)
    this.totalCount = Number(summary.stats['total_devices'] || 0)
    this.syncClimate()
  } catch (err) {
    this.errorMessage = '家庭总览加载失败'
  } finally {
    this.loading = false
  }
}
```

- [ ] **Step 2: Add per-command loading, success, and error feedback in the remote page**

```ts
// openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets
@State commandBusy: boolean = false
@State errorMessage: string = ''
@State successMessage: string = ''

async cmd(id: number, action: string, params?: Object): Promise<void> {
  this.commandBusy = true
  this.errorMessage = ''
  this.successMessage = ''
  try {
    let eid = buildEntityId(this.dt, id)
    await callService(eid, action, params)
    this.successMessage = '设备操作成功'
    await this.load()
  } catch (err) {
    this.errorMessage = (err as Error).message || '设备操作失败'
  } finally {
    this.commandBusy = false
  }
}
```

- [ ] **Step 3: Rebuild and smoke-check the entry module**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
node hvigorw.js --mode module -p product=default -p module=entry assembleHap
```

Expected:

- Dashboard compiles against `getDashboardSummary()`
- Remote page compiles with command feedback state and no undeclared variables

- [ ] **Step 4: Commit the dashboard and remote-control slice**

```bash
git add openharmony/entry/src/main/ets/pages/DashboardPage.ets openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets openharmony/entry/src/main/ets/common/MqttClient.ets
git commit -m "feat: add dashboard summary and control feedback loop"
```

### Task 6: Upgrade Monitoring And Rule Editing To User-Facing Workflows

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets`
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`

- [ ] **Step 1: Add real empty, loading, and filter behavior to the monitoring page**

```ts
// openharmony/entry/src/main/ets/pages/DataMonitorPage.ets
@State errorMessage: string = ''
@State historyLoading: boolean = false
@State logsLoading: boolean = false

async refresh(): Promise<void> {
  this.errorMessage = ''
  try {
    if (this.tab === 1) {
      this.historyLoading = true
      this.sdata = await getSensorHistory(this.curId > 0 ? this.curId : undefined, 60)
      this.historyLoading = false
      return
    }
    if (this.tab === 2) {
      this.logsLoading = true
      this.logs = await getDeviceLogs(this.curId > 0 ? this.curId : undefined, 40)
      this.logsLoading = false
      return
    }
    await this.loadSensors()
  } catch (err) {
    this.errorMessage = '监控数据刷新失败'
    this.historyLoading = false
    this.logsLoading = false
  }
}
```

- [ ] **Step 2: Replace raw JSON rule creation with option-driven form mapping**

```ts
// openharmony/entry/src/main/ets/pages/RulesPage.ets
@State targetId: number = 0
@State targetType: string = 'ac'
@State optionsLoaded: boolean = false
@State ruleOptions: Record<string, Object> = {}
@State modeValue: string = 'cool'
@State tempValue: number = 26
@State brightnessValue: number = 80

async loadOptions(): Promise<void> {
  this.ruleOptions = await getRuleOptions()
  this.optionsLoaded = true
}

buildConditionJson(): string {
  let value: Object = this.tr === 'pir_sensor' ? (this.vl === 'true') : Number(this.vl)
  return JSON.stringify({ trigger: this.tr, field: this.fl, operator: this.op, value: value })
}

buildActionJson(): string {
  let params: Record<string, Object> = {}
  if (this.targetType === 'ac' && this.an === 'set') {
    params['power'] = 'on'
    params['mode'] = this.modeValue
    params['temp'] = this.tempValue
  }
  return JSON.stringify([{ device_id: this.targetId, device_type: this.targetType, action: this.an, params: params }])
}
```

- [ ] **Step 3: Rebuild the client after the monitoring and rules changes**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
node hvigorw.js --mode module -p product=default -p module=entry assembleHap
```

Expected:

- Monitoring page compiles with per-tab loading and empty states
- Rules page compiles without direct JSON entry fields

- [ ] **Step 4: Commit the monitoring and rules slice**

```bash
git add openharmony/entry/src/main/ets/pages/DataMonitorPage.ets openharmony/entry/src/main/ets/pages/RulesPage.ets openharmony/entry/src/main/ets/common/ApiClient.ets
git commit -m "feat: make monitoring and rules user-facing"
```

### Task 7: Final Verification Against The Spec

**Files:**
- Test: `cloud/backend/tests/test_dashboard_contract.py`
- Test: `cloud/backend/tests/test_devices.py`
- Test: `cloud/backend/tests/test_rules.py`
- Test: `cloud/backend/tests/test_data.py`
- Test: `cloud/backend/tests/test_integration.py`

- [ ] **Step 1: Run the backend regression suite**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\cloud\backend
$env:PYTHONPATH='.'
python -m pytest tests/test_dashboard_contract.py tests/test_devices.py tests/test_rules.py tests/test_data.py tests/test_integration.py -q
```

Expected:

- All targeted backend tests pass
- No regression in device, rule, or monitoring flows

- [ ] **Step 2: Run the OpenHarmony build one final time**

Run:

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
node hvigorw.js --mode module -p product=default -p module=entry assembleHap
```

Expected:

- Entry module builds successfully
- No ArkTS compile errors in touched pages or shared client code

- [ ] **Step 3: Smoke-check the user journey against the spec**

Checklist:

```text
1. 设备管理页扫描候选设备，不新增随机正式设备
2. 候选设备可绑定到房间并出现在正式设备列表
3. 首页展示设备统计、环境数据、场景、最近操作
4. 遥控页设备操作有成功/失败反馈并回刷状态
5. 监控页支持实时、历史、日志三种视图
6. 规则页通过表单创建规则，不要求手写 JSON
```

- [ ] **Step 4: Commit the verified feature set**

```bash
git add cloud/backend openharmony/entry/src/main/ets docs/superpowers/specs/2026-07-07-smart-home-real-functionality-design.md docs/superpowers/plans/2026-07-07-smart-home-real-functionality.md
git commit -m "feat: deliver real smart home control workflow"
```
