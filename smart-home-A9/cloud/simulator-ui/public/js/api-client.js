import { ENDPOINTS } from "./config.js";


export class ApiError extends Error {
  constructor(status, detail) {
    super(String(detail || `HTTP ${status}`));
    this.name = "ApiError";
    this.status = status;
    this.detail = String(detail || `HTTP ${status}`);
    this.dispatched = this.detail === "command_post_dispatch_failed";
  }
}


async function responseData(response) {
  if (response.status === 204) {
    return null;
  }
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}


function errorDetail(data, response) {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = data.detail;
    if (detail && typeof detail === "object") {
      return detail.code || JSON.stringify(detail);
    }
    return detail;
  }
  if (typeof data === "string" && data) {
    return data;
  }
  return response.statusText || `HTTP ${response.status}`;
}


async function parseResponse(response) {
  const data = await responseData(response);
  if (!response.ok) {
    throw new ApiError(response.status, errorDetail(data, response));
  }
  return data;
}


export class ApiClient {
  #credentials;
  #fetch;
  #token = "";

  constructor({ fetchFn = globalThis.fetch, credentials }) {
    this.#fetch = fetchFn;
    this.#credentials = { ...credentials };
  }

  get token() {
    return this.#token;
  }

  async checkReady() {
    const response = await this.#fetch(ENDPOINTS.ready, {
      headers: { Accept: "application/json" },
    });
    return parseResponse(response);
  }

  async login() {
    const response = await this.#fetch(ENDPOINTS.login, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(this.#credentials),
    });
    const data = await parseResponse(response);
    if (!data || typeof data.token !== "string" || !data.token) {
      throw new ApiError(502, "invalid_login_response");
    }
    this.#token = data.token;
    return this.#token;
  }

  async getStates() {
    return this.#authorizedRequest(ENDPOINTS.states);
  }

  async getLogs() {
    return this.#authorizedRequest(ENDPOINTS.logs);
  }

  async sendCommand(deviceId, command) {
    return this.#authorizedRequest(ENDPOINTS.command(deviceId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(command),
    });
  }

  async #authorizedRequest(url, options = {}, allowRetry = true) {
    if (!this.#token) {
      await this.login();
    }

    const response = await this.#fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        ...options.headers,
        Authorization: `Bearer ${this.#token}`,
      },
    });

    if (response.status === 401 && allowRetry) {
      this.#token = "";
      await this.login();
      return this.#authorizedRequest(url, options, false);
    }

    return parseResponse(response);
  }
}


export function reconnectDelay(attempt) {
  return [1_000, 2_000, 5_000, 10_000, 30_000][Math.min(attempt, 4)];
}


export function buildRealtimeUrl(location, token) {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}${ENDPOINTS.realtime}?token=${encodeURIComponent(token)}`;
}


export class RealtimeClient {
  #attempt = 0;
  #clearTimeout;
  #location;
  #onMessage;
  #onStatus;
  #setTimeout;
  #socket = null;
  #stopped = true;
  #timer = null;
  #token = "";
  #webSocketFactory;

  constructor({
    webSocketFactory = (url) => new WebSocket(url),
    location = globalThis.location,
    setTimeoutFn = globalThis.setTimeout,
    clearTimeoutFn = globalThis.clearTimeout,
    onMessage = () => {},
    onStatus = () => {},
  } = {}) {
    this.#webSocketFactory = webSocketFactory;
    this.#location = location;
    this.#setTimeout = setTimeoutFn;
    this.#clearTimeout = clearTimeoutFn;
    this.#onMessage = onMessage;
    this.#onStatus = onStatus;
  }

  connect(token) {
    this.#token = token;
    this.#stopped = false;
    this.#attempt = 0;
    this.#openSocket("connecting");
  }

  stop() {
    this.#stopped = true;
    if (this.#timer !== null) {
      this.#clearTimeout(this.#timer);
      this.#timer = null;
    }
    if (this.#socket) {
      const socket = this.#socket;
      this.#socket = null;
      socket.onclose = null;
      socket.close();
    }
    this.#onStatus("closed");
  }

  #openSocket(status) {
    if (this.#stopped) {
      return;
    }
    this.#onStatus(status);
    const socket = this.#webSocketFactory(
      buildRealtimeUrl(this.#location, this.#token),
    );
    this.#socket = socket;

    socket.onopen = () => {
      if (socket !== this.#socket || this.#stopped) {
        return;
      }
      this.#attempt = 0;
      this.#onStatus("open");
    };
    socket.onmessage = (event) => {
      if (socket !== this.#socket || this.#stopped) {
        return;
      }
      try {
        const message = JSON.parse(event.data);
        if (message && typeof message === "object") {
          this.#onMessage(message);
        }
      } catch {
        // Ignore malformed frames; the next state poll remains authoritative.
      }
    };
    socket.onerror = () => {};
    socket.onclose = () => {
      if (socket !== this.#socket || this.#stopped) {
        return;
      }
      this.#socket = null;
      this.#scheduleReconnect();
    };
  }

  #scheduleReconnect() {
    this.#onStatus("reconnecting");
    const delay = reconnectDelay(this.#attempt);
    this.#attempt += 1;
    this.#timer = this.#setTimeout(() => {
      this.#timer = null;
      this.#openSocket("connecting");
    }, delay);
  }
}
