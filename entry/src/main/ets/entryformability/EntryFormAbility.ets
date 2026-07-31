import Want from '@ohos.app.ability.Want'
import FormExtensionAbility from '@ohos.app.form.FormExtensionAbility'
import formBindingData from '@ohos.app.form.formBindingData'
import formInfo from '@ohos.app.form.formInfo'
import formProvider from '@ohos.app.form.formProvider'
import hilog from '@ohos.hilog'
import http from '@ohos.net.http'
import { DEFAULT_SERVER_URL, DEVICE_LIST_PATH } from '../common/ServerConfig'
import { initPreferences, loadAuthData, loadServerUrl } from '../common/SecureStorage'

const TAG = 'SmartHomeForm'
const DOMAIN = 0x0000

let formIds: string[] = []
let fetchInFlight: Promise<Record<string, Object>> | null = null

class WidgetState {
  temperature: string = '--'
  temperatureUpdated: string = ''
  humidity: string = '--'
  humidityUpdated: string = ''
  lightOn: boolean = false
  lightKnown: boolean = false
  acOn: boolean = false
  acKnown: boolean = false
  locked: boolean = true
  lockKnown: boolean = false
  curtainOpen: boolean = false
  curtainKnown: boolean = false
  humidifierOn: boolean = false
  humidifierKnown: boolean = false
}

function unavailableFormPayload(message: string = '状态不可用'): Record<string, Object> {
  return {
    'temperature': '--',
    'humidity': '--',
    'lightOn': false,
    'lightKnown': false,
    'acOn': false,
    'acKnown': false,
    'locked': true,
    'lockKnown': false,
    'curtainOpen': false,
    'curtainKnown': false,
    'humidifierOn': false,
    'humidifierKnown': false,
    'updateTime': message
  }
}

function createBindingDataSafely(data: Record<string, Object>): formBindingData.FormBindingData {
  try {
    return formBindingData.createFormBindingData(data)
  } catch (err) {
    hilog.error(DOMAIN, TAG, 'createFormBindingData failed: %{public}s', JSON.stringify(err))
    return { data: data } as formBindingData.FormBindingData
  }
}

async function updateFormSafely(formId: string, data: Record<string, Object>): Promise<void> {
  let bindingData = createBindingDataSafely(data)
  try {
    await formProvider.updateForm(formId, bindingData)
  } catch (err) {
    hilog.error(DOMAIN, TAG, 'updateForm failed: %{public}s', JSON.stringify(err))
  }
}

async function resolveWidgetUrl(): Promise<string> {
  let savedBaseUrl = await loadServerUrl()
  let baseUrl = savedBaseUrl || DEFAULT_SERVER_URL
  return `${baseUrl}${DEVICE_LIST_PATH}`
}

function parseStatus(statusJson: Object): Record<string, Object> | null {
  if (typeof statusJson !== 'string') {
    return null
  }
  try {
    return JSON.parse(statusJson as string) as Record<string, Object>
  } catch (err) {
    return null
  }
}

function updatedAt(device: Record<string, Object>): string {
  let value = device['updated_at'] || device['last_seen_at']
  return value !== undefined && value !== null ? String(value) : ''
}

function shouldReplaceReading(currentUpdated: string, nextUpdated: string): boolean {
  if (!currentUpdated) {
    return true
  }
  if (!nextUpdated) {
    return false
  }
  let currentTime = new Date(currentUpdated).getTime()
  let nextTime = new Date(nextUpdated).getTime()
  if (!Number.isNaN(currentTime) && !Number.isNaN(nextTime)) {
    return nextTime >= currentTime
  }
  return nextUpdated >= currentUpdated
}

function aggregateDevice(state: WidgetState, device: Record<string, Object>): void {
  if (device['online'] === false) {
    return
  }
  let typeValue = device['type']
  let statusValue = device['status_json']
  if (typeof typeValue !== 'string' || statusValue === undefined || statusValue === null) {
    return
  }
  let status = parseStatus(statusValue)
  if (status === null) {
    return
  }

  let deviceType = typeValue as string
  let timestamp = updatedAt(device)
  if (deviceType === 'temperature_sensor') {
    let value = status['value']
    if (typeof value === 'number' && shouldReplaceReading(state.temperatureUpdated, timestamp)) {
      state.temperature = (value as number).toFixed(1)
      state.temperatureUpdated = timestamp
    }
  } else if (deviceType === 'humidity_sensor') {
    let value = status['value']
    if (typeof value === 'number' && shouldReplaceReading(state.humidityUpdated, timestamp)) {
      state.humidity = (value as number).toFixed(0)
      state.humidityUpdated = timestamp
    }
  } else if (deviceType === 'light') {
    let power = status['power']
    if (power === 'on' || power === 'off') {
      state.lightKnown = true
      state.lightOn = state.lightOn || power === 'on'
    }
  } else if (deviceType === 'ac') {
    let power = status['power']
    if (power === 'on' || power === 'off') {
      state.acKnown = true
      state.acOn = state.acOn || power === 'on'
    }
  } else if (deviceType === 'door_lock') {
    let locked = status['locked']
    if (typeof locked === 'boolean') {
      state.lockKnown = true
      state.locked = state.locked && locked as boolean
    }
  } else if (deviceType === 'curtain') {
    let position = status['position']
    if (typeof position === 'number') {
      state.curtainKnown = true
      state.curtainOpen = state.curtainOpen || (position as number) > 0
    }
  } else if (deviceType === 'humidifier') {
    let power = status['power']
    if (power === 'on' || power === 'off') {
      state.humidifierKnown = true
      state.humidifierOn = state.humidifierOn || power === 'on'
    }
  }
}

