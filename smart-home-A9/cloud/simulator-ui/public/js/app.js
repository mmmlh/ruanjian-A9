import { ApiClient, ApiError, RealtimeClient } from "./api-client.js";
import {
  DEFAULT_CREDENTIALS,
  EVENT_LIMIT,
  STATE_POLL_INTERVAL_MS,
} from "./config.js";
import {
  appendEvent,
  applyMqttEvent,
  buildCommand,
  filterDevices,
  formatDeviceStatus,
  normalizeStates,
} from "./device-model.js";


const TYPE_LABELS = {
  temperature_sensor: "温度传感器",
  humidity_sensor: "湿度传感器",
  pir_sensor: "人体感应",
  light: "智能灯",
  ac: "空调",
  door_lock: "门锁",
  curtain: "窗帘",
  humidifier: "加湿器",
};

const MODE_OPTIONS = [
  ["cool", "制冷"],
  ["heat", "制热"],
  ["auto", "自动"],
  ["dehumidify", "除湿"],
  ["fan_only", "送风"],
];

const FAN_OPTIONS = [
  ["auto", "自动"],
  ["low", "低"],
  ["medium", "中"],
  ["high", "高"],
];

const api = new ApiClient({ credentials: DEFAULT_CREDENTIALS });

const state = {
  devices: [],
  selectedId: null,
  filters: {
    query: "",
    room: "all",
    type: "all",
    online: "all",
  },
  events: [],
  eventPaused: false,
  eventCollapsed: false,
  eventTopic: "",
  busyDeviceId: null,
  refreshing: false,
  realtimeToken: "",
  drafts: new Map(),
  health: {
    backend: "connecting",
    database: "connecting",
    mqtt: "connecting",
    realtime: "connecting",
  },
};

const elements = {
  startup: document.querySelector("#startup-status"),
  shell: document.querySelector(".app-shell"),
  health: document.querySelector("#service-health"),
  metrics: document.querySelector("#metric-strip"),
  search: document.querySelector("#device-search"),
  roomFilter: document.querySelector("#room-filter"),
  typeFilter: document.querySelector("#type-filter"),
  onlineFilter: document.querySelector("#online-filter"),
  refresh: document.querySelector("#refresh-button"),
  deviceList: document.querySelector("#device-list"),
  inspector: document.querySelector("#device-inspector"),
  eventState: document.querySelector("#event-connection-state"),
  eventConsole: document.querySelector(".event-console"),
  eventTopic: document.querySelector("#event-topic-filter"),
  eventCollapse: document.querySelector("#event-collapse-button"),
  eventPause: document.querySelector("#event-pause-button"),
  eventClear: document.querySelector("#event-clear-button"),
  eventList: document.querySelector("#event-list"),
  toasts: document.querySelector("#toast-region"),
};

const realtime = new RealtimeClient({
  onStatus: handleRealtimeStatus,
  onMessage: handleRealtimeMessage,
});

let statePollTimer = null;


function createElement(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== "") {
    element.textContent = text;
  }
  return element;
}


function createIcon(name) {
  const icon = createElement("i");
  icon.dataset.lucide = name;
  icon.setAttribute("aria-hidden", "true");
  return icon;
}


function renderIcons() {
  if (globalThis.lucide?.createIcons) {
    globalThis.lucide.createIcons();
  }
}


function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((left, right) => (
    left.localeCompare(right, "zh-CN")
  ));
}


function fillSelect(select, firstLabel, values, selected, labels = {}) {
  const fragment = document.createDocumentFragment();
  const first = createElement("option", "", firstLabel);
  first.value = "all";
  fragment.append(first);
  values.forEach((value) => {
    const option = createElement("option", "", labels[value] || value);
    option.value = value;
    fragment.append(option);
  });
  select.replaceChildren(fragment);
  select.value = values.includes(selected) ? selected : "all";
}


