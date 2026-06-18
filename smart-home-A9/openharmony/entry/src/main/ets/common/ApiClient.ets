/**
 * HTTP 请求封装 — 调用后端 REST API
 */
import { http } from '@kit.NetworkKit'
import { preferences } from '@kit.ArkData'

// 服务器地址（部署时修改为实际 IP）
// 本地开发使用 localhost，部署后改为阿里云 IP
const BASE_URL = 'http://localhost:8000'

// 存储 token
let cachedToken: string = ''

export async function setToken(token: string): Promise<void> {
  cachedToken = token
}

export function getToken(): string {
  return cachedToken
}

export function getBaseUrl(): string {
  return BASE_URL
}

/**
 * 通用请求方法
 */
async function request<T>(method: http.RequestMethod, path: string, data?: Object): Promise<T> {
  const httpRequest = http.create()
  const url = `${BASE_URL}${path}`

  const options: http.HttpRequestOptions = {
    method: method,
    header: {
      'Content-Type': 'application/json',
    },
    connectTimeout: 10000,
    readTimeout: 10000,
  }

  if (cachedToken) {
    options.header!['Authorization'] = `Bearer ${cachedToken}`
  }

  if (data && (method === http.RequestMethod.POST || method === http.RequestMethod.PUT)) {
    options.extraData = JSON.stringify(data)
  }

  try {
    const response = await httpRequest.request(url, options)
    if (response.responseCode === 200) {
      return JSON.parse(response.result as string) as T
    } else {
      const err = JSON.parse(response.result as string)
      throw new Error(err.detail || `请求失败: ${response.responseCode}`)
    }
  } catch (err) {
    throw err
  } finally {
    httpRequest.destroy()
  }
}

// ── 认证 API ──

export async function login(username: string, password: string) {
  const result = await request<{
    token: string
    user: { id: number; username: string; role: string }
  }>(http.RequestMethod.POST, '/api/auth/login', { username, password })
  await setToken(result.token)
  return result
}

export async function register(username: string, password: string) {
  const result = await request<{
    token: string
    user: { id: number; username: string; role: string }
  }>(http.RequestMethod.POST, '/api/auth/register', { username, password })
  await setToken(result.token)
  return result
}

export async function getMe() {
  return request<{ id: number; username: string; role: string }>(
    http.RequestMethod.GET, '/api/auth/me'
  )
}

// ── 房间 API ──

export async function getRooms() {
  return request<Array<{
    id: number; name: string; floor: number; description: string; device_count: number
  }>>(http.RequestMethod.GET, '/api/rooms')
}

export async function getRoom(roomId: number) {
  return request<{
    id: number; name: string; devices: Array<Object>
  }>(http.RequestMethod.GET, `/api/rooms/${roomId}`)
}

// ── 设备 API ──

export async function getDevices(roomId?: number, type?: string) {
  let path = '/api/devices'
  const params: string[] = []
  if (roomId) params.push(`room_id=${roomId}`)
  if (type) params.push(`type=${type}`)
  if (params.length) path += '?' + params.join('&')
  return request<Array<Object>>(http.RequestMethod.GET, path)
}

export async function getDevice(deviceId: number) {
  return request<Object>(http.RequestMethod.GET, `/api/devices/${deviceId}`)
}

export async function sendCommand(deviceId: number, action: string, params?: Record<string, Object>) {
  return request<{ success: boolean }>(
    http.RequestMethod.POST,
    `/api/devices/${deviceId}/command`,
    { action, params }
  )
}

// ── 规则 API ──

export async function getRules() {
  return request<Array<Object>>(http.RequestMethod.GET, '/api/rules')
}

export async function toggleRule(ruleId: number) {
  return request<Object>(http.RequestMethod.POST, `/api/rules/${ruleId}/toggle`)
}
