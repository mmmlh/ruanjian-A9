# Home Assistant Backend Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the backend and OpenHarmony client around a single Home Assistant style state read path and service write path without breaking the legacy device command API.

**Architecture:** Extract shared entity-state helpers plus a shared device-command execution path, then make `/api/states`, `/api/services`, and the legacy `/api/devices/{id}/command` all reuse the same logic. Finally, point the OpenHarmony client wrapper at the unified write path while preserving the existing call sites.

**Tech Stack:** FastAPI, SQLite, pytest, ArkTS, MQTT mock patching

---

### Task 1: Lock The Backend Contract With Tests

**Files:**
- Create: `cloud/backend/tests/test_home_assistant_api.py`

- [ ] Add tests for `/api/states` seed coverage, `/api/services` returning updated state, and `/api/devices/{id}/command` updating `/api/states`.
- [ ] Run: `cd cloud/backend; $env:PYTHONPATH='.'; python -m pytest tests/test_home_assistant_api.py -q`
- [ ] Confirm at least the new service/state assertions fail before implementation.

### Task 2: Extract Shared Entity State And Command Logic

**Files:**
- Create: `cloud/backend/app/services/entity_state.py`
- Create: `cloud/backend/app/services/device_command.py`
- Modify: `cloud/backend/app/api/states.py`
- Modify: `cloud/backend/app/api/services.py`
- Modify: `cloud/backend/app/api/devices.py`

- [ ] Move duplicated entity parsing and state shaping code into shared helpers.
- [ ] Implement one shared command execution path that decodes encrypted payloads, writes device logs, applies optimistic status updates, publishes MQTT, and returns a normalized state object.
- [ ] Make `/api/services` and legacy `/api/devices/{id}/command` reuse that shared execution path.

### Task 3: Repoint The OpenHarmony Client To The Unified Write Path

**Files:**
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`

- [ ] Keep `callService()` as the canonical write helper.
- [ ] Make `sendCommand()` delegate to `callService()` so existing page code keeps working while the backend contract is unified.

### Task 4: Verify The Slice

**Files:**
- Test: `cloud/backend/tests/test_home_assistant_api.py`
- Test: `cloud/backend/tests/test_auth.py`
- Test: `cloud/backend/tests/test_devices.py`

- [ ] Run: `cd cloud/backend; $env:PYTHONPATH='.'; python -m pytest tests/test_home_assistant_api.py tests/test_auth.py tests/test_devices.py -q`
- [ ] Check that the new contract tests pass and no existing auth/device regression appears in this slice.
