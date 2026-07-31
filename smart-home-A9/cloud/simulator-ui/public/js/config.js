export const DEFAULT_CREDENTIALS = Object.freeze({
  username: "admin",
  password: "admin123",
});

export const ENDPOINTS = Object.freeze({
  ready: "/api/ready",
  login: "/api/login",
  states: "/api/states",
  logs: "/api/data/logs?limit=100",
  command: (deviceId) => `/api/devices/${encodeURIComponent(deviceId)}/command`,
  realtime: "/ws/realtime",
});

export const STATE_POLL_INTERVAL_MS = 10_000;
export const EVENT_LIMIT = 300;
