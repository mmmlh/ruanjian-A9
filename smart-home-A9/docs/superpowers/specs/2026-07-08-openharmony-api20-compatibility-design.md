# OpenHarmony API 20 Compatibility Remediation Design

## 1. Background

The active OpenHarmony client project is `D:/ruanjianbei/smart-home-A9/openharmony`.
The current codebase was previously aligned to `API 22`, but the local DevEco Studio environment available for this project is constrained to `API 20` and lower.
As a result, the project must be remediated so that the entire OpenHarmony application is compatible with `API 20`, while preserving as much existing functionality as possible.

The current incompatibility is not limited to version numbers in build files. The project also contains:

- newer SDK configuration assumptions such as `compileSdkVersion`, `targetSdkVersion`, and `compatibleSdkVersion` set to `22`
- newer import style usage through `@kit.*`
- page-level navigation patterns centered on `this.getUIContext().getRouter()`
- form and widget capability code through `EntryFormAbility`, `form_config.json`, and `WidgetCard.ets`
- local SDK proxy content tied to `22`

This means the work is a full compatibility remediation, not a one-line configuration downgrade.

## 2. Goal

Bring the entire OpenHarmony project down to `API 20` compatibility and below, while keeping the current main-app feature set and preserving widget/form functionality whenever `API 20` provides a workable equivalent.

Success means:

- the project configuration targets `API 20`
- the ArkTS code compiles against `API 20` SDK symbols and syntax
- the main application flow still works
- widget/form capability is retained if API 20 supports it, otherwise downgraded in a controlled way
- compatibility problems are removed systematically rather than hidden behind partial patches

## 3. Scope

Included:

- project and module build configuration under `openharmony/`
- ArkTS imports and SDK symbol usage in `entry/src/main/ets/`
- navigation, storage, networking, and page interaction code
- `EntryAbility`
- `EntryFormAbility`
- widget source under `entry/src/main/ets/widget/`
- profile resources such as `main_pages.json` and `form_config.json`
- build and SDK path verification needed to produce a working `API 20` build

Not included:

- backend feature redesign in `cloud/`
- non-OpenHarmony repo cleanup outside what is required for the compatibility pass
- UI redesign unrelated to compatibility

## 4. Current Findings

### 4.1 Configuration layer

The project is currently configured around `API 22` in [build-profile.json5](D:/ruanjianbei/smart-home-A9/openharmony/build-profile.json5).
The repo also contains `.sdk-proxy/22/`, which reinforces the `API 22` toolchain assumption.

### 4.2 SDK path layer

The current [local.properties](D:/ruanjianbei/smart-home-A9/openharmony/local.properties) points `sdk.dir` at:

`C:/Users/21302/AppData/Local/OpenHarmony/Sdk`

In the current shell environment, that path does not exist, and `hvigorw.bat assembleHap --stacktrace` fails before compilation with a configuration error stating that `sdk.dir` or `OHOS_BASE_SDK_HOME` cannot be resolved.

This is a separate blocker from code compatibility and must be corrected as part of the remediation path.

### 4.3 ArkTS and SDK usage layer

The app uses newer `@kit.*` imports in multiple files, including:

- [EntryAbility.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/entryability/EntryAbility.ets)
- [EntryFormAbility.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets)
- [ApiClient.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/ApiClient.ets)
- [MqttClient.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/MqttClient.ets)
- [CryptoUtil.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/CryptoUtil.ets)

The page layer also relies broadly on `this.getUIContext().getRouter()` instead of older routing access patterns.

### 4.4 Feature-risk layer

The highest-risk features for `API 20` compatibility are:

- `EntryFormAbility`
- `WidgetCard.ets`
- widget-related `LocalStorage` and card action behavior
- any SDK symbols only available through newer `@kit.*` aggregation packages

The main application pages are still expected to be preservable, but may require broad symbol and routing rewrites.

## 5. Design Principles

### 5.1 Main app must remain usable