function setStartup(message, detail = "", tone = "loading") {
  const mark = createElement("div", "startup-mark", "A9");
  mark.setAttribute("aria-hidden", "true");
  const copy = createElement("div", "startup-copy");
  copy.append(createElement("p", "", message));
  if (detail) {
    copy.append(createElement("small", "", detail));
  }
  elements.startup.dataset.tone = tone;
  elements.startup.replaceChildren(mark, copy);
}


function showStartupError(error) {
  const detail = error instanceof ApiError
    ? `${error.status} · ${error.detail}`
    : String(error?.message || error || "连接失败");
  setStartup("模拟器服务暂不可用", detail, "error");
  const retry = createElement("button", "startup-retry", "重新连接");
  retry.type = "button";
  retry.addEventListener("click", startApplication, { once: true });
  elements.startup.append(retry);
}


function showApplication() {
  elements.startup.hidden = true;
  elements.shell.hidden = false;
  renderAll();
}


function healthLabel(value) {
  return {
    connecting: "连接中",
    ok: "正常",
    error: "异常",
    open: "已连接",
    reconnecting: "重连中",
    closed: "已断开",
  }[value] || value;
}


function healthTone(value) {
  if (["ok", "open"].includes(value)) {
    return "ok";
  }
  if (["connecting", "reconnecting"].includes(value)) {
    return "warning";
  }
  return "error";
}


function renderHealth() {
  const labels = {
    backend: "后端",
    database: "数据库",
    mqtt: "MQTT",
    realtime: "实时流",
  };
  const fragment = document.createDocumentFragment();
  Object.entries(labels).forEach(([key, label]) => {
    const item = createElement("span", "health-item");
    item.dataset.tone = healthTone(state.health[key]);
    item.append(createElement("i", "health-dot"));
    item.append(createElement("span", "", `${label} ${healthLabel(state.health[key])}`));
    fragment.append(item);
  });
  elements.health.replaceChildren(fragment);
}


function recentEventCount() {
  const cutoff = Date.now() - 60_000;
  return state.events.filter((event) => {
    const timestamp = Date.parse(event.receivedAt || event.timestamp || "");
    return Number.isFinite(timestamp) && timestamp >= cutoff;
  }).length;
}


function renderMetrics() {
  const online = state.devices.filter((device) => device.online).length;
  const metrics = [
    ["模拟设备", state.devices.length, "server"],
    ["当前在线", online, "wifi"],
    ["房间", uniqueSorted(state.devices.map((device) => device.roomName)).length, "house"],
    ["近一分钟消息", recentEventCount(), "activity"],
  ];
  const fragment = document.createDocumentFragment();
  metrics.forEach(([label, value, iconName]) => {
    const item = createElement("div", "metric-item");
    const icon = createElement("span", "metric-icon");
    icon.append(createIcon(iconName));
    const copy = createElement("span", "metric-copy");
    copy.append(createElement("strong", "", String(value)));
    copy.append(createElement("small", "", label));
    item.append(icon, copy);
    fragment.append(item);
  });
  elements.metrics.replaceChildren(fragment);
}


function renderFilterOptions() {
  const rooms = uniqueSorted(state.devices.map((device) => device.roomName));
  const types = uniqueSorted(state.devices.map((device) => device.type));
  fillSelect(elements.roomFilter, "全部房间", rooms, state.filters.room);
  fillSelect(elements.typeFilter, "全部类型", types, state.filters.type, TYPE_LABELS);
}


