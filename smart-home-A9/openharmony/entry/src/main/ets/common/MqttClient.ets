import { BusinessError } from '@ohos.base'
import webSocket from '@ohos.net.webSocket'
import { SERVER_WEBSOCKET_URL } from './ServerConfig'
import { getToken } from './ApiClient'

let ws: webSocket.WebSocket | null = null
let messageCallback: ((msg: string) => void) | null = null
let statusCallback: ((connected: boolean) => void) | null = null
let reconnectTimer: number = -1
let isConnecting: boolean = false

export function connectWS(onMessage: (msg: string) => void, onStatus?: (connected: boolean) => void): void {
  messageCallback = onMessage
  statusCallback = onStatus || null
  _doConnect()
}

function _doConnect(): void {
  if (isConnecting) return
  isConnecting = true

  let token = getToken()
  let url = `${SERVER_WEBSOCKET_URL}/ws/realtime?token=${token}`

  ws = webSocket.createWebSocket()
  ws!.on('open', () => {
    console.info('WebSocket connected')
    isConnecting = false
    if (reconnectTimer > 0) {
      clearInterval(reconnectTimer)
      reconnectTimer = -1
    }
    if (statusCallback) {
      statusCallback(true)
    }
  })

  ws!.on('message', (err: BusinessError, data: string | ArrayBuffer) => {
    if (typeof data === 'string') {
      if (messageCallback) {
        messageCallback(data)
      }
    }
  })

  ws!.on('close', () => {
    console.info('WebSocket closed')
    isConnecting = false
    if (statusCallback) {
      statusCallback(false)
    }
    _scheduleReconnect()
  })

  ws!.on('error', (err: BusinessError) => {
    console.error('WebSocket error', err)
    isConnecting = false
  })

  ws!.connect(url).catch((err: Error) => {
    console.error('WebSocket connect failed', err)
    isConnecting = false
    _scheduleReconnect()
  })
}

function _scheduleReconnect(): void {
  if (reconnectTimer > 0) return
  reconnectTimer = setInterval(() => {
    console.info('WebSocket reconnecting...')
    _doConnect()
  }, 5000)
}

export function disconnectWS(): void {
  if (reconnectTimer > 0) {
    clearInterval(reconnectTimer)
    reconnectTimer = -1
  }
  if (ws) {
    try {
      ws.close()
    } catch (e) {
      console.error('WebSocket close error', e)
    }
    ws = null
  }
  messageCallback = null
}
