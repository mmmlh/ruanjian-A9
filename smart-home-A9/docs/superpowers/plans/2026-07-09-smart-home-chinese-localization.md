# Smart Home Chinese Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize user-visible frontend UI text and backend response text into Chinese without changing machine-readable error codes, API paths, or business behavior.

**Architecture:** Add a lightweight ArkTS text layer in `UiText.ets` for shared UI labels, page copy, and network/API error copy. Migrate OpenHarmony pages and `ApiClient.ets` to consume those centralized strings, then update backend user-facing labels and tests that intentionally assert visible text while preserving stable `detail` codes such as `rule_name_required` and `device_offline`.

**Tech Stack:** OpenHarmony ArkTS, FastAPI, pytest, PowerShell, hvigor

---

## File Structure

- Create: `openharmony/entry/src/main/ets/common/UiText.ets`
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Modify: `openharmony/entry/src/main/ets/pages/LoginPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RegisterPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/ProfilePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/ACControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/CurtainControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DoorLockPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/HumidifierControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/LightControlPage.ets`
- Modify: `cloud/backend/app/main.py`
- Modify: `cloud/backend/app/api/bind_device.py`
- Modify: `cloud/backend/app/api/rules.py`
- Modify: `cloud/backend/app/services/device_command.py`
- Modify: `cloud/backend/app/services/discovery_catalog.py`
- Test: `cloud/backend/tests/test_devices.py`
- Test: `cloud/backend/tests/test_rules.py`
- Test: `tests/test_ui_log_formatting_regression.py`
- Verify: `tests/test_openharmony_control_regressions.py`

### Responsibility Map

- `UiText.ets`: single lightweight source for reusable Chinese UI labels, page titles, empty states, and small formatter helpers.
- `ApiClient.ets`: transport/API error mapping boundary; keep machine codes intact, convert user-facing messages to Chinese before pages render them.
- ArkTS page files: remove inline English UI copy and consume `UiText.ets` constants/helpers.
- Backend API/service files: update only display-oriented `message`, app title, operator labels, and candidate names/hints that are surfaced directly to users.
- pytest files: update assertions that intentionally verify visible copy, while leaving machine-code assertions unchanged.

### Guardrails

- Do not rename error-code payloads like `rule_name_required`, `candidate_not_found`, `device_offline`.
- Do not change request/response schema keys, database column names, or MQTT action values.
- Prefer centralized text constants over one-off replacements, but do not introduce a full i18n framework or language switching.
- Because the worktree is dirty, stage only files touched by each task.

### Task 1: Introduce the Frontend Text Layer and Error Mapping

**Files:**
- Create: `openharmony/entry/src/main/ets/common/UiText.ets`
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`

- [ ] **Step 1: Capture the current English error copy before editing**

Run:

```powershell
rg -n "Network request failed|Request timed out|Connection refused|TLS or certificate validation failed|Empty response body|Request failed|Device is offline" `
  "D:\ruanjianbei\smart-home-A9\openharmony\entry\src\main\ets\common\ApiClient.ets"
```

Expected: matches for the existing English transport and API error strings around `extractTransportErrorMessage()` and `mapApiErrorMessage()`.

- [ ] **Step 2: Create `UiText.ets` with shared Chinese labels and formatter helpers**

Add:

