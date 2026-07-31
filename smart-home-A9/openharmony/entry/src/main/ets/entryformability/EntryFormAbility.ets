import Want from '@ohos.app.ability.Want'
import FormExtensionAbility from '@ohos.app.form.FormExtensionAbility'
import formBindingData from '@ohos.app.form.formBindingData'
import formInfo from '@ohos.app.form.formInfo'
import formProvider from '@ohos.app.form.formProvider'
import hilog from '@ohos.hilog'
import http from '@ohos.net.http'
import { SERVER_BASE_URL } from '../common/ServerConfig'
import { initPreferences } from '../common/SecureStorage'
import { formatUtcClock } from '../common/UtcTimeUtil'

const TAG = 'SmartHomeForm'
const DOMAIN = 0x0000

let formIds: string[] = []
let updateTimer: number = -1

function defaultFormPayload(): Record<string, Object> {
  return {
    'temperature': '--',
    'humidity': '--',
    'lightOn': false,
    'acOn': false,
    'locked': true,
    'curtainOpen': false,
    'humidifierOn': false,
    'updateTime': '--:--'
  }
}

function createBindingDataSafely(data: Record<string, Object>): formBindingData.FormBindingData {
  try {
    return formBindingData.createFormBindingData(data)
  } catch (e) {
    hilog.error(DOMAIN, TAG, 'createFormBindingData failed: %{public}s', JSON.stringify(e))
    return { data: data } as formBindingData.FormBindingData
  }
}

async function updateFormSafely(formId: string, data: Record<string, Object>): Promise<void> {
  let bindingData = createBindingDataSafely(data)
  try {
    await formProvider.updateForm(formId, bindingData)
  } catch (e) {
    hilog.error(DOMAIN, TAG, 'updateForm failed: %{public}s', JSON.stringify(e))
  }
}

async function resolveWidgetUrl(): Promise<string> {
  return `${SERVER_BASE_URL}/api/devices`
}

async function fetchDeviceData(): Promise<Record<string, Object>> {
  try {
    let httpRequest = http.createHttp()
    let response = await httpRequest.request(await resolveWidgetUrl(), {
      method: http.RequestMethod.GET,
      header: { 'Content-Type': 'application/json' },
      connectTimeout: 5000,
      readTimeout: 5000
    })
    httpRequest.destroy()
    if (response.responseCode === 200) {
      let devices: Array<Object> = JSON.parse(response.result as string) as Array<Object>
      let tempStr = '--'
      let humStr = '--'
      let lightOn = false
      let acOn = false
      let locked = true
      let curtainOpen = false
      let humidifierOn = false
      for (let i = 0; i < devices.length; i++) {
        let d = devices[i] as Record<string, Object>
        let dtype = d['type']
        let sjson = d['status_json']
        if (dtype !== undefined && dtype !== null && sjson !== undefined && sjson !== null) {
          let status: Record<string, Object> = JSON.parse(sjson as string) as Record<string, Object>
          if (dtype === 'temperature_sensor') {
            let v = status['value']
            if (v !== undefined && v !== null) tempStr = (v as number).toFixed(1)
          } else if (dtype === 'humidity_sensor') {
            let v = status['value']
            if (v !== undefined && v !== null) humStr = (v as number).toFixed(0)
          } else if (dtype === 'light') {
            let p = status['power']
            if (p === 'on') lightOn = true
          } else if (dtype === 'ac') {
            let p = status['power']
            if (p === 'on') acOn = true
          } else if (dtype === 'door_lock') {
            let l = status['locked']
            if (l !== undefined && l !== null) locked = l as boolean
          } else if (dtype === 'curtain') {
            let pos = status['position']
            if (pos !== undefined && pos !== null && (pos as number) > 0) curtainOpen = true
          } else if (dtype === 'humidifier') {
            let p = status['power']
            if (p === 'on') humidifierOn = true
          }
        }
      }
      let now = new Date()
      return {
        'temperature': tempStr,
        'humidity': humStr,
        'lightOn': lightOn,
        'acOn': acOn,
        'locked': locked,
        'curtainOpen': curtainOpen,
        'humidifierOn': humidifierOn,
        'updateTime': formatUtcClock(now)
      }
    }
  } catch (e) {
    hilog.error(DOMAIN, TAG, 'Fetch device data failed: %{public}s', JSON.stringify(e))
  }
  return defaultFormPayload()
}

async function refreshAllForms(): Promise<void> {
  for (let i = 0; i < formIds.length; i++) {
    let formId = formIds[i]
    let data = await fetchDeviceData()
    await updateFormSafely(formId, data)
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
      let data = await fetchDeviceData()
      await updateFormSafely(formId, data)
    }
    hydrateForm()

    if (updateTimer < 0) {
      updateTimer = setInterval(() => {
        refreshAllForms()
      }, 60000)
    }

    let initPayload = defaultFormPayload()
    initPayload['updateTime'] = '正在加载...'
    return createBindingDataSafely(initPayload)
  }

  onRemoveForm(formId: string): void {
    hilog.info(DOMAIN, TAG, 'onRemoveForm')
    let idx = formIds.indexOf(formId)
    if (idx >= 0) {
      formIds.splice(idx, 1)
    }
    if (formIds.length === 0 && updateTimer > 0) {
      clearInterval(updateTimer)
      updateTimer = -1
    }
  }

  onUpdateForm(formId: string): void {
    hilog.info(DOMAIN, TAG, 'onUpdateForm')
    let refreshForm = async (): Promise<void> => {
      await initPreferences(this.context)
      let data = await fetchDeviceData()
      await updateFormSafely(formId, data)
    }
    refreshForm()
  }

  onFormEvent(formId: string, message: string): void {
    hilog.info(DOMAIN, TAG, 'onFormEvent: %{public}s', message)
    if (message === 'refresh') {
      let refreshForm = async (): Promise<void> => {
        await initPreferences(this.context)
        let data = await fetchDeviceData()
        await updateFormSafely(formId, data)
      }
      refreshForm()
    }
  }

  onAcquireFormState(want: Want): formInfo.FormState {
    return formInfo.FormState.READY
  }
}
