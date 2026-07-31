import test from "node:test";
import assert from "node:assert/strict";
import { ENDPOINTS } from "../public/js/config.js";
import {
  ApiClient,
  ApiError,
  RealtimeClient,
  buildRealtimeUrl,
  reconnectDelay,
} from "../public/js/api-client.js";


test("exports only frozen existing endpoints", () => {
  assert.deepEqual(Object.keys(ENDPOINTS).sort(), [
    "command",
    "login",
    "logs",
    "ready",
    "realtime",
    "states",
  ]);
  assert.equal(ENDPOINTS.command(5), "/api/devices/5/command");
  assert.equal(ENDPOINTS.realtime, "/ws/realtime");
  assert.ok(Object.isFrozen(ENDPOINTS));
});


test("logs in and sends the bearer token", async () => {
  const calls = [];
  const fetchFn = async (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/login") {
      return new Response(JSON.stringify({
        token: "jwt",
        user: { username: "admin" },
      }), { status: 200 });
    }
    return new Response(JSON.stringify([]), { status: 200 });
  };
  const client = new ApiClient({
    fetchFn,
    credentials: { username: "admin", password: "admin123" },
  });

  await client.getStates();

  assert.equal(calls[0].url, "/api/login");
  assert.equal(calls[1].url, "/api/states");
  assert.equal(calls[1].options.headers.Authorization, "Bearer jwt");
  assert.equal(client.token, "jwt");
});


test("invokes browser fetch with the global receiver", async () => {
  const receivers = [];
  const fetchFn = function fetchWithReceiverCheck() {
    receivers.push(this);
    return Promise.resolve(new Response(JSON.stringify({ status: "ready" }), {
      status: 200,
    }));
  };
  const client = new ApiClient({
    fetchFn,
    credentials: { username: "admin", password: "admin123" },
  });

  await client.checkReady();

  assert.equal(receivers[0], globalThis);
});


test("reauthenticates once after a 401", async () => {
  let protectedCalls = 0;
  let loginCalls = 0;
  const fetchFn = async (url) => {
    if (url === "/api/login") {
      loginCalls += 1;
      return new Response(JSON.stringify({ token: `jwt-${loginCalls}` }), {
        status: 200,
      });
    }
    protectedCalls += 1;
    return protectedCalls === 1
      ? new Response(JSON.stringify({ detail: "expired" }), { status: 401 })
      : new Response(JSON.stringify([]), { status: 200 });
  };
  const client = new ApiClient({
    fetchFn,
    credentials: { username: "admin", password: "admin123" },
  });

  assert.deepEqual(await client.getStates(), []);
  assert.equal(loginCalls, 2);
  assert.equal(protectedCalls, 2);
});


test("does not loop after a second 401", async () => {
  let loginCalls = 0;
  const fetchFn = async (url) => {
    if (url === "/api/login") {
      loginCalls += 1;
      return new Response(JSON.stringify({ token: `jwt-${loginCalls}` }), {
        status: 200,
      });
    }
    return new Response(JSON.stringify({ detail: "still expired" }), {
      status: 401,
    });
  };
  const client = new ApiClient({
    fetchFn,
    credentials: { username: "admin", password: "admin123" },
  });

  await assert.rejects(client.getStates(), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 401);
    assert.equal(error.detail, "still expired");
    return true;
  });
  assert.equal(loginCalls, 2);
});


test("sends the existing command body without reshaping it", async () => {
  const calls = [];
  const fetchFn = async (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/login") {
      return new Response(JSON.stringify({ token: "jwt" }), { status: 200 });
    }
    return new Response(JSON.stringify({ success: true }), { status: 200 });
  };
  const client = new ApiClient({ fetchFn, credentials: { username: "admin", password: "admin123" } });
  const command = { action: "set", params: { position: 45 } };

  await client.sendCommand(15, command);

  assert.equal(calls[1].url, "/api/devices/15/command");
  assert.deepEqual(JSON.parse(calls[1].options.body), command);
});


test("preserves backend error detail and uncertain dispatch state", async () => {
  const fetchFn = async (url) => url === "/api/login"
    ? new Response(JSON.stringify({ token: "jwt" }), { status: 200 })
    : new Response(JSON.stringify({ detail: "command_post_dispatch_failed" }), { status: 502 });
  const client = new ApiClient({ fetchFn, credentials: { username: "admin", password: "admin123" } });

  await assert.rejects(client.sendCommand(5, { action: "on", params: {} }), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.detail, "command_post_dispatch_failed");
    assert.equal(error.dispatched, true);
    return true;
  });
});


test("builds same-origin realtime URLs and caps reconnect delays", () => {
  assert.equal(buildRealtimeUrl({ protocol: "https:", host: "localhost" }, "a b"), "wss://localhost/ws/realtime?token=a%20b");
  assert.equal(buildRealtimeUrl({ protocol: "http:", host: "localhost:8080" }, "jwt"), "ws://localhost:8080/ws/realtime?token=jwt");
  assert.deepEqual([0, 1, 2, 3, 4, 8].map(reconnectDelay), [
    1000,
    2000,
    5000,
    10000,
    30000,
    30000,
  ]);
});


test("reports realtime state, messages, and schedules reconnect", () => {
  const sockets = [];
  const timers = [];
  const statuses = [];
  const messages = [];
  const webSocketFactory = (url) => {
    const socket = {
      url,
      closeCalled: false,
      close() { this.closeCalled = true; },
    };
    sockets.push(socket);
    return socket;
  };
  const realtime = new RealtimeClient({
    webSocketFactory,
    location: { protocol: "https:", host: "localhost" },
    setTimeoutFn: (callback, delay) => {
      timers.push({ callback, delay });
      return timers.length;
    },
    clearTimeoutFn: () => {},
    onStatus: (status) => statuses.push(status),
    onMessage: (message) => messages.push(message),
  });

  realtime.connect("jwt");
  sockets[0].onopen();
  sockets[0].onmessage({ data: JSON.stringify({ type: "mqtt", topic: "home/#", payload: {} }) });
  sockets[0].onclose();

  assert.equal(sockets[0].url, "wss://localhost/ws/realtime?token=jwt");
  assert.deepEqual(statuses, ["connecting", "open", "reconnecting"]);
  assert.equal(messages[0].topic, "home/#");
  assert.equal(timers[0].delay, 1000);

  timers[0].callback();
  assert.equal(sockets.length, 2);
  realtime.stop();
  assert.equal(sockets[1].closeCalled, true);
  assert.equal(statuses.at(-1), "closed");
});
