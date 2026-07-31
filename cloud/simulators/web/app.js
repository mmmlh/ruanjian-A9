const TYPE_LABELS = {
  temperature_sensor: "温度传感器",
  humidity_sensor: "湿度传感器",
  pir_sensor: "人体感应器",
  light: "智能灯",
  ac: "空调",
  door_lock: "智能门锁",
  curtain: "智能窗帘",
  humidifier: "加湿器",
};

const TYPE_GLYPHS = {
  temperature_sensor: "温度",
  humidity_sensor: "湿度",
  pir_sensor: "人体",
  light: "灯光",
  ac: "空调",
  door_lock: "门锁",
  curtain: "窗帘",
  humidifier: "加湿",
};

const ROOM_LABELS = { livingroom: "客厅", bedroom: "卧室", study: "书房" };
const app = { devices: [], meta: null, loading: false };

const elements = {
  grid: document.querySelector("#deviceGrid"),
  empty: document.querySelector("#emptyState"),
  resultCount: document.querySelector("#resultCount"),
  search: document.querySelector("#searchInput"),
  roomFilter: document.querySelector("#roomFilter"),
  typeFilter: document.querySelector("#typeFilter"),
  stateFilter: document.querySelector("#stateFilter"),
  dialog: document.querySelector("#addDialog"),
  addForm: document.querySelector("#addForm"),
  addType: document.querySelector("#addType"),
  addRoom: document.querySelector("#addRoom"),
  brandField: document.querySelector("#brandField"),
  topicPreview: document.querySelector("#topicPreview"),
  toastRegion: document.querySelector("#toastRegion"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `请求失败 (${response.status})`);
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function roomLabel(room) {
  return ROOM_LABELS[room] || room;
}

function formatTime(timestamp) {
  if (!timestamp) return "暂无活动";
  return `更新于 ${new Date(timestamp * 1000).toLocaleTimeString("zh-CN", { hour12: false })}`;
}

function friendlyError(message) {
  if (!message) return "";
  if (/10061|connection refused|actively refused/i.test(message)) return "MQTT Broker 未连接";
  if (/timed out|timeout/i.test(message)) return "MQTT Broker 连接超时";
  return message;
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  elements.toastRegion.append(toast);
  setTimeout(() => toast.remove(), 3200);
}

function updateOverview() {
  const running = app.devices.filter((device) => device.running).length;
  const connected = app.devices.filter((device) => device.connected).length;
  document.querySelector("#deviceCount").textContent = app.devices.length;
  document.querySelector("#runningCount").textContent = running;
  document.querySelector("#connectedCount").textContent = connected;
  document.querySelector("#roomCount").textContent = new Set(app.devices.map((device) => device.room)).size;

  const broker = document.querySelector("#brokerState");
  broker.className = `broker-state ${connected ? "online" : "offline"}`;
  broker.querySelector("span:last-child").textContent = connected
    ? `MQTT 在线 · ${connected}/${app.devices.length}`
    : running ? "MQTT 未连接" : "模拟器已停止";
}

function matchesFilters(device) {
  const query = elements.search.value.trim().toLowerCase();
  const haystack = `${device.id} ${device.room} ${roomLabel(device.room)} ${device.type} ${TYPE_LABELS[device.type]} ${device.topic}`.toLowerCase();
  if (query && !haystack.includes(query)) return false;
  if (elements.roomFilter.value && device.room !== elements.roomFilter.value) return false;
  if (elements.typeFilter.value && device.type !== elements.typeFilter.value) return false;
  if (elements.stateFilter.value === "connected" && !device.connected) return false;
  if (elements.stateFilter.value === "running" && !device.running) return false;
  if (elements.stateFilter.value === "stopped" && device.running) return false;
  return true;
}

function statePresentation(device) {
  const state = device.state || {};
  switch (device.type) {
    case "temperature_sensor":
      return { primary: `${state.value ?? "--"} °C`, detail: "环境温度" };
    case "humidity_sensor":
      return { primary: `${state.value ?? "--"} %`, detail: "相对湿度" };
    case "pir_sensor":
      return { primary: state.presence ? "检测到有人" : "当前无人", detail: "人体活动状态" };
    case "light":
      return { primary: state.power === "on" ? "已开启" : "已关闭", detail: `亮度 ${state.brightness ?? 0}% · ${state.color === "cool" ? "冷光" : "暖光"}` };
    case "ac":
      return { primary: state.power === "on" ? `${state.temp ?? 26} °C` : "已关闭", detail: `${modeLabel(state.mode)} · ${fanLabel(state.fan)} · ${brandLabel(state.brand || device.brand)}` };
    case "door_lock":
      return { primary: state.locked === false ? "已解锁" : "已上锁", detail: "门禁安全状态" };
    case "curtain":
      return { primary: `${state.position ?? 0}%`, detail: state.position >= 100 ? "已完全打开" : state.position <= 0 ? "已完全关闭" : "当前开合度" };
    case "humidifier":
      return { primary: state.power === "on" ? "运行中" : "已关闭", detail: `${state.level ?? 2} 档 · 目标湿度 ${state.target_humidity ?? 60}%` };
    default:
      return { primary: "未知状态", detail: "" };
  }
}

function modeLabel(value) {
  return ({ cool: "制冷", heat: "制热", dehumidify: "除湿", fan_only: "送风", auto: "自动" })[value] || "制冷";
}

function fanLabel(value) {
  return ({ auto: "自动风", low: "低风", medium: "中风", high: "高风" })[value] || "自动风";
}

function brandLabel(value) {
  return ({ gree: "格力", haier: "海尔", midea: "美的", generic: "通用" })[value] || "通用";
}

function option(value, label, selectedValue) {
  return `<option value="${value}" ${value === selectedValue ? "selected" : ""}>${label}</option>`;
}

function controlsFor(device) {
  const state = device.state || {};
  const disabled = device.running ? "" : "disabled";
  if (device.type === "temperature_sensor" || device.type === "humidity_sensor") {
    const isTemperature = device.type === "temperature_sensor";
    return `<form class="control-row" data-operation="sensor" data-device-id="${device.id}">
      <label>${isTemperature ? "温度" : "湿度"}<input name="value" type="number" data-number step="0.1" min="${isTemperature ? 15 : 20}" max="${isTemperature ? 38 : 95}" value="${state.value ?? (isTemperature ? 25 : 55)}" ${disabled}></label>
      <button class="button secondary" type="submit" ${disabled}>发布读数</button>
    </form>`;
  }
  if (device.type === "pir_sensor") {
    return `<div class="control-row"><div class="segmented">
      <button class="button" type="button" data-sensor-presence="true" data-device-id="${device.id}" ${disabled}>检测到有人</button>
      <button class="button" type="button" data-sensor-presence="false" data-device-id="${device.id}" ${disabled}>设为无人</button>
    </div></div>`;
  }
  if (device.type === "light") {
    return `<div class="control-row"><div class="segmented">
      <button class="button" type="button" data-device-command="on" data-device-id="${device.id}" ${disabled}>开启</button>
      <button class="button" type="button" data-device-command="off" data-device-id="${device.id}" ${disabled}>关闭</button>
    </div></div>
    <form class="control-row" data-operation="command" data-action="set" data-device-id="${device.id}">
      <label>亮度<input name="brightness" type="range" data-number min="0" max="100" value="${state.brightness ?? 80}" ${disabled}></label>
      <select name="color" aria-label="灯光色温" ${disabled}>${option("warm", "暖光", state.color)}${option("cool", "冷光", state.color)}</select>
      <button class="button secondary" type="submit" ${disabled}>应用</button>
    </form>`;
  }
  if (device.type === "ac") {
    return `<div class="control-row"><div class="segmented">
      <button class="button" type="button" data-device-command="on" data-device-id="${device.id}" ${disabled}>开启</button>
      <button class="button" type="button" data-device-command="off" data-device-id="${device.id}" ${disabled}>关闭</button>
    </div></div>
    <form class="control-row" data-operation="command" data-action="set" data-device-id="${device.id}">
      <input name="temp" type="number" data-number min="16" max="30" value="${state.temp ?? 26}" aria-label="目标温度" ${disabled}>
      <select name="mode" aria-label="空调模式" ${disabled}>${option("cool", "制冷", state.mode)}${option("heat", "制热", state.mode)}${option("dehumidify", "除湿", state.mode)}${option("fan_only", "送风", state.mode)}${option("auto", "自动", state.mode)}</select>
      <select name="fan" aria-label="风速" ${disabled}>${option("auto", "自动风", state.fan)}${option("low", "低风", state.fan)}${option("medium", "中风", state.fan)}${option("high", "高风", state.fan)}</select>
      <button class="button secondary" type="submit" ${disabled}>应用</button>
    </form>`;
  }
  if (device.type === "door_lock") {
    return `<div class="control-row"><div class="segmented">
      <button class="button" type="button" data-device-command="lock" data-device-id="${device.id}" ${disabled}>上锁</button>
      <button class="button" type="button" data-device-command="unlock" data-device-id="${device.id}" ${disabled}>解锁</button>
    </div></div>`;
  }
  if (device.type === "curtain") {
    return `<div class="control-row"><div class="segmented">
      <button class="button" type="button" data-device-command="open" data-device-id="${device.id}" ${disabled}>打开</button>
      <button class="button" type="button" data-device-command="close" data-device-id="${device.id}" ${disabled}>关闭</button>
    </div></div>
    <form class="control-row" data-operation="command" data-action="set" data-device-id="${device.id}">
      <label>开合度<input name="position" type="range" data-number min="0" max="100" value="${state.position ?? 0}" ${disabled}></label>
      <button class="button secondary" type="submit" ${disabled}>应用</button>
    </form>`;
  }
  return `<div class="control-row"><div class="segmented">
    <button class="button" type="button" data-device-command="on" data-device-id="${device.id}" ${disabled}>开启</button>
    <button class="button" type="button" data-device-command="off" data-device-id="${device.id}" ${disabled}>关闭</button>
  </div></div>
  <form class="control-row" data-operation="command" data-action="set" data-device-id="${device.id}">
    <select name="level" data-number aria-label="加湿档位" ${disabled}>${option("1", "1 档", String(state.level))}${option("2", "2 档", String(state.level))}${option("3", "3 档", String(state.level))}</select>
    <label>目标<input name="target_humidity" type="number" data-number min="30" max="90" value="${state.target_humidity ?? 60}" ${disabled}></label>
    <button class="button secondary" type="submit" ${disabled}>应用</button>
  </form>`;
}

function renderCard(device) {
  const presentation = statePresentation(device);
  const category = app.meta?.device_types?.[device.type]?.category || "controller";
  const cardState = device.error && !device.connected ? "error" : device.connected ? "connected" : device.running ? "running" : "stopped";
  const connectionText = device.connected ? "MQTT 在线" : device.running ? "连接中" : "已停止";
  return `<article class="device-card ${cardState} ${category === "sensor" ? "sensor" : ""}" data-card-id="${device.id}">
    <div class="card-head">
      <div class="device-glyph" aria-hidden="true">${TYPE_GLYPHS[device.type]}</div>
      <div class="device-title"><h3>${TYPE_LABELS[device.type]} #${device.id}</h3><p>${escapeHtml(roomLabel(device.room))} · ${escapeHtml(device.room)}</p></div>
      <span class="connection-label">${connectionText}</span>
    </div>
    <div class="state-panel">
      <div class="state-primary"><strong>${escapeHtml(presentation.primary)}</strong></div>
      <div class="state-details">${escapeHtml(friendlyError(device.error) || presentation.detail)}</div>
      <code class="topic" title="${escapeHtml(device.topic)}">${escapeHtml(device.topic)}</code>
    </div>
    <div class="control-panel">${controlsFor(device)}</div>
    <footer class="card-footer">
      <span class="activity">${formatTime(device.last_activity_at)}</span>
      <button class="text-button" type="button" data-toggle-device="${device.running ? "stop" : "start"}" data-device-id="${device.id}">${device.running ? "停止" : "启动"}</button>
      <button class="text-button danger" type="button" data-delete-device data-device-id="${device.id}">删除</button>
    </footer>
  </article>`;
}

function renderDevices() {
  updateOverview();
  const devices = app.devices.filter(matchesFilters);
  elements.grid.innerHTML = devices.map(renderCard).join("");
  elements.resultCount.textContent = `${devices.length} 台设备`;
  elements.empty.hidden = devices.length > 0;
}

async function loadDevices({ quiet = false } = {}) {
  if (app.loading) return;
  app.loading = true;
  try {
    const payload = await api("/api/devices");
    app.devices = payload.devices;
    renderDevices();
  } catch (error) {
    document.querySelector("#brokerState").className = "broker-state offline";
    document.querySelector("#brokerState span:last-child").textContent = "控制台服务不可用";
    if (!quiet) showToast(error.message, "error");
  } finally {
    app.loading = false;
  }
}

async function loadMeta() {
  app.meta = await api("/api/meta");
  const types = Object.keys(app.meta.device_types);
  elements.typeFilter.innerHTML = `<option value="">全部类型</option>${types.map((type) => `<option value="${type}">${TYPE_LABELS[type]}</option>`).join("")}`;
  elements.addType.innerHTML = types.map((type) => `<option value="${type}">${TYPE_LABELS[type]}</option>`).join("");
  refreshRoomOptions();
  updateAddPreview();
}

function refreshRoomOptions() {
  const rooms = [...new Set(app.devices.map((device) => device.room))].sort();
  const currentFilter = elements.roomFilter.value;
  elements.roomFilter.innerHTML = `<option value="">全部房间</option>${rooms.map((room) => `<option value="${escapeHtml(room)}">${escapeHtml(roomLabel(room))}</option>`).join("")}`;
  elements.roomFilter.value = currentFilter;
  document.querySelector("#roomOptions").innerHTML = rooms.map((room) => `<option value="${escapeHtml(room)}">`).join("");
}

function updateAddPreview() {
  const type = elements.addType.value || "device";
  const room = elements.addRoom.value.trim().toLowerCase() || "room";
  elements.topicPreview.textContent = `home/${room}/${type}`;
  elements.brandField.hidden = type !== "ac";
}

function payloadFromForm(form) {
  const params = {};
  for (const input of form.elements) {
    if (!input.name || input.disabled) continue;
    params[input.name] = input.hasAttribute("data-number") ? Number(input.value) : input.value;
  }
  return params;
}

async function sendOperation(deviceId, endpoint, payload, successMessage) {
  try {
    await api(`/api/devices/${deviceId}/${endpoint}`, { method: "POST", body: JSON.stringify(payload) });
    showToast(successMessage);
    setTimeout(() => loadDevices({ quiet: true }), 300);
  } catch (error) {
    showToast(error.message, "error");
  }
}

elements.grid.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-operation]");
  if (!form) return;
  event.preventDefault();
  const deviceId = form.dataset.deviceId;
  const params = payloadFromForm(form);
  if (form.dataset.operation === "sensor") {
    await sendOperation(deviceId, "sensor", params, "传感器读数已发布");
  } else {
    await sendOperation(deviceId, "command", { action: form.dataset.action, ...params }, "控制命令已发送");
  }
});

