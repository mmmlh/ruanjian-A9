# Control Center UI and API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the OpenHarmony app into a competition-ready control center while verifying the app's key backend routes and improving client-side network error visibility.

**Architecture:** Keep the current ArkTS page structure and backend API surface, but refactor the highest-visibility pages into a unified control-center visual system. Start by hardening `ApiClient.ets`, then reshape dashboard, device control, monitoring, profile, and login pages around the verified route contracts already exposed by the FastAPI backend.

**Tech Stack:** OpenHarmony ArkTS, FastAPI, pytest, hvigor build, existing app models/common utilities

---

## File Map

- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/ApiClient.ets`
  - Improve request error extraction and preserve route compatibility.
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DashboardPage.ets`
  - Replace the current flat card layout with a control-center dashboard.
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
  - Rework device-type pages into stronger operation panels.
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
  - Reframe live, history, and logs into a monitoring console layout.
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/ProfilePage.ets`
  - Fix text rendering and align with the new visual system.
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/LoginPage.ets`
  - Apply light polish and clearer server configuration feedback.
- Verify: `D:/ruanjianbei/smart-home-A9/cloud/backend/tests/test_dashboard_contract.py`
  - Keep dashboard route usage anchored to passing backend tests.

### Task 1: Harden API Error Reporting

**Files:**
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/ApiClient.ets`
- Test: manual login and route failure checks after build

- [ ] **Step 1: Add transport-error extraction helpers**

```ts
function normalizeUnknownError(err: Object): string {
  let text = ''
  if (err === null || err === undefined) {
    return 'Network request failed'
  }
  try {
    text = JSON.stringify(err)
  } catch (stringifyErr) {
    text = ''
  }
  return text || 'Network request failed'
}

function extractTransportErrorMessage(err: Object): string {
  if (err instanceof Error) {
    return err.message || 'Network request failed'
  }
  let raw = normalizeUnknownError(err)
  if (raw.indexOf('timeout') >= 0) return 'Request timed out. Check server connection.'
  if (raw.indexOf('refused') >= 0) return 'Connection refused. Check server IP and port.'
  if (raw.indexOf('certificate') >= 0 || raw.indexOf('ssl') >= 0 || raw.indexOf('tls') >= 0) {
    return 'TLS or certificate validation failed.'
  }
  return raw
}
```

- [ ] **Step 2: Update `request()` catch path to stop collapsing errors into `Unknown error`**

```ts
  } catch (err) {
    if (err instanceof Error) {
      throw err
    }
    throw new Error(extractTransportErrorMessage(err as Object))
  } finally {
    httpRequest.destroy()
  }
```

- [ ] **Step 3: Improve non-2xx response parsing**

```ts
    let detailMessage = `Request failed: ${response.responseCode}`
    let resultText = response.result as string
    if (resultText) {
      try {
        let errObj: Record<string, Object> = JSON.parse(resultText) as Record<string, Object>
        let detail = errObj['detail']
        let message = errObj['message']
        if (detail !== undefined && detail !== null) {
          detailMessage = detail as string
        } else if (message !== undefined && message !== null) {
          detailMessage = message as string
        }
      } catch (parseErr) {
        detailMessage = `Request failed: ${response.responseCode}`
      }
    }
```

- [ ] **Step 4: Verify backend route contract still matches frontend call sites**

Run: `cd D:/ruanjianbei/smart-home-A9/cloud/backend; python -m pytest tests/test_dashboard_contract.py -q`  
Expected: `passed`

- [ ] **Step 5: Commit**

```bash
git add D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/ApiClient.ets D:/ruanjianbei/smart-home-A9/cloud/backend/tests/test_dashboard_contract.py
git commit -m "feat: improve client api error reporting"
```

### Task 2: Rebuild the Dashboard Into a Control Center

**Files:**
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Test: dashboard load after HAP build

- [ ] **Step 1: Preserve existing data-loading and realtime refresh methods**

```ts
  aboutToAppear(): void {
    this.ld()
    connectWS((msg: string) => this.ws(msg), (connected: boolean) => {
      this.ok = connected
    })
  }

  async ld(): Promise<void> {
    this.loading = true
    this.errorMessage = ''
    try {
      let summary = await getDashboardSummary()
      this.rooms = summary.rooms
      this.devices = summary.devices
      this.scenes = summary.scenes
      this.recentLogs = summary.recent_logs
      this.onlineCount = summary.stats.online_devices
      this.totalCount = summary.stats.total_devices
      this.syncClimate()
    } catch (err) {
      this.errorMessage = (err as Error).message || 'Failed to load dashboard summary'
    } finally {
      this.loading = false
    }
  }
