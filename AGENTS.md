# Repository Guidelines

## Project Structure & Module Organization

This is a single-module OpenHarmony API 20 application. Application metadata and shared icons live in `AppScope/`. The `entry/` module contains the HAP configuration and all runtime code. ArkTS sources are under `entry/src/main/ets/`: `pages/` contains routed screens, `common/` contains API, storage, crypto, theme, and reusable UI helpers, `model/` contains domain models, and `entryability/` plus `entryformability/` define application and widget lifecycles. Manifests, page registration, strings, colors, media, and network configuration are under `entry/src/main/resources/`. Treat `entry/build/`, `.hvigor/`, `.idea/`, logs, and `local.properties` as generated or machine-local. Reference device captures are in `screenshots/`.

## Build, Test, and Development Commands

- `./hvigorw.bat assembleHap --stacktrace` compiles ArkTS, packages resources, and produces signed/unsigned HAPs in `entry/build/default/outputs/default/`.
- `./hvigorw.bat --stop-daemon` stops stale Hvigor workers before retrying a failed build.
- `hdc install entry\build\default\outputs\default\entry-default-signed.hap` installs the debug package on a connected API 20 device.

For interactive development, open the repository root in DevEco Studio, configure the API 20 SDK in `local.properties`, select the `entry` target, and run it on an API 20 device or emulator.

## Coding Style & Naming Conventions

Follow the existing ArkTS style: two-space indentation, single quotes, no semicolons, and explicit parameter/return types. Use `PascalCase` for components, classes, models, and their files (`DeviceModel.ets`); use `camelCase` for functions and state; reserve `UPPER_SNAKE_CASE` for constants. Keep API mapping in `ApiClient.ets`, persisted values in `SecureStorage.ets`, and shared visual tokens in `ControlCenterTheme.ets`. Format with DevEco Studio and keep imports grouped at the top.

## Testing Guidelines

No automated test framework, coverage threshold, or test task is currently configured. Every change must at least pass `assembleHap` and receive an API 20 device/emulator smoke test. Exercise affected login, REST/WebSocket, device-control, automation, and widget flows. New tests should use OpenHarmony/Hypium conventions under `entry/src/test/` for unit tests or `entry/src/ohosTest/` for device tests, with descriptive `*.test.ets` names.

## Commit & Pull Request Guidelines

Git history is absent from this repository snapshot, so no local commit convention can be inferred. Use short imperative subjects, optionally scoped, such as `fix(api): handle expired tokens`. Keep commits focused. Pull requests should explain behavior changes, list verification commands and devices, link the relevant issue, and include updated screenshots for UI changes.

## Security & Configuration

Never add SDK paths, tokens, private keys, certificates, or signing passwords. Create per-machine signing configuration in DevEco Studio, rotate any exposed material, and review `build-profile.json5`, `local.properties`, and network URLs before sharing changes or artifacts.
