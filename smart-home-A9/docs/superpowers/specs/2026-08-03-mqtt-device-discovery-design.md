# MQTT Device Discovery Design

## Goal

Replace the fixed candidate catalog with a real discovery flow for devices that
connect to this deployment's MQTT broker and announce themselves using the
existing `home/<area>/<device_type>/hello` protocol.

## Discovery Contract

A discoverable device publishes a retained MQTT message to
`home/<area>/<device_type>/hello`:

```json
{
  "hardware_id": "vendor-model-serial",
  "protocol_version": "1.0",
  "capabilities": {"actions": ["on", "off"], "params": {}}
}
```

It publishes `heartbeat` messages with the same `hardware_id`. The backend
records the last accepted hello and heartbeat in a `discovered_devices` table.
Only a device announced in the last 90 seconds, not already represented by a
`devices.mqtt_topic` row, is returned by `POST /api/discovery`.

## Binding

Binding receives a discovered hardware identifier instead of a static catalog
identifier. In one SQLite `BEGIN IMMEDIATE` transaction it validates the room,
loads a fresh discovery record, rejects already-bound topics, then creates the
device carrying its announced topic, hardware ID, protocol version and
capabilities. The discovery record is retained for presence history, but the
device ceases to appear in subsequent scans due to the bound-topic filter.

## Client Behavior

The device-management screen keeps its scan and bind workflow. Results show
the actual device type, hardware identifier, announced area, online state and
last report time. A failed scan clears stale results and displays the request
error; a successful scan clears old errors. No fixed candidates or fabricated
timestamps remain in the discovery response.

## Compatibility And Validation

Existing simulators already publish the required retained hello and regular
heartbeats, so they exercise the same protocol used by physical devices. Tests
will prove discovery registration, freshness filtering, duplicate prevention,
binding metadata transfer and the public HTTP workflow.