elements.grid.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const deviceId = button.dataset.deviceId;
  if (button.dataset.deviceCommand) {
    const payload = { action: button.dataset.deviceCommand };
    if (payload.action === "unlock") payload.auth_code = "simulator-dashboard";
    await sendOperation(deviceId, "command", payload, "控制命令已发送");
  } else if (button.dataset.sensorPresence) {
    await sendOperation(deviceId, "sensor", { presence: button.dataset.sensorPresence === "true" }, "人体感应状态已发布");
  } else if (button.dataset.toggleDevice) {
    await sendOperation(deviceId, button.dataset.toggleDevice, {}, button.dataset.toggleDevice === "start" ? "模拟设备已启动" : "模拟设备已停止");
  } else if (button.hasAttribute("data-delete-device")) {
    const device = app.devices.find((item) => String(item.id) === String(deviceId));
    if (!confirm(`删除 ${TYPE_LABELS[device.type]} #${device.id}？`)) return;
    try {
      await api(`/api/devices/${deviceId}`, { method: "DELETE" });
      showToast("模拟设备已删除");
      await loadDevices();
      refreshRoomOptions();
    } catch (error) {
      showToast(error.message, "error");
    }
  }
});

elements.addForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(elements.addForm);
  const payload = { type: formData.get("type"), room: String(formData.get("room")).trim().toLowerCase() };
  if (formData.get("id")) payload.id = Number(formData.get("id"));
  if (payload.type === "ac") payload.brand = formData.get("brand");
  try {
    await api("/api/devices", { method: "POST", body: JSON.stringify(payload) });
    elements.dialog.close();
    elements.addForm.reset();
    showToast("模拟设备已添加并启动");
    await loadDevices();
    refreshRoomOptions();
    updateAddPreview();
  } catch (error) {
    showToast(error.message, "error");
  }
});

for (const input of [elements.search, elements.roomFilter, elements.typeFilter, elements.stateFilter]) {
  input.addEventListener(input === elements.search ? "input" : "change", renderDevices);
}

document.querySelector("#addButton").addEventListener("click", () => elements.dialog.showModal());
document.querySelector("#closeDialogButton").addEventListener("click", () => elements.dialog.close());
document.querySelector("#cancelDialogButton").addEventListener("click", () => elements.dialog.close());
document.querySelector("#refreshButton").addEventListener("click", () => loadDevices());
elements.addType.addEventListener("change", updateAddPreview);
elements.addRoom.addEventListener("input", updateAddPreview);

async function initialize() {
  try {
    await Promise.all([loadMeta(), loadDevices()]);
    refreshRoomOptions();
  } catch (error) {
    showToast(error.message, "error");
  }
  setInterval(() => {
    if (!document.hidden && !elements.grid.matches(":focus-within")) loadDevices({ quiet: true });
  }, 3000);
}

initialize();