```

- [ ] **Step 2: Replace the top bar with a dark hero summary card**

```ts
  @Builder buildHeroCard() {
    Column() {
      Row() {
        Column() {
          Text('Smart Home Control').fontSize(24).fontWeight(FontWeight.Bold).fontColor('#F7F8FA')
          Text(this.ok ? 'Realtime connected' : 'Realtime offline').fontSize(12).fontColor('#B7C2D0').margin({ top: 6 })
        }.alignItems(HorizontalAlign.Start)
        Blank()
        Column() {
          Text(this.onlineCount.toString()).fontSize(34).fontWeight(FontWeight.Bold).fontColor('#7FE3C5')
          Text('/' + this.totalCount.toString() + ' online').fontSize(12).fontColor('#B7C2D0')
        }.alignItems(HorizontalAlign.End)
      }.width('100%')
    }
    .padding(20)
    .borderRadius(24)
    .backgroundColor('#18212D')
  }
```

- [ ] **Step 3: Move scenes, recent activity, room chips, and device grid into dedicated builder sections**

```ts
  @Builder buildSceneStrip() { /* render larger scene cards */ }
  @Builder buildActivityPanel() { /* render recent_logs cards */ }
  @Builder buildRoomFilter() { /* render All + room chips */ }
  @Builder buildDeviceGrid() { /* render larger cards with better hierarchy */ }
```

- [ ] **Step 4: Swap the page body to the new section order**

```ts
      Scroll() {
        Column() {
          this.buildHeroCard()
          this.buildSceneStrip()
          this.buildActivityPanel()
          this.buildRoomFilter()
          this.buildDeviceGrid()
        }
        .padding({ left: 16, right: 16, top: 16, bottom: 88 })
      }
```

- [ ] **Step 5: Commit**

```bash
git add D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DashboardPage.ets
git commit -m "feat: redesign dashboard as control center"
```

### Task 3: Refactor Device Control Panels

**Files:**
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- Test: command flows for at least one device page

- [ ] **Step 1: Keep the current load and command methods intact**

```ts
  async load(): Promise<void> {
    this.loading = true
    try {
      let curId = 0
      let current = this.cur()
      if (current) curId = current.id
      this.ds = await getDevicesForUi(undefined, this.dt)
      if (this.ds.length === 0) {
        this.ix = 0
        this.clr()
        return
      }
      let next = 0
      for (let i = 0; i < this.ds.length; i++) {
        if (this.ds[i].id === curId) next = i
      }
      this.sl(next)
    } catch (err) {
      this.errorMessage = (err as Error).message || 'Failed to load devices'
    } finally {
      this.loading = false
    }
  }
```

- [ ] **Step 2: Introduce a shared status header and device-switcher chip row**

```ts
  @Builder buildStatusHeader() {
    let current = this.cur()
    Column() {
      Text(this.tn()).fontSize(24).fontWeight(FontWeight.Bold).fontColor('#F7F8FA')
      Text(current ? current.name : 'No device selected').fontSize(13).fontColor('#B7C2D0').margin({ top: 6 })
    }
    .width('100%')
    .padding(20)
    .borderRadius(24)
    .backgroundColor('#18212D')
  }
```

- [ ] **Step 3: Rebuild each device type area as a stronger control panel**

```ts
  @Builder buildLightPanel() { /* hero icon, brightness, power CTA */ }
  @Builder buildAcPanel() { /* temperature hero, mode chips, power CTA */ }
  @Builder buildLockPanel() { /* security state, unlock/lock CTA */ }
  @Builder buildCurtainPanel() { /* position hero, quick open/close, slider */ }
  @Builder buildHumidifierPanel() { /* level, target humidity, power CTA */ }
```

- [ ] **Step 4: Route `build()` through the new panel builders**

```ts
      } else if (this.dt === 'light') {
        Scroll() { Column() { this.buildStatusHeader(); this.buildLightPanel() } }
      } else if (this.dt === 'ac') {
        Scroll() { Column() { this.buildStatusHeader(); this.buildAcPanel() } }
      }
```

- [ ] **Step 5: Commit**

```bash
git add D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets
git commit -m "feat: redesign device control panels"
```

### Task 4: Reframe Monitoring Into an Operations Console

**Files:**
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
- Test: load live, history, and logs after build

- [ ] **Step 1: Keep `load()`, `refresh()`, and device/history/log retrieval logic**

```ts
  async load(): Promise<void> {
    this.loading = true
    this.errorMessage = ''
    try {
      await this.loadSensors()
      this.sdata = await getSensorHistory(undefined, 60)
      this.logs = await getDeviceLogs(undefined, 40)
    } catch (err) {
      this.errorMessage = (err as Error).message || 'Failed to load monitor data'
    } finally {
      this.loading = false
    }
  }
