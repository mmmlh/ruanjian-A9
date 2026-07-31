# Simulator Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Docker-served visual operations console for the 17 existing smart-home simulators without changing any FastAPI or MQTT interface.

**Architecture:** Add a build-free ES module application under `cloud/simulator-ui/`, mount only its `public/` directory into the existing Nginx container, and expose it at `/simulator/`. Pure JavaScript modules own device normalization, command construction, API authentication, and bounded realtime state; a thin DOM controller renders the workbench and calls only the frozen endpoint whitelist.

**Tech Stack:** HTML5, CSS, browser ES modules, Node.js built-in test runner, Python/pytest contract tests, existing Nginx and Docker Compose.

---

## File Structure

- Create `cloud/simulator-ui/package.json`: mark the project as ES modules and define the Node test command.
- Create `cloud/simulator-ui/public/index.html`: semantic workbench shell and accessible templates.
- Create `cloud/simulator-ui/public/styles.css`: desktop/mobile layout, controls, health states, event console, and focus states.
- Create `cloud/simulator-ui/public/vendor/lucide.min.js`: pinned local icon runtime for offline Docker use.
- Create `cloud/simulator-ui/public/js/config.js`: immutable credentials and existing endpoint whitelist.
- Create `cloud/simulator-ui/public/js/device-model.js`: normalize states, map MQTT events, filter devices, and build command payloads.
- Create `cloud/simulator-ui/public/js/api-client.js`: readiness, automatic login, authenticated fetch retry, and WebSocket reconnect.
- Create `cloud/simulator-ui/public/js/app.js`: browser state, rendering, input handling, polling, command feedback, and startup.
- Create `cloud/simulator-ui/tests/device-model.test.js`: pure state and command tests.
- Create `cloud/simulator-ui/tests/api-client.test.js`: fetch authentication and retry tests.
- Create `tests/test_simulator_console_contract.py`: static entrypoint, accessibility, endpoint whitelist, Nginx, and Compose regression tests.
- Modify `cloud/nginx/nginx.conf`: add MIME types and the `/simulator/` static location while preserving all existing proxies.
- Modify `cloud/docker-compose.yml`: add one read-only simulator UI mount to the existing Nginx service.

### Task 1: Lock the Static Contract and Create the Shell

**Files:**
- Create: `tests/test_simulator_console_contract.py`
- Create: `cloud/simulator-ui/package.json`
- Create: `cloud/simulator-ui/public/index.html`
- Create: `cloud/simulator-ui/public/vendor/lucide.min.js`

- [ ] **Step 1: Write the failing entrypoint and accessibility tests**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "cloud" / "simulator-ui" / "public"


def read(relative: str) -> str:
    return (UI / relative).read_text(encoding="utf-8")


def test_simulator_console_static_entrypoint_exists():
    html = read("index.html")
    assert '<html lang="zh-CN">' in html
    assert '<link rel="stylesheet" href="./styles.css">' in html
    assert '<script src="./vendor/lucide.min.js"></script>' in html
    assert '<script type="module" src="./js/app.js"></script>' in html
    assert (UI / "vendor" / "lucide.min.js").stat().st_size > 10000


def test_simulator_console_exposes_accessible_workbench_regions():
    html = read("index.html")
    for marker in [
        'id="startup-status"',
        'id="device-search"',
        'id="room-filter"',
        'id="type-filter"',
        'id="online-filter"',
        'id="device-list"',
        'id="device-inspector"',
        'id="event-list"',
        'id="toast-region" aria-live="polite"',
    ]:
        assert marker in html
