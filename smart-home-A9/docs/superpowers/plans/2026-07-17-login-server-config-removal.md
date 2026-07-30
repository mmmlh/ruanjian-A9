# Login Server Configuration Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the server-address editor from the OpenHarmony login page while preserving centralized address initialization.

**Architecture:** `LoginPage.ets` will no longer own a server URL or persist it during login. `ApiClient.ets` will continue to initialize the base URL from local preferences or `DEFAULT_SERVER_URL`, preserving existing behavior for normal app pages and the desktop card.

**Tech Stack:** ArkTS, OpenHarmony ArkUI, Python pytest source-regression checks.

---

### Task 1: Lock in the login-page boundary

**Files:**
- Modify: `tests/test_frontend_config_regression.py`
- Test: `tests/test_frontend_config_regression.py`

- [ ] **Step 1: Write the failing regression test**

```python
def test_login_page_does_not_expose_server_configuration():
    login_source = LOGIN_PAGE.read_text(encoding="utf-8")

    assert "setBaseUrl" not in login_source
    assert "showCfg" not in login_source
    assert "DEFAULT_SERVER_URL" not in login_source
    assert "getBaseUrl" not in login_source
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_frontend_config_regression.py::test_login_page_does_not_expose_server_configuration -q`

Expected: FAIL because the current login page imports and calls `setBaseUrl`, stores `showCfg` and a server URL, and reads `getBaseUrl`.

### Task 2: Remove login-page server configuration

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/LoginPage.ets`
- Test: `tests/test_frontend_config_regression.py`

- [ ] **Step 1: Replace the API client import**

```typescript
import { getToken, initApiClient, login } from '../common/ApiClient'
```

- [ ] **Step 2: Delete server configuration state and controls**

Delete the `url` and `showCfg` states, the `getBaseUrl` assignment in `aboutToAppear`, and the `Row` plus conditional `Column` that render the configuration control and server address input.

- [ ] **Step 3: Keep login focused on authentication**

```typescript
try {
  await login(this.user, this.pwd)
  this.getUIContext().getRouter().replaceUrl({ url: 'pages/DashboardPage' })
}
```

- [ ] **Step 4: Run the focused regression test**

Run: `python -m pytest tests/test_frontend_config_regression.py -q`

Expected: PASS, including existing checks that `ApiClient.ets` still imports `DEFAULT_SERVER_URL` and waits for preference initialization.

### Task 3: Verify no broader configuration regression

**Files:**
- Verify: `tests/test_frontend_config_regression.py`
- Verify: `tests/test_mobile_layout_regression.py`

- [ ] **Step 1: Run configuration and login-layout regressions**

Run: `python -m pytest tests/test_frontend_config_regression.py tests/test_mobile_layout_regression.py -q`

Expected: PASS, confirming the UI no longer exposes server configuration and the remaining login layout keeps its required scrollable structure.
