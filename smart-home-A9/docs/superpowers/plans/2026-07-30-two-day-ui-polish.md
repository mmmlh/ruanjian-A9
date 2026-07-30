# A9 Two-Day UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify all eight OpenHarmony pages around one compact visual system without changing routes, backend APIs, MQTT semantics, or realtime state behavior.

**Architecture:** Extend the existing `ControlCenterTheme` and `ControlCenterKit` as the shared UI boundary, add app-owned SVG navigation/action assets, and migrate pages in two groups. Source-level pytest contracts protect navigation semantics, forbidden copy, touch sizes, confirmation states, and icon usage before ArkTS changes are made.

**Tech Stack:** OpenHarmony API 20, ArkTS, ArkUI, SVG media resources, pytest, Hvigor

---

## File Map

- Create `tests/test_ui_polish_regression.py`: source contracts for the approved UI system.
- Modify `openharmony/entry/src/main/ets/common/ControlCenterTheme.ets`: compact semantic tokens.
- Modify `openharmony/entry/src/main/ets/common/ControlCenterKit.ets`: shared top bar, bottom navigation, empty state, and confirmation panel.
- Create `openharmony/entry/src/main/resources/base/media/nav_*.svg` and `action_*.svg`: bundled Lucide-style icons.
- Modify all files in `openharmony/entry/src/main/ets/pages/`: migrate the eight active pages.

### Task 1: Lock the UI contract with failing tests

**Files:**
- Create: `tests/test_ui_polish_regression.py`

- [ ] **Step 1: Write the complete source contract**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "openharmony/entry/src/main/ets/pages"
COMMON = ROOT / "openharmony/entry/src/main/ets/common"
MEDIA = ROOT / "openharmony/entry/src/main/resources/base/media"


def source(name: str) -> str:
    return (PAGES / name).read_text(encoding="utf-8")


def test_compact_semantic_theme_and_shared_components_exist():
    theme = (COMMON / "ControlCenterTheme.ets").read_text(encoding="utf-8")
    kit = (COMMON / "ControlCenterKit.ets").read_text(encoding="utf-8")
    assert "static readonly pageBg: string = '#F4F6F5'" in theme
    assert "static readonly accent: string = '#14875B'" in theme
    assert "static readonly radiusCard: number = 8" in theme
    assert "export struct AppTopBar" in kit
    assert "export struct EmptyState" in kit
    assert "export struct ConfirmPanel" in kit


def test_navigation_and_action_svg_assets_are_bundled():
    names = [
        "nav_home.svg", "nav_devices.svg", "nav_automation.svg", "nav_profile.svg",
        "action_back.svg", "action_add.svg", "action_refresh.svg",
    ]
    for name in names:
        text = (MEDIA / name).read_text(encoding="utf-8")
        assert text.startswith("<svg")


def test_root_pages_use_root_navigation_without_back_controls():
    expected = {
        "DashboardPage.ets": "home",
        "DeviceManagePage.ets": "devices",
        "RulesPage.ets": "automation",
        "ProfilePage.ets": "profile",
    }
    for name, active in expected.items():
        text = source(name)
        assert f"AppBottomNav({{ active: '{active}' }})" in text
        assert f"AppTopBar({{ title:" in text
        assert "showBack: true" not in text


def test_destructive_flows_have_explicit_confirmation_state():
    assert "@State pendingDeleteId: number = -1" in source("DeviceManagePage.ets")
    assert "@State pendingDeleteId: number = -1" in source("RulesPage.ets")
    assert "@State confirmLogout: boolean = false" in source("ProfilePage.ets")
    assert "ConfirmPanel" in source("DeviceManagePage.ets")
    assert "ConfirmPanel" in source("RulesPage.ets")
    assert "ConfirmPanel" in source("ProfilePage.ets")


def test_user_facing_pages_do_not_contain_development_copy_or_emoji_escapes():
    forbidden = ["便于答辩", "更像完整产品", "长 JSON", "\\uD83", "\\uD83E"]
    for path in PAGES.glob("*.ets"):
        text = path.read_text(encoding="utf-8")
        for item in forbidden:
            assert item not in text, f"{path.name} still contains {item}"


def test_device_add_flow_is_secondary_and_touch_targets_are_accessible():
    text = source("DeviceManagePage.ets")
    assert "@State showAddFlow: boolean = false" in text
    assert "if (this.showAddFlow)" in text
    assert "height(ControlCenterTheme.tapTarget)" in text