```

- [ ] **Step 2: Run the focused test and confirm the missing-file failure**

Run: `pytest tests/test_simulator_console_contract.py -q`

Expected: FAIL because `cloud/simulator-ui/public/index.html` does not exist.

- [ ] **Step 3: Add the ES module manifest and semantic page shell**

Create `cloud/simulator-ui/package.json`:

```json
{
  "name": "smart-home-a9-simulator-console",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test tests/device-model.test.js tests/api-client.test.js"
  }
}
```

Download the pinned UMD build with:

```powershell
New-Item -ItemType Directory -Force cloud/simulator-ui/public/vendor | Out-Null
curl.exe -L https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js -o cloud/simulator-ui/public/vendor/lucide.min.js
```

Create `index.html` with these concrete regions in order: a blocking `#startup-status`, a header containing service health labels, a four-cell `#metric-strip`, a toolbar containing the four named filters and refresh icon button, a `#device-list` table body, a `#device-inspector` aside, a bounded `#event-list` console with pause/filter/clear controls, and `#toast-region`. Load the local Lucide runtime before `app.js`, use `data-lucide` names for icons, and call `lucide.createIcons()` after dynamic renders. Use native `button`, `input`, `select`, and `form` elements; every icon-only button must have both `title` and `aria-label`.

- [ ] **Step 4: Run the focused contract tests**

Run: `pytest tests/test_simulator_console_contract.py -q`

Expected: PASS for the two shell tests.

- [ ] **Step 5: Commit the isolated shell**

```bash
git add tests/test_simulator_console_contract.py cloud/simulator-ui/package.json cloud/simulator-ui/public/index.html cloud/simulator-ui/public/vendor/lucide.min.js
git commit -m "feat: add simulator console shell"
```

### Task 2: Implement Device State and Command Mapping with TDD

**Files:**
- Create: `cloud/simulator-ui/tests/device-model.test.js`
- Create: `cloud/simulator-ui/public/js/device-model.js`

- [ ] **Step 1: Write failing normalization, filtering, event, and command tests**

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import {
  appendEvent,
  applyMqttEvent,
  buildCommand,
  filterDevices,
  normalizeStates,
} from "../public/js/device-model.js";

const states = [{
  entity_id: "ac.device_5",
  state: "cool",
  last_updated: "2026-07-31T08:42:00Z",
  attributes: {
    device_id: 5,
    friendly_name: "客厅空调",
    room_name: "客厅",
    mqtt_topic: "home/livingroom/ac",
    online: true,
    power: "on",
    mode: "cool",
    temp: 25,
    fan: "auto"
  }
}];

test("normalizes existing /api/states objects", () => {
  const [device] = normalizeStates(states);
  assert.equal(device.id, 5);
  assert.equal(device.type, "ac");
  assert.equal(device.status.temp, 25);
});

test("filters by room, type, online state, name, and MQTT topic", () => {
  const devices = normalizeStates(states);
  assert.equal(filterDevices(devices, { query: "livingroom", room: "客厅", type: "ac", online: "online" }).length, 1);
  assert.equal(filterDevices(devices, { query: "卧室", room: "all", type: "all", online: "all" }).length, 0);
});

test("unwraps response events and updates the matching device", () => {
  const devices = normalizeStates(states);
  const updated = applyMqttEvent(devices, {
    topic: "home/livingroom/ac/response",
    payload: { success: true, state: { power: "on", mode: "cool", temp: 24 } }
  });
  assert.equal(updated[0].status.temp, 24);
});

test("keeps only the newest 300 events", () => {
  let events = [];
  for (let index = 0; index < 305; index += 1) events = appendEvent(events, { topic: String(index) });
  assert.equal(events.length, 300);
  assert.equal(events[0].topic, "5");
});

test("builds commands matching existing backend validation", () => {
  assert.deepEqual(buildCommand("light", { power: "on", brightness: 72, color: "warm" }), {
    action: "on", params: { brightness: 72, color: "warm" }
  });
  assert.deepEqual(buildCommand("ac", { power: "on", temp: 24, mode: "cool", fan: "high", swing: "off" }), {
    action: "on", params: { temp: 24, mode: "cool", fan: "high", swing: "off" }
  });
  assert.deepEqual(buildCommand("door_lock", { locked: false, auth_code: "demo" }), {
    action: "unlock", params: { auth_code: "demo" }
  });
  assert.deepEqual(buildCommand("curtain", { position: 45 }), { action: "set", params: { position: 45 } });
  assert.deepEqual(buildCommand("humidifier", { power: "on", level: 2, target_humidity: 60 }), {
    action: "on", params: { level: 2, target_humidity: 60 }
  });
});

