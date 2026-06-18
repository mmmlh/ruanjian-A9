/**
 * 数据模型定义
 */

// 用户信息
export interface UserInfo {
  id: number
  username: string
  role: string
}

// 登录响应
export interface LoginResponse {
  token: string
  user: UserInfo
}

// 房间
export interface Room {
  id: number
  name: string
  floor: number
  description: string
  device_count: number
  devices?: Device[]
}

// 设备
export interface Device {
  id: number
  room_id: number
  type: string
  name: string
  brand: string | null
  mqtt_topic: string
  status_json: string
  room_name: string
  status?: DeviceStatus
}

// 设备状态
export interface DeviceStatus {
  power?: string
  brightness?: number
  color?: string
  mode?: string
  temp?: number
  fan?: string
  swing?: string
  brand?: string
  locked?: boolean
  presence?: boolean
  value?: number
  unit?: string
}

// 控制指令
export interface CommandRequest {
  action: string
  params?: Record<string, Object>
}

// 联动规则
export interface AutomationRule {
  id: number
  name: string
  condition_json: string
  action_json: string
  enabled: number
}

// WebSocket 消息
export interface WSMessage {
  type: string
  topic?: string
  payload?: Object
  device_id?: number
  room_id?: number
  data?: Object
  timestamp?: number
}