```ts
export const CommonText = {
  appName: '智慧家居',
  refresh: '刷新',
  cancel: '取消',
  create: '创建',
  save: '保存',
  edit: '编辑',
  delete: '删除',
  bind: '绑定',
  online: '在线',
  offline: '离线',
  loading: '加载中...'
}

export const NetworkText = {
  requestFailed: '网络请求失败',
  timeout: '请求超时，请检查服务器连接。',
  refused: '连接被拒绝，请检查服务器地址和端口。',
  tlsFailed: 'TLS 或证书校验失败。',
  emptyBody: '服务器返回了空响应。',
  requestFailedWithCode: (code: number): string => `请求失败：${code}`,
  deviceOffline: '设备离线，请重新连接后再发送指令。',
  commandDispatchFailed: '指令下发失败，请检查设备连接和 MQTT 服务。',
  entityNotMatched: '当前设备与控制面板不匹配，请刷新后重试。'
}

export const AuthText = {
  slogan: '在一个地方控制你的全屋设备',
  signIn: '登录',
  signingIn: '登录中...',
  register: '注册',
  registering: '注册中...',
  username: '用户名',
  password: '密码',
  confirmPassword: '确认密码',
  passwordMin: '密码（至少 6 位）',
  noAccount: '还没有账号？',
  alreadyHaveAccount: '已有账号？',
  serverSettings: '服务器设置',
  hideServerSettings: '收起服务器设置'
}

export const DeviceText = {
  noRecentState: '暂无最新状态',
  awaitingFirstReport: '等待首次上报',
  justDiscovered: '刚刚发现',
  displayNamePlaceholder: '设备显示名称',
  bindToRoom: '绑定到房间',
  noCandidateDevices: '当前没有可绑定设备',
  scanHint: '可通过扫描刷新候选设备列表',
  lastSeen: (label: string): string => `最近在线：${label}`
}

export const RuleText = {
  title: '自动化规则',
  createTitle: '新建规则',
  ruleName: '规则名称',
  trigger: '触发条件',
  operator: '运算符',
  threshold: '阈值',
  targetDevice: '目标设备',
  action: '执行动作',
  exampleThreshold: '例如：28'
}
```

- [ ] **Step 3: Route `ApiClient.ets` through the new text layer without changing machine-code behavior**

Update imports and mappings:

```ts
import { NetworkText } from './UiText'

function extractTransportErrorMessage(err: Object): string {
  if (err instanceof Error && err.message) {
    return err.message
  }

  let raw = stringifyUnknownError(err)
  let lower = raw.toLowerCase()
  if (lower.indexOf('timeout') >= 0) {
    return NetworkText.timeout
  }
  if (lower.indexOf('refused') >= 0 || lower.indexOf('failed to connect') >= 0) {
    return NetworkText.refused
  }
  if (lower.indexOf('certificate') >= 0 || lower.indexOf('ssl') >= 0 || lower.indexOf('tls') >= 0) {
    return NetworkText.tlsFailed
  }
  if (raw) {
    return raw
  }
  return NetworkText.requestFailed
}

function mapApiErrorMessage(detail: string): string {
  switch (detail) {
    case 'device_offline':
      return NetworkText.deviceOffline
    case 'command_dispatch_failed':
      return NetworkText.commandDispatchFailed
    case 'entity_id_not_found':
      return NetworkText.entityNotMatched
    default:
      return detail
  }
}
```

Also replace:

```ts
throw new Error(NetworkText.emptyBody)
```

and:

```ts
let detailMessage = NetworkText.requestFailedWithCode(response.responseCode)
```

- [ ] **Step 4: Build the OpenHarmony app to catch import/type errors immediately**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9\openharmony"
.\hvigorw.bat --stop-daemon
.\hvigorw.bat assembleHap --stacktrace
```

Expected: HAP build succeeds; no new ArkTS errors from `UiText.ets` imports or formatter signatures.

- [ ] **Step 5: Commit only the text-layer changes**

Run:

```powershell
git add `
  "openharmony/entry/src/main/ets/common/UiText.ets" `
  "openharmony/entry/src/main/ets/common/ApiClient.ets"
git commit -m "feat: centralize Chinese UI text and API error copy"
```

### Task 2: Localize Authentication and Profile Flows

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/LoginPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RegisterPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/ProfilePage.ets`

- [ ] **Step 1: Replace login-page inline English copy with centralized text**

Update:

```ts
import { AuthText, CommonText } from '../common/UiText'

Text(CommonText.appName)
Text(AuthText.slogan)
Text(AuthText.signIn)
TextInput({ placeholder: AuthText.username, text: this.user })
TextInput({ placeholder: AuthText.password, text: this.pwd })
Text(this.showCfg ? AuthText.hideServerSettings : AuthText.serverSettings)
Button(this.loading ? AuthText.signingIn : AuthText.signIn)
Text(AuthText.noAccount)
Text(' ' + AuthText.register)
```

