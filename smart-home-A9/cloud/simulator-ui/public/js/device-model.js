const META_KEYS = new Set([
  "device_id",
  "room_id",
  "friendly_name",
  "room_name",
  "mqtt_topic",
  "brand",
  "online",
  "status_summary",
]);

const MESSAGE_META_KEYS = new Set([
  "device_id",
  "brand_command",
  "success",
]);

const READ_ONLY_TYPES = new Set([
  "temperature_sensor",
  "humidity_sensor",
  "pir_sensor",
]);

const SIMULATOR_DEVICE_COUNT = 17;

const MODE_LABELS = {
  cool: "制冷",
  heat: "制热",
  dehumidify: "除湿",
  fan_only: "送风",
  auto: "自动",
};


function boundedNumber(value, minimum, maximum, field) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < minimum || number > maximum) {
    throw new Error(`${field} must be between ${minimum} and ${maximum}`);
  }
  return number;
}


function statusFromAttributes(attributes) {
  return Object.fromEntries(
    Object.entries(attributes).filter(([key]) => !META_KEYS.has(key)),
  );
}


export function normalizeStates(payload) {
  if (!Array.isArray(payload)) {
    return [];
  }

  return payload.flatMap((item) => {
    if (!item || typeof item !== "object" || typeof item.entity_id !== "string") {
      return [];
    }

    const [type] = item.entity_id.split(".device_");
    const attributes = item.attributes && typeof item.attributes === "object"
      ? item.attributes
      : {};
    const id = Number(attributes.device_id);
    if (!Number.isInteger(id) || id < 1 || id > SIMULATOR_DEVICE_COUNT || !type) {
      return [];
    }

    return [{
      id,
      entityId: item.entity_id,
      type,
      name: String(attributes.friendly_name || item.entity_id),
      roomId: Number(attributes.room_id) || 0,
      roomName: String(attributes.room_name || ""),
      mqttTopic: String(attributes.mqtt_topic || ""),
      brand: String(attributes.brand || ""),
      online: attributes.online === true,
      state: String(item.state || "unknown"),
      statusSummary: String(attributes.status_summary || ""),
      status: statusFromAttributes(attributes),
      lastUpdated: String(item.last_updated || item.last_changed || ""),
    }];
  });
}


export function filterDevices(devices, filters) {
  const query = String(filters.query || "").trim().toLocaleLowerCase();

  return devices.filter((device) => {
    const searchable = `${device.name} ${device.mqttTopic}`.toLocaleLowerCase();
    const matchesQuery = !query || searchable.includes(query);
    const matchesRoom = filters.room === "all" || device.roomName === filters.room;
    const matchesType = filters.type === "all" || device.type === filters.type;
    const matchesOnline = filters.online === "all"
      || (filters.online === "online" ? device.online : !device.online);

    return matchesQuery && matchesRoom && matchesType && matchesOnline;
  });
}


export function applyMqttEvent(devices, event, now = new Date().toISOString()) {
  if (
    !event
    || typeof event.topic !== "string"
    || !event.payload
    || typeof event.payload !== "object"
  ) {
    return devices;
  }

  const mqttTopic = event.topic.replace(/\/(sensor|status|response)$/, "");
  const index = devices.findIndex((device) => device.mqttTopic === mqttTopic);
  if (index < 0) {
    return devices;
  }

  const rawStatus = event.topic.endsWith("/response")
    ? event.payload.state
    : event.payload;
  if (!rawStatus || typeof rawStatus !== "object" || Array.isArray(rawStatus)) {
    return devices;
  }

  const status = Object.fromEntries(
    Object.entries(rawStatus).filter(([key]) => !MESSAGE_META_KEYS.has(key)),
  );
  if (Object.keys(status).length === 0) {
    return devices;
  }

  const updated = devices.slice();
  const current = devices[index];
  updated[index] = {
    ...current,
    online: true,
    status: { ...current.status, ...status },
    lastUpdated: now,
  };
  return updated;
}


export function appendEvent(events, event, limit = 300) {
  return [...events, event].slice(-limit);
}


export function buildCommand(deviceType, draft) {
  if (READ_ONLY_TYPES.has(deviceType)) {
    throw new Error(`${deviceType} is read-only`);
  }

  if (deviceType === "light") {
    if (draft.power === "off") {
      return { action: "off", params: {} };
    }
    return {
      action: "on",
      params: {
        brightness: boundedNumber(draft.brightness, 0, 100, "brightness"),
        color: String(draft.color || "warm"),
      },
    };
  }

  if (deviceType === "ac") {
    if (draft.power === "off") {
      return { action: "off", params: {} };
    }
    return {
      action: "on",
      params: {
        temp: boundedNumber(draft.temp, 16, 30, "temp"),
        mode: String(draft.mode || "cool"),
        fan: String(draft.fan || "auto"),
        swing: String(draft.swing || "off"),
      },
    };
  }

  if (deviceType === "door_lock") {
    if (draft.locked !== false) {
      return { action: "lock", params: {} };
    }
    const authCode = String(draft.auth_code || "").trim();
    if (!authCode) {
      throw new Error("auth_code is required to unlock");
    }
    return { action: "unlock", params: { auth_code: authCode } };
  }

  if (deviceType === "curtain") {
    const position = boundedNumber(draft.position, 0, 100, "position");
    if (position === 0) {
      return { action: "close", params: {} };
    }
    if (position === 100) {
      return { action: "open", params: {} };
    }
    return { action: "set", params: { position } };
  }

  if (deviceType === "humidifier") {
    if (draft.power === "off") {
      return { action: "off", params: {} };
    }
    return {
      action: "on",
      params: {
        level: boundedNumber(draft.level, 1, 3, "level"),
        target_humidity: boundedNumber(
          draft.target_humidity,
          30,
          80,
          "target_humidity",
        ),
      },
    };
  }

  throw new Error(`Unsupported device type: ${deviceType}`);
}


export function formatDeviceStatus(device) {
  const status = device.status || {};

  if (device.type === "light") {
    return status.power === "on"
      ? `开启 · ${status.brightness ?? 0}%`
      : "已关闭";
  }
  if (device.type === "ac") {
    if (status.power !== "on") {
      return "待机";
    }
    return `${MODE_LABELS[status.mode] || status.mode || "运行"} · ${status.temp ?? 26}°C`;
  }
  if (device.type === "door_lock") {
    return status.locked === false ? "已解锁" : "已上锁";
  }
  if (device.type === "temperature_sensor") {
    return status.value == null ? "暂无读数" : `${status.value}°C`;
  }
  if (device.type === "humidity_sensor") {
    return status.value == null ? "暂无读数" : `${status.value}%`;
  }
  if (device.type === "pir_sensor") {
    return status.presence ? "检测到活动" : "无人活动";
  }
  if (device.type === "curtain") {
    const position = Number(status.position);
    if (!Number.isFinite(position)) {
      return "位置未知";
    }
    if (position <= 0) {
      return "已关闭";
    }
    if (position >= 100) {
      return "已全开";
    }
    return `开启 ${position}%`;
  }
  if (device.type === "humidifier") {
    return status.power === "on"
      ? `${status.level ?? 2} 档 · 目标 ${status.target_humidity ?? 60}%`
      : "已关闭";
  }

  return device.statusSummary || "状态未知";
}