The login flow, dashboard, device control, rules, monitoring, and profile flows remain first-class requirements.
Compatibility work must not “solve” the build by stripping core application behavior.

### 5.2 Preserve features where API 20 has an equivalent

If `API 20` supports an older equivalent API for a newer construct, we replace it rather than remove the feature.

### 5.3 Prefer compatibility rewrites over abstraction-heavy refactors

This codebase already embeds SDK usage directly in pages and common utilities.
A large compatibility wrapper layer would increase risk and slow delivery.
The preferred approach is targeted direct replacement with minimal structural churn.

### 5.4 Degrade high-risk capability only when necessary

If widget/form functionality cannot be kept exactly as-is under `API 20`, it should be downgraded deliberately and locally, not removed casually.

### 5.5 Separate environment fixes from code fixes

The SDK path problem and the code/API problem must be tracked separately.
Otherwise build failures will hide whether compatibility work is actually succeeding.

## 6. Recommended Approach

Recommended approach: perform a full in-place downgrade to `API 20`, preserving all practical functionality and only degrading where `API 20` lacks a viable equivalent.

This approach is chosen because:

- the user explicitly wants the whole `openharmony` project to be compatible with `API 20`
- the user wants to keep as much functionality as possible
- the code already has a broad feature footprint that would be expensive to split into separate migration tracks

## 7. Target Architecture After Remediation

### 7.1 Configuration target

The OpenHarmony project should compile and package with:

- `compileSdkVersion = 20`
- `targetSdkVersion = 20`
- `compatibleSdkVersion = 20`

Any project-local SDK proxy should point to `20`, or be removed if it is safer to rely on the actual installed SDK path.

### 7.2 Import target

All `@kit.*` imports should be audited and converted to `API 20`-compatible imports and symbol references supported by the actual local SDK.

This likely means moving from newer aggregation imports toward older module-specific imports where required.

### 7.3 Navigation target

All page navigation should use a routing pattern verified to exist in `API 20`.

This includes:

- page entry
- forward navigation
- replace navigation
- back navigation
- route parameter passing

The replacement must be applied consistently across the page set so navigation behavior remains predictable.

### 7.4 Storage and network target

Utility modules such as secure storage, HTTP client, WebSocket client, token handling, and crypto helpers should be kept, but rewritten only as needed to use `API 20`-available symbols and initialization flows.

### 7.5 Widget/form target

The desired end state is:

- `EntryFormAbility` still exists
- widget data refresh still works
- `WidgetCard.ets` still renders

If `API 20` cannot support the current exact implementation, the fallback target is:

- keep `EntryFormAbility` and widget registration structure
- simplify widget interactions or state propagation
- preserve read-only status visibility before interactive polish

## 8. Component-Level Plan

### 8.1 Build configuration remediation

Files:

- [build-profile.json5](D:/ruanjianbei/smart-home-A9/openharmony/build-profile.json5)
- [module.json5](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/module.json5)
- [local.properties](D:/ruanjianbei/smart-home-A9/openharmony/local.properties)
- SDK proxy references under `openharmony/.sdk-proxy/`

Changes:

- lower SDK version fields from `22` to `20`
- align any proxy/toolchain assumptions to `20`
- correct SDK lookup so `hvigor` can actually see a valid installed SDK

### 8.2 Core ability remediation

Files:

- [EntryAbility.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/entryability/EntryAbility.ets)
- [EntryFormAbility.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/entryformability/EntryFormAbility.ets)

Changes:

- replace `@kit.*` imports with API 20-compatible imports
- verify `UIAbility`, `Want`, `WindowStage`, form classes, and related callbacks against API 20
- preserve lifecycle behavior while rewriting unsupported symbols

### 8.3 Common utility remediation

Files:

- [ApiClient.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/ApiClient.ets)
- [MqttClient.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/MqttClient.ets)
- [CryptoUtil.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/CryptoUtil.ets)
- [TokenUtil.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/TokenUtil.ets)
- [SecureStorage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/common/SecureStorage.ets)

