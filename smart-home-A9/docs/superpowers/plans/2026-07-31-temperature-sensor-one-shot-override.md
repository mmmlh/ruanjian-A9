# Temperature Sensor One-Shot Override Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the simulator console write a temperature sensor reading once, keep that reading in the Python simulator for 20 seconds, and then resume automatic readings without changing any HTTP or MQTT interface.

**Architecture:** The browser reuses `POST /api/states/{entity_id}` with the existing `attributes.value` body. The backend keeps the current state-write response contract and forwards eligible temperature writes through the device's existing `/command` topic; the Python temperature simulator holds the value against a monotonic deadline and then resumes its existing Gaussian generator.

**Tech Stack:** Native HTML/CSS/ES modules, Node test runner, FastAPI/Pydantic, pytest, Paho MQTT, Docker Compose, Nginx.

---

## File Map

- Create `cloud/simulators/tests/test_temperature_sensor.py`: deterministic unit coverage for the 20-second simulator override.
- Modify `cloud/simulators/temperature_sensor.py`: validate the existing command envelope and maintain the in-memory override.
- Modify `cloud/backend/app/api/states.py`: forward eligible existing state writes to the existing device command topic.
- Modify `cloud/backend/tests/test_devices.py`: lock the state-write response and MQTT forwarding behavior.
- Modify `cloud/simulator-ui/public/js/api-client.js`: add an API client method over the existing state path.
- Modify `cloud/simulator-ui/public/js/device-model.js`: validate and shape temperature override attributes.
- Modify `cloud/simulator-ui/tests/api-client.test.js`: verify the exact frozen path and body.
- Modify `cloud/simulator-ui/tests/device-model.test.js`: verify temperature boundaries and keep other sensors read-only.
- Modify `cloud/simulator-ui/public/js/app.js`: render and submit the temperature override control.
- Modify `cloud/simulator-ui/public/styles.css`: separate the override form from the live reading without changing layout structure.
- Modify `tests/test_simulator_console_contract.py`: keep the UI and interface freeze visible to static regression tests.

### Task 1: Temperature Simulator Override

**Files:**
- Create: `cloud/simulators/tests/test_temperature_sensor.py`
- Modify: `cloud/simulators/temperature_sensor.py`

- [ ] **Step 1: Write deterministic failing simulator tests**

Create `cloud/simulators/tests/test_temperature_sensor.py`:

```python
import sys
from pathlib import Path

import pytest


SIMULATORS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIMULATORS))

import temperature_sensor as temperature_module
from temperature_sensor import TemperatureSensor


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_sensor(clock: FakeClock) -> TemperatureSensor:
    return TemperatureSensor(1, "livingroom", clock=clock)


def test_set_command_holds_reading_for_20_seconds_then_resumes_random(monkeypatch):
    clock = FakeClock()
    sensor = make_sensor(clock)
    published = []
    sensor.publish_sensor_data = published.append
    monkeypatch.setattr(temperature_module.random, "gauss", lambda *_: 24.2)

    sensor.handle_command({"action": "set", "value": 28})

    assert published[-1]["value"] == 28
    assert sensor.generate_data()["value"] == 28
    clock.advance(19.9)
    assert sensor.generate_data()["value"] == 28
    clock.advance(0.1)
    assert sensor.generate_data()["value"] == 24.2


def test_new_valid_command_replaces_value_and_restarts_window(monkeypatch):
    clock = FakeClock()
    sensor = make_sensor(clock)
    sensor.publish_sensor_data = lambda _: None
    monkeypatch.setattr(temperature_module.random, "gauss", lambda *_: 24.0)

    sensor.handle_command({"action": "set", "value": 27})
    clock.advance(15)
    sensor.handle_command({"action": "set", "value": 30.5})
    clock.advance(10)
    assert sensor.generate_data()["value"] == 30.5
    clock.advance(10)
    assert sensor.generate_data()["value"] == 24.0


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "off", "value": 28},
        {"action": "set", "value": True},
        {"action": "set", "value": "28"},
        {"action": "set", "value": 14.9},
        {"action": "set", "value": 38.1},
        {"action": "set", "value": float("nan")},
    ],
)
def test_invalid_commands_do_not_replace_active_override(payload):
    clock = FakeClock()
    sensor = make_sensor(clock)
    sensor.publish_sensor_data = lambda _: None
    sensor.handle_command({"action": "set", "value": 28})

    sensor.handle_command(payload)

    assert sensor.generate_data()["value"] == 28
```