```

- [ ] **Step 2: Run the new test and verify RED**

Run: `python -m pytest tests/test_ui_polish_regression.py -q`

Expected: failures for missing compact tokens, shared components, SVG assets, confirmation state, and secondary add flow.

- [ ] **Step 3: Commit the failing contract**

```powershell
git add tests/test_ui_polish_regression.py
git commit -m "test: define two-day UI polish contract"
```

### Task 2: Implement the shared visual system

**Files:**
- Modify: `openharmony/entry/src/main/ets/common/ControlCenterTheme.ets`
- Modify: `openharmony/entry/src/main/ets/common/ControlCenterKit.ets`
- Create: `openharmony/entry/src/main/resources/base/media/nav_home.svg`
- Create: `openharmony/entry/src/main/resources/base/media/nav_devices.svg`
- Create: `openharmony/entry/src/main/resources/base/media/nav_automation.svg`
- Create: `openharmony/entry/src/main/resources/base/media/nav_profile.svg`
- Create: `openharmony/entry/src/main/resources/base/media/action_back.svg`
- Create: `openharmony/entry/src/main/resources/base/media/action_add.svg`
- Create: `openharmony/entry/src/main/resources/base/media/action_refresh.svg`

- [ ] **Step 1: Replace theme values with the approved token set**

```typescript
static readonly pageBg: string = '#F4F6F5'
static readonly surfaceMuted: string = '#EEF2F0'
static readonly accent: string = '#14875B'
static readonly accentSoft: string = '#E4F3EC'
static readonly warning: string = '#A96917'
static readonly warningSoft: string = '#FFF0D5'
static readonly danger: string = '#B34F4F'
static readonly dangerSoft: string = '#F9E7E7'
static readonly textPrimary: string = '#19211D'
static readonly textSecondary: string = '#66716B'
static readonly textTertiary: string = '#89938E'
static readonly radiusHero: number = 12
static readonly radiusCard: number = 8
static readonly radiusInner: number = 8
static readonly radiusChip: number = 8
```

- [ ] **Step 2: Add `AppTopBar`, `EmptyState`, and `ConfirmPanel`**

```typescript
@Component
export struct AppTopBar {
  @Prop title: string = ''
  @Prop subtitle: string = ''
  @Prop showBack: boolean = false
  @Prop actionLabel: string = ''
  @Prop onAction: () => void = () => {}

  build() {
    Row() {
      if (this.showBack) {
        Image($r('app.media.action_back'))
          .width(20).height(20)
          .padding(12)
          .onClick(() => this.getUIContext().getRouter().back())
      }
      Column() {
        Text(this.title).fontSize(22).fontWeight(FontWeight.Bold)
        if (this.subtitle) {
          Text(this.subtitle).fontSize(12).margin({ top: 4 })
        }
      }.layoutWeight(1).alignItems(HorizontalAlign.Start)
      if (this.actionLabel) {
        Button(this.actionLabel)
          .height(ControlCenterTheme.tapTarget)
          .borderRadius(ControlCenterTheme.radiusInner)
          .onClick(this.onAction)
      }
    }.width('100%').alignItems(VerticalAlign.Center)
  }
}
```

Add the following component contracts:

```typescript
@Component
export struct EmptyState {
  @Prop title: string = ''
  @Prop detail: string = ''

  build() {
    Column() {
      Text(this.title).fontSize(16).fontWeight(FontWeight.Bold)
      Text(this.detail).fontSize(12).margin({ top: 6 })
    }
    .width('100%')
    .padding({ top: 24, bottom: 24 })
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(ControlCenterTheme.surface)
  }
}

@Component
export struct ConfirmPanel {
  @Prop title: string = ''
  @Prop detail: string = ''
  @Prop confirmLabel: string = '确认'
  @Prop danger: boolean = true
  @Prop onCancel: () => void = () => {}
  @Prop onConfirm: () => void = () => {}

  build() {
    Column() {
      Text(this.title).fontSize(16).fontWeight(FontWeight.Bold)
      Text(this.detail).fontSize(12).margin({ top: 6 })
      Row() {
        Button('取消').height(ControlCenterTheme.tapTarget).onClick(this.onCancel)
        Button(this.confirmLabel).height(ControlCenterTheme.tapTarget).onClick(this.onConfirm)
      }.width('100%').margin({ top: 12 })
    }
    .width('100%')
    .padding(16)
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(this.danger ? ControlCenterTheme.dangerSoft : ControlCenterTheme.warningSoft)
  }
}
```

- [ ] **Step 3: Replace bottom navigation glyphs with SVG media images**

Use `Image($r('app.media.nav_home'))`, `nav_devices`, `nav_automation`, and `nav_profile`; keep the existing `replaceUrl` route map and active text state.

- [ ] **Step 4: Add the seven SVG resources**

Each file uses a `24 24` view box, `fill="none"`, `stroke="#14875B"`, `stroke-width="1.8"`, and rounded caps. Use these exact path bodies:

| File | SVG body |
| --- | --- |
| `nav_home.svg` | `<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v10h13V10"/><path d="M9.5 20v-6h5v6"/>` |
| `nav_devices.svg` | `<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6M10 17h4"/>` |
| `nav_automation.svg` | `<rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M9 6h4a4 4 0 0 1 4 4v5M15 18h-4a4 4 0 0 1-4-4V9"/>` |
| `nav_profile.svg` | `<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>` |
| `action_back.svg` | `<path d="m15 18-6-6 6-6"/>` |
| `action_add.svg` | `<path d="M12 5v14M5 12h14"/>` |
| `action_refresh.svg` | `<path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M6.1 8a7 7 0 0 1 11.5-1L20 12M4 12l2.4 5a7 7 0 0 0 11.5-1"/>` |