- [ ] **Step 2: Localize register-page labels, placeholders, and loading copy**

Update:

```ts
import { AuthText } from '../common/UiText'

Text('创建账号')
Text('加入你的智慧家居')
TextInput({ placeholder: AuthText.username, text: this.user })
TextInput({ placeholder: AuthText.passwordMin, text: this.pwd })
TextInput({ placeholder: AuthText.confirmPassword, text: this.pwd2 })
Button(this.loading ? AuthText.registering : AuthText.register)
Text(AuthText.alreadyHaveAccount)
Text(' ' + AuthText.signIn)
```

- [ ] **Step 3: Localize the profile center, password-change form, and account actions**

Update:

```ts
import { CommonText } from '../common/UiText'

Text('个人中心')
TextInput({ placeholder: '当前密码', text: this.old })
TextInput({ placeholder: '新密码', text: this.np })
TextInput({ placeholder: '确认新密码', text: this.np2 })
Button(this.changing ? '更新中...' : '确认修改密码')
Button('切换账号')
Button('退出登录')
Text('正在加载个人信息...')
```

- [ ] **Step 4: Rebuild after auth/profile migration**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9\openharmony"
.\hvigorw.bat assembleHap --stacktrace
```

Expected: build succeeds and there are no missing imports from `UiText.ets`.

- [ ] **Step 5: Commit the auth/profile localization**

Run:

```powershell
git add `
  "openharmony/entry/src/main/ets/pages/LoginPage.ets" `
  "openharmony/entry/src/main/ets/pages/RegisterPage.ets" `
  "openharmony/entry/src/main/ets/pages/ProfilePage.ets"
git commit -m "feat: localize auth and profile flows"
```

### Task 3: Localize the Main Operational Pages

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets`

- [ ] **Step 1: Replace dashboard hero, scene, activity, and room-empty-state copy**

Update representative strings:

```ts
Text('智慧家居控制中心')
Text('正在加载控制中心...')
this.successMessage = '场景执行成功'
this.errorMessage = (err as Error).message || '场景执行失败'
Text('快捷场景')
Text('自动化捷径')
Text('最近动态')
Text('最新设备操作')
Text('当前空间暂无设备')
Text('请先绑定设备或切换到其他房间')
Text('打开控制面板')
```

Also translate status-summary helpers:

```ts
return '离线 - ' + device.status_summary
return '亮度 ' + s.brightness + '%'
return '目标湿度 ' + s.target_humidity + '%'
return s.presence ? '检测到人体活动' : '区域空闲'
```

- [ ] **Step 2: Localize device-management status, empty states, bind flow, and remote-console labels**

Update representative strings:

```ts
import { CommonText, DeviceText } from '../common/UiText'

Text(device.online ? CommonText.online : CommonText.offline)
Text(DeviceHelper.summaryText(device.status_summary, DeviceText.noRecentState))
Text(DeviceHelper.seenText(device.last_seen_at, DeviceText.awaitingFirstReport))
Text(CommonText.edit)
Text(CommonText.delete)
Text('候选设备')
Text(DeviceText.bindToRoom)
Text(DeviceText.noCandidateDevices)
Text(DeviceText.scanHint)
TextInput({ placeholder: DeviceText.displayNamePlaceholder, text: this.bindName })
Button(this.binding && this.bindTargetId === candidate.id ? '绑定中...' : CommonText.bind)
```

Update remote page title/state copy:

```ts
case 'light': return '灯光控制台'
case 'ac': return '空调控制台'
case 'door_lock': return '门锁控制台'
case 'curtain': return '窗帘控制台'
case 'humidifier': return '加湿器控制台'