- [ ] **Step 2: Run the simulator tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest cloud/simulators/tests/test_temperature_sensor.py -q
```

Expected: FAIL because `TemperatureSensor.__init__` does not accept `clock` and `handle_command` ignores the command.

- [ ] **Step 3: Implement the minimal 20-second override**

Update `cloud/simulators/temperature_sensor.py` so the complete class behavior is:

```python
"""Temperature sensor simulator with a short-lived manual reading override."""
import math
import random
import threading
import time

from base_device import BaseDevice


class TemperatureSensor(BaseDevice):
    OVERRIDE_SECONDS = 20.0
    MIN_TEMP = 15.0
    MAX_TEMP = 38.0

    def __init__(self, device_id: int, room_id: str, clock=time.monotonic, **kwargs):
        super().__init__(device_id, room_id, "temperature_sensor", **kwargs)
        self.base_temp = 25.0
        self.std_dev = 0.5
        self._clock = clock
        self._override_lock = threading.Lock()
        self._override_value: float | None = None
        self._override_until = 0.0

    def generate_data(self) -> dict:
        with self._override_lock:
            now = self._clock()
            if self._override_value is not None and now < self._override_until:
                temp = self._override_value
            else:
                self._override_value = None
                self._override_until = 0.0
                temp = round(random.gauss(self.base_temp, self.std_dev), 1)
                temp = max(self.MIN_TEMP, min(self.MAX_TEMP, temp))
        return {
            "value": temp,
            "unit": "celsius",
            "device_id": f"temp_{self.device_id:03d}",
            "ts": int(time.time()),
        }

    def handle_command(self, payload: dict):
        value = payload.get("value")
        if (
            payload.get("action") != "set"
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not self.MIN_TEMP <= value <= self.MAX_TEMP
        ):
            return

        with self._override_lock:
            self._override_value = value
            self._override_until = self._clock() + self.OVERRIDE_SECONDS

        self.publish_sensor_data(self.generate_data())
```

- [ ] **Step 4: Run the simulator tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest cloud/simulators/tests/test_temperature_sensor.py -q
```

Expected: all simulator override tests PASS.

- [ ] **Step 5: Commit the simulator behavior**

```powershell
git add cloud/simulators/temperature_sensor.py cloud/simulators/tests/test_temperature_sensor.py
git commit -m "feat: add temporary temperature sensor override"
```

### Task 2: Existing State Write to Existing MQTT Topic

**Files:**
- Modify: `cloud/backend/tests/test_devices.py`
- Modify: `cloud/backend/app/api/states.py`

- [ ] **Step 1: Write failing backend forwarding tests**

Add `import app.api.states as states_api` near the imports in `cloud/backend/tests/test_devices.py`, then add these methods to `TestDevices`:

