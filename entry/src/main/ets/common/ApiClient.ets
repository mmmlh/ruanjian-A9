import http from '@ohos.net.http'
import { extractAesKey } from './TokenUtil'
import { aesEncrypt } from './CryptoUtil'
import { DEFAULT_SERVER_URL, loadServerUrl, saveServerUrl, saveAuthData, loadAuthData, clearAuthData } from './SecureStorage'
import { UiText } from './UiText'
import {
  Room,
  Device,
  UserInfo,
  LoginResponse,
  Scene,
  AutomationRule,
  HAEntityState,
  DiscoveredDevice,
  DashboardSummary,
  DashboardStats,
  SensorDataItem,
  LogItem,
  RuleOptions,
  RuleTriggerOption,
  RuleOperatorOption,
  RuleTargetOption,
  ServiceCallResult
} from '../model/DeviceModel'

let baseUrl: string = ''

class LoginRequest {
  username: string = ''
  password: string = ''
}

class RegisterRequest {
  username: string = ''
  password: string = ''
  role: string = ''
}

class EncryptedParams {
  encrypted: string = ''
}

export class CreateDeviceParams {
  room_id: number = 0
  type: string = ''
  name: string = ''
  brand: string = ''
  mqtt_topic: string = ''
}

export class ChangePasswordRequest {
  old_password: string = ''
  new_password: string = ''
}

let cachedToken: string = ''
let cachedAesKey: string = ''
let sessionExpiredHandler: (() => void) | null = null
let sessionInvalidating: boolean = false

function stringifyUnknownError(err: Object): string {
  if (err === null || err === undefined) {
    return ''
  }
  try {
    return JSON.stringify(err)
  } catch (stringifyErr) {
    return ''
  }
}

function extractTransportErrorMessage(err: Object): string {
  if (err instanceof Error) {
    return UiText.mapTransportMessage(err.message)
  }

  let raw = stringifyUnknownError(err)
  return UiText.mapTransportMessage(raw)
}

function mapApiErrorMessage(detail: string): string {
  return UiText.mapApiDetail(detail)
}

function readString(record: Record<string, Object>, key: string, defaultValue: string = ''): string {
  let value = record[key]
  if (value === undefined || value === null) {
    return defaultValue
  }
  return value as string
}

function readNumber(record: Record<string, Object>, key: string, defaultValue: number = 0): number {
  let value = record[key]
  if (value === undefined || value === null) {
    return defaultValue
  }
  return value as number
}

function readBoolean(record: Record<string, Object>, key: string, defaultValue: boolean = false): boolean {
  let value = record[key]
  if (value === undefined || value === null) {
    return defaultValue
  }
  return value as boolean
}

function readObject(record: Record<string, Object>, key: string): Record<string, Object> {
  let value = record[key]
  if (value === undefined || value === null) {
    return {}
  }
  return value as Record<string, Object>
}

function readObjectArray(record: Record<string, Object>, key: string): Array<Object> {
  let value = record[key]
  if (value === undefined || value === null) {
    return []
  }
  return value as Array<Object>
}

function mapUserInfo(record: Record<string, Object>): UserInfo {
  let user = new UserInfo()
  user.id = readNumber(record, 'id')
  user.username = readString(record, 'username')
  user.role = readString(record, 'role')
  return user
}

function mapRoom(record: Record<string, Object>): Room {
  let room = new Room()
  room.id = readNumber(record, 'id')
  room.name = readString(record, 'name')
  room.floor = readNumber(record, 'floor')
  room.description = readString(record, 'description')
  room.device_count = readNumber(record, 'device_count')
  return room
}

function mapDevice(record: Record<string, Object>): Device {
  let device = new Device()
  device.id = readNumber(record, 'id')
  device.room_id = readNumber(record, 'room_id')
  device.type = readString(record, 'type')
  device.name = readString(record, 'name')
  device.brand = readString(record, 'brand')
  device.mqtt_topic = readString(record, 'mqtt_topic')
  device.status_json = readString(record, 'status_json')
  device.room_name = readString(record, 'room_name')
  device.updated_at = readString(record, 'updated_at')
  device.last_seen_at = readString(record, 'last_seen_at', device.updated_at)
  device.status_summary = readString(record, 'status_summary')
  device.online = readBoolean(record, 'online', false)
  return device
}