test("rejects writes for sensor device types", () => {
  assert.throws(() => buildCommand("temperature_sensor", { value: 30 }), /read-only/);
});
```

- [ ] **Step 2: Run the Node test and confirm the module-not-found failure**

Run: `node --test cloud/simulator-ui/tests/device-model.test.js`

Expected: FAIL because `public/js/device-model.js` does not exist.

- [ ] **Step 3: Implement the pure device model**

Export exactly these functions from `device-model.js`:

```javascript
const META_KEYS = new Set([
  "device_id", "room_id", "friendly_name", "room_name", "mqtt_topic",
  "brand", "online", "status_summary"
]);

function boundedNumber(value, minimum, maximum, field) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < minimum || number > maximum) {
    throw new Error(`${field} must be between ${minimum} and ${maximum}`);
  }
  return number;
}

export function normalizeStates(payload) {
  if (!Array.isArray(payload)) return [];
  return payload.flatMap((item) => {
    if (!item || typeof item !== "object" || typeof item.entity_id !== "string") return [];
    const [type] = item.entity_id.split(".device_");
    const attributes = item.attributes && typeof item.attributes === "object" ? item.attributes : {};
    const id = Number(attributes.device_id);
    if (!Number.isInteger(id)) return [];
    const status = Object.fromEntries(Object.entries(attributes).filter(([key]) => !META_KEYS.has(key)));
    return [{
      id,
      entityId: item.entity_id,
      type,
      name: String(attributes.friendly_name || item.entity_id),
      roomName: String(attributes.room_name || ""),
      mqttTopic: String(attributes.mqtt_topic || ""),
      brand: String(attributes.brand || ""),
      online: attributes.online === true,
      state: String(item.state || "unknown"),
      status,
      lastUpdated: String(item.last_updated || item.last_changed || "")
    }];
  });
}

export function filterDevices(devices, filters) {
  const query = String(filters.query || "").trim().toLocaleLowerCase();
  return devices.filter((device) => {
    const matchesQuery = !query || `${device.name} ${device.mqttTopic}`.toLocaleLowerCase().includes(query);
    const matchesRoom = filters.room === "all" || device.roomName === filters.room;
    const matchesType = filters.type === "all" || device.type === filters.type;
    const matchesOnline = filters.online === "all"
      || (filters.online === "online" ? device.online : !device.online);
    return matchesQuery && matchesRoom && matchesType && matchesOnline;
  });
}

export function applyMqttEvent(devices, event) {
  if (!event || typeof event.topic !== "string" || !event.payload || typeof event.payload !== "object") {
    return devices;
  }
  const mqttTopic = event.topic.replace(/\/(sensor|status|response)$/, "");
  const rawStatus = event.topic.endsWith("/response") ? event.payload.state : event.payload;
  if (!rawStatus || typeof rawStatus !== "object") return devices;
  const status = Object.fromEntries(
    Object.entries(rawStatus).filter(([key]) => !["device_id", "brand_command", "success"].includes(key))
  );
  return devices.map((device) => device.mqttTopic === mqttTopic
    ? { ...device, online: true, status: { ...device.status, ...status }, lastUpdated: new Date().toISOString() }
    : device);
}

export function appendEvent(events, event, limit = 300) {
  return [...events, event].slice(-limit);
}