Changes:

- replace unsupported imports and symbol names
- keep behavioral contracts stable so page code changes stay focused on compatibility
- preserve request, auth, realtime, and storage responsibilities

### 8.4 Page-layer remediation

Files include at minimum:

- [LoginPage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/LoginPage.ets)
- [DashboardPage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DashboardPage.ets)
- [RegisterPage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/RegisterPage.ets)
- [RulesPage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/RulesPage.ets)
- [ProfilePage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/ProfilePage.ets)
- [DeviceManagePage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DeviceManagePage.ets)
- [DeviceRemotePage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets)
- [DataMonitorPage.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/pages/DataMonitorPage.ets)
- specialized control pages such as AC, curtain, door lock, humidifier, and light control pages

Changes:

- replace unsupported router access pattern if necessary
- rewrite unsupported component property calls or syntax
- preserve route structure from `main_pages.json`
- keep existing feature flows intact

### 8.5 Widget and profile remediation

Files:

- [WidgetCard.ets](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/ets/widget/pages/WidgetCard.ets)
- [form_config.json](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/resources/base/profile/form_config.json)
- [main_pages.json](D:/ruanjianbei/smart-home-A9/openharmony/entry/src/main/resources/base/profile/main_pages.json)

Changes:

- validate that form metadata remains acceptable for API 20
- replace unsupported widget state or card action APIs if required
- preserve widget registration and display path if supported

## 9. Testing Strategy

### 9.1 Root-cause-first verification

Compatibility work will be done in batches and verified after each batch so we can distinguish:

- SDK path failures
- build configuration failures
- unsupported import or symbol failures
- page-level syntax or type failures
- widget/form-specific failures

### 9.2 Build verification

The main acceptance command remains:

- `./hvigorw.bat assembleHap --stacktrace`

But before this can prove code compatibility, the SDK resolution issue must be fixed so the command can actually compile instead of failing at environment validation.

### 9.3 Functional verification

Manual verification focus:

- app launches into login page
- login to dashboard navigation works
- dashboard entry points still navigate correctly
- device remote pages still accept and use route params
- rules, profile, and data monitor pages still open
- widget/form ability still builds, or clearly falls back to the downgraded compatible version

## 10. Risks

### Risk 1: SDK path mismatch blocks all signal

If the local SDK path remains unresolved, every build attempt will fail before proving whether the code is compatible.

Mitigation:

- correct `sdk.dir` or `OHOS_BASE_SDK_HOME` first
- re-run build immediately after path correction before broad code edits

### Risk 2: `@kit.*` imports have no one-to-one API 20 replacement

Some newer aggregation imports may map to older module names or slightly different types.

Mitigation:

- audit symbol-by-symbol against the actual API 20 SDK
- migrate common utilities first so later page fixes are smaller

### Risk 3: widget/form behavior may be partially unsupported

Interactive widget refresh behavior may not translate directly.

Mitigation:

- preserve registration and read-only state first
- restore active refresh behavior second

### Risk 4: distributed navigation rewrites can create regressions

Navigation is spread across many pages.

Mitigation:

- standardize on one verified API 20 routing pattern
- apply it consistently across all pages

## 11. Acceptance Criteria

This remediation is complete when:

- the OpenHarmony project is configured for `API 20`
- `hvigor` resolves a valid SDK path
- the ArkTS code no longer depends on unsupported higher-version constructs
- the main application pages still compile and navigate
- core device-control flows remain present
- widget/form capability is either preserved under API 20 or explicitly downgraded in a documented, buildable way

## 12. Implementation Readiness

This design is intentionally execution-oriented.
The next step is to convert it into a detailed implementation plan that breaks the remediation into testable batches:

- environment and build path correction
- configuration downgrade
- common utility import remediation
- ability remediation
- page navigation remediation
- widget/form remediation
- final build verification
