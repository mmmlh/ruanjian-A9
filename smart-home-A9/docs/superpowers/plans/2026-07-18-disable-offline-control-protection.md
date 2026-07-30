# Disable Offline Control Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permit commands for offline devices while retaining the device's displayed online/offline status.

**Architecture:** The OpenHarmony remote page will retain only its in-flight command lock, so offline state no longer disables a control or aborts a command. The FastAPI command service will retain entity and publish-failure validation but remove its freshness-based command rejection.

**Tech Stack:** ArkTS/OpenHarmony, FastAPI, pytest.

---

### Task 1: Replace the remote-page protection regression

**Files:**
- Modify: `D:\ruanjianbei\smart-home-A9\tests\test_remote_offline_guard_regression.py:8-13`
- Modify: `D:\ruanjianbei\smart-home-A9\openharmony\entry\src\main\ets\pages\DeviceRemotePage.ets:215-239,436-459,494,560-564,604-630`

- [ ] **Step 1: Write the failing regression test**

```python
def test_device_remote_page_allows_commands_when_current_device_is_offline():
    source = REMOTE_PAGE.read_text(encoding="utf-8")

    assert ".enabled(!this.commandBusy)" in source
    assert ".enabled(this.currentOnline() && !this.commandBusy)" not in source
    assert "if (!current.online)" not in source
    assert "if (!this.currentOnline())" not in source
    assert "控制按钮已受保护" not in source
```

- [ ] **Step 2: Verify the test fails against the current guard**

Run: `python -m pytest tests/test_remote_offline_guard_regression.py -q`

Expected: FAIL because controls are still gated by `currentOnline()` and offline commands return early.

- [ ] **Step 3: Remove only remote-page offline command guards**

```typescript
async cmdCurrent(action: string, params?: Object): Promise<void> {
  let current = this.cur()
  if (!current || this.commandBusy) {
    return
  }
  await this.cmd(current.id, action, params)
}

@Builder buildPrimaryButton(label: string, color: string, action: () => void) {
  // Existing Button configuration remains unchanged.
  Button(this.commandBusy ? '执行中...' : label)
    .enabled(!this.commandBusy)
    .onClick(action)
}
```

Remove the analogous slider early return, offline warning banner, and protection-specific copy. Keep online/offline labels and retain `commandBusy` locking in both button builders.

- [ ] **Step 4: Verify the remote-page regression passes**

Run: `python -m pytest tests/test_remote_offline_guard_regression.py -q`

Expected: PASS.

### Task 2: Permit offline commands in the API

**Files:**
- Modify: `D:\ruanjianbei\smart-home-A9\cloud\backend\tests\test_devices.py:263-283`
- Modify: `D:\ruanjianbei\smart-home-A9\cloud\backend\app\services\device_command.py:9,127-129`

- [ ] **Step 1: Write the failing API regression test**

```python
def test_service_call_accepts_offline_device(self, client, auth_headers, db):
    db.execute("UPDATE devices SET updated_at = ? WHERE id = 4", ("2000-01-01 00:00:00",))
    db.commit()

    response = client.post(
        "/api/services",
        json={"entity_id": "light.device_4", "action": "on", "params": {"brightness": 75}},
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["entity_id"] == "light.device_4"
    assert payload["action"] == "on"
    assert payload["service_response"]["light.device_4"]["payload"] == {"action": "on", "brightness": 75}
```

- [ ] **Step 2: Verify the test fails with the existing rejection**

Run: `python -m pytest cloud/backend/tests/test_devices.py::TestDevices::test_service_call_accepts_offline_device -q`

Expected: FAIL with `409` and `device_offline`.

- [ ] **Step 3: Remove only the freshness-based dispatch rejection**

```python
from app.services.mqtt_client import publish_message
# Do not import is_device_online here.

# After expected_device_type validation, decode the command directly.
actual_action, actual_params = decode_command_payload(action, params, user)
```

Delete the `last_seen_source` assignment and the `is_device_online` condition. Preserve all other validation and MQTT failure handling.

- [ ] **Step 4: Verify the API regression passes**

Run: `python -m pytest cloud/backend/tests/test_devices.py::TestDevices::test_service_call_accepts_offline_device -q`

Expected: PASS.

### Task 3: Verify the changed control contract

**Files:**
- Verify: `D:\ruanjianbei\smart-home-A9\tests\test_remote_offline_guard_regression.py`
- Verify: `D:\ruanjianbei\smart-home-A9\cloud\backend\tests\test_devices.py`

- [ ] **Step 1: Run both focused regression files**

Run: `python -m pytest tests/test_remote_offline_guard_regression.py cloud/backend/tests/test_devices.py -q`

Expected: PASS with no warnings or failures.

- [ ] **Step 2: Run the repository suite**

Run: `python -m pytest tests -q`

Expected: PASS with no failures.

- [ ] **Step 3: Inspect the final diff**

Run: `git diff --check; git diff -- tests/test_remote_offline_guard_regression.py cloud/backend/tests/test_devices.py cloud/backend/app/services/device_command.py openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`

Expected: no whitespace errors; only the planned test and protection changes.