export function buildCommand(deviceType, draft) {
  if (["temperature_sensor", "humidity_sensor", "pir_sensor"].includes(deviceType)) {
    throw new Error(`${deviceType} is read-only`);
  }
  if (deviceType === "light") {
    if (draft.power === "off") return { action: "off", params: {} };
    return {
      action: "on",
      params: {
        brightness: boundedNumber(draft.brightness, 0, 100, "brightness"),
        color: String(draft.color || "warm")
      }
    };
  }
  if (deviceType === "ac") {
    if (draft.power === "off") return { action: "off", params: {} };
    return {
      action: "on",
      params: {
        temp: boundedNumber(draft.temp, 16, 30, "temp"),
        mode: String(draft.mode || "cool"),
        fan: String(draft.fan || "auto"),
        swing: String(draft.swing || "off")
      }
    };
  }
  if (deviceType === "door_lock") {
    if (draft.locked !== false) return { action: "lock", params: {} };
    const authCode = String(draft.auth_code || "").trim();
    if (!authCode) throw new Error("auth_code is required to unlock");
    return { action: "unlock", params: { auth_code: authCode } };
  }
  if (deviceType === "curtain") {
    const position = boundedNumber(draft.position, 0, 100, "position");
    if (position === 0) return { action: "close", params: {} };
    if (position === 100) return { action: "open", params: {} };
    return { action: "set", params: { position } };
  }
  if (deviceType === "humidifier") {
    if (draft.power === "off") return { action: "off", params: {} };
    return {
      action: "on",
      params: {
        level: boundedNumber(draft.level, 1, 3, "level"),
        target_humidity: boundedNumber(draft.target_humidity, 30, 80, "target_humidity")
      }
    };
  }
  throw new Error(`Unsupported device type: ${deviceType}`);
}
```

Numeric validation must enforce brightness 0-100, AC temperature 16-30, curtain position 0-100, humidifier level 1-3, and target humidity 30-80. Door unlock must reject an empty `auth_code`. Unknown device types and non-finite numeric values must throw descriptive `Error` objects before any HTTP request.

- [ ] **Step 4: Run the model tests**

Run: `node --test cloud/simulator-ui/tests/device-model.test.js`

Expected: 6 tests PASS.

- [ ] **Step 5: Commit the model**

```bash
git add cloud/simulator-ui/public/js/device-model.js cloud/simulator-ui/tests/device-model.test.js
git commit -m "feat: model simulator device controls"
```

### Task 3: Implement the Frozen API Client and Realtime Reconnect

**Files:**
- Create: `cloud/simulator-ui/public/js/config.js`
- Create: `cloud/simulator-ui/public/js/api-client.js`
- Create: `cloud/simulator-ui/tests/api-client.test.js`

- [ ] **Step 1: Write failing API whitelist and retry tests**

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { ENDPOINTS } from "../public/js/config.js";
import { ApiClient, reconnectDelay } from "../public/js/api-client.js";

test("exports only frozen existing endpoints", () => {
  assert.deepEqual(Object.keys(ENDPOINTS).sort(), ["command", "login", "logs", "ready", "realtime", "states"]);
  assert.equal(ENDPOINTS.command(5), "/api/devices/5/command");
  assert.equal(ENDPOINTS.realtime, "/ws/realtime");
  assert.ok(Object.isFrozen(ENDPOINTS));
});

test("logs in and sends the bearer token", async () => {
  const calls = [];
  const fetchFn = async (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/login") return new Response(JSON.stringify({ token: "jwt", user: { username: "admin" } }), { status: 200 });
    return new Response(JSON.stringify([]), { status: 200 });
  };
  const client = new ApiClient({ fetchFn, credentials: { username: "admin", password: "admin123" } });
  await client.getStates();
  assert.equal(calls[1].options.headers.Authorization, "Bearer jwt");
});

test("reauthenticates once after a 401", async () => {
  let protectedCalls = 0;
  let loginCalls = 0;
  const fetchFn = async (url) => {
    if (url === "/api/login") {
      loginCalls += 1;
      return new Response(JSON.stringify({ token: `jwt-${loginCalls}` }), { status: 200 });
    }
    protectedCalls += 1;
    return protectedCalls === 1
      ? new Response(JSON.stringify({ detail: "expired" }), { status: 401 })
      : new Response(JSON.stringify([]), { status: 200 });
  };
  const client = new ApiClient({ fetchFn, credentials: { username: "admin", password: "admin123" } });
  assert.deepEqual(await client.getStates(), []);
  assert.equal(loginCalls, 2);
  assert.equal(protectedCalls, 2);
});

test("uses capped reconnect delays", () => {
  assert.deepEqual([0, 1, 2, 3, 4, 8].map(reconnectDelay), [1000, 2000, 5000, 10000, 30000, 30000]);
});
```

