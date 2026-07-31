import test from "node:test";
import assert from "node:assert/strict";
import {
  appendEvent,
  applyMqttEvent,
  buildCommand,
  filterDevices,
  formatDeviceStatus,
  normalizeStates,
} from "../public/js/device-model.js";


const states = [{
  entity_id: "ac.device_5",
  state: "cool",
  last_updated: "2026-07-31T08:42:00Z",
  attributes: {
    device_id: 5,
    friendly_name: "客厅空调",
    room_name: "客厅",
    mqtt_topic: "home/livingroom/ac",
    brand: "gree",
    online: true,
    status_summary: "制冷 25°C",
    power: "on",
    mode: "cool",
    temp: 25,
    fan: "auto",
  },
}];


test("normalizes existing /api/states objects", () => {
  const [device] = normalizeStates(states);

  assert.equal(device.id, 5);
  assert.equal(device.type, "ac");
  assert.equal(device.brand, "gree");
  assert.equal(device.status.temp, 25);
  assert.equal(device.status.device_id, undefined);
});


test("ignores malformed state entries", () => {
  assert.deepEqual(normalizeStates(null), []);
  assert.deepEqual(normalizeStates([{ entity_id: "ac.device_5", attributes: {} }, null]), []);
});


test("filters by room, type, online state, name, and MQTT topic", () => {
  const devices = normalizeStates(states);

  assert.equal(filterDevices(devices, {
    query: "livingroom",
    room: "客厅",
    type: "ac",
    online: "online",
  }).length, 1);
  assert.equal(filterDevices(devices, {
    query: "卧室",
    room: "all",
    type: "all",
    online: "all",
  }).length, 0);
});


test("unwraps response events and updates the matching device", () => {
  const devices = normalizeStates(states);
  const updated = applyMqttEvent(devices, {
    topic: "home/livingroom/ac/response",
    payload: {
      success: true,
      state: { power: "on", mode: "cool", temp: 24, device_id: "ac_005" },
    },
  }, "2026-07-31T08:43:00Z");

  assert.equal(updated[0].status.temp, 24);
  assert.equal(updated[0].status.device_id, undefined);
  assert.equal(updated[0].lastUpdated, "2026-07-31T08:43:00Z");
  assert.notEqual(updated, devices);
});


test("leaves device state unchanged for unknown MQTT topics", () => {
  const devices = normalizeStates(states);

  assert.equal(applyMqttEvent(devices, {
    topic: "home/study/light/status",
    payload: { power: "on" },
  }), devices);
});


test("keeps only the newest 300 events", () => {
  let events = [];
  for (let index = 0; index < 305; index += 1) {
    events = appendEvent(events, { topic: String(index) });
  }

  assert.equal(events.length, 300);
  assert.equal(events[0].topic, "5");
});


test("builds commands matching existing backend validation", () => {
  assert.deepEqual(buildCommand("light", {
    power: "on",
    brightness: 72,
    color: "warm",
  }), {
    action: "on",
    params: { brightness: 72, color: "warm" },
  });
  assert.deepEqual(buildCommand("ac", {
    power: "on",
    temp: 24,
    mode: "cool",
    fan: "high",
    swing: "off",
  }), {
    action: "on",
    params: { temp: 24, mode: "cool", fan: "high", swing: "off" },
  });
  assert.deepEqual(buildCommand("door_lock", {
    locked: false,
    auth_code: "demo",
  }), {
    action: "unlock",
    params: { auth_code: "demo" },
  });
  assert.deepEqual(buildCommand("curtain", { position: 45 }), {
    action: "set",
    params: { position: 45 },
  });
  assert.deepEqual(buildCommand("humidifier", {
    power: "on",
    level: 2,
    target_humidity: 60,
  }), {
    action: "on",
    params: { level: 2, target_humidity: 60 },
  });
});


test("uses canonical boundary actions for off, open, close, and lock", () => {
  assert.deepEqual(buildCommand("light", { power: "off" }), { action: "off", params: {} });
  assert.deepEqual(buildCommand("curtain", { position: 0 }), { action: "close", params: {} });
  assert.deepEqual(buildCommand("curtain", { position: 100 }), { action: "open", params: {} });
  assert.deepEqual(buildCommand("door_lock", { locked: true }), { action: "lock", params: {} });
});


test("rejects read-only sensors and invalid controller values", () => {
  assert.throws(() => buildCommand("temperature_sensor", { value: 30 }), /read-only/);
  assert.throws(() => buildCommand("door_lock", { locked: false, auth_code: "" }), /auth_code/);
  assert.throws(() => buildCommand("ac", { power: "on", temp: 31 }), /temp/);
  assert.throws(() => buildCommand("humidifier", {
    power: "on",
    level: 2,
    target_humidity: 81,
  }), /target_humidity/);
});


test("formats status text for controller and sensor rows", () => {
  assert.equal(formatDeviceStatus({ type: "ac", status: { power: "on", mode: "cool", temp: 25 } }), "制冷 · 25°C");
  assert.equal(formatDeviceStatus({ type: "humidity_sensor", status: { value: 56.2 } }), "56.2%");
  assert.equal(formatDeviceStatus({ type: "pir_sensor", status: { presence: false } }), "无人活动");
});
