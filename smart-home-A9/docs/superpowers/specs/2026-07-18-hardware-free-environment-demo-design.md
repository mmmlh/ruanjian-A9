# Hardware-Free Environment Demo

## Goal

Make the existing virtual temperature and humidity sensors drive a credible
no-hardware demonstration: devices remain online when simulator sensor data is
received, and every device remote page shows the current environment for its
room.

## Root Cause

Virtual sensors publish to MQTT `.../sensor` topics every five seconds. The
backend records those values in sensor history but only updates a device's
`status_json` and `updated_at` for `.../status` or `.../response` topics.
Sensor devices consequently become stale and the app reports them offline.

## Design

### Backend Sensor State

Extend the existing MQTT device-state synchronization path to accept
`.../sensor` topics. For a valid sensor message, locate the device by its MQTT
topic, store the payload fields as its status, and update `updated_at`. Sensor
history persistence and all non-sensor status/response handling remain
unchanged.

### Remote Environment Display

`DeviceRemotePage` loads the current device's room devices and derives room
temperature and humidity from `temperature_sensor` and `humidity_sensor`
status values. It presents a compact environment row below the device summary.
Rooms without a humidity sensor show `湿度未采集`; all current remote-page rooms
have a temperature sensor.

The page refreshes only the room environment every five seconds while visible.
It does not reload the controlled-device list or change the current selection.

### Error Handling

Missing, malformed, or unavailable sensor values remain a display-only issue:
the page shows the corresponding unavailable label and keeps device controls
usable. A failed periodic environment fetch leaves the last valid values on
screen.

## Verification

- Backend regression proves a simulated `.../sensor` message updates the
  matching device status and freshness timestamp.
- Frontend regression proves the remote page loads room devices, exposes
  temperature/humidity labels, and manages the five-second environment timer.
- Run targeted tests, the repository suite, and the OpenHarmony HAP build.
- Deploy the backend change to the existing server and verify its health API.