```python
    def test_temperature_state_write_forwards_existing_command_envelope(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            states_api,
            "publish_message",
            lambda topic, payload: published.append((topic, json.loads(payload))),
        )

        response = client.post(
            "/api/states/temperature_sensor.device_1",
            json={"attributes": {"value": 28}},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["entity_id"] == "temperature_sensor.device_1"
        assert response.json()["attributes"]["value"] == 28
        assert published == [(
            "home/livingroom/temperature_sensor/command",
            {"action": "set", "value": 28},
        )]

    def test_non_temperature_state_write_does_not_publish_override(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        published = []
        monkeypatch.setattr(
            states_api,
            "publish_message",
            lambda *args: published.append(args),
        )

        response = client.post(
            "/api/states/humidity_sensor.device_2",
            json={"attributes": {"value": 55.5}},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert published == []

    def test_temperature_override_publish_failure_uses_existing_error_shape(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        monkeypatch.setattr(
            states_api,
            "publish_message",
            lambda *_: (_ for _ in ()).throw(RuntimeError("mqtt_not_connected")),
        )

        response = client.post(
            "/api/states/temperature_sensor.device_1",
            json={"attributes": {"value": 28}},
            headers=auth_headers,
        )

        assert response.status_code == 503
        assert response.json() == {"detail": "temperature_override_dispatch_failed"}
```

- [ ] **Step 2: Run targeted backend tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest cloud/backend/tests/test_devices.py -q -k "temperature_state_write_forwards or non_temperature_state_write or temperature_override_publish_failure"
```

Expected: FAIL because `states_api.publish_message` is not defined and no command is forwarded.

- [ ] **Step 3: Add a narrowly scoped forwarding helper**

In `cloud/backend/app/api/states.py`, import `logging` and `publish_message`, define a module logger, and add:

```python
logger = logging.getLogger(__name__)

_SIMULATOR_TEMPERATURE_MIN = 15.0
_SIMULATOR_TEMPERATURE_MAX = 38.0


def _dispatch_temperature_override(
    device: dict[str, Any],
    attributes: dict[str, Any] | None,
) -> None:
    if device["type"] != "temperature_sensor" or not attributes:
        return
    value = attributes.get("value")
    if (
        not _is_finite_number(value)
        or not _SIMULATOR_TEMPERATURE_MIN <= value <= _SIMULATOR_TEMPERATURE_MAX
    ):
        return

    topic = f"{device['mqtt_topic']}/command"
    payload = json.dumps({"action": "set", "value": value})
    try:
        publish_message(topic, payload)
    except RuntimeError as exc:
        logger.warning("temperature override publish failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="temperature_override_dispatch_failed",
        ) from exc
```

Import with:

```python
from app.services.mqtt_client import publish_message
```

After the existing successful `refresh_device_state(device_id)` block in `set_state`, and before returning the unchanged state object, call:

```python
    _dispatch_temperature_override(device, req.attributes)
```

Do not change `StateUpdateRequest`, route decorators, response construction, numeric validation, or any MQTT topic definition.

- [ ] **Step 4: Run the targeted and existing state tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest cloud/backend/tests/test_devices.py -q -k "state_write or state_attributes or temperature_override"
```

Expected: all selected tests PASS, including existing acceptance of direct values outside the simulator UI range.

- [ ] **Step 5: Commit backend forwarding**

```powershell
git add cloud/backend/app/api/states.py cloud/backend/tests/test_devices.py
git commit -m "feat: forward temporary temperature state writes"
```

### Task 3: Frozen Browser API and Temperature Value Model

**Files:**
- Modify: `cloud/simulator-ui/tests/api-client.test.js`
- Modify: `cloud/simulator-ui/tests/device-model.test.js`
- Modify: `cloud/simulator-ui/public/js/api-client.js`
- Modify: `cloud/simulator-ui/public/js/device-model.js`

- [ ] **Step 1: Write failing API and model tests**

Append to `cloud/simulator-ui/tests/api-client.test.js`:

```javascript
test("writes a sensor value through the existing state endpoint", async () => {
  const calls = [];
  const fetchFn = async (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/login") {
      return new Response(JSON.stringify({ token: "jwt" }), { status: 200 });
    }
    return new Response(JSON.stringify({
      entity_id: "temperature_sensor.device_1",
      attributes: { value: 28 },
    }), { status: 200 });
  };
  const client = new ApiClient({
    fetchFn,
    credentials: { username: "admin", password: "admin123" },
  });

  await client.setState("temperature_sensor.device_1", { value: 28 });

  assert.equal(calls[1].url, "/api/states/temperature_sensor.device_1");
  assert.equal(calls[1].options.method, "POST");
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    attributes: { value: 28 },
  });
});
```