- [ ] **Step 2: Run the API tests and confirm failure**

Run: `node --test cloud/simulator-ui/tests/api-client.test.js`

Expected: FAIL because the API modules do not exist.

- [ ] **Step 3: Add the immutable configuration**

`config.js` must export only:

```javascript
export const DEFAULT_CREDENTIALS = Object.freeze({ username: "admin", password: "admin123" });
export const ENDPOINTS = Object.freeze({
  ready: "/api/ready",
  login: "/api/login",
  states: "/api/states",
  logs: "/api/data/logs?limit=100",
  command: (deviceId) => `/api/devices/${encodeURIComponent(deviceId)}/command`,
  realtime: "/ws/realtime",
});
export const STATE_POLL_INTERVAL_MS = 10000;
export const EVENT_LIMIT = 300;
```

- [ ] **Step 4: Implement `ApiClient`, `RealtimeClient`, and `reconnectDelay`**

`ApiClient` must inject `fetchFn`, keep the JWT only in a private field, expose it through a read-only `token` getter for WebSocket setup, parse JSON error `detail`, and expose `checkReady()`, `login()`, `getStates()`, `getLogs()`, and `sendCommand(deviceId, command)`. `login()` returns the new Token string. Its protected request helper may retry exactly once after `401`.

`RealtimeClient` must inject a WebSocket factory and timer functions, build `ws:` or `wss:` from `window.location`, URL-encode the JWT query parameter, report `connecting/open/reconnecting/closed`, reset the attempt counter after open, and use `reconnectDelay(attempt)` values `1000, 2000, 5000, 10000, 30000` with a 30-second cap. Calling `stop()` must cancel reconnects.

- [ ] **Step 5: Run all JavaScript unit tests**

Run: `npm test --prefix cloud/simulator-ui`

Expected: all model and API tests PASS.

- [ ] **Step 6: Commit the API layer**

```bash
git add cloud/simulator-ui/public/js/config.js cloud/simulator-ui/public/js/api-client.js cloud/simulator-ui/tests/api-client.test.js
git commit -m "feat: connect simulator console to existing APIs"
```

### Task 4: Build the Workbench UI

**Files:**
- Create: `cloud/simulator-ui/public/styles.css`
- Create: `cloud/simulator-ui/public/js/app.js`
- Modify: `cloud/simulator-ui/public/index.html`
- Modify: `tests/test_simulator_console_contract.py`

- [ ] **Step 1: Extend the static tests before implementing the UI**

Add tests that assert the stylesheet defines the stable desktop grid and mobile breakpoint, all icon-only buttons have labels, `app.js` imports only local modules, the exact five controller types appear, the three sensor types are marked read-only, the event limit is imported from config, and no source file contains `mqtt://`, `ws://localhost`, `/api/auth/register`, or direct database references.

```python
def test_console_uses_only_the_frozen_browser_transport():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in UI.rglob("*.js"))
    for forbidden in ["mqtt://", "ws://localhost", "/api/auth/register", "sqlite", "DATABASE_URL"]:
        assert forbidden not in combined
    for allowed in ["ENDPOINTS.states", "ENDPOINTS.command", "ENDPOINTS.realtime"]:
        assert allowed in combined


def test_console_has_controller_and_read_only_sensor_views():
    app = read("js/app.js")
    for device_type in ["light", "ac", "door_lock", "curtain", "humidifier"]:
        assert f'case "{device_type}"' in app
    for device_type in ["temperature_sensor", "humidity_sensor", "pir_sensor"]:
        assert device_type in app
    assert "只读传感器" in app
```