function mapState(record: Record<string, Object>): HAEntityState {
  let st = new HAEntityState()
  st.entity_id = readString(record, 'entity_id')
  st.state = readString(record, 'state')
  st.attributes = readObject(record, 'attributes')
  st.last_changed = readString(record, 'last_changed')
  st.last_updated = readString(record, 'last_updated')
  return st
}

function mapScene(record: Record<string, Object>): Scene {
  let scene = new Scene()
  scene.id = readNumber(record, 'id')
  scene.name = readString(record, 'name')
  scene.icon = readString(record, 'icon')
  scene.description = readString(record, 'description')
  scene.actions_json = readString(record, 'actions_json')
  return scene
}

function mapRule(record: Record<string, Object>): AutomationRule {
  let rule = new AutomationRule()
  rule.id = readNumber(record, 'id')
  rule.name = readString(record, 'name')
  rule.condition_json = readString(record, 'condition_json')
  rule.action_json = readString(record, 'action_json')
  rule.enabled = readNumber(record, 'enabled')
  return rule
}

function mapDiscoveredDevice(record: Record<string, Object>): DiscoveredDevice {
  let device = new DiscoveredDevice()
  device.id = readString(record, 'id')
  device.room = readString(record, 'room')
  device.room_hint = readString(record, 'room_hint')
  device.type = readString(record, 'type')
  device.name = readString(record, 'name')
  device.brand = readString(record, 'brand')
  device.mqtt_topic = readString(record, 'mqtt_topic')
  device.status = readObject(record, 'status')
  device.status_summary = readString(record, 'status_summary')
  device.last_seen_at = readString(record, 'last_seen_at')
  device.online = readBoolean(record, 'online', true)
  return device
}

function mapLogItem(record: Record<string, Object>): LogItem {
  let item = new LogItem()
  item.id = readNumber(record, 'id')
  item.device_id = readNumber(record, 'device_id')
  item.event_type = readString(record, 'event_type')
  item.title = readString(record, 'title')
  item.action = readString(record, 'action')
  item.detail = readString(record, 'detail')
  item.source = readString(record, 'source')
  item.user_id = readNumber(record, 'user_id')
  item.timestamp = readString(record, 'timestamp')
  return item
}

function mapSensorDataItem(record: Record<string, Object>): SensorDataItem {
  let item = new SensorDataItem()
  item.id = readNumber(record, 'id')
  item.device_id = readNumber(record, 'device_id')
  item.data_type = readString(record, 'data_type')
  item.value = readNumber(record, 'value')
  item.extra_json = readString(record, 'extra_json')
  item.timestamp = readString(record, 'timestamp')
  return item
}

function mapDashboardStats(record: Record<string, Object>): DashboardStats {
  let stats = new DashboardStats()
  stats.total_devices = readNumber(record, 'total_devices')
  stats.online_devices = readNumber(record, 'online_devices')
  stats.offline_devices = readNumber(record, 'offline_devices')
  stats.total_rooms = readNumber(record, 'total_rooms')
  stats.total_scenes = readNumber(record, 'total_scenes')
  return stats
}

function mapStringArray(values: Array<Object>): string[] {
  let mapped: string[] = []
  for (let i = 0; i < values.length; i++) {
    mapped.push(values[i] as string)
  }
  return mapped
}

export async function initApiClient(): Promise<void> {
  let saved = await loadAuthData()
  if (saved[0]) {
    cachedToken = saved[0]
    cachedAesKey = saved[1]
  }
  let serverUrl = await loadServerUrl()
  baseUrl = serverUrl || DEFAULT_SERVER_URL
}

export function setBaseUrl(url: string): void {
  if (!url.startsWith('http')) {
    url = 'http://' + url
  }
  baseUrl = url
  saveServerUrl(url)
}

export function getBaseUrl(): string {
  return baseUrl
}

export async function setToken(token: string): Promise<void> {
  if (!token.trim()) {
    throw new Error(UiText.invalidAuthResponse)
  }
  cachedToken = token
  cachedAesKey = extractAesKey(token)
  sessionInvalidating = false
  await saveAuthData(token, cachedAesKey)
}

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  sessionExpiredHandler = handler
}

