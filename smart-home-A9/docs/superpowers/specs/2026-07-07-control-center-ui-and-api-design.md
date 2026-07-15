# OpenHarmony Control Center UI and API Integration Design

## Goal

Refactor the OpenHarmony app into a competition-ready smart-home control center for the Huawei Software Cup A9 task while preserving the working backend contract and existing device-control capabilities.

This design focuses on two outcomes:

1. Make the app look like a polished demo product instead of a collection of default cards.
2. Verify and harden the actual API paths used by the app so the main flows are fully connected and easier to debug during real-device demos.

## Scope

In scope:

- `openharmony/entry/src/main/ets/pages/DashboardPage.ets`
- `openharmony/entry/src/main/ets/pages/DeviceRemotePage.ets`
- `openharmony/entry/src/main/ets/pages/DataMonitorPage.ets`
- `openharmony/entry/src/main/ets/pages/ProfilePage.ets`
- `openharmony/entry/src/main/ets/pages/LoginPage.ets` for small visual and usability polish only
- `openharmony/entry/src/main/ets/common/ApiClient.ets`

Supporting verification scope:

- `cloud/backend/tests/test_dashboard_contract.py`
- current backend routes used by the app

Out of scope:

- redesigning backend business logic
- replacing existing ArkTS route structure
- introducing new backend endpoints unless a missing contract is discovered
- reworking deployment architecture

## Product Direction

The app will use a "Control Center" visual language:

- light overall canvas for cleanliness
- one strong dark hero card at the top for immediate impact
- large status numbers with clear hierarchy
- room-driven filtering and scene shortcuts
- stronger color semantics for online, warning, climate, and security states
- fewer tiny controls, more obvious primary actions

This direction is chosen because it best fits a competition demo: judges can understand system status, control entry points, and automation capability at a glance.

## Information Architecture

### Dashboard

The dashboard becomes the app's operational hub with four layers:

1. Hero summary card
   - online devices
   - current temperature
   - current humidity
   - realtime connection status
   - shortcuts to profile, device management, and monitoring
2. Scene quick actions
   - horizontally scrollable high-visibility scene cards
   - clear execution feedback
3. Room filter strip
   - `All` plus room chips
4. Device grid
   - larger cards
   - stronger icon/status contrast
   - visible state chip or dot
   - tap-through to device control page

Recent activity remains on the dashboard, but it moves below the hero area and uses cleaner timeline-style cards so it supports the story of "system is alive" without stealing focus from control.

### Device Control

`DeviceRemotePage` becomes a device-type-specific command panel rather than a generic form.

Common structure:

- top status band with current device name and state
- large primary visual for the current value or state
- one dominant primary action button
- one focused control region for the main parameter
- smaller secondary controls only where needed

Per device type:

- Light: emphasis on on/off state and brightness
- AC: emphasis on target temperature and mode
- Door lock: emphasis on lock state and secure feedback
- Curtain: emphasis on opening percentage and quick open/close
- Humidifier: emphasis on power, level, and target humidity

When multiple devices of the same type exist, the device switcher remains but changes from plain labels to segmented chips.

### Data Monitor

`DataMonitorPage` becomes a monitoring workspace with three clearly separated tabs:

- Live: current sensor cards
- History: recent sensor history list with stronger metric labeling
- Logs: recent operation log list

The layout should feel closer to an operations console than a plain list page.

### Profile

`ProfilePage` becomes a clean account and security page:

- account identity card
- account information block
- password update block
- logout and switch account actions

Text encoding issues must be corrected so the page is fully presentable in Chinese or English, but the implementation should stay internally consistent with the rest of the app's current language choice.

## Visual System

### Palette

Target color roles:

- background: warm light gray
- hero card: deep charcoal or blue-green dark tone
- primary accent: teal
- positive state: green
- warning or security action: amber
- destructive action: muted red
- body text: dark slate
- secondary text: neutral gray

### Surfaces

- rounded cards with clearer spacing and shadow separation
- hero card uses stronger contrast and subtle layered panels
- ordinary cards remain light but gain better depth and spacing

