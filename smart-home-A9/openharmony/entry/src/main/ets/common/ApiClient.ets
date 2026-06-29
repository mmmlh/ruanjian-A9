import { http } from '@kit.NetworkKit'
import { extractAesKey } from './TokenUtil'
import { Room, Device, UserInfo, LoginResponse } from '../model/DeviceModel'

const BASE_URL = 'http://localhost:8000'

class LoginRequest {
  username: string = ''
  password: string = ''
}

class RegisterRequest {
  username: string = ''
  password: string = ''
  role: string = ''
}

class CommandRequest {
  action: string = ''
  params: Object | null = null
}

let cachedToken: string = ''
let cachedAesKey: string = ''

export async function setToken(token: string): Promise<void> {
  cachedToken = token
  cachedAesKey = extractAesKey(token)
}

export function getToken(): string {
  return cachedToken
}

export function getAesKey(): string {
  return cachedAesKey
}

export function getBaseUrl(): string {
  return BASE_URL
}

class ApiResponse<T> {
  data: T | null = null
  error: string = ''
  code: number = 0
}

async function request<T>(method: http.RequestMethod, path: string, data?: Object): Promise<T> {
  let httpRequest = http.createHttp()
  let url = `${BASE_URL}${path}`

  let headers: Record<string, string> = {
    'Content-Type': 'application/json'
  }

  if (cachedToken) {
    headers['Authorization'] = `Bearer ${cachedToken}`
  }

  let options: http.HttpRequestOptions = {
    method: method,
    header: headers,
    connectTimeout: 10000,
    readTimeout: 10000,
  }

  if (data && (method === http.RequestMethod.POST || method === http.RequestMethod.PUT)) {
    options.extraData = JSON.stringify(data)
  }

  try {
    let response = await httpRequest.request(url, options)
    if (response.responseCode === 200) {
      let result: T = JSON.parse(response.result as string) as T
      return result
    } else {
      let errObj: Record<string, Object> = JSON.parse(response.result as string) as Record<string, Object>
      let detail = errObj['detail']
      throw new Error((detail !== undefined && detail !== null ? detail as string : `请求失败: ${response.responseCode}`))
    }
  } catch (err) {
    if (err instanceof Error) {
      throw err
    } else {
      throw new Error('Unknown error')
    }
  } finally {
    httpRequest.destroy()
  }
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  let req = new LoginRequest()
  req.username = username
  req.password = password
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.POST, '/api/auth/login', req
  )
  let tokenVal = result['token']
  let userObj = result['user']
  let resp = new LoginResponse()
  if (tokenVal !== undefined && tokenVal !== null) {
    resp.token = tokenVal as string
  }
  if (userObj !== undefined && userObj !== null) {
    let userRecord = userObj as Record<string, Object>
    resp.user = new UserInfo()
    let uid = userRecord['id']
    if (uid !== undefined && uid !== null) resp.user.id = uid as number
    let uname = userRecord['username']
    if (uname !== undefined && uname !== null) resp.user.username = uname as string
    let urole = userRecord['role']
    if (urole !== undefined && urole !== null) resp.user.role = urole as string
  }
  await setToken(resp.token)
  return resp
}

export async function register(username: string, password: string): Promise<LoginResponse> {
  let req = new RegisterRequest()
  req.username = username
  req.password = password
  req.role = 'user'
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.POST, '/api/auth/register', req
  )
  let tokenVal = result['token']
  let userObj = result['user']
  let resp = new LoginResponse()
  if (tokenVal !== undefined && tokenVal !== null) {
    resp.token = tokenVal as string
  }
  if (userObj !== undefined && userObj !== null) {
    let userRecord = userObj as Record<string, Object>
    resp.user = new UserInfo()
    let uid = userRecord['id']
    if (uid !== undefined && uid !== null) resp.user.id = uid as number
    let uname = userRecord['username']
    if (uname !== undefined && uname !== null) resp.user.username = uname as string
    let urole = userRecord['role']
    if (urole !== undefined && urole !== null) resp.user.role = urole as string
  }
  await setToken(resp.token)
  return resp
}