async function invalidateSession(): Promise<void> {
  if (sessionInvalidating) {
    return
  }
  sessionInvalidating = true
  cachedToken = ''
  cachedAesKey = ''
  await clearAuthData()
  if (sessionExpiredHandler) {
    sessionExpiredHandler()
  }
}

export function getToken(): string {
  return cachedToken
}

export function getAesKey(): string {
  return cachedAesKey
}

async function request<T>(method: http.RequestMethod, path: string, data?: Object): Promise<T> {
  let httpRequest = http.createHttp()
  let url = `${baseUrl}${path}`

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
    readTimeout: 10000
  }

  if (data && (method === http.RequestMethod.POST || method === http.RequestMethod.PUT)) {
    options.extraData = JSON.stringify(data)
  }

  try {
    let response = await httpRequest.request(url, options)
    if (response.responseCode >= 200 && response.responseCode < 300) {
      let raw = response.result as string
      if (!raw) {
        throw new Error(UiText.emptyResponseBody)
      }
      return JSON.parse(raw) as T
    }

    if ((response.responseCode === 401 || response.responseCode === 403) && cachedToken) {
      await invalidateSession()
      throw new Error(UiText.sessionExpired)
    }

    let detailMessage = UiText.requestFailed(response.responseCode)
    let resultText = response.result as string
    if (resultText) {
      try {
        let errObj: Record<string, Object> = JSON.parse(resultText) as Record<string, Object>
        let detail = errObj['detail']
        let message = errObj['message']
        if (typeof detail === 'string') {
          detailMessage = mapApiErrorMessage(detail)
        } else if (typeof message === 'string') {
          detailMessage = mapApiErrorMessage(message)
        }
      } catch (parseErr) {
        detailMessage = UiText.requestFailed(response.responseCode)
      }
    }
    throw new Error(detailMessage)
  } catch (err) {
    if (err instanceof Error) {
      throw new Error(extractTransportErrorMessage(err as Object))
    }
    throw new Error(extractTransportErrorMessage(err as Object))
  } finally {
    httpRequest.destroy()
  }
}

namespace LoginApi {
  let loginPath: string = '/api/login'
  export function setPath(p: string): void { loginPath = p }
  export function path(): string { return loginPath }
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  let req = new LoginRequest()
  req.username = username
  req.password = password
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.POST, LoginApi.path(), req
  )
  let resp = new LoginResponse()
  resp.token = readString(result, 'token')
  if (!resp.token.trim()) {
    throw new Error(UiText.invalidAuthResponse)
  }
  let userObj = result['user']
  if (userObj !== undefined && userObj !== null) {
    resp.user = mapUserInfo(userObj as Record<string, Object>)
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
  let resp = new LoginResponse()
  resp.token = readString(result, 'token')
  if (!resp.token.trim()) {
    throw new Error(UiText.invalidAuthResponse)
  }
  let userObj = result['user']
  if (userObj !== undefined && userObj !== null) {
    resp.user = mapUserInfo(userObj as Record<string, Object>)
  }
  await setToken(resp.token)
  return resp
}

export async function getMe(): Promise<UserInfo> {
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.GET, '/api/auth/me'
  )
  return mapUserInfo(result)
}

export async function getRooms(): Promise<Room[]> {
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, '/api/rooms')
  let rooms: Room[] = []
  for (let i = 0; i < result.length; i++) {
    rooms.push(mapRoom(result[i] as Record<string, Object>))
  }
  return rooms
}

export async function getRoom(roomId: number): Promise<Room> {
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.GET, `/api/rooms/${roomId}`
  )
  return mapRoom(result)
}

export async function getStates(): Promise<HAEntityState[]> {
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, '/api/states')
  let states: HAEntityState[] = []
  for (let i = 0; i < result.length; i++) {
    states.push(mapState(result[i] as Record<string, Object>))
  }
  return states
}

