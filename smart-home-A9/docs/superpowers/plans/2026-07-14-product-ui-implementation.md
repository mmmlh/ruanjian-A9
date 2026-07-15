# A9 Smart Home Product UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 OpenHarmony 客户端收敛为一套以“看清全屋状态、快速完成控制、明确获得结果”为核心的智能家居产品体验，同时不破坏 FastAPI、MQTT 与实时更新链路。

**Architecture:** 保留现有八个路由和 `DashboardPage → DeviceRemotePage` 控制路径；新增的只是共享视觉/导航组件和页面内状态，不重写后端领域模型。根页面采用固定底部导航，设备详情、数据监测等任务页保留返回导航，所有控制结果继续通过现有 `ApiClient`、`ServiceCallResult` 与实时刷新回流。

**Tech Stack:** OpenHarmony ArkTS、ArkUI、FastAPI、MQTT、pytest、Hvigor。

---

## Product Scope and Success Criteria

### Product decision

产品定位为“家庭控制中心”，不是设备类型快捷遥控器。一级导航固定为：`首页`、`设备`、`自动化`、`我的`：

- `首页`：全屋状态、常用场景、房间设备和最近活动；
- `设备`：已绑定设备优先，添加/扫描设备是次级任务；
- `自动化`：规则、场景联动和创建入口；
- `我的`：账户、安全与会话；
- `数据监测`：从首页入口进入的任务页，不占一级导航。

### Definition of Done

- 首页不再显示硬编码的环境摘要；状态、上次同步时间和在线设备数来自当前请求/实时状态。
- 一级导航在根页面固定可见，切换根页面不堆叠路由历史；设备类型不再作为一级 Tab。
- 注册、设备、自动化、监测、个人中心都使用 `ControlCenterTheme` 与统一的间距、圆角、反馈规范。
- 场景、设备控制、离线保护、加载、空数据和失败状态都能让用户知道“发生了什么、下一步做什么”。
- 所有既有后端测试、根目录 UI 回归测试和 HAP 构建继续通过；真实控制请求仍走现有 `/api/services` 和 MQTT 流程。

## File Map

- Modify: `openharmony/entry/src/main/ets/common/ControlCenterTheme.ets` — 设计令牌与可访问尺寸。
- Modify: `openharmony/entry/src/main/ets/common/ControlCenterKit.ets` — 顶栏、固定导航、统一空状态与反馈组件。
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets` — 首页信息层级、状态可信度、固定导航和场景确认。
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets` — “设备”根页面与设备接入二级流程。
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets` — 自动化根页面与固定导航。
- Modify: `openharmony/entry/src/main/ets/pages/ProfilePage.ets` — “我的”根页面与账户操作语义。
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets` — 指令中、已下发、已同步的控制反馈。
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets` — 监测筛选、趋势摘要、空/错状态。
- Modify: `openharmony/entry/src/main/ets/pages/LoginPage.ets`, `RegisterPage.ets` — 认证体验收口与键盘可达性。
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`, `openharmony/entry/src/main/ets/model/DeviceModel.ets` — 仅在监测时间范围/展示模型确有缺口时扩展。
- Modify: `cloud/backend/app/api/data.py`, `cloud/backend/tests/test_data.py` — 为监测时间范围提供最小、可测试的查询契约。
- Modify: `tests/test_ui_theme_regression.py`, `tests/test_mobile_layout_regression.py`, `tests/test_openharmony_control_regressions.py` — 保护新的交互约束。

## Work Package A — Product Foundation and Navigation

### Task 1: Freeze interaction inventory before visual changes

**Files:**
- Test: `tests/test_ui_theme_regression.py`
- Test: `tests/test_mobile_layout_regression.py`

- [ ] Add source-regression assertions that the four root pages import `ControlCenterTheme` and the shared bottom navigation component.
- [ ] Add an assertion that `RegisterPage.ets` contains `Scroll()` so software keyboard input cannot hide the submit action.
- [ ] Run `python -m pytest tests/test_ui_theme_regression.py tests/test_mobile_layout_regression.py -q` and confirm the new assertions fail before UI implementation.

### Task 2: Define one reusable visual and touch system

**Files:**
- Modify: `openharmony/entry/src/main/ets/common/ControlCenterTheme.ets`
- Modify: `openharmony/entry/src/main/ets/common/ControlCenterKit.ets`