```

- [ ] **Step 2: Add a top summary band and stronger tab switcher**

```ts
  @Builder buildMonitorHero() {
    Row() {
      Column() {
        Text('Data Monitor').fontSize(22).fontWeight(FontWeight.Bold).fontColor('#F7F8FA')
        Text('Live telemetry, history, and operation logs').fontSize(12).fontColor('#B7C2D0').margin({ top: 6 })
      }
      Blank()
      Text(this.sensors.length.toString()).fontSize(30).fontWeight(FontWeight.Bold).fontColor('#7FE3C5')
    }
    .padding(20)
    .borderRadius(24)
    .backgroundColor('#18212D')
  }
```

- [ ] **Step 3: Convert each tab into a dedicated section builder**

```ts
  @Builder buildLivePanel() { /* metric cards for sensor status */ }
  @Builder buildHistoryPanel() { /* filter chips + history list */ }
  @Builder buildLogsPanel() { /* operations list cards */ }
```

- [ ] **Step 4: Replace the plain page layout with the hero + tabs + section builder flow**

```ts
      Scroll() {
        Column() {
          this.buildMonitorHero()
          this.buildTabBar()
          if (this.tab === 0) this.buildLivePanel()
          else if (this.tab === 1) this.buildHistoryPanel()
          else this.buildLogsPanel()
        }
      }
```

- [ ] **Step 5: Commit**

```bash
git add D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DataMonitorPage.ets
git commit -m "feat: redesign data monitor console"
```

### Task 5: Refresh Profile and Login Presentation

**Files:**
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/ProfilePage.ets`
- Modify: `D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/LoginPage.ets`
- Test: login and profile navigation after build

- [ ] **Step 1: Replace garbled strings in `ProfilePage.ets` and keep the current password-change flow**

```ts
  if (!this.old || !this.np || !this.np2) { this.err = 'Please fill in all fields'; return }
  if (this.np.length < 6) { this.err = 'New password must be at least 6 characters'; return }
  if (this.np !== this.np2) { this.err = 'The two passwords do not match'; return }
```

- [ ] **Step 2: Rebuild profile into identity, account, security, and session sections**

```ts
  @Builder buildIdentityCard() { /* avatar, username, role */ }
  @Builder buildAccountCard() { /* account info rows */ }
  @Builder buildSecurityCard() { /* password form */ }
  @Builder buildSessionCard() { /* switch account + logout */ }
```

- [ ] **Step 3: Lightly polish `LoginPage.ets` with cleaner copy and stronger hierarchy**

```ts
        Text('Smart Home').fontSize(28).fontWeight(FontWeight.Bold).fontColor('#18212D')
        Text('Control your connected home in one place').fontSize(13).fontColor('#6B7785').margin({ top: 8 })
```

- [ ] **Step 4: Clarify login validation and server URL messaging**

```ts
    if (!this.user || !this.pwd) {
      this.err = 'Please enter username and password'
      return
    }
```

- [ ] **Step 5: Commit**

```bash
git add D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/ProfilePage.ets D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/LoginPage.ets
git commit -m "feat: polish profile and login experience"
```

### Task 6: Verify Integration End-to-End

**Files:**
- Verify only

- [ ] **Step 1: Run backend contract tests**

Run: `cd D:/ruanjianbei/smart-home-A9/cloud/backend; python -m pytest tests/test_dashboard_contract.py -q`  
Expected: `3 passed`

- [ ] **Step 2: Run the full backend suite**

Run: `cd D:/ruanjianbei/smart-home-A9/cloud/backend; python -m pytest tests -q`  
Expected: all tests pass

- [ ] **Step 3: Build the OpenHarmony HAP**

Run: `cd D:/ruanjianbei/smart-home-A9/openharmony; .\\hvigorw.bat assembleHap --stacktrace`  
Expected: build success and `entry-default-signed.hap` generated

- [ ] **Step 4: Spot-check app flows**

```text
1. Open LoginPage and verify readable text and server config field.
2. Log in and verify DashboardPage loads summary data.
3. Open one device control page and send a command.
4. Open DataMonitorPage and verify live/history/log tabs load.
5. Open ProfilePage and verify account info loads.
```

- [ ] **Step 5: Commit final integration fixes if needed**

```bash
git add D:/ruanjianbei/smart-home-A9
git commit -m "fix: finalize control center integration polish"
```
