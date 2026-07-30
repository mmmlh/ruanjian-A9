import dataPreferences from '@ohos.data.preferences'

const PREFS_NAME = 'smart_home_auth'
const KEY_TOKEN = 'auth_token'
const KEY_AES_KEY = 'aes_key'

let prefsInstance: dataPreferences.Preferences | null = null
let prefsInitPromise: Promise<void> | null = null

export async function initPreferences(context: Context): Promise<void> {
  if (prefsInstance) {
    return
  }
  if (!prefsInitPromise) {
    prefsInitPromise = (async () => {
      try {
        prefsInstance = await dataPreferences.getPreferences(context, PREFS_NAME)
      } catch (e) {
        console.error('initPreferences failed', e)
      }
    })()
  }
  await prefsInitPromise
}

async function ensurePreferencesReady(): Promise<void> {
  if (prefsInitPromise) {
    await prefsInitPromise
  }
}

export async function saveAuthData(token: string, aesKey: string): Promise<void> {
  await ensurePreferencesReady()
  if (!prefsInstance) return
  try {
    await prefsInstance.put(KEY_TOKEN, token)
    await prefsInstance.put(KEY_AES_KEY, aesKey)
    await prefsInstance.flush()
  } catch (e) {
    console.error('saveAuthData failed', e)
  }
}

export async function loadAuthData(): Promise<string[]> {
  await ensurePreferencesReady()
  if (!prefsInstance) return ['', '']
  try {
    let token = await prefsInstance.get(KEY_TOKEN, '') as string
    let aesKey = await prefsInstance.get(KEY_AES_KEY, '') as string
    return [token, aesKey]
  } catch (e) {
    return ['', '']
  }
}

export async function clearAuthData(): Promise<void> {
  await ensurePreferencesReady()
  if (!prefsInstance) return
  try {
    await prefsInstance.clear()
    await prefsInstance.flush()
  } catch (e) {
    console.error('clearAuthData failed', e)
  }
}