export function stateToDevice(st: HAEntityState): Device {
  let device = new Device()
  let attrs = st.attributes
  let did = attrs['device_id']
  if (did !== undefined && did !== null) device.id = did as number
  let rid = attrs['room_id']
  if (rid !== undefined && rid !== null) device.room_id = rid as number
  let fname = attrs['friendly_name']
  if (fname !== undefined && fname !== null) device.name = fname as string
  let mqtt = attrs['mqtt_topic']
  if (mqtt !== undefined && mqtt !== null) device.mqtt_topic = mqtt as string
  let rname = attrs['room_name']
  if (rname !== undefined && rname !== null) device.room_name = rname as string
  let brand = attrs['brand']
  if (brand !== undefined && brand !== null) device.brand = brand as string
  let updated = st.last_updated
  if (updated) {
    device.updated_at = updated
  }
  let eid = st.entity_id
  let dotIdx = eid.indexOf('.')
  if (dotIdx > 0) {
    device.type = eid.substring(0, dotIdx)
  }
  let metaKeys = ['device_id', 'room_id', 'friendly_name', 'room_name', 'mqtt_topic', 'brand']
  let statusObj: Record<string, Object> = {}
  let attrKeys = Object.keys(attrs)
  for (let j = 0; j < attrKeys.length; j++) {
    let key = attrKeys[j]
    let isMeta = false
    for (let k = 0; k < metaKeys.length; k++) {
      if (metaKeys[k] === key) {
        isMeta = true
        break
      }
    }
    if (!isMeta) {
      statusObj[key] = attrs[key]
    }
  }
  device.status_json = JSON.stringify(statusObj)
  return device
}

export function statesToDevices(states: HAEntityState[]): Device[] {
  let devices: Device[] = []
  for (let i = 0; i < states.length; i++) {
    devices.push(stateToDevice(states[i]))
  }
  return devices
}

export async function getDevicesFromStates(type?: string, roomId?: number): Promise<Device[]> {
  let devices = statesToDevices(await getStates())
  let filtered: Device[] = []
  for (let i = 0; i < devices.length; i++) {
    let device = devices[i]
    if (type && device.type !== type) {
      continue
    }
    if (roomId !== undefined && roomId !== 0 && device.room_id !== roomId) {
      continue
    }
    filtered.push(device)
  }
  return filtered
}

export async function getDevices(roomId?: number, type?: string): Promise<Device[]> {
  let path = '/api/devices'
  let queries: string[] = []
  if (roomId !== undefined && roomId !== 0) {
    queries.push('room_id=' + roomId.toString())
  }
  if (type) {
    queries.push('type=' + encodeURIComponent(type))
  }
  if (queries.length > 0) {
    path += '?' + queries.join('&')
  }

  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, path)
  let devices: Device[] = []
  for (let i = 0; i < result.length; i++) {
    devices.push(mapDevice(result[i] as Record<string, Object>))
  }
  return devices
}

export async function getDevicesForUi(roomId?: number, type?: string): Promise<Device[]> {
  return getDevices(roomId, type)
}

export async function createDevice(params: CreateDeviceParams): Promise<Record<string, Object>> {
  let body: Record<string, Object> = {
    'room_id': params.room_id,
    'type': params.type,
    'name': params.name,
    'brand': params.brand,
    'mqtt_topic': params.mqtt_topic
  }
  return request<Record<string, Object>>(http.RequestMethod.POST, '/api/devices', body)
}

export async function updateDeviceName(deviceId: number, name: string, brand: string): Promise<Record<string, Object>> {
  let body: Record<string, Object> = { 'name': name, 'brand': brand }
  return request<Record<string, Object>>(http.RequestMethod.PUT, `/api/devices/${deviceId}`, body)
}

export async function deleteDevice(deviceId: number): Promise<Record<string, Object>> {
  return request<Record<string, Object>>(http.RequestMethod.DELETE, `/api/devices/${deviceId}`)
}

export async function getDevice(deviceId: number): Promise<Device> {
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.GET, `/api/devices/${deviceId}`
  )
  return mapDevice(result)
}