Import `buildStateUpdate` in `cloud/simulator-ui/tests/device-model.test.js`, then add:

```javascript
test("builds bounded one-shot temperature state updates", () => {
  assert.deepEqual(buildStateUpdate("temperature_sensor", { value: 15 }), { value: 15 });
  assert.deepEqual(buildStateUpdate("temperature_sensor", { value: 28.1 }), { value: 28.1 });
  assert.deepEqual(buildStateUpdate("temperature_sensor", { value: 38 }), { value: 38 });
  assert.throws(() => buildStateUpdate("temperature_sensor", { value: 14.9 }), /value/);
  assert.throws(() => buildStateUpdate("temperature_sensor", { value: 38.1 }), /value/);
  assert.throws(() => buildStateUpdate("temperature_sensor", { value: Number.NaN }), /value/);
  assert.throws(() => buildStateUpdate("humidity_sensor", { value: 55 }), /read-only/);
  assert.throws(() => buildStateUpdate("pir_sensor", { presence: true }), /read-only/);
});
```

Change the existing read-only assertion so `buildCommand` continues rejecting all sensor writes; the temperature override must go through `buildStateUpdate`, not the device command endpoint.

- [ ] **Step 2: Run JavaScript tests and verify RED**

Run:

```powershell
npm test --prefix cloud/simulator-ui
```

Expected: FAIL because `setState` and `buildStateUpdate` do not exist.

- [ ] **Step 3: Implement the API client method over the frozen base path**

Add to `ApiClient` in `cloud/simulator-ui/public/js/api-client.js`:

```javascript
  async setState(entityId, attributes) {
    return this.#authorizedRequest(
      `${ENDPOINTS.states}/${encodeURIComponent(entityId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attributes }),
      },
    );
  }
```

Do not add an `ENDPOINTS` key; the endpoint freeze test must continue to list exactly the current six keys.

- [ ] **Step 4: Implement the temperature state-update builder**

Add to `cloud/simulator-ui/public/js/device-model.js`:

```javascript
export function buildStateUpdate(deviceType, draft) {
  if (deviceType === "temperature_sensor") {
    return { value: boundedNumber(draft.value, 15, 38, "value") };
  }
  if (["humidity_sensor", "pir_sensor"].includes(deviceType)) {
    throw new Error(`${deviceType} is read-only`);
  }
  throw new Error(`${deviceType} does not use direct state updates`);
}
```

- [ ] **Step 5: Run JavaScript tests and verify GREEN**

Run:

```powershell
npm test --prefix cloud/simulator-ui
```

Expected: all API and device-model tests PASS.

- [ ] **Step 6: Commit the browser transport and model**

```powershell
git add cloud/simulator-ui/public/js/api-client.js cloud/simulator-ui/public/js/device-model.js cloud/simulator-ui/tests/api-client.test.js cloud/simulator-ui/tests/device-model.test.js
git commit -m "feat: model temporary temperature state writes"
```

### Task 4: Temperature Sensor Inspector Control

**Files:**
- Modify: `tests/test_simulator_console_contract.py`
- Modify: `cloud/simulator-ui/public/js/app.js`
- Modify: `cloud/simulator-ui/public/styles.css`

- [ ] **Step 1: Write a failing static UI contract test**

Extend `test_console_has_controller_and_read_only_sensor_views` in `tests/test_simulator_console_contract.py` with:

```python
    assert 'addRangeControl(form, "模拟温度", "value", 15, 38, 0.1' in app
    assert "buildStateUpdate" in app
    assert "api.setState(device.entityId, attributes)" in app
    assert "写入一次" in app
```

Retain the existing checks that humidity and PIR sensor types render through the sensor inspector and that no new transport is created in `app.js`.

- [ ] **Step 2: Run the UI contract and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_simulator_console_contract.py -q
```

