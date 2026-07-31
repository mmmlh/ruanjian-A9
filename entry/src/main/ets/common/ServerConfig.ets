export const PRODUCTION_SERVER_URL: string = 'http://8.162.10.179:8000'
export const LOCAL_SERVER_URL: string = 'http://localhost:8000'
export const EMULATOR_SERVER_URL: string = 'http://10.0.2.2:8000'

// Change this value to switch the server used when no runtime override is saved.
// Use EMULATOR_SERVER_URL when the emulator maps its host through 10.0.2.2.
// A URL persisted through ApiClient.setBaseUrl() takes precedence at runtime.
export const DEFAULT_SERVER_URL: string = EMULATOR_SERVER_URL

export const WEBSOCKET_REALTIME_PATH: string = '/ws/realtime'
export const DEVICE_LIST_PATH: string = '/api/devices'