- [ ] **Step 5: Run the focused shared-system tests**

Run: `python -m pytest tests/test_ui_polish_regression.py tests/test_ui_theme_regression.py tests/test_mobile_layout_regression.py -q`

Expected: asset and shared-component assertions pass; page migration assertions may still fail.

### Task 3: Migrate authentication, home, and device management

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/LoginPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RegisterPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`

- [ ] **Step 1: Align authentication pages**

Keep both pages scrollable. Add visible `Text('用户名')`, `Text('密码')`, and registration confirmation labels at 12sp, replace local 50/52vp values with `ControlCenterTheme.controlHeight`, and keep one green primary action.

- [ ] **Step 2: Replace the dashboard header and pictograms**

```typescript
AppTopBar({
  title: '我的家',
  subtitle: this.syncStatusLabel(),
  actionLabel: '刷新',
  onAction: () => this.rf()
})
```

Replace device and scene Emoji return values with stable Chinese category marks (`灯`, `空`, `锁`, `温`, `湿`, `人`, `帘`, `雾`, `景`). Remove unused legacy hero and bottom-navigation Builders after confirming there are no call sites.

- [ ] **Step 3: Make discovery a secondary device flow**

Add:

```typescript
@State showAddFlow: boolean = false
@State pendingDeleteId: number = -1
```

Remove automatic `scanCandidates(false)` from `ld()`. The top bar action sets `showAddFlow = true` and calls `scanCandidates(false)`. Render the candidate section only inside `if (this.showAddFlow)`. The delete action sets `pendingDeleteId`; `ConfirmPanel` calls `doDel(this.pendingDeleteId)` only after confirmation.

- [ ] **Step 4: Run the page contracts**

Run: `python -m pytest tests/test_ui_polish_regression.py tests/test_mobile_layout_regression.py tests/test_ui_theme_regression.py -q`

Expected: authentication, dashboard, and device assertions pass.

### Task 4: Migrate control, automation, monitoring, and profile

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/ProfilePage.ets`

- [ ] **Step 1: Apply task-page top bars**

Use `AppTopBar({ title: this.tn(), showBack: true, actionLabel: '刷新', onAction: () => this.load() })` on device control and `AppTopBar({ title: '数据监测', showBack: true, actionLabel: '刷新', onAction: () => this.refresh() })` on monitoring.

- [ ] **Step 2: Remove control-page Emoji escapes without changing commands**

Return stable category marks from `heroIcon()` and sensor icon helpers. Leave `cmd`, `cmdCurrent`, `queueSliderCommand`, device-type panels, and offline command behavior unchanged.

- [ ] **Step 3: Make automation a clean root page with deletion confirmation**

Add `@State pendingDeleteId: number = -1`, use one `AppTopBar` action to open the existing rule dialog, remove the hero plus control, remove development copy, and change the delete tap handler to set `pendingDeleteId`. Confirming calls `dD(pendingDeleteId)`.

- [ ] **Step 4: Simplify profile and confirm logout**

Add `@State confirmLogout: boolean = false`, replace the custom back top bar with `AppTopBar({ title: '我的' })`, remove the duplicate account-switch button, and make the remaining logout action show `ConfirmPanel` before calling `doOut()`.

- [ ] **Step 5: Run all UI source regressions**

Run: `python -m pytest tests -q`

Expected: all root source regressions pass.

### Task 5: Build and verify the deliverable

**Files:**
- Verify: `openharmony/entry/build/default/outputs/default/entry-default-signed.hap`

- [ ] **Step 1: Run backend regression tests**

Run: `python -m pytest cloud/backend/tests -q`

Expected: all backend tests pass because the implementation does not change APIs or models.

- [ ] **Step 2: Build the HAP**

Run: `openharmony\hvigorw.bat --stop-daemon` from `openharmony`, then `openharmony\hvigorw.bat assembleHap --stacktrace`.

Expected: build succeeds and produces the signed HAP.

- [ ] **Step 3: Inspect the final diff**

Run: `git diff --check` and `git diff --stat`.

Expected: no whitespace errors; changes are limited to the design/plan, UI tests, common UI files, media assets, and eight pages.

- [ ] **Step 4: Commit the implementation**

```powershell
git add tests openharmony docs/superpowers/plans/2026-07-30-two-day-ui-polish.md
git commit -m "feat: unify OpenHarmony UI visual system"
```