export async function getMe(): Promise<UserInfo> {
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.GET, '/api/auth/me'
  )
  let info = new UserInfo()
  let uid = result['id']
  if (uid !== undefined && uid !== null) info.id = uid as number
  let uname = result['username']
  if (uname !== undefined && uname !== null) info.username = uname as string
  let urole = result['role']
  if (urole !== undefined && urole !== null) info.role = urole as string
  return info
}

export async function getRooms(): Promise<Room[]> {
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, '/api/rooms')
  let rooms: Room[] = []
  for (let i = 0; i < result.length; i++) {
    let item = result[i] as Record<string, Object>
    let room = new Room()
    let rid = item['id']
    if (rid !== undefined && rid !== null) room.id = rid as number
    let rname = item['name']
    if (rname !== undefined && rname !== null) room.name = rname as string
    let rfloor = item['floor']
    if (rfloor !== undefined && rfloor !== null) room.floor = rfloor as number
    let rdesc = item['description']
    if (rdesc !== undefined && rdesc !== null) room.description = rdesc as string
    let rcount = item['device_count']
    if (rcount !== undefined && rcount !== null) room.device_count = rcount as number
    rooms.push(room)
  }
  return rooms
}

export async function getRoom(roomId: number): Promise<Room> {
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.GET, `/api/rooms/${roomId}`
  )
  let room = new Room()
  let rid = result['id']
  if (rid !== undefined && rid !== null) room.id = rid as number
  let rname = result['name']
  if (rname !== undefined && rname !== null) room.name = rname as string
  return room
}

export async function getDevices(roomId?: number, type?: string): Promise<Device[]> {
  let path = '/api/devices'
  let params: string[] = []
  if (roomId) params.push(`room_id=${roomId}`)
  if (type) params.push(`type=${type}`)
  if (params.length) path += '?' + params.join('&')
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, path)
  let devices: Device[] = []
  for (let i = 0; i < result.length; i++) {
    let item = result[i] as Record<string, Object>
    let device = new Device()
    let did = item['id']
    if (did !== undefined && did !== null) device.id = did as number
    let droomId = item['room_id']
    if (droomId !== undefined && droomId !== null) device.room_id = droomId as number
    let dtype = item['type']
    if (dtype !== undefined && dtype !== null) device.type = dtype as string
    let dname = item['name']
    if (dname !== undefined && dname !== null) device.name = dname as string
    let dbrand = item['brand']
    if (dbrand !== undefined && dbrand !== null) device.brand = dbrand as string
    let dtopic = item['mqtt_topic']
    if (dtopic !== undefined && dtopic !== null) device.mqtt_topic = dtopic as string
    let dstatus = item['status_json']
    if (dstatus !== undefined && dstatus !== null) device.status_json = dstatus as string
    let droomName = item['room_name']
    if (droomName !== undefined && droomName !== null) device.room_name = droomName as string
    devices.push(device)
  }
  return devices
}

export async function getDevice(deviceId: number): Promise<Device> {
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.GET, `/api/devices/${deviceId}`
  )
  let device = new Device()
  let did = result['id']
  if (did !== undefined && did !== null) device.id = did as number
  let dtype = result['type']
  if (dtype !== undefined && dtype !== null) device.type = dtype as string
  let dname = result['name']
  if (dname !== undefined && dname !== null) device.name = dname as string
  return device
}

export async function sendCommand(deviceId: number, action: string, params?: Object): Promise<boolean> {
  let req = new CommandRequest()
  req.action = action
  req.params = params !== undefined ? params : null
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.POST,
    `/api/devices/${deviceId}/command`,
    req
  )
  let success = result['success']
  if (success !== undefined && success !== null) {
    return success as boolean
  }
  return false
}

export async function getRules(): Promise<Array<Object>> {
  return request<Array<Object>>(http.RequestMethod.GET, '/api/rules')
}

export async function toggleRule(ruleId: number): Promise<Object> {
  return request<Object>(http.RequestMethod.POST, `/api/rules/${ruleId}/toggle`)
}

export async function getScenes(): Promise<Array<Object>> {
  return request<Array<Object>>(http.RequestMethod.GET, '/api/scenes')
}

export async function executeScene(sceneId: number): Promise<Object> {
  return request<Object>(http.RequestMethod.POST, `/api/scenes/${sceneId}/execute`)
}