- [ ] Add spacing tokens `spaceXs=4`, `spaceSm=8`, `spaceMd=12`, `spaceLg=16`, `spaceXl=24` and control-size tokens `tapTarget=44`, `controlHeight=48` to `ControlCenterTheme`.
- [ ] Keep one semantic palette: green for primary/success, amber for attention, muted red for destructive actions, and neutral surfaces for secondary actions. Do not introduce page-local brand colors.
- [ ] Add `AppTopBar`, `AppBottomNav`, and `EmptyState` to `ControlCenterKit`. `AppBottomNav` accepts the active key and uses `replaceUrl` for root-page changes; its items are exactly 首页、设备、自动化、我的.
- [ ] Use text plus icon for status; no state may be represented by color alone.
- [ ] Run the two root UI tests again and confirm they pass.

### Task 3: Apply the shared shell to root and authentication pages

**Files:**
- Modify: `DashboardPage.ets`, `DeviceManagePage.ets`, `RulesPage.ets`, `ProfilePage.ets`
- Modify: `LoginPage.ets`, `RegisterPage.ets`

- [ ] Move each root page's `AppBottomNav` outside its `Scroll()` container so it remains visible while content scrolls.
- [ ] Use `AppTopBar` for task pages; DeviceRemotePage and DataMonitorPage retain a back action instead of bottom navigation.
- [ ] Convert every user-visible color in `RegisterPage.ets` to theme tokens; match LoginPage card radius, input height, primary button, error banner, and page background.
- [ ] Wrap registration content in `Scroll()` with bottom inset so the button remains reachable while the keyboard is open.
- [ ] Run `python -m pytest tests/test_ui_theme_regression.py tests/test_mobile_layout_regression.py -q`.

**Acceptance:** A user can reach every root capability with one tap from a persistent four-item nav, and login/registration look like the same application.

## Work Package B — Home and Device Experience

### Task 4: Make dashboard status truthful and scannable

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Test: `tests/test_openharmony_control_regressions.py`

- [ ] Replace the static date/city/temperature subtitle with `最后同步 HH:mm` derived when `getDashboardSummary()` succeeds; show “正在连接” only while initial data is unavailable.
- [ ] Keep the top hierarchy as: 全屋状态 → online/total devices → environment metrics → quick scenes → room devices → recent activity.
- [ ] Retain the existing websocket local-patch behavior; a realtime update must update the matching card rather than ask users to refresh manually.
- [ ] Use a single prominent alert when any device is offline. The alert text names the offline count and offers the user a device-page entry.
- [ ] Add a regression assertion that the static weather-style subtitle is absent and `updateDeviceFromRealtime` remains used.
- [ ] Run `python -m pytest tests/test_openharmony_control_regressions.py -q`.

### Task 5: Add intentional scene execution feedback

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`

- [ ] Classify scenes containing `离家`, `安防`, `门锁`, or `锁门` as safety-sensitive and show a confirmation dialog before calling `executeScene`.
- [ ] The confirmation copy must state the scene name and that affected devices will be controlled; actions are `取消` and `确认执行`.
- [ ] For every scene, change card state in order: normal → 执行中 → 已下发/执行失败; refresh dashboard summary after completion to reconcile the device cards.
- [ ] Preserve the existing backend scene endpoint and do not fabricate success when `/api/scenes/{id}/execute` fails.
- [ ] Manually verify: execute one normal scene, cancel one safety-sensitive scene, then execute it and check recent activity.

### Task 6: Turn device management into a device hub

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`
- Test: `cloud/backend/tests/test_dashboard_contract.py`

- [ ] Make “我的设备” the default content and move discovery behind a clear `添加设备` entry; preserve the existing `discoverDevices()` and `bindDevice()` calls.
- [ ] Device cards show name, room, type, online text, last update, and status summary. Remove `mqtt_topic` from the default card; expose it only in a development-only details area if it remains needed.
- [ ] Use a three-step bind sheet: choose candidate → choose room → optionally edit display name → bind. Disable the final action until a room is chosen.
- [ ] Require a confirmation dialog before deleting a bound device; success refreshes the device list and returns explicit feedback.
- [ ] Run `cd cloud/backend; python -m pytest tests/test_dashboard_contract.py tests/test_devices.py -q`.

**Acceptance:** The path “发现设备 → 绑定到房间 → 首页可见 → 进入控制” is understandable without seeing MQTT terminology.

### Task 7: Strengthen control confidence without changing control semantics

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- Test: `tests/test_openharmony_control_regressions.py`
- Test: `tests/test_remote_offline_guard_regression.py`

- [ ] Standardize control feedback to `指令发送中` → `指令已下发` → `状态已同步`; if the refresh fails, keep “已下发，等待设备回报” rather than reporting a false final state.
- [ ] Keep primary actions disabled for offline devices and surface the existing protected-offline explanation above the controls.
- [ ] Keep sliders debounced and show the value the user is about to apply; do not publish one MQTT command per drag frame.
- [ ] Preserve type-specific panels for light, air conditioner, lock, curtain, and humidifier; each panel has only one visually dominant primary action.
- [ ] Run `python -m pytest tests/test_openharmony_control_regressions.py tests/test_remote_offline_guard_regression.py -q`.