- [ ] **Step 2: Run the expanded pytest file and verify failure**

Run: `pytest tests/test_simulator_console_contract.py -q`

Expected: FAIL because the UI implementation and controller cases are absent.

- [ ] **Step 3: Implement the application state and startup flow**

`app.js` must keep one state object containing `devices`, `selectedId`, `filters`, `events`, `eventPaused`, `eventTopic`, `busyDeviceId`, `health`, and `drafts`. Startup order is: bind listeners, render startup state, `checkReady`, automatic `login`, parallel `getStates/getLogs`, connect realtime, then start the 10-second reconciliation timer. No password may be passed to logging or toast functions.

- [ ] **Step 4: Implement the table, inspector, metrics, and event rendering**

Use DOM creation and `textContent` for API-derived data. The inspector must switch on the exact device types from the design and use native switches/checkboxes, segmented radio controls, range plus number inputs, and a password input for door unlock authentication. Sensor views must contain no submit button. Submit must call `buildCommand`, disable only the active device submission, await `sendCommand`, merge returned `changed_state`, and preserve draft values on failure.

- [ ] **Step 5: Implement the quiet operational visual system**

`styles.css` must use an unframed full-height application shell, a stable `minmax(0, 1fr) 300px` desktop work area, a dense device table, an always-visible desktop event band, radii no greater than 8px, and neutral/charcoal surfaces with teal, amber, and red semantic accents. Add a mobile breakpoint at 820px that moves the inspector below the device list and makes the event panel collapsible. Add `:focus-visible`, reduced-motion support, stable 40-44px controls, overflow wrapping, and no viewport-scaled font sizes, decorative gradients, or nested cards.

- [ ] **Step 6: Run unit and static contract tests**

Run: `npm test --prefix cloud/simulator-ui`

Expected: all JavaScript tests PASS.

Run: `pytest tests/test_simulator_console_contract.py -q`

Expected: all static contract tests PASS.

- [ ] **Step 7: Commit the complete browser UI**

```bash
git add cloud/simulator-ui/public/index.html cloud/simulator-ui/public/styles.css cloud/simulator-ui/public/js/app.js tests/test_simulator_console_contract.py
git commit -m "feat: build simulator operations workbench"
```

### Task 5: Serve the Console Through Existing Nginx

**Files:**
- Modify: `cloud/nginx/nginx.conf`
- Modify: `cloud/docker-compose.yml`
- Modify: `tests/test_simulator_console_contract.py`

- [ ] **Step 1: Write failing integration contract tests**

```python
def test_nginx_serves_simulator_without_changing_existing_proxies():
    nginx = (ROOT / "cloud" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert "include /etc/nginx/mime.types;" in nginx
    assert "location = /simulator" in nginx
    assert "return 301 /simulator/;" in nginx
    assert "location /simulator/" in nginx
    assert "try_files $uri $uri/ /simulator/index.html;" in nginx
    for existing in ["location /api/", "location /ws/", "location /docs", "location /openapi.json"]:
        assert existing in nginx


def test_compose_mounts_only_public_simulator_assets_read_only():
    compose = (ROOT / "cloud" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "./simulator-ui/public:/usr/share/nginx/html/simulator:ro" in compose
```

- [ ] **Step 2: Run the integration contract tests and verify failure**

Run: `pytest tests/test_simulator_console_contract.py -q`

Expected: FAIL on the missing Nginx route and Compose mount.

- [ ] **Step 3: Add the Nginx static route**

Inside the existing `http` block, include `/etc/nginx/mime.types`. Before the root proxy location, add:

```nginx
location = /simulator {
    return 301 /simulator/;
}

location /simulator/ {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /simulator/index.html;
}
```