function relativeTime(value) {
  const timestamp = Date.parse(value || "");
  if (!Number.isFinite(timestamp)) {
    return "未知";
  }
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1_000));
  if (seconds < 5) {
    return "刚刚";
  }
  if (seconds < 60) {
    return `${seconds} 秒前`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes} 分钟前`;
  }
  return new Date(timestamp).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}


function selectDevice(deviceId) {
  state.selectedId = deviceId;
  renderDeviceList();
  renderInspector();
}


function renderDeviceList() {
  const devices = filterDevices(state.devices, state.filters);
  const fragment = document.createDocumentFragment();

  if (devices.length === 0) {
    const row = createElement("tr", "empty-row");
    const cell = createElement("td", "", "没有符合筛选条件的设备");
    cell.colSpan = 5;
    row.append(cell);
    fragment.append(row);
  }

  devices.forEach((device) => {
    const row = createElement("tr", "device-row");
    if (device.id === state.selectedId) {
      row.classList.add("is-selected");
    }

    const statusCell = createElement("td", "online-cell");
    const status = createElement("span", "online-indicator");
    status.dataset.online = String(device.online);
    status.setAttribute("aria-label", device.online ? "在线" : "离线");
    statusCell.append(status);

    const deviceCell = createElement("td", "device-cell");
    const button = createElement("button", "device-select", "");
    button.type = "button";
    button.setAttribute("aria-pressed", String(device.id === state.selectedId));
    button.append(createElement("strong", "", device.name));
    button.append(createElement("small", "", device.mqttTopic));
    button.addEventListener("click", () => selectDevice(device.id));
    deviceCell.append(button);

    row.append(statusCell);
    row.append(deviceCell);
    row.append(createElement("td", "room-cell", device.roomName || "未分配"));
    row.append(createElement("td", "state-cell", formatDeviceStatus(device)));
    row.append(createElement("td", "time-cell", relativeTime(device.lastUpdated)));
    fragment.append(row);
  });

  elements.deviceList.replaceChildren(fragment);
}


function defaultDraft(device) {
  const status = device.status || {};
  switch (device.type) {
    case "light":
      return {
        power: status.power || "off",
        brightness: Number(status.brightness ?? 80),
        color: status.color || "warm",
      };
    case "ac":
      return {
        power: status.power || "off",
        temp: Number(status.temp ?? 26),
        mode: status.mode || "cool",
        fan: status.fan || "auto",
        swing: status.swing || "off",
      };
    case "door_lock":
      return { locked: status.locked !== false, auth_code: "" };
    case "curtain":
      return { position: Number(status.position ?? 0) };
    case "humidifier":
      return {
        power: status.power || "off",
        level: Number(status.level ?? 2),
        target_humidity: Number(status.target_humidity ?? 60),
      };
    case "temperature_sensor":
    case "humidity_sensor":
    case "pir_sensor":
      return {};
    default:
      return {};
  }
}


function draftFor(device) {
  if (!state.drafts.has(device.id)) {
    state.drafts.set(device.id, defaultDraft(device));
  }
  return state.drafts.get(device.id);
}


function fieldset(label) {
  const group = createElement("fieldset", "control-group");
  group.append(createElement("legend", "control-label", label));
  return group;
}


function addSegmentedControl(container, label, name, options, draft, transform = (value) => value) {
  const group = fieldset(label);
  const controls = createElement("div", "segmented-control");
  options.forEach(([value, text]) => {
    const option = createElement("label", "segment-option");
    const input = createElement("input");
    input.type = "radio";
    input.name = `${name}-${state.selectedId}`;
    input.value = String(value);
    input.checked = String(draft[name]) === String(value);
    input.addEventListener("change", () => {
      if (input.checked) {
        draft[name] = transform(input.value);
      }
    });
    option.append(input, createElement("span", "", text));
    controls.append(option);
  });
  group.append(controls);
  container.append(group);
  return group;
}


function addRangeControl(container, label, name, minimum, maximum, step, draft, unit) {
  const group = fieldset(label);
  const controls = createElement("div", "range-control");
  const range = createElement("input");
  range.type = "range";
  range.name = name;
  range.min = String(minimum);
  range.max = String(maximum);
  range.step = String(step);
  range.value = String(draft[name]);
  range.setAttribute("aria-label", label);

  const numberWrap = createElement("label", "number-field");
  const number = createElement("input");
  number.type = "number";
  number.name = `${name}-number`;
  number.min = String(minimum);
  number.max = String(maximum);
  number.step = String(step);
  number.value = String(draft[name]);
  number.setAttribute("aria-label", `${label}数值`);
  numberWrap.append(number, createElement("span", "", unit));

  const syncValue = (source, target) => {
    draft[name] = Number(source.value);
    target.value = source.value;
  };
  range.addEventListener("input", () => syncValue(range, number));
  number.addEventListener("input", () => syncValue(number, range));
  controls.append(range, numberWrap);
  group.append(controls);
  container.append(group);
  return group;
}


function addSelectControl(container, label, name, options, draft) {
  const group = createElement("label", "control-group select-control");
  group.append(createElement("span", "control-label", label));
  const select = createElement("select");
  select.name = name;
  options.forEach(([value, text]) => {
    const option = createElement("option", "", text);
    option.value = value;
    option.selected = draft[name] === value;
    select.append(option);
  });
  select.addEventListener("change", () => {
    draft[name] = select.value;
  });
  group.append(select);
  container.append(group);
}


function addSwitchControl(container, label, name, draft) {
  const group = createElement("label", "switch-control");
  const copy = createElement("span");
  copy.append(createElement("strong", "", label));
  const input = createElement("input");
  input.type = "checkbox";
  input.name = name;
  input.checked = draft[name] === "on";
  input.addEventListener("change", () => {
    draft[name] = input.checked ? "on" : "off";
  });
  const track = createElement("span", "switch-track");
  group.append(copy, input, track);
  container.append(group);
}


function addPasswordControl(container, draft) {
  const group = createElement("label", "control-group password-control");
  group.append(createElement("span", "control-label", "解锁认证码"));
  const input = createElement("input");
  input.type = "password";
  input.name = "auth_code";
  input.autocomplete = "off";
  input.placeholder = "输入非空认证码";
  input.value = draft.auth_code;
  input.addEventListener("input", () => {
    draft.auth_code = input.value;
  });
  group.append(input);
  container.append(group);
  return group;
}


function renderControllerFields(form, device, draft) {
  switch (device.type) {
    case "light":
      addSegmentedControl(form, "电源", "power", [["on", "开启"], ["off", "关闭"]], draft);
      addRangeControl(form, "亮度", "brightness", 0, 100, 1, draft, "%");
      addSegmentedControl(form, "色温", "color", [["warm", "暖光"], ["cool", "冷光"]], draft);
      break;
    case "ac":
      addSegmentedControl(form, "电源", "power", [["on", "开启"], ["off", "关闭"]], draft);
      addRangeControl(form, "设定温度", "temp", 16, 30, 1, draft, "°C");
      addSegmentedControl(form, "运行模式", "mode", MODE_OPTIONS, draft);
      addSelectControl(form, "风速", "fan", FAN_OPTIONS, draft);
      addSwitchControl(form, "上下摆风", "swing", draft);
      break;
    case "door_lock": {
      const lockGroup = addSegmentedControl(
        form,
        "门锁状态",
        "locked",
        [["true", "上锁"], ["false", "解锁"]],
        draft,
        (value) => value === "true",
      );
      const password = addPasswordControl(form, draft);
      const updatePasswordVisibility = () => {
        password.hidden = draft.locked !== false;
      };
      lockGroup.addEventListener("change", updatePasswordVisibility);
      updatePasswordVisibility();
      break;
    }
    case "curtain":
      addRangeControl(form, "开启位置", "position", 0, 100, 1, draft, "%");
      addSegmentedControl(
        form,
        "快捷位置",
        "position",
        [["0", "全关"], ["50", "半开"], ["100", "全开"]],
        draft,
        Number,
      );
      break;
    case "humidifier":
      addSegmentedControl(form, "电源", "power", [["on", "开启"], ["off", "关闭"]], draft);
      addSegmentedControl(form, "运行档位", "level", [["1", "1 档"], ["2", "2 档"], ["3", "3 档"]], draft, Number);
      addRangeControl(form, "目标湿度", "target_humidity", 30, 80, 1, draft, "%");
      break;
    default:
      break;
  }
}


function sensorReading(device) {
  if (device.type === "temperature_sensor") {
    return [device.status.value ?? "--", "°C", "thermometer"];
  }
  if (device.type === "humidity_sensor") {
    return [device.status.value ?? "--", "%", "droplets"];
  }
  return [device.status.presence ? "有人" : "无人", "", "scan-line"];
}


function renderSensorInspector(body, device) {
  const [value, unit, iconName] = sensorReading(device);
  const reading = createElement("div", "sensor-reading");
  const icon = createElement("span", "sensor-reading-icon");
  icon.append(createIcon(iconName));
  const copy = createElement("span");
  copy.append(createElement("strong", "", String(value)));
  copy.append(createElement("small", "", unit));
  reading.append(icon, copy);

  const note = createElement("div", "read-only-note");
  note.append(createIcon("lock-keyhole"));
  const noteCopy = createElement("span");
  noteCopy.append(createElement("strong", "", "只读传感器"));
  noteCopy.append(createElement("small", "", "自动上报"));
  note.append(noteCopy);

  body.append(reading, note);
}


function updateDeviceFromCommand(result) {
  if (!result?.changed_state) {
    return;
  }
  const [changed] = normalizeStates([result.changed_state]);
  if (!changed) {
    return;
  }
  const index = state.devices.findIndex((device) => device.id === changed.id);
  if (index < 0) {
    return;
  }
  const devices = state.devices.slice();
  devices[index] = changed;
  state.devices = devices;
}


async function submitDeviceCommand(event, device, draft) {
  event.preventDefault();
  if (state.busyDeviceId !== null) {
    return;
  }

  try {
    const command = buildCommand(device.type, draft);
    state.busyDeviceId = device.id;
    renderInspector();
    const result = await api.sendCommand(device.id, command);
    updateDeviceFromCommand(result);
    state.drafts.delete(device.id);
    notify(`${device.name} 命令已发送`, "success");
    renderAll();
    ensureRealtimeToken();
  } catch (error) {
    if (error instanceof ApiError && error.dispatched) {
      notify("命令可能已执行，请观察实时状态", "warning", 6_000);
    } else {
      notify(error.detail || error.message || "命令发送失败", "error", 6_000);
    }
  } finally {
    state.busyDeviceId = null;
    renderInspector();
  }
}


function renderInspector() {
  const device = state.devices.find((item) => item.id === state.selectedId);
  if (!device) {
    const empty = createElement("div", "inspector-empty");
    empty.append(createIcon("mouse-pointer-click"));
    empty.append(createElement("strong", "", "未选择设备"));
    elements.inspector.replaceChildren(empty);
    renderIcons();
    return;
  }

  const header = createElement("header", "inspector-header");
  const heading = createElement("div");
  heading.append(createElement("span", "eyebrow", TYPE_LABELS[device.type] || device.type));
  heading.append(createElement("h2", "", device.name));
  heading.append(createElement(
    "p",
    "",
    `${device.entityId}${device.brand ? ` · ${device.brand}` : ""}`,
  ));
  const online = createElement("span", "inspector-online", device.online ? "在线" : "离线");
  online.dataset.online = String(device.online);
  header.append(heading, online);

  const body = createElement("div", "inspector-body");
  if (["temperature_sensor", "humidity_sensor", "pir_sensor"].includes(device.type)) {
    renderSensorInspector(body, device);
  } else {
    const form = createElement("form", "device-control-form");
    const draft = draftFor(device);
    renderControllerFields(form, device, draft);

    const footer = createElement("div", "inspector-footer");
    const status = createElement(
      "span",
      "command-status",
      state.busyDeviceId === device.id ? "正在发送命令" : "命令就绪",
    );
    const submit = createElement(
      "button",
      "primary-button",
      state.busyDeviceId === device.id ? "发送中" : "发送命令",
    );
    submit.type = "submit";
    submit.disabled = state.busyDeviceId !== null;
    if (state.busyDeviceId === device.id) {
      submit.prepend(createIcon("loader-circle"));
    } else {
      submit.prepend(createIcon("send"));
    }
    footer.append(status, submit);
    form.append(footer);
    form.addEventListener("submit", (event) => submitDeviceCommand(event, device, draft));
    body.append(form);
  }

  elements.inspector.replaceChildren(header, body);
  renderIcons();
}


function eventTimestamp(event) {
  const raw = event.receivedAt || event.timestamp;
  const date = raw ? new Date(raw) : new Date();
  if (Number.isNaN(date.getTime())) {
    return "--:--:--";
  }
  return date.toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
  });
}


function eventPayload(payload) {
  if (typeof payload === "string") {
    return payload;
  }
  try {
    return JSON.stringify(payload);
  } catch {
    return String(payload);
  }
}


function renderEvents() {
  const query = state.eventTopic.trim().toLocaleLowerCase();
  const events = state.events.filter((event) => (
    !query || String(event.topic || "").toLocaleLowerCase().includes(query)
  ));
  const fragment = document.createDocumentFragment();

  if (events.length === 0) {
    fragment.append(createElement("div", "event-empty", "等待 MQTT 事件"));
  }

  events.slice(-100).forEach((event) => {
    const row = createElement("div", "event-row");
    row.append(createElement("time", "event-time", eventTimestamp(event)));
    row.append(createElement("code", "event-topic", String(event.topic || "system")));
    row.append(createElement("code", "event-payload", eventPayload(event.payload)));
    fragment.append(row);
  });

  elements.eventList.replaceChildren(fragment);
  if (!state.eventPaused) {
    elements.eventList.scrollTop = elements.eventList.scrollHeight;
  }

  elements.eventPause.replaceChildren(createIcon(state.eventPaused ? "play" : "pause"));
  const pauseLabel = state.eventPaused ? "恢复自动滚动" : "暂停自动滚动";
  elements.eventPause.title = pauseLabel;
  elements.eventPause.setAttribute("aria-label", pauseLabel);
  elements.eventConsole.dataset.collapsed = String(state.eventCollapsed);
  elements.eventCollapse.replaceChildren(createIcon(
    state.eventCollapsed ? "chevron-up" : "chevron-down",
  ));
  const collapseLabel = state.eventCollapsed ? "展开事件面板" : "折叠事件面板";
  elements.eventCollapse.title = collapseLabel;
  elements.eventCollapse.setAttribute("aria-label", collapseLabel);
  renderIcons();
}


function renderAll() {
  renderHealth();
  renderMetrics();
  renderFilterOptions();
  renderDeviceList();
  renderInspector();
  renderEvents();
  renderIcons();
}


function notify(message, tone = "info", duration = 4_000) {
  const toast = createElement("div", "toast", message);
  toast.dataset.tone = tone;
  elements.toasts.append(toast);
  globalThis.setTimeout(() => toast.remove(), duration);
}


function logToEvent(entry) {
  let payload = entry.detail || entry.title || entry.action || entry;
  if (typeof payload === "string") {
    try {
      payload = JSON.parse(payload);
    } catch {
      // Keep human-readable log text unchanged.
    }
  }
  return {
    timestamp: entry.timestamp,
    receivedAt: entry.timestamp,
    topic: `device/${entry.device_id ?? "system"}/log`,
    payload,
  };
}


function handleRealtimeStatus(status) {
  state.health.realtime = status;
  elements.eventState.textContent = healthLabel(status);
  elements.eventState.dataset.tone = healthTone(status);
  renderHealth();
}


function handleRealtimeMessage(message) {
  if (message.type !== "mqtt" || typeof message.topic !== "string") {
    return;
  }
  const event = {
    ...message,
    receivedAt: new Date().toISOString(),
  };
  state.events = appendEvent(state.events, event, EVENT_LIMIT);
  state.devices = applyMqttEvent(state.devices, message, event.receivedAt);
  renderMetrics();
  renderDeviceList();
  renderInspector();
  renderEvents();
}


function ensureRealtimeToken() {
  if (!api.token || api.token === state.realtimeToken) {
    return;
  }
  if (state.realtimeToken) {
    realtime.stop();
  }
  state.realtimeToken = api.token;
  realtime.connect(api.token);
}


async function refreshDevices({ silent = false } = {}) {
  if (state.refreshing) {
    return;
  }
  state.refreshing = true;
  elements.refresh.disabled = true;
  elements.refresh.classList.add("is-spinning");
  try {
    const payload = await api.getStates();
    state.devices = normalizeStates(payload);
    if (!state.devices.some((device) => device.id === state.selectedId)) {
      state.selectedId = state.devices[0]?.id ?? null;
    }
    state.health.backend = "ok";
    renderAll();
    ensureRealtimeToken();
    if (!silent) {
      notify("设备状态已刷新", "success");
    }
  } catch (error) {
    state.health.backend = "error";
    renderHealth();
    if (!silent) {
      notify(error.detail || error.message || "刷新失败", "error");
    }
  } finally {
    state.refreshing = false;
    elements.refresh.disabled = false;
    elements.refresh.classList.remove("is-spinning");
  }
}


function bindEvents() {
  elements.search.addEventListener("input", () => {
    state.filters.query = elements.search.value;
    renderDeviceList();
  });
  elements.roomFilter.addEventListener("change", () => {
    state.filters.room = elements.roomFilter.value;
    renderDeviceList();
  });
  elements.typeFilter.addEventListener("change", () => {
    state.filters.type = elements.typeFilter.value;
    renderDeviceList();
  });
  elements.onlineFilter.addEventListener("change", () => {
    state.filters.online = elements.onlineFilter.value;
    renderDeviceList();
  });
  elements.refresh.addEventListener("click", () => refreshDevices());
  elements.eventTopic.addEventListener("input", () => {
    state.eventTopic = elements.eventTopic.value;
    renderEvents();
  });
  elements.eventPause.addEventListener("click", () => {
    state.eventPaused = !state.eventPaused;
    renderEvents();
  });
  elements.eventCollapse.addEventListener("click", () => {
    state.eventCollapsed = !state.eventCollapsed;
    renderEvents();
  });
  elements.eventClear.addEventListener("click", () => {
    state.events = [];
    renderMetrics();
    renderEvents();
  });
}


async function startApplication() {
  elements.shell.hidden = true;
  elements.startup.hidden = false;
  setStartup("正在检查服务状态", "", "loading");

  try {
    const ready = await api.checkReady();
    state.health.backend = "ok";
    state.health.database = ready?.checks?.database === "ok" ? "ok" : "error";
    state.health.mqtt = ready?.checks?.mqtt === "ok" ? "ok" : "error";

    setStartup("正在自动登录", "", "loading");
    await api.login();

    setStartup("正在加载模拟设备", "", "loading");
    const [statePayload, logPayload] = await Promise.all([
      api.getStates(),
      api.getLogs(),
    ]);
    state.devices = normalizeStates(statePayload);
    state.selectedId = state.devices[0]?.id ?? null;
    state.events = Array.isArray(logPayload)
      ? logPayload.slice().reverse().map(logToEvent).slice(-EVENT_LIMIT)
      : [];
    showApplication();
    ensureRealtimeToken();

    if (statePollTimer !== null) {
      globalThis.clearInterval(statePollTimer);
    }
    statePollTimer = globalThis.setInterval(
      () => refreshDevices({ silent: true }),
      STATE_POLL_INTERVAL_MS,
    );
  } catch (error) {
    state.health.backend = "error";
    state.health.database = "error";
    state.health.mqtt = "error";
    showStartupError(error);
  }
}


bindEvents();
renderIcons();
startApplication();

globalThis.addEventListener("beforeunload", () => {
  realtime.stop();
  if (statePollTimer !== null) {
    globalThis.clearInterval(statePollTimer);
  }
});
