# OpenHarmony API 20 Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Downgrade `D:/ruanjianbei/smart-home-A9/openharmony` to `API 20` compatibility while preserving the main app and as much widget/form functionality as `API 20` allows.

**Architecture:** First restore a valid SDK resolution path and lower the project configuration to `API 20`, because no code-level signal is trustworthy until the build can see a real SDK. Next convert shared imports and core abilities away from higher-version assumptions, then rewrite page navigation and widget/form code to use APIs actually supported by the local `API 20` SDK. Verify each batch with focused searches and `hvigor` builds so environment failures, symbol failures, and page-level failures stay separated.

**Tech Stack:** OpenHarmony ArkTS, hvigor, DevEco SDK/toolchains, JSON5 config, widget/form abilities

---

### Task 1: Reproduce The Baseline Failure And Find The Real API 20 SDK Path

**Files:**
- Modify: `openharmony/local.properties`
- Test: `openharmony/hvigorw.bat`

- [ ] **Step 1: Add a failing-build evidence note by rerunning the baseline build**

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
if (Test-Path 'D:/d s/DevEco Studio/jbr/bin/java.exe') {
  $env:JAVA_HOME='D:/d s/DevEco Studio/jbr'
  $env:PATH='D:/d s/DevEco Studio/jbr/bin;' + $env:PATH
}
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected:

- build fails before ArkTS compilation
- error mentions unresolved `sdk.dir` or `OHOS_BASE_SDK_HOME`

- [ ] **Step 2: Locate the actual installed API 20 SDK on disk**

```powershell
Get-ChildItem 'C:\Users\21302\AppData\Local' -Directory |
  Where-Object { $_.Name -match 'Huawei|Harmony|OpenHarmony|ohos' } |
  Select-Object Name, FullName

Get-ChildItem 'C:\Users\21302\AppData\Local\Huawei\Sdk' -ErrorAction SilentlyContinue |
  Select-Object Name, FullName

Get-ChildItem 'C:\Users\21302\AppData\Local\Huawei\Sdk\20' -ErrorAction SilentlyContinue |
  Select-Object Name, FullName
```

Expected:

- one concrete SDK root exists on disk
- that root contains `20\ets`, `20\js`, `20\toolchains`, or equivalent API 20 components

- [ ] **Step 3: Rewrite `local.properties` to the real SDK root**

```properties
# openharmony/local.properties
sdk.dir=C:/Users/21302/AppData/Local/Huawei/Sdk
```

If the actual directory differs, use that exact path and keep forward slashes.

- [ ] **Step 4: Verify the build gets past SDK resolution**

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected:

- no `sdk.dir` configuration error
- next failure, if any, is now a real config or ArkTS compatibility error

### Task 2: Lower Project Configuration From API 22 To API 20

**Files:**
- Modify: `openharmony/build-profile.json5`
- Modify: `openharmony/entry/src/main/module.json5`
- Modify: `openharmony/.sdk-proxy/` contents or references if necessary

- [ ] **Step 1: Write the API 20 configuration lines into the project build profile**

```json5
// openharmony/build-profile.json5
{
  "app": {
    "products": [
      {
        "name": "default",
        "compileSdkVersion": 20,
        "targetSdkVersion": 20,
        "compatibleSdkVersion": 20,
        "runtimeOS": "OpenHarmony"
      }
    ]
  }
}
```

- [ ] **Step 2: Keep module metadata compatible with the downgraded target**

```json5
// openharmony/entry/src/main/module.json5
{
  "module": {
    "name": "entry",
    "type": "entry",
    "deviceTypes": ["default"],
    "pages": "$profile:main_pages",
    "abilities": [
      {
        "name": "EntryAbility",
        "srcEntry": "./ets/entryability/EntryAbility.ets",
        "exported": true
      }
    ]
  }
}
```

Keep the existing ability and form metadata unless the API 20 build explicitly rejects a field.