## Work Package C — Automation, Monitoring, and Account Completion

### Task 8: Make automation a first-class root capability

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets`
- Test: `cloud/backend/tests/test_rules.py`

- [ ] Apply fixed `AppBottomNav` with `自动化` active; keep rule creation as a dedicated modal/task flow.
- [ ] On each rule card, render a readable summary in the format “当 [触发条件] 时，执行 [动作]”，with enabled state and last relevant result where available.
- [ ] Keep server-provided `/api/rules/options` as the source of valid triggers, targets and actions; the UI must not expose unsupported combinations.
- [ ] After creation, toggle, or deletion, reload the rule list and present an in-context success/error banner.
- [ ] Run `cd cloud/backend; python -m pytest tests/test_rules.py -q`.

### Task 9: Upgrade monitoring from raw list to operational insight

**Files:**
- Modify: `cloud/backend/app/api/data.py`
- Modify: `cloud/backend/tests/test_data.py`
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`

- [ ] Extend only the sensor-history query with optional `start_at` and `end_at` ISO-8601 parameters, retaining current `device_id` and `limit` behavior for existing callers.
- [ ] Add backend tests for valid 24-hour filtering, valid 7-day filtering, and invalid timestamp rejection; existing no-filter behavior must remain unchanged.
- [ ] Add client range chips `24小时` and `7天`; pass the chosen timestamps through `getSensorHistory`.
- [ ] Above the history list, display summary values: latest value, change versus first sample in range, and sample count. Do not add a third-party chart library in this iteration.
- [ ] Keep Live, History, and Logs as separate states. Each must have distinct loading, empty, and retry messages.
- [ ] Run `cd cloud/backend; python -m pytest tests/test_data.py -q`.

### Task 10: Complete account semantics and accessibility basics

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/ProfilePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/LoginPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RegisterPage.ets`

- [ ] Rename the action currently labelled “切换账号” to “退出当前账号并登录其他账号”, or implement a genuinely different account-switch flow; labels and behavior must match.
- [ ] Add destructive confirmation for logout and clarify that local login state will be cleared.
- [ ] Ensure auxiliary text is at least 12sp and operational text is at least 14sp; make every tap target at least `tapTarget` high/wide.
- [ ] Replace newly touched Emoji controls with one consistent icon treatment; existing device-type pictograms may remain until a final asset pass.
- [ ] Manually verify login, registration with keyboard open, password update, and logout.

## Work Package D — Release Verification

### Task 11: Run automated regression gates

**Files:**
- Test: `tests/`
- Test: `cloud/backend/tests/`

- [ ] Run `python -m pytest tests -q` from repository root.
- [ ] Run `cd cloud/backend; python -m pytest tests -q`.
- [ ] Resolve only regressions introduced by this UI plan; do not refactor unrelated backend or deployment code.

### Task 12: Validate the competition demo journey on device

**Files:**
- Verify: `openharmony/entry/build/default/outputs/default/entry-default-signed.hap`

- [ ] Build with `cd openharmony; .\hvigorw.bat --stop-daemon; .\hvigorw.bat assembleHap --stacktrace`.
- [ ] On a real device or emulator, record evidence for: login → 首页；发现/绑定设备；执行普通场景；执行离家确认；控制在线设备；查看离线保护；创建规则；查看 24 小时历史；退出账号。
- [ ] Test 320dp-equivalent narrow layout and keyboard-open registration; no primary action may be clipped.
- [ ] Capture final screenshots for 首页、设备、设备控制、自动化、数据监测、我的 and compare them against the shared token specification.

## Release Metrics

| Metric | Acceptance target |
| --- | --- |
| Core path | Login to first device control within three taps after landing on 首页 |
| Status trust | No hardcoded environmental/current-state values in user-visible home content |
| Control feedback | Every action has busy, success/failure, and post-action state outcome |
| Safety | Offline controls blocked; safety-sensitive scene and destructive account/device actions confirmed |
| Visual consistency | All active pages use shared theme tokens; no page-local primary color |
| Regression | Root/UI tests, backend tests, and HAP build pass |

## Risks and Explicit Non-goals

- Do not introduce a new device registry, MQTT topic scheme, analytics service, or third-party chart library.
- Do not turn a scene command result into a claimed device-state result before MQTT/status refresh confirms it.
- Do not delete legacy code or change active route manifests as part of this plan unless a reference scan proves the item unreachable.
- If SDK configuration blocks HAP packaging, report it as an environment blocker after source-level tests pass; do not change ArkTS business logic to mask it.