### Typography

- larger headline numbers for climate and online count
- fewer medium-sized labels competing for attention
- device names remain readable at a glance
- secondary metadata becomes visibly subordinate

### Motion and Feedback

No heavy animation is required, but page interactions should feel more intentional:

- pressed-state feedback on chips and cards
- clear loading placeholders or progress indicators
- success and error banners styled consistently across pages

## API Integration Design

### Required verified routes

The frontend must remain aligned with these backend contracts already present in the repository:

- `POST /api/login`
- `GET /api/dashboard/summary`
- `GET /api/devices`
- `POST /api/services`
- `GET /api/data/sensors`
- `GET /api/data/logs`
- `GET /api/auth/me`
- `PUT /api/auth/change-password`

### Frontend usage mapping

- `DashboardPage.ets` uses `getDashboardSummary()` and `executeScene()`
- `DeviceRemotePage.ets` uses `getDevicesForUi()` and `callService()`
- `DataMonitorPage.ets` uses `getDevicesForUi()`, `getSensorHistory()`, and `getDeviceLogs()`
- `ProfilePage.ets` uses `getMe()`, `changePassword()`, and `logout()`
- `LoginPage.ets` uses `login()`

### Error handling

`ApiClient.ets` currently hides some transport-layer failures behind `Unknown error`.

It will be improved to:

- extract more useful error text from request failures
- surface status code, server error detail, and transport failures separately
- keep messages readable for demo and debugging use
- avoid masking TLS, network, timeout, or unreachable-server issues

### Environment behavior

The app should continue using the configured server URL pattern already supported by `SecureStorage`.

The design does not change the deployment strategy, but the UI should make failures easier to understand when:

- the server base URL is wrong
- the server is unreachable
- login fails
- a device command fails

## Component Boundaries

To avoid another large monolithic UI file, the refactor should prefer small local helper builders inside each page where useful.

Expected boundaries:

- page-level state and data loading stay in the page file
- repeated visual sections should become `@Builder` helpers
- `ApiClient.ets` remains the transport layer
- device model parsing remains in model/common utilities

This keeps the current code organization intact while making the redesigned pages easier to maintain.

## Data Flow

### Dashboard flow

1. page appears
2. fetch `GET /api/dashboard/summary`
3. map rooms, devices, scenes, logs, and stats
4. derive climate summary from device status
5. render hero card, scenes, activity, filters, and device grid
6. websocket or MQTT realtime notification triggers throttled refresh

### Device command flow

1. load devices for selected type from `GET /api/devices`
2. user changes a control
3. page calls `POST /api/services`
4. service result returns success or failure
5. page shows feedback and refreshes local device state

### Monitoring flow

1. load sensor devices from `GET /api/devices`
2. load sensor history from `GET /api/data/sensors`
3. load command logs from `GET /api/data/logs`
4. filter by device when a chip is selected

## Failure Handling

The redesigned pages should explicitly handle:

- empty device lists
- empty logs or history
- loading state
- command-in-progress state
- server request failure
- realtime connection offline state

Each of these states should have a visible, intentional UI rather than a blank area or weak text line.

## Verification Plan

Before claiming completion, verify:

1. backend tests still pass, especially dashboard contract coverage
2. main frontend pages compile into a HAP successfully
3. dashboard loads with summary data
4. device command pages can still send control actions
5. monitoring page loads live data, history, and logs
6. profile page loads account data and password change path still works
7. network and transport failures now produce readable client messages

## Implementation Plan Handoff

The implementation phase should proceed in this order:

1. strengthen `ApiClient.ets` error handling
2. redesign `DashboardPage.ets`
3. redesign `DeviceRemotePage.ets`
4. redesign `DataMonitorPage.ets`
5. redesign `ProfilePage.ets`
6. apply light polish to `LoginPage.ets`
7. build and verify OpenHarmony package

This order keeps the networking and contract layer stable first, then improves the highest-visibility pages for competition demo value.