export async function callService(entityId: string, action: string, params?: Object): Promise<ServiceCallResult> {
  let aesKey = getAesKey()
  if (!aesKey) {
    throw new Error(UiText.secureCommandUnavailable)
  }

  let cmd: Record<string, Object> = { 'action': action }
  if (params) {
    cmd['params'] = params
  }
  let encrypted = ''
  try {
    encrypted = await aesEncrypt(JSON.stringify(cmd), aesKey)
  } catch (err) {
    throw new Error(UiText.secureCommandUnavailable)
  }
  let encryptedParams = new EncryptedParams()
  encryptedParams.encrypted = encrypted
  let body: Record<string, Object> = {
    'entity_id': entityId,
    'action': 'encrypted',
    'params': encryptedParams
  }

  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.POST,
    '/api/services',
    body
  )

  let serviceResult = new ServiceCallResult()
  serviceResult.success = readBoolean(result, 'success', true)
  serviceResult.message = readString(result, 'message')
  serviceResult.entity_id = readString(result, 'entity_id', entityId)
  serviceResult.action = readString(result, 'action', action)
  serviceResult.executed_at = readString(result, 'executed_at')
  serviceResult.service_response = readObject(result, 'service_response')

  let changedStates = readObjectArray(result, 'changed_states')
  for (let i = 0; i < changedStates.length; i++) {
    serviceResult.changed_states.push(mapState(changedStates[i] as Record<string, Object>))
  }
  return serviceResult
}

export function buildEntityId(deviceType: string, deviceId: number): string {
  return deviceType + '.device_' + deviceId.toString()
}

export async function discoverDevices(): Promise<DiscoveredDevice[]> {
  let emptyBody: Record<string, Object> = {}
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.POST, '/api/discovery', emptyBody
  )
  let list = readObjectArray(result, 'discovered')
  let devices: DiscoveredDevice[] = []
  for (let i = 0; i < list.length; i++) {
    devices.push(mapDiscoveredDevice(list[i] as Record<string, Object>))
  }
  return devices
}

export async function bindDevice(deviceId: string, roomId: number, name?: string): Promise<Record<string, Object>> {
  let body: Record<string, Object> = {
    'device_id': deviceId,
    'room_id': roomId
  }
  if (name) {
    body['name'] = name
  }
  return request<Record<string, Object>>(http.RequestMethod.POST, '/api/bind_device', body)
}

export async function sendCommand(deviceId: number, action: string, params?: Object): Promise<boolean> {
  let device = await getDevice(deviceId)
  if (!device.type) {
    return false
  }
  let entityId = buildEntityId(device.type, deviceId)
  let result = await callService(entityId, action, params)
  return result.success
}

export async function getRules(): Promise<AutomationRule[]> {
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, '/api/rules')
  let rules: AutomationRule[] = []
  for (let i = 0; i < result.length; i++) {
    rules.push(mapRule(result[i] as Record<string, Object>))
  }
  return rules
}

export async function getRuleOptions(): Promise<RuleOptions> {
  let result: Record<string, Object> = await request<Record<string, Object>>(http.RequestMethod.GET, '/api/rules/options')
  let options = new RuleOptions()

  let triggers = readObjectArray(result, 'triggers')
  for (let i = 0; i < triggers.length; i++) {
    let option = new RuleTriggerOption()
    let triggerRecord = triggers[i] as Record<string, Object>
    option.label = readString(triggerRecord, 'label')
    option.value = readString(triggerRecord, 'value')
    option.field = readString(triggerRecord, 'field')
    option.room_name = readString(triggerRecord, 'room_name')
    options.triggers.push(option)
  }

  let operators = readObjectArray(result, 'operators')
  for (let i = 0; i < operators.length; i++) {
    let option = new RuleOperatorOption()
    let operatorRecord = operators[i] as Record<string, Object>
    option.label = readString(operatorRecord, 'label')
    option.value = readString(operatorRecord, 'value')
    options.operators.push(option)
  }

  let actionsRecord = readObject(result, 'actions')
  let actionTypes = Object.keys(actionsRecord)
  for (let i = 0; i < actionTypes.length; i++) {
    let key = actionTypes[i]
    let values = actionsRecord[key] as Array<Object>
    options.actions[key] = mapStringArray(values || [])
  }

  let targets = readObjectArray(result, 'targets')
  for (let i = 0; i < targets.length; i++) {
    let option = new RuleTargetOption()
    let targetRecord = targets[i] as Record<string, Object>
    option.device_id = readNumber(targetRecord, 'device_id')
    option.label = readString(targetRecord, 'label')
    option.type = readString(targetRecord, 'type')
    let roomId = targetRecord['room_id']
    if (roomId !== undefined && roomId !== null) {
      option.room_id = String(roomId)
    }
    option.room_name = readString(targetRecord, 'room_name')
    let targetActions = targetRecord['actions']
    if (targetActions !== undefined && targetActions !== null) {
      option.actions = mapStringArray(targetActions as Array<Object>)
    }
    options.targets.push(option)
  }

  return options
}