Expected: FAIL because the temperature form and submission flow are absent.

- [ ] **Step 3: Add the temperature draft and state replacement helper**

Import `buildStateUpdate` from `device-model.js` in `cloud/simulator-ui/public/js/app.js`.

Change the temperature branch in `defaultDraft` to:

```javascript
    case "temperature_sensor":
      return { value: Number(status.value ?? 25) };
    case "humidity_sensor":
    case "pir_sensor":
      return {};
```

Replace the body of `updateDeviceFromCommand` with a shared raw-state helper while preserving controller behavior:

```javascript
function replaceDeviceState(rawState) {
  const [changed] = normalizeStates([rawState]);
  if (!changed) {
    return;
  }
  const index = state.devices.findIndex((device) => device.id === changed.id);
  if (index < 0) {
    return;
  }
  const devices = state.devices.slice();
  devices[index] = changed;
  state.devices = devices;
}


function updateDeviceFromCommand(result) {
  if (result?.changed_state) {
    replaceDeviceState(result.changed_state);
  }
}
```

- [ ] **Step 4: Add the one-shot submission flow**

Add to `cloud/simulator-ui/public/js/app.js`:

```javascript
async function submitTemperatureOverride(event, device, draft) {
  event.preventDefault();
  if (state.busyDeviceId !== null) {
    return;
  }

  try {
    const attributes = buildStateUpdate(device.type, draft);
    state.busyDeviceId = device.id;
    renderInspector();
    const result = await api.setState(device.entityId, attributes);
    replaceDeviceState(result);
    state.drafts.delete(device.id);
    notify(`${device.name} 已写入 ${attributes.value}°C`, "success");
    renderAll();
    ensureRealtimeToken();
  } catch (error) {
    notify(error.detail || error.message || "温度写入失败", "error", 6_000);
  } finally {
    state.busyDeviceId = null;
    renderInspector();
  }
}
```

- [ ] **Step 5: Render the temperature form while keeping other sensors read-only**

In `renderSensorInspector`, construct `reading` exactly as today, then branch on the device type before constructing the read-only note. For `temperature_sensor`, render:

```javascript
  if (device.type === "temperature_sensor") {
    const form = createElement("form", "device-control-form sensor-override-form");
    const draft = draftFor(device);
    addRangeControl(form, "模拟温度", "value", 15, 38, 0.1, draft, "°C");

    const footer = createElement("div", "inspector-footer");
    const status = createElement(
      "span",
      "command-status",
      state.busyDeviceId === device.id ? "正在写入" : "一次写入就绪",
    );
    const submit = createElement(
      "button",
      "primary-button",
      state.busyDeviceId === device.id ? "写入中" : "写入一次",
    );
    submit.type = "submit";
    submit.disabled = state.busyDeviceId !== null;
    submit.prepend(createIcon(state.busyDeviceId === device.id ? "loader-circle" : "send"));
    footer.append(status, submit);
    form.append(footer);
    form.addEventListener("submit", (event) => submitTemperatureOverride(event, device, draft));
    body.append(reading, form);
    return;
  }
```

Keep the existing read-only note for humidity and PIR, then append `reading` and `note` for those types.

- [ ] **Step 6: Add restrained form separation**

Add to `cloud/simulator-ui/public/styles.css` near the sensor inspector styles:

```css
.sensor-override-form {
  padding-top: 18px;
  border-top: 1px solid var(--line);
}
```

Use the existing range, number, footer, button, responsive, focus, and reduced-motion styles; do not introduce a card or nested panel.

- [ ] **Step 7: Run frontend and contract tests**

Run:

```powershell
npm test --prefix cloud/simulator-ui
.\.venv\Scripts\python.exe -m pytest tests/test_simulator_console_contract.py -q
```

Expected: JavaScript and all simulator console contract tests PASS.

- [ ] **Step 8: Commit the inspector UI**

