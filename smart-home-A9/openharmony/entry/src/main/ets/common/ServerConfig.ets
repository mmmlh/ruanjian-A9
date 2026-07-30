// Edit these values when the backend deployment changes.
export const SERVER_PROTOCOL: string = 'http'
export const SERVER_HOST: string = '8.162.10.179'
export const SERVER_PORT: number = 8000

export const SERVER_BASE_URL: string = `${SERVER_PROTOCOL}://${SERVER_HOST}:${SERVER_PORT}`
export const SERVER_WEBSOCKET_URL: string =
  `${SERVER_PROTOCOL === 'https' ? 'wss' : 'ws'}://${SERVER_HOST}:${SERVER_PORT}`