- [ ] **Step 3: Align or remove stale API 22 proxy assumptions**

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
if (Test-Path '.sdk-proxy\22') { Rename-Item '.sdk-proxy\22' '20' -ErrorAction SilentlyContinue }
Get-ChildItem '.sdk-proxy' -Recurse -File | Select-String '22'
```

Expected:

- either the proxy is aligned to `20`
- or all live project config stops depending on `22`

- [ ] **Step 4: Rebuild to expose the next real incompatibility**

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
./hvigorw.bat assembleHap --stacktrace
```

Expected:

- no remaining `compileSdkVersion/targetSdkVersion/compatibleSdkVersion` references to `22`
- next failures point at imports, symbols, or ArkTS syntax

### Task 3: Replace Higher-Version Shared Imports And Ability APIs

**Files:**
- Modify: `openharmony/entry/src/main/ets/entryability/EntryAbility.ets`
- Modify: `openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets`
- Modify: `openharmony/entry/src/main/ets/common/ApiClient.ets`
- Modify: `openharmony/entry/src/main/ets/common/MqttClient.ets`
- Modify: `openharmony/entry/src/main/ets/common/CryptoUtil.ets`
- Modify: `openharmony/entry/src/main/ets/common/TokenUtil.ets`
- Modify: `openharmony/entry/src/main/ets/common/SecureStorage.ets`

- [ ] **Step 1: Convert `@kit.*` imports in the core files to API 20-compatible module imports**

```ts
// EntryAbility.ets
import UIAbility from '@ohos:app.ability.UIAbility';
import type Want from '@ohos:app.ability.Want';
import type AbilityConstant from '@ohos:app.ability.AbilityConstant';
import hilog from '@ohos:hilog';
import type window from '@ohos:window';

// ApiClient.ets
import http from '@ohos:net.http';

// MqttClient.ets
import webSocket from '@ohos:net.webSocket';
import type { BusinessError } from '@ohos:base';
```

Apply the same symbol-by-symbol replacement pattern to the other common files.

- [ ] **Step 2: Preserve `EntryAbility` behavior while using older import syntax**

```ts
export default class EntryAbility extends UIAbility {
  onWindowStageCreate(windowStage: window.WindowStage): void {
    windowStage.loadContent('pages/LoginPage', (err) => {
      if (err.code) {
        hilog.error(0x0000, 'SmartHome', 'Failed to load content: %{public}s', JSON.stringify(err));
        return;
      }
    });
  }
}
```

- [ ] **Step 3: Preserve `EntryFormAbility` structure while migrating its imports**

```ts
import FormExtensionAbility from '@ohos:app.form.FormExtensionAbility';
import formBindingData from '@ohos:app.form.formBindingData';
import formProvider from '@ohos:app.form.formProvider';
import formInfo from '@ohos:app.form.formInfo';
import type Want from '@ohos:app.ability.Want';
import hilog from '@ohos:hilog';
import http from '@ohos:net.http';
```

Keep the update loop and data hydration logic unless the API 20 build rejects a specific symbol.

- [ ] **Step 4: Run a focused search to confirm all `@kit.*` imports are gone from the main app**

```powershell
rg -n '@kit\.' D:\ruanjianbei\smart-home-A9\openharmony\entry\src\main\ets
```

Expected:

- no remaining `@kit.*` imports in the app source tree

- [ ] **Step 5: Rebuild to expose the page-layer compatibility failures**

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
./hvigorw.bat assembleHap --stacktrace
```

Expected:

- core import errors are reduced or removed
- remaining failures point at page navigation, widget syntax, or other page-level symbols

### Task 4: Standardize Page Navigation And Unsupported UI Calls For API 20

**Files:**
- Modify: `openharmony/entry/src/main/ets/pages/LoginPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RegisterPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/ProfilePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceManagePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/RulesPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/ACControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/LightControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/DoorLockPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/CurtainControlPage.ets`
- Modify: `openharmony/entry/src/main/ets/pages/HumidifierControlPage.ets`

- [ ] **Step 1: Replace `this.getUIContext().getRouter()` usage with one API 20-compatible routing pattern**

```ts
import router from '@ohos:router';

