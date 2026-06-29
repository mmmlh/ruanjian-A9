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

export class Device {
  id: number = 0
  room_id: number = 0
  type: string = ''
  name: string = ''
  brand: string = ''
  mqtt_topic: string = ''
  status_json: string = ''
  room_name: string = ''
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
}

export class CommandParams {
  mode: string = ''
  fan: string = ''
  brightness: number = 0
  color: string = ''
  auth_code: string = ''
  temp: number = 0
  swing: string = ''
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

export class WSMessage {
  type: string = ''
  topic: string = ''
  payload: Record<string, Object> = {}
  device_id: number = 0
  room_id: number = 0
  data: Record<string, number> = {}
  timestamp: number = 0
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
      status.brightness = (brightnessVal as number)
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
      status.temp = (tempVal as number)
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
      status.locked = (lockedVal as boolean)
    }
    let presenceVal = obj['presence']
    if (presenceVal !== undefined && presenceVal !== null) {
      status.presence = (presenceVal as boolean)
    }
    let valueVal = obj['value']
    if (valueVal !== undefined && valueVal !== null) {
      status.value = (valueVal as number)
    }
    let unitVal = obj['unit']
    if (unitVal !== undefined && unitVal !== null) {
      status.unit = unitVal as string
    }
    return status
  } catch (e) {
    return new DeviceStatus()
  }
}
