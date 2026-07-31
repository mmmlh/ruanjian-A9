# UTC Time Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every user-visible business timestamp in the OpenHarmony client display explicitly in UTC and generate history query boundaries in UTC.

**Architecture:** Add one dependency-free ArkTS utility that owns UTC parsing, formatting, and API serialization. Pages keep raw API model values and format only at display/query boundaries, so backend contracts and database fields remain unchanged.

**Tech Stack:** ArkTS/OpenHarmony API 20, Python `pytest` source-contract regressions, Hvigor OpenHarmony build, DevEco emulator manual verification.

---

## File Map

- Create `openharmony/entry/src/main/ets/common/UtcTimeUtil.ets`: pure UTC parsing, display formatting, and API timestamp serialization.
- Create `tests/test_utc_time_regression.py`: source-contract tests for the utility and every integration point.
- Modify `openharmony/entry/src/main/ets/pages/DashboardPage.ets`: UTC sync clock and activity timestamps.
- Modify `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`: UTC device last-seen text.
- Modify `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`: UTC history/log timestamps and UTC query boundary.
- Modify `openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets`: UTC service-card update clock.

### Task 1: Define The UTC Utility Contract

**Files:**
- Create: `tests/test_utc_time_regression.py`
- Create: `openharmony/entry/src/main/ets/common/UtcTimeUtil.ets`

- [ ] **Step 1: Write the failing utility contract test**

Create `tests/test_utc_time_regression.py` with:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UTC_UTIL = ROOT / "openharmony/entry/src/main/ets/common/UtcTimeUtil.ets"
DASHBOARD = ROOT / "openharmony/entry/src/main/ets/pages/DashboardPage.ets"
DEVICES = ROOT / "openharmony/entry/src/main/ets/pages/DeviceManagePage.ets"
MONITOR = ROOT / "openharmony/entry/src/main/ets/pages/DataMonitorPage.ets"
FORM_ABILITY = ROOT / "openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets"


def test_utc_time_utility_defines_display_and_api_contracts():
    assert UTC_UTIL.exists()
    source = UTC_UTIL.read_text(encoding="utf-8")

    assert "export function formatUtcTimestamp(" in source
    assert "export function formatUtcClock(" in source
    assert "export function toUtcApiTimestamp(" in source
    assert "getUTCMonth()" in source
    assert "getUTCDate()" in source
    assert "getUTCHours()" in source
    assert "getUTCMinutes()" in source
    assert " UTC" in source
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
pytest -q tests/test_utc_time_regression.py::test_utc_time_utility_defines_display_and_api_contracts
```

Expected: FAIL because `UtcTimeUtil.ets` does not exist.

- [ ] **Step 3: Implement the minimal UTC utility**

Create `openharmony/entry/src/main/ets/common/UtcTimeUtil.ets`:

```typescript
function pad2(value: number): string {
  return value < 10 ? '0' + value.toString() : value.toString()
}

function normalizeUtcInput(value: string): string {
  let input = value.trim()
  let noZonePattern = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$/
  if (!noZonePattern.test(input)) {
    return input
  }
  let normalized = input.replace(' ', 'T')
  if (normalized.length === 16) {
    normalized = normalized + ':00'
  }
  return normalized + 'Z'
}