if (this.dt === 'light') return this.ltOn ? '灯光已开启' : '灯光已关闭'
if (this.dt === 'door_lock') return this.dlLk ? '门锁已上锁' : '门锁已解锁'
Text(CommonText.refresh)
this.dlMsg = '解锁成功'
this.dlMsg = '上锁成功'
this.dlMsg = '操作失败'
```

- [ ] **Step 3: Localize rules page labels, rule summaries, and slider captions**

Update representative strings:

```ts
import { CommonText, RuleText } from '../common/UiText'

Text('条件：' + this.cs(r))
Text('动作：' + this.as(r))
Text(CommonText.delete)
Text(RuleText.createTitle)
TextInput({ text: this.nm, placeholder: RuleText.ruleName })
Text(RuleText.trigger)
Text(RuleText.operator)
Text(RuleText.threshold)
TextInput({ text: this.vl, placeholder: RuleText.exampleThreshold })
Text(RuleText.targetDevice)
Text(RuleText.action)
Text('亮度')
Text('温度')
Text('目标湿度')
Button(CommonText.cancel)
Button(CommonText.create)
```

- [ ] **Step 4: Localize monitor-page labels, tabs, empty states, and loading copy**

Update representative strings:

```ts
Text('数据监测')
Text(CommonText.refresh)
Text('监测工作台')
Text('实时遥测、历史记录与日志')
this.tabChip('历史记录', this.tab === 1, () => { this.tab = 1; this.refresh() })
this.tabChip('运行日志', this.tab === 2, () => { this.tab = 2; this.refresh() })
this.buildEmptyState('暂无传感器设备', '请先绑定传感器设备后查看实时数据')
this.buildSectionLoading('正在刷新历史记录...')
this.buildEmptyState('暂无历史数据', '历史传感器记录会显示在这里')
this.buildSectionLoading('正在刷新日志...')
this.buildEmptyState('暂无操作日志', '设备与自动化日志会显示在这里')
Text('正在加载监测工作台...')
```

Also translate type/status helpers:

```ts
if (dataType === 'temperature') return '温度'
if (dataType === 'humidity') return '湿度'
return '人体活动'
return status.presence ? '检测到活动' : '空闲'
```

- [ ] **Step 5: Rebuild the app after main-page localization**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9\openharmony"
.\hvigorw.bat assembleHap --stacktrace
```

Expected: build succeeds with all five updated pages compiling.

- [ ] **Step 6: Commit the main operational page work**

Run:

```powershell
git add `
  "openharmony/entry/src/main/ets/pages/DashboardPage.ets" `
  "openharmony/entry/src/main/ets/pages/DeviceManagePage.ets" `
  "openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets" `
  "openharmony/entry/src/main/ets/pages/DataMonitorPage.ets" `
  "openharmony/entry/src/main/ets/pages/RulesPage.ets"
git commit -m "feat: localize control center and rules UI"
```

### Task 4: Localize Device-Specific Control Pages

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/ACControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/CurtainControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DoorLockPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/HumidifierControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/LightControlPage.ets`

- [ ] **Step 1: Translate the AC and humidifier control labels**

Update:

```ts
Text('空调控制')
Button(this.on ? '关闭' : '开启')
Text('模式')
Text('风速')

Text('加湿器控制')
Text('暂无加湿器设备')
Button(this.on ? '关闭' : '开启')
Text('雾量档位')
Text('目标湿度')
```

- [ ] **Step 2: Translate curtain and door-lock state/action copy**

Update:

```ts
Text('窗帘控制')
Text('暂无窗帘设备')
Text(this.cp === 0 ? '已关闭' : this.cp >= 100 ? '已全开' : '部分开启')
Button('关闭')
Button('打开')
Text('开合位置')

Text('门锁控制')
Text(this.locked ? '已上锁' : '已解锁')
Button(this.loading ? '处理中...' : (this.locked ? '解锁' : '上锁'))
this.sm('解锁成功')
this.sm('上锁成功')
Text('门锁操作受 AES-256 + JWT 保护。')
```

- [ ] **Step 3: Normalize the light-control page so terminology matches the new shared copy**

Update:

```ts
Text('照明控制')
Text('亮度')
Text('色温')
Button(this.on ? '关闭' : '开启')
```

- [ ] **Step 4: Rebuild after control-page cleanup**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9\openharmony"
.\hvigorw.bat assembleHap --stacktrace
```

Expected: all device-specific pages still compile and navigation targets remain intact.

- [ ] **Step 5: Commit the control-page localization**

Run:

```powershell
git add `
  "openharmony/entry/src/main/ets/pages/ACControlPage.ets" `
  "openharmony/entry/src/main/ets/pages/CurtainControlPage.ets" `
  "openharmony/entry/src/main/ets/pages/DoorLockPage.ets" `
  "openharmony/entry/src/main/ets/pages/HumidifierControlPage.ets" `
  "openharmony/entry/src/main/ets/pages/LightControlPage.ets"
git commit -m "feat: localize device-specific control pages"
```

### Task 5: Localize Backend User-Facing Responses and Update Assertions

**Files:**
- Modify: `cloud/backend/app/main.py`
- Modify: `cloud/backend/app/api/bind_device.py`
- Modify: `cloud/backend/app/api/rules.py`
- Modify: `cloud/backend/app/services/device_command.py`
- Modify: `cloud/backend/app/services/discovery_catalog.py`
- Test: `cloud/backend/tests/test_devices.py`
- Test: `cloud/backend/tests/test_rules.py`

- [ ] **Step 1: Update only the backend strings that are rendered to users**

Modify:

```python
app = FastAPI(
    title="智慧家居设备控制系统",
    description="OpenHarmony 智慧家居后端 API",
    version="1.0.0",
    lifespan=lifespan,
)
```

```python
return {
    "success": True,
    "entity_id": entity_id,
    "action": actual_action,
    "message": f"已下发“{actual_action}”指令",
    "changed_states": changed_states,
}
```

```python
return {
    "device_id": device["id"],
    "room_id": room["id"],
    "message": f"设备“{device['name']}”已绑定到“{room['name']}”",
}
```

```python
operators = [
    {"label": "等于", "value": "eq"},
    {"label": "不等于", "value": "neq"},
    {"label": "大于", "value": "gt"},
    {"label": "大于等于", "value": "gte"},
    {"label": "小于", "value": "lt"},
    {"label": "小于等于", "value": "lte"},
]
```

And localize the seeded candidate catalog:

```python
{
    "id": "candidate-livingroom-ambient-light",
    "room": "livingroom",
    "room_hint": "客厅",
    "type": "light",
    "name": "客厅氛围灯",
    "brand": "",
    "mqtt_topic": "home/livingroom/light_extra",
}
```

Also translate candidate status summaries:

```python
return "已开启" if status.get("power") == "on" else "已关闭"
return "待机"
return "已上锁" if status.get("locked", True) else "已解锁"
return f"开启 {int(status.get('position', 0))}%"
```

- [ ] **Step 2: Update tests that intentionally assert user-facing copy**

Modify:

```python
assert payload["message"] == "已下发“on”指令"
```

and:

```python
assert payload["operators"] == [
    {"label": "等于", "value": "eq"},
    {"label": "不等于", "value": "neq"},
    {"label": "大于", "value": "gt"},
    {"label": "大于等于", "value": "gte"},
    {"label": "小于", "value": "lt"},
    {"label": "小于等于", "value": "lte"},
]
```

Do not change assertions like:

```python
assert payload["message"] == "device_offline"
```

because that machine-code contract is intentionally out of scope.

- [ ] **Step 3: Run the focused backend tests for changed copy**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9"
python -m pytest `
  "cloud/backend/tests/test_devices.py" `
  "cloud/backend/tests/test_rules.py" `
  "cloud/backend/tests/test_rooms.py" `
  "cloud/backend/tests/test_scenes.py" -q