Do not alter any existing proxy path or `proxy_pass` target.

- [ ] **Step 4: Add the read-only Compose mount**

Under the existing Nginx `volumes`, add exactly:

```yaml
- ./simulator-ui/public:/usr/share/nginx/html/simulator:ro
```

Preserve all pre-existing uncommitted database and backend configuration edits. Stage only the new mount hunk if a commit is created.

- [ ] **Step 5: Validate static contracts and Compose rendering**

Run: `pytest tests/test_simulator_console_contract.py -q`

Expected: PASS.

Run: `docker compose -f cloud/docker-compose.yml config`

Expected: exit code 0 and an Nginx bind mount targeting `/usr/share/nginx/html/simulator` with read-only mode.

- [ ] **Step 6: Commit only integration-owned hunks**

```bash
git add cloud/nginx/nginx.conf tests/test_simulator_console_contract.py
# Stage only the simulator-ui mount hunk from cloud/docker-compose.yml.
git diff --cached --check
git commit -m "feat: serve simulator console through nginx"
```

### Task 6: Run End-to-End and Visual Verification

**Files:**
- Modify only if verification reveals a defect in `cloud/simulator-ui/public/`, its tests, Nginx, or the simulator mount.

- [ ] **Step 1: Start or refresh the existing stack**

Run: `docker compose -f cloud/docker-compose.yml up -d --build`

Expected: `mqtt`, `backend`, `simulators`, and `nginx` reach running state.

- [ ] **Step 2: Verify health and the static entrypoint**

Run: `curl.exe -k -I https://localhost/simulator/`

Expected: HTTP 200 with HTML content.

Run: `curl.exe -k https://localhost/api/ready`

Expected: HTTP 200 with `status: ready`, `database: ok`, and `mqtt: ok`.

- [ ] **Step 3: Exercise desktop workflows in the in-app browser**

At a 1440x900 viewport, verify automatic login, 17 devices, all four filters, device selection, each of the five controller forms, command busy state, success/failure feedback, event pause/filter/clear, and WebSocket live status. Confirm the Network panel contains only the documented API whitelist and `/ws/realtime`.

- [ ] **Step 4: Exercise mobile workflows and capture screenshots**

At a 390x844 viewport, verify the list, inspector, and collapsible event panel remain reachable with no overlaps, clipped labels, or uncontrolled horizontal scrolling. Capture desktop and mobile screenshots for final visual inspection.

- [ ] **Step 5: Simulate recovery paths**

Stop and restart the backend container to verify readiness failure, WebSocket reconnect, and state reconciliation. Trigger one invalid door unlock draft locally to verify no request is sent, then use a valid auth code to verify the existing command endpoint is called.

- [ ] **Step 6: Fix any discovered defect with a regression test first**

Add the smallest failing Node or pytest assertion that reproduces each issue, run it to confirm failure, implement the correction, and rerun both focused suites before repeating browser verification.

### Task 7: Final Regression and Delivery

**Files:**
- No planned source changes.

- [ ] **Step 1: Run all console tests from a clean command invocation**

Run: `npm test --prefix cloud/simulator-ui`

Expected: PASS.

Run: `pytest tests/test_simulator_console_contract.py -q`

Expected: PASS.

- [ ] **Step 2: Run existing backend regression tests**

Run: `pytest cloud/backend/tests -q`

Expected: PASS; no existing endpoint contract changes.

- [ ] **Step 3: Revalidate Docker configuration and working tree ownership**

Run: `docker compose -f cloud/docker-compose.yml config --quiet`

Expected: exit code 0.

Run: `git status --short`

Expected: simulator console changes are committed or intentionally staged; unrelated pre-existing changes remain untouched.

- [ ] **Step 4: Record the final evidence**

Report the test counts, Docker service status, final URL `https://localhost/simulator/`, browser viewport checks, files changed, and any unrelated failing tests or environment limitation without claiming they were fixed.
