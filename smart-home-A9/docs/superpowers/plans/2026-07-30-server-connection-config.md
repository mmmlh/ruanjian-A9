# Server Connection Configuration Implementation Plan

**Goal:** Make the OpenHarmony client use one editable source for HTTP and WebSocket server connection settings.

**Architecture:** `common/ServerConfig.ets` stores protocol, host, and port and derives the HTTP and WebSocket base URLs. `ApiClient`, `MqttClient`, and `EntryFormAbility` consume those derived values directly; `SecureStorage` remains responsible only for authentication data.

**Tech Stack:** OpenHarmony ArkTS API 20, Preferences, HTTP, WebSocket, pytest regression checks, Hvigor HAP build.

---

### Task 1: Define the configuration source

**Files:**
- Create: `openharmony/entry/src/main/ets/common/ServerConfig.ets`
- Test: `tests/test_frontend_config_regression.py`

- [x] Store `SERVER_PROTOCOL`, `SERVER_HOST`, and `SERVER_PORT` in the new module.
- [x] Derive `SERVER_BASE_URL` and `SERVER_WEBSOCKET_URL` from those values.
- [x] Assert the deployment host appears only in the new module.

### Task 2: Remove runtime server overrides

**Files:**
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Modify: `openharmony/entry/src/main/ets/common/SecureStorage.ets`
- Modify: `openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets`
- Modify: `openharmony/entry/src/main/ets/common/MqttClient.ets`

- [x] Remove `setBaseUrl`, `saveServerUrl`, `loadServerUrl`, and the `server_url` preference key.
- [x] Use the shared HTTP URL for REST and the shared WebSocket URL for realtime updates.
- [x] Keep authentication preference initialization and token persistence unchanged.

### Task 3: Remove stale network metadata and document the boundary

**Files:**
- Modify: `openharmony/entry/src/main/resources/rawfile/network_security_config.xml`
- Modify: `docs/项目完整解析.md`

- [x] Remove the hard-coded deployment IP from the network security resource.
- [x] Document `ServerConfig.ets` as the only server connection setting.

### Task 4: Verify

- [x] Run `python -m pytest tests/test_frontend_config_regression.py -q`.
- [x] Run `python -m pytest -q`.
- [x] Run `openharmony/hvigorw.bat --stop-daemon` and `openharmony/hvigorw.bat assembleHap --stacktrace`.
- [x] Review the final diff and branch status before committing.
