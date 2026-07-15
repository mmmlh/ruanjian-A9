export class UserInfo {
  id: number = 0
  username: string = ''
  role: string = ''
}

export class LoginResponse {
  token: string = ''
  user: UserInfo = new UserInfo()
}

export class Room {
  id: number = 0
  name: string = ''
  floor: number = 0
  description: string = ''
  device_count: number = 0
  devices: Device[] = []
}

export class HAEntityState {
  attributes: Record<string, Object> = {}
  entity_id: string = ''
  last_changed: string = ''
  last_updated: string = ''
  state: string = ''
}

export class Device {
  id: number = 0
  room_id: number = 0
  type: string = ''
  name: string = ''
  brand: string = ''
  mqtt_topic: string = ''
  status_json: string = ''
  room_name: string = ''
  updated_at: string = ''
  last_seen_at: string = ''
  status_summary: string = ''
  online: boolean = false
}

export class DeviceStatus {
  power: string = ''
  brightness: number = 0
  color: string = ''
  mode: string = ''
  temp: number = 0
  fan: string = ''
  swing: string = ''
  brand: string = ''
  locked: boolean = false
  presence: boolean = false
  value: number = 0
  unit: string = ''
  position: number = 0
  level: number = 0
  target_humidity: number = 0
  power_watts: number = 0
  total_kwh: number = 0
}

export class CommandParams {
  mode: string = ''
  fan: string = ''
  brightness: number = 0
  color: string = ''
  auth_code: string = ''
  temp: number = 0
  swing: string = ''
  position: number = 0
  level: number = 0
  target_humidity: number = 0
  presence: boolean = false
}

export class CommandRequest {
  action: string = ''
  params: Record<string, Object> = {}
}

export class AutomationRule {
  id: number = 0
  name: string = ''
  condition_json: string = ''
  action_json: string = ''
  enabled: number = 0
}

export class Scene {
  id: number = 0
  name: string = ''
  icon: string = ''
  description: string = ''
  actions_json: string = ''
}

export class WSMessage {
  type: string = ''
  topic: string = ''
  payload: Record<string, Object> = {}
  device_id: number = 0
  room_id: number = 0
  data: Record<string, number> = {}
  timestamp: number = 0
}

export class DiscoveredDevice {
  id: string = ''
  room: string = ''
  room_hint: string = ''
  type: string = ''
  name: string = ''
  brand: string = ''
  mqtt_topic: string = ''
  status: Record<string, Object> = {}
  status_summary: string = ''
  last_seen_at: string = ''
  online: boolean = true
}

export class DashboardStats {
  total_devices: number = 0
  online_devices: number = 0
  offline_devices: number = 0
  total_rooms: number = 0
  total_scenes: number = 0
}

export class SensorDataItem {
  id: number = 0
  device_id: number = 0
  data_type: string = ''
  value: number = 0
  extra_json: string = ''
  timestamp: string = ''
}

export class LogItem {
  id: number = 0
  device_id: number = 0
  event_type: string = ''
  title: string = ''
  action: string = ''
  detail: string = ''
  source: string = ''
  user_id: number = 0
  timestamp: string = ''
}

export class DashboardSummary {
  rooms: Room[] = []
  devices: Device[] = []
  scenes: Scene[] = []
  recent_logs: LogItem[] = []
  stats: DashboardStats = new DashboardStats()
}

export class RuleTriggerOption {
  label: string = ''
  value: string = ''
  field: string = ''
  room_name: string = ''
}

export class RuleOperatorOption {
  label: string = ''
  value: string = ''
}

export class RuleTargetOption {
  device_id: number = 0
  label: string = ''
  type: string = ''
  room_name: string = ''
  actions: string[] = []
}

export class RuleOptions {
  triggers: RuleTriggerOption[] = []
  operators: RuleOperatorOption[] = []
  actions: Record<string, string[]> = {}
  targets: RuleTargetOption[] = []
}

export class ServiceCallResult {
  success: boolean = false
  message: string = ''
  entity_id: string = ''
  action: string = ''
  changed_states: HAEntityState[] = []
  service_response: Record<string, Object> = {}
  executed_at: string = ''
}

export function parseDeviceStatus(json: string): DeviceStatus {
  try {
    let obj: Record<string, Object> = JSON.parse(json) as Record<string, Object>
    let status = new DeviceStatus()
    let powerVal = obj['power']
    if (powerVal !== undefined && powerVal !== null) {
      status.power = powerVal as string
    }
    let brightnessVal = obj['brightness']
    if (brightnessVal !== undefined && brightnessVal !== null) {
      status.brightness = brightnessVal as number
    }
    let colorVal = obj['color']
    if (colorVal !== undefined && colorVal !== null) {
      status.color = colorVal as string
    }
    let modeVal = obj['mode']
    if (modeVal !== undefined && modeVal !== null) {
      status.mode = modeVal as string
    }
    let tempVal = obj['temp']
    if (tempVal !== undefined && tempVal !== null) {
      status.temp = tempVal as number
    }
    let fanVal = obj['fan']
    if (fanVal !== undefined && fanVal !== null) {
      status.fan = fanVal as string
    }
    let swingVal = obj['swing']
    if (swingVal !== undefined && swingVal !== null) {
      status.swing = swingVal as string
    }
    let brandVal = obj['brand']
    if (brandVal !== undefined && brandVal !== null) {
      status.brand = brandVal as string
    }
    let lockedVal = obj['locked']
    if (lockedVal !== undefined && lockedVal !== null) {
      status.locked = lockedVal as boolean
    }
    let presenceVal = obj['presence']
    if (presenceVal !== undefined && presenceVal !== null) {
      status.presence = presenceVal as boolean
    }
    let valueVal = obj['value']
    if (valueVal !== undefined && valueVal !== null) {
      status.value = valueVal as number
    }
    let unitVal = obj['unit']
    if (unitVal !== undefined && unitVal !== null) {
      status.unit = unitVal as string
    }
    let positionVal = obj['position']
    if (positionVal !== undefined && positionVal !== null) {
      status.position = positionVal as number
    }
    let levelVal = obj['level']
    if (levelVal !== undefined && levelVal !== null) {
      status.level = levelVal as number
    }
    let targetHumVal = obj['target_humidity']
    if (targetHumVal !== undefined && targetHumVal !== null) {
      status.target_humidity = targetHumVal as number
    }
    let wattsVal = obj['power_watts']
    if (wattsVal !== undefined && wattsVal !== null) {
      status.power_watts = wattsVal as number
    }
    let kwhVal = obj['total_kwh']
    if (kwhVal !== undefined && kwhVal !== null) {
      status.total_kwh = kwhVal as number
    }
    return status
  } catch (e) {
    return new DeviceStatus()
  }
}