router.pushUrl({ url: 'pages/RegisterPage' });
router.replaceUrl({ url: 'pages/DashboardPage' });
router.back();
let params = router.getParams() as Record<string, Object>;
```

Use this one pattern consistently across the full page set if the API 20 SDK confirms it.

- [ ] **Step 2: Remove or rewrite unsupported UI property chains one class at a time**

```ts
// If `.enabled(...)` is rejected on a specific component:
Button(label)
  .opacity(disabled ? 0.4 : 1)
  .onClick(() => {
    if (disabled) {
      return;
    }
    this.handleAction();
  });
```

Use behavior-preserving fallbacks like guarded `onClick`, visual disabled state, or simpler modifiers where the API 20 build rejects newer chains.

- [ ] **Step 3: Keep route contracts stable while migrating parameter access**

```ts
router.pushUrl({
  url: 'pages/DeviceRemotePage',
  params: { 'deviceType': device.type, 'deviceId': device.id }
});

let params = router.getParams() as Record<string, Object>;
this.deviceId = Number(params['deviceId'] || 0);
```

- [ ] **Step 4: Rebuild after the main page set is migrated**

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
./hvigorw.bat assembleHap --stacktrace
```

Expected:

- navigation-related compile failures are eliminated
- remaining failures are isolated to widget/form or residual page symbols

### Task 5: Remediate Widget/Form Compatibility And Finish Verification

**Files:**
- Modify: `openharmony/entry/src/main/ets/widget/pages/WidgetCard.ets`
- Modify: `openharmony/entry/src/main/resources/base/profile/form_config.json`
- Modify: `openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets`
- Modify: `openharmony/entry/src/main/module.json5` if form metadata needs downgrading

- [ ] **Step 1: Keep the widget buildable with the simplest API 20-compatible state model**

```ts
@Entry(new LocalStorage())
@Component
struct WidgetCard {
  @LocalStorageProp('temperature') temperature: string = '--';
  @LocalStorageProp('humidity') humidity: string = '--';

  build() {
    Column() {
      Text('Smart Home');
      Text(`${this.temperature}°C`);
      Text(`${this.humidity}%`);
    }
  }
}
```

If interactive card actions fail under API 20, preserve read-only rendering first and reintroduce the action path only if the build supports it.

- [ ] **Step 2: Keep form metadata minimal if API 20 rejects richer settings**

```json
{
  "forms": [
    {
      "name": "widget",
      "src": "./ets/widget/pages/WidgetCard.ets",
      "uiSyntax": "arkts",
      "isDefault": true,
      "defaultDimension": "2*2",
      "supportDimensions": ["2*2", "2*4"]
    }
  ]
}
```

Retain only the fields accepted by the actual API 20 build if any current metadata is rejected.

- [ ] **Step 3: Run the final full build**

```powershell
cd D:\ruanjianbei\smart-home-A9\openharmony
./hvigorw.bat --stop-daemon
./hvigorw.bat assembleHap --stacktrace
```

Expected:

- build succeeds for the `entry` module
- no `API 22` config remains
- no unsupported `@kit.*` imports remain
- widget/form code is either preserved or downgraded in a buildable way

- [ ] **Step 4: Run the final regression searches**

```powershell
rg -n 'compileSdkVersion|targetSdkVersion|compatibleSdkVersion' D:\ruanjianbei\smart-home-A9\openharmony
rg -n '@kit\.' D:\ruanjianbei\smart-home-A9\openharmony\entry\src\main\ets
```

Expected:

- only `20` remains in live config
- no `@kit.*` imports remain in live source

- [ ] **Step 5: Commit the verified remediation**

```bash
git add openharmony/build-profile.json5 openharmony/local.properties openharmony/entry/src/main/module.json5 openharmony/entry/src/main/ets openharmony/entry/src/main/resources/base/profile
git commit -m "fix: downgrade OpenHarmony client to API 20 compatibility"
```
