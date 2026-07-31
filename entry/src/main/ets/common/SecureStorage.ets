import dataPreferences from '@ohos.data.preferences'

const PREFS_NAME = 'smart_home_auth'
const KEY_TOKEN = 'auth_token'
const KEY_AES_KEY = 'aes_key'
const KEY_SERVER_URL = 'server_url'

let prefsInstance: dataPreferences.Preferences | null = null
let prefsInitPromise: Promise<void> | null = null
let prefsContext: Context | null = null

export async function initPreferences(context: Context): Promise<void> {
  prefsContext = context
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
  let currentInit = prefsInitPromise
  await currentInit
  if (!prefsInstance && prefsInitPromise === currentInit) {
    prefsInitPromise = null
  }
}

async function ensurePreferencesReady(): Promise<void> {
  if (prefsInstance) {
    return
  }
  if (prefsContext) {
    await initPreferences(prefsContext)
  } else if (prefsInitPromise) {
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

export async function saveServerUrl(url: string): Promise<void> {
  await ensurePreferencesReady()
  if (!prefsInstance) return
  try {
    await prefsInstance.put(KEY_SERVER_URL, url)
    await prefsInstance.flush()
  } catch (e) {
    console.error('saveServerUrl failed', e)
  }
}

export async function loadServerUrl(): Promise<string> {
  await ensurePreferencesReady()
  if (!prefsInstance) return ''
  try {
    return await prefsInstance.get(KEY_SERVER_URL, '') as string
  } catch (e) {
    return ''
  }
}

export async function clearAuthData(): Promise<void> {
  await ensurePreferencesReady()
  if (!prefsInstance) return
  try {
    await prefsInstance.delete(KEY_TOKEN)
    await prefsInstance.delete(KEY_AES_KEY)
    await prefsInstance.flush()
  } catch (e) {
    console.error('clearAuthData failed', e)
  }
}