export async function toggleRule(ruleId: number): Promise<Record<string, Object>> {
  return request<Record<string, Object>>(http.RequestMethod.POST, `/api/rules/${ruleId}/toggle`)
}

export async function createRule(name: string, conditionJson: string, actionJson: string): Promise<Record<string, Object>> {
  let body: Record<string, Object> = {
    'name': name,
    'condition_json': conditionJson,
    'action_json': actionJson,
    'enabled': 1
  }
  return request<Record<string, Object>>(http.RequestMethod.POST, '/api/rules', body)
}

export async function deleteRule(ruleId: number): Promise<Record<string, Object>> {
  return request<Record<string, Object>>(http.RequestMethod.DELETE, `/api/rules/${ruleId}`)
}

export async function getScenes(): Promise<Scene[]> {
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, '/api/scenes')
  let scenes: Scene[] = []
  for (let i = 0; i < result.length; i++) {
    scenes.push(mapScene(result[i] as Record<string, Object>))
  }
  return scenes
}

export async function executeScene(sceneId: number): Promise<Record<string, Object>> {
  return request<Record<string, Object>>(http.RequestMethod.POST, `/api/scenes/${sceneId}/execute`)
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  let result: Record<string, Object> = await request<Record<string, Object>>(http.RequestMethod.GET, '/api/dashboard/summary')
  let summary = new DashboardSummary()

  let rooms = readObjectArray(result, 'rooms')
  for (let i = 0; i < rooms.length; i++) {
    summary.rooms.push(mapRoom(rooms[i] as Record<string, Object>))
  }

  let devices = readObjectArray(result, 'devices')
  for (let i = 0; i < devices.length; i++) {
    summary.devices.push(mapDevice(devices[i] as Record<string, Object>))
  }

  let scenes = readObjectArray(result, 'scenes')
  for (let i = 0; i < scenes.length; i++) {
    summary.scenes.push(mapScene(scenes[i] as Record<string, Object>))
  }

  let logs = readObjectArray(result, 'recent_logs')
  for (let i = 0; i < logs.length; i++) {
    summary.recent_logs.push(mapLogItem(logs[i] as Record<string, Object>))
  }

  summary.stats = mapDashboardStats(readObject(result, 'stats'))
  return summary
}

export async function changePassword(oldPwd: string, newPwd: string): Promise<boolean> {
  let req = new ChangePasswordRequest()
  req.old_password = oldPwd
  req.new_password = newPwd
  let result: Record<string, Object> = await request<Record<string, Object>>(
    http.RequestMethod.PUT, '/api/auth/change-password', req
  )
  return readBoolean(result, 'success')
}

export async function logout(): Promise<void> {
  cachedToken = ''
  cachedAesKey = ''
  sessionInvalidating = false
  await clearAuthData()
}

export async function getSensorHistory(deviceId?: number, limit: number = 50, start?: string, end?: string): Promise<SensorDataItem[]> {
  let path = `/api/data/sensors?limit=${limit}`
  if (deviceId) {
    path += `&device_id=${deviceId}`
  }
  if (start) {
    path += `&start=${encodeURIComponent(start)}`
  }
  if (end) {
    path += `&end=${encodeURIComponent(end)}`
  }
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, path)
  let items: SensorDataItem[] = []
  for (let i = 0; i < result.length; i++) {
    items.push(mapSensorDataItem(result[i] as Record<string, Object>))
  }
  return items
}

export async function getDeviceLogs(deviceId?: number, limit: number = 50): Promise<LogItem[]> {
  let path = `/api/data/logs?limit=${limit}`
  if (deviceId) {
    path += `&device_id=${deviceId}`
  }
  let result: Array<Object> = await request<Array<Object>>(http.RequestMethod.GET, path)
  let items: LogItem[] = []
  for (let i = 0; i < result.length; i++) {
    items.push(mapLogItem(result[i] as Record<string, Object>))
  }
  return items
}