function parseUtc(value: string): Date | null {
  let parsed = new Date(normalizeUtcInput(value))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function formatUtcTimestamp(value: string, fallback: string = ''): string {
  if (!value.trim()) {
    return fallback
  }
  let parsed = parseUtc(value)
  if (parsed === null) {
    return value
  }
  return pad2(parsed.getUTCMonth() + 1) + '-' + pad2(parsed.getUTCDate()) + ' ' +
    pad2(parsed.getUTCHours()) + ':' + pad2(parsed.getUTCMinutes()) + ' UTC'
}

export function formatUtcClock(value: Date): string {
  return pad2(value.getUTCHours()) + ':' + pad2(value.getUTCMinutes()) + ' UTC'
}

export function toUtcApiTimestamp(value: Date): string {
  return value.getUTCFullYear().toString() + '-' + pad2(value.getUTCMonth() + 1) + '-' +
    pad2(value.getUTCDate()) + ' ' + pad2(value.getUTCHours()) + ':' +
    pad2(value.getUTCMinutes()) + ':' + pad2(value.getUTCSeconds())
}
```

- [ ] **Step 4: Run the utility test and verify GREEN**

Run the Step 2 command again.

Expected: `1 passed`.

- [ ] **Step 5: Commit the utility contract**

```powershell
git add -- tests/test_utc_time_regression.py openharmony/entry/src/main/ets/common/UtcTimeUtil.ets
git commit -m "feat: add shared UTC time utility"
```

### Task 2: Format Backend Timestamps At Display Boundaries

**Files:**
- Modify: `tests/test_utc_time_regression.py`
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets:1-7,594-600`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets:1-6,93-101`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets:1-6,170-173`

- [ ] **Step 1: Add the failing display integration test**

Append:

```python
def test_business_timestamp_displays_use_the_shared_utc_formatter():
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    devices = DEVICES.read_text(encoding="utf-8")
    monitor = MONITOR.read_text(encoding="utf-8")

    assert "import { formatUtcClock, formatUtcTimestamp } from '../common/UtcTimeUtil'" in dashboard
    assert "return formatUtcTimestamp(value, value)" in dashboard
    assert "import { formatUtcTimestamp } from '../common/UtcTimeUtil'" in devices
    assert "'最近上报 ' + formatUtcTimestamp(value, value)" in devices
    assert "import { formatUtcTimestamp, toUtcApiTimestamp } from '../common/UtcTimeUtil'" in monitor
    assert "return formatUtcTimestamp(ts, ts)" in monitor
    assert "substring(5, 16)" not in dashboard
    assert "substring(5, 16)" not in devices
    assert "substring(5, 16)" not in monitor
```

- [ ] **Step 2: Run the new test and verify RED**

```powershell
pytest -q tests/test_utc_time_regression.py::test_business_timestamp_displays_use_the_shared_utc_formatter
```

Expected: FAIL on the missing imports and formatter calls.

- [ ] **Step 3: Replace page-local timestamp slicing**

In `DashboardPage.ets`, add:

```typescript
import { formatUtcClock, formatUtcTimestamp } from '../common/UtcTimeUtil'
```

Replace `shortTime` with:

```typescript
shortTime(value: string): string {
  return formatUtcTimestamp(value, value)
}
```

In `DeviceManagePage.ets`, add:

```typescript
import { formatUtcTimestamp } from '../common/UtcTimeUtil'
```

Replace `DeviceHelper.seenText` with:

```typescript
static seenText(value: string, fallback: string): string {
  if (!value) {
    return fallback
  }
  return '最近上报 ' + formatUtcTimestamp(value, value)
}
```

In `DataMonitorPage.ets`, add:

```typescript
import { formatUtcTimestamp, toUtcApiTimestamp } from '../common/UtcTimeUtil'
```

Replace `tm` with:

```typescript
tm(ts: string): string {
  return formatUtcTimestamp(ts, ts)
}
```

- [ ] **Step 4: Run the display test and verify GREEN**

Run the Step 2 command again.

Expected: `1 passed`.

- [ ] **Step 5: Commit display integration**

```powershell
git add -- tests/test_utc_time_regression.py openharmony/entry/src/main/ets/pages/DashboardPage.ets openharmony/entry/src/main/ets/pages/DeviceManagePage.ets openharmony/entry/src/main/ets/pages/DataMonitorPage.ets
git commit -m "fix: display backend timestamps in UTC"
```

### Task 3: Generate Client Times And History Boundaries In UTC

**Files:**
- Modify: `tests/test_utc_time_regression.py`
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets:307-315`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets:175-195`
- Modify: `openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets:1-10,101-113`

- [ ] **Step 1: Add the failing generated-time test**

Append:

```python
def test_client_generated_times_and_history_queries_are_utc():
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    monitor = MONITOR.read_text(encoding="utf-8")
    form_ability = FORM_ABILITY.read_text(encoding="utf-8")

    assert "return formatUtcClock(new Date())" in dashboard
    assert "return toUtcApiTimestamp(cutoff)" in monitor
    assert "import { formatUtcClock } from '../common/UtcTimeUtil'" in form_ability
    assert "'updateTime': formatUtcClock(now)" in form_ability
    assert "getHours()" not in dashboard
    assert "getMinutes()" not in dashboard
    assert "getHours()" not in monitor
    assert "getMinutes()" not in monitor
    assert "getHours()" not in form_ability
    assert "getMinutes()" not in form_ability
```

- [ ] **Step 2: Run the generated-time test and verify RED**

```powershell
pytest -q tests/test_utc_time_regression.py::test_client_generated_times_and_history_queries_are_utc
```

Expected: FAIL because the three call sites still use local clock fields.

- [ ] **Step 3: Replace local clock generation**

Replace `DashboardPage.syncTime` with:

```typescript
syncTime(): string {
  return formatUtcClock(new Date())
}
```

Replace `DataMonitorPage.historyStart` and remove `apiTime`:

```typescript
historyStart(): string {
  let cutoff = new Date(new Date().getTime() - this.historyHours * 60 * 60 * 1000)
  return toUtcApiTimestamp(cutoff)
}
```

In `EntryFormAbility.ets`, add:

```typescript
import { formatUtcClock } from '../common/UtcTimeUtil'
```

Replace its payload field with:

```typescript
'updateTime': formatUtcClock(now)
```

- [ ] **Step 4: Run all UTC tests and verify GREEN**

```powershell
pytest -q tests/test_utc_time_regression.py
```

Expected: `3 passed`.

- [ ] **Step 5: Commit generated-time integration**

```powershell
git add -- tests/test_utc_time_regression.py openharmony/entry/src/main/ets/pages/DashboardPage.ets openharmony/entry/src/main/ets/pages/DataMonitorPage.ets openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets
git commit -m "fix: generate client timestamps in UTC"
```

### Task 4: Regression, Build, And Runtime Verification

**Files:**
- Verify only; no planned production edits.

- [ ] **Step 1: Run focused frontend regressions**

```powershell
pytest -q tests/test_utc_time_regression.py tests/test_ui_log_formatting_regression.py tests/test_frontend_config_regression.py tests/test_mobile_layout_regression.py tests/test_ui_polish_regression.py
```

Expected: all selected tests pass.

- [ ] **Step 2: Run the complete Python suite**

```powershell
pytest -q
```

Expected: all repository tests pass with no failures.

- [ ] **Step 3: Build the OpenHarmony application**

```powershell
.\hvigorw.bat --mode module -p product=default -p module=entry@default -p buildMode=debug assembleHap
```

Run from `openharmony`.

Expected: `BUILD SUCCESSFUL` and a debug HAP under `entry/build/default/outputs/default/`.

- [ ] **Step 4: Verify the installed app in the DevEco emulator**

Rebuild/deploy through the existing DevEco run target, then check:

- Home subtitle uses `HH:mm UTC`.
- Device cards use `MM-DD HH:mm UTC`.
- Data history and runtime logs use `MM-DD HH:mm UTC`.
- The 24-hour and 7-day history filters still return records.
- Service card update time uses `HH:mm UTC` after its next refresh.

Expected: all visible business times carry `UTC`; no local-hour-only timestamp remains.

- [ ] **Step 5: Verify backend health was unaffected**

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/api/ready
```

Expected: HTTP 200 with database and MQTT both `ok`.

- [ ] **Step 6: Inspect final diff and worktree**

```powershell
git diff --check
git status --short --branch
```

Expected: no whitespace errors; only the planned UTC implementation remains if the task commits have not yet been made. The two pre-existing ZIP files remain untracked and unstaged.