```powershell
git add cloud/simulator-ui/public/js/app.js cloud/simulator-ui/public/styles.css tests/test_simulator_console_contract.py
git commit -m "feat: control temporary temperature sensor readings"
```

### Task 5: Integrated Verification and Browser Acceptance

**Files:**
- No production files expected unless a failing test reveals a defect.

- [ ] **Step 1: Run focused suites from a clean command invocation**

```powershell
.\.venv\Scripts\python.exe -m pytest cloud/simulators/tests/test_temperature_sensor.py -q
npm test --prefix cloud/simulator-ui
.\.venv\Scripts\python.exe -m pytest tests/test_simulator_console_contract.py -q
```

Expected: all focused suites PASS with zero failures.

- [ ] **Step 2: Run the complete backend regression and Compose validation**

```powershell
.\.venv\Scripts\python.exe -m pytest cloud/backend/tests -q
docker compose -f cloud/docker-compose.yml config --quiet
```

Expected: the full backend suite passes; Compose exits `0`. The pre-existing obsolete `version` warning is acceptable.

- [ ] **Step 3: Rebuild only the affected runtime services**

```powershell
docker compose -f cloud/docker-compose.yml up -d --build backend simulators nginx
curl.exe -k -s https://localhost/api/ready
```

Expected: readiness returns `{"status":"ready","checks":{"database":"ok","mqtt":"ok"}}`.

- [ ] **Step 4: Verify the unchanged endpoint and 20-second recovery over HTTP**

Use the existing login and state endpoints only:

```powershell
$loginBody = '{"username":"admin","password":"admin123"}'
$token = (curl.exe -k -s -X POST https://localhost/api/login -H "Content-Type: application/json" --data-binary $loginBody | ConvertFrom-Json).token
$authorization = "Authorization: Bearer $token"
$writeBody = '{"attributes":{"value":28}}'

curl.exe -k -s -X POST https://localhost/api/states/temperature_sensor.device_1 -H $authorization -H "Content-Type: application/json" --data-binary $writeBody
$immediate = curl.exe -k -s https://localhost/api/states/temperature_sensor.device_1 -H $authorization | ConvertFrom-Json
Start-Sleep -Seconds 15
$during = curl.exe -k -s https://localhost/api/states/temperature_sensor.device_1 -H $authorization | ConvertFrom-Json
Start-Sleep -Seconds 10
$recovered = curl.exe -k -s https://localhost/api/states/temperature_sensor.device_1 -H $authorization | ConvertFrom-Json

Write-Output "immediate=$($immediate.attributes.value)"
Write-Output "during=$($during.attributes.value)"
Write-Output "recovered=$($recovered.attributes.value)"
```

Expected: `immediate=28`, `during=28`, and `recovered` is a newly generated simulator value. Do not add a diagnostic endpoint or query parameter.

- [ ] **Step 5: Perform desktop browser acceptance**

Open `/simulator/` at `1440x900`. Select each of the three temperature sensors and confirm the `15-38°C` slider, synchronized numeric input, and “写入一次” button. Write `28°C`, verify the success toast, device row, inspector reading, and `/sensor` event payload. Confirm humidity and PIR still show the read-only note with no submit button.

- [ ] **Step 6: Perform mobile browser acceptance**

At `390x844`, verify the temperature range and numeric input remain usable, the submit label fits, the inspector does not overlap the event console, and the document has no horizontal overflow. Capture desktop and mobile screenshots and read browser console logs; expect no errors or warnings.

- [ ] **Step 7: Reset browser state and clean temporary preview resources**

Reset the viewport override. If a temporary HTTP Nginx preview container was required because of the self-signed certificate, stop it and delete only its known temporary config file. Finalize browser tabs after the last browser check.

- [ ] **Step 8: Inspect the final boundary**

```powershell
git diff --check
git status --short --branch
git log --oneline -8
```

Expected: feature commits contain only the files listed in this plan. Existing unrelated backend connection, Compose, OpenHarmony, UI polish, archive, and `TODOS.md` changes remain untouched and uncommitted.