function availableFormPayload(devices: Array<Object>): Record<string, Object> {
  let state = new WidgetState()
  for (let i = 0; i < devices.length; i++) {
    aggregateDevice(state, devices[i] as Record<string, Object>)
  }
  let now = new Date()
  return {
    'temperature': state.temperature,
    'humidity': state.humidity,
    'lightOn': state.lightOn,
    'lightKnown': state.lightKnown,
    'acOn': state.acOn,
    'acKnown': state.acKnown,
    'locked': state.locked,
    'lockKnown': state.lockKnown,
    'curtainOpen': state.curtainOpen,
    'curtainKnown': state.curtainKnown,
    'humidifierOn': state.humidifierOn,
    'humidifierKnown': state.humidifierKnown,
    'updateTime': now.getHours().toString().padStart(2, '0') + ':' +
      now.getMinutes().toString().padStart(2, '0')
  }
}

async function fetchDeviceData(): Promise<Record<string, Object>> {
  let httpRequest = http.createHttp()
  try {
    let authData = await loadAuthData()
    let token = authData[0]
    if (!token) {
      return unavailableFormPayload('登录后查看')
    }
    let response = await httpRequest.request(await resolveWidgetUrl(), {
      method: http.RequestMethod.GET,
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      connectTimeout: 5000,
      readTimeout: 5000
    })
    if (response.responseCode === 401 || response.responseCode === 403) {
      return unavailableFormPayload('登录后查看')
    }
    if (response.responseCode !== 200) {
      return unavailableFormPayload()
    }
    let devices = JSON.parse(response.result as string) as Array<Object>
    if (!Array.isArray(devices)) {
      return unavailableFormPayload()
    }
    return availableFormPayload(devices)
  } catch (err) {
    hilog.error(DOMAIN, TAG, 'Fetch device data failed: %{public}s', JSON.stringify(err))
    return unavailableFormPayload()
  } finally {
    httpRequest.destroy()
  }
}

async function sharedDeviceData(): Promise<Record<string, Object>> {
  if (fetchInFlight) {
    return fetchInFlight
  }
  fetchInFlight = fetchDeviceData()
  try {
    return await fetchInFlight
  } finally {
    fetchInFlight = null
  }
}

async function refreshForms(targetIds: string[]): Promise<void> {
  if (targetIds.length === 0) {
    return
  }
  let data = await sharedDeviceData()
  for (let i = 0; i < targetIds.length; i++) {
    await updateFormSafely(targetIds[i], data)
  }
}

export default class EntryFormAbility extends FormExtensionAbility {
  onAddForm(want: Want): formBindingData.FormBindingData {
    hilog.info(DOMAIN, TAG, 'onAddForm')
    let formId = want.parameters![formInfo.FormParam.IDENTITY_KEY] as string
    if (formIds.indexOf(formId) < 0) {
      formIds.push(formId)
    }

    let hydrateForm = async (): Promise<void> => {
      await initPreferences(this.context)
      await refreshForms([formId])
    }
    hydrateForm()
    return createBindingDataSafely(unavailableFormPayload('正在加载...'))
  }

  onRemoveForm(formId: string): void {
    hilog.info(DOMAIN, TAG, 'onRemoveForm')
    let index = formIds.indexOf(formId)
    if (index >= 0) {
      formIds.splice(index, 1)
    }
  }

  onUpdateForm(formId: string): void {
    hilog.info(DOMAIN, TAG, 'onUpdateForm')
    let refreshForm = async (): Promise<void> => {
      await initPreferences(this.context)
      await refreshForms([formId])
    }
    refreshForm()
  }

  onChangeFormVisibility(newStatus: Record<string, number>): void {
    let visibleIds: string[] = []
    let ids = Object.keys(newStatus)
    for (let i = 0; i < ids.length; i++) {
      let formId = ids[i]
      if (newStatus[formId] === formInfo.VisibilityType.FORM_VISIBLE) {
        visibleIds.push(formId)
      }
    }
    let refreshVisibleForms = async (): Promise<void> => {
      await initPreferences(this.context)
      await refreshForms(visibleIds)
    }
    refreshVisibleForms()
  }

  onFormEvent(formId: string, message: string): void {
    hilog.info(DOMAIN, TAG, 'onFormEvent: %{public}s', message)
    if (message === 'refresh') {
      let refreshForm = async (): Promise<void> => {
        await initPreferences(this.context)
        await refreshForms([formId])
      }
      refreshForm()
    }
  }

  onAcquireFormState(want: Want): formInfo.FormState {
    return formInfo.FormState.READY
  }
}