```

Expected: all targeted backend tests pass; failures should be limited to text-assertion mismatches if any string was missed.

- [ ] **Step 4: Commit the backend localization and test updates**

Run:

```powershell
git add `
  "cloud/backend/app/main.py" `
  "cloud/backend/app/api/bind_device.py" `
  "cloud/backend/app/api/rules.py" `
  "cloud/backend/app/services/device_command.py" `
  "cloud/backend/app/services/discovery_catalog.py" `
  "cloud/backend/tests/test_devices.py" `
  "cloud/backend/tests/test_rules.py"
git commit -m "feat: localize backend response copy"
```

### Task 6: Sweep for Remaining English UI Copy and Run Full Verification

**Files:**
- Verify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Verify: `openharmony/entry/src/main/ets/pages/*.ets`
- Verify: `cloud/backend/app/**/*.py`
- Verify: `tests/*.py`

- [ ] **Step 1: Search for obvious leftover English user-facing strings in the touched frontend/backend files**

Run:

```powershell
rg -n "Sign in|Register|Loading|Refresh|Offline|Online|Create Rule|Target Device|Action|Brightness|Temperature|Humidity|Profile Center|Control|Console|Living Room|Bedroom|Study|command dispatched|Smart Home Device Control System" `
  "D:\ruanjianbei\smart-home-A9\openharmony\entry\src\main\ets" `
  "D:\ruanjianbei\smart-home-A9\cloud\backend\app"
```

Expected: remaining matches should be limited to machine-readable values, comments, or intentionally preserved protocol strings. Any user-visible match should be fixed before final verification.

- [ ] **Step 2: Run repo-root regression tests that protect the current OpenHarmony/backend contract**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9"
python -m pytest tests -q
```

Expected: root regression suite passes, including `test_openharmony_control_regressions.py` and `test_ui_log_formatting_regression.py`.

- [ ] **Step 3: Run the backend test suite**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9\cloud\backend"
python -m pytest tests -q
```

Expected: backend suite passes with Chinese operator labels and response messages while machine-code assertions stay unchanged.

- [ ] **Step 4: Produce the final signed HAP and confirm the artifact path**

Run:

```powershell
Set-Location "D:\ruanjianbei\smart-home-A9\openharmony"
.\hvigorw.bat --stop-daemon
.\hvigorw.bat assembleHap --stacktrace
Get-Item "D:\ruanjianbei\smart-home-A9\openharmony\entry\build\default\outputs\default\entry-default-signed.hap" | Select-Object FullName, Length, LastWriteTime
```

Expected: `entry-default-signed.hap` exists at `openharmony/entry/build/default/outputs/default/entry-default-signed.hap`.

- [ ] **Step 5: Commit the verification-safe finishing sweep**

Run:

```powershell
git add `
  "openharmony/entry/src/main/ets/common/UiText.ets" `
  "openharmony/entry/src/main/ets/common/ApiClient.ets" `
  "openharmony/entry/src/main/ets/pages" `
  "cloud/backend/app" `
  "cloud/backend/tests"
git commit -m "chore: finish Chinese localization verification sweep"
```

## Self-Review

### Spec Coverage Check

- Frontend page copy: covered by Task 2, Task 3, and Task 4.
- `ApiClient.ets` network/API error mapping: covered by Task 1.
- Backend `message`, title, operator labels, candidate names/room hints: covered by Task 5.
- Machine-readable error codes unchanged: reinforced in Guardrails and Task 5 Step 2.
- Verification via pytest and HAP packaging: covered by Task 1 Step 4, Task 3 Step 5, Task 5 Step 3, and Task 6.

### Placeholder Scan

- No `TBD`, `TODO`, or “implement later” placeholders remain.
- Each code-editing step includes concrete code to add or replace.
- Each verification step includes explicit commands and expected outcomes.

### Type Consistency Check

- ArkTS text imports consistently come from `../common/UiText` in pages and `./UiText` in `ApiClient.ets`.
- Shared helper names are consistent: `CommonText`, `NetworkText`, `AuthText`, `DeviceText`, `RuleText`.
- Backend-visible copy changes keep existing response keys (`message`, `action`, `entity_id`, `operators`) unchanged.
