import { BusinessError } from '@ohos.base'
import webSocket from '@ohos.net.webSocket'
import { getBaseUrl, getToken } from './ApiClient'
import { WEBSOCKET_REALTIME_PATH } from './ServerConfig'

const RECONNECT_DELAYS: number[] = [2000, 5000, 10000, 20000, 30000]

let ws: webSocket.WebSocket | null = null
let messageCallback: ((msg: string) => void) | null = null
let statusCallback: ((connected: boolean) => void) | null = null
let reconnectTimer: number = -1
let reconnectAttempt: number = 0
let isConnecting: boolean = false
let manualClose: boolean = true
let connectionGeneration: number = 0

export function connectWS(onMessage: (msg: string) => void, onStatus?: (connected: boolean) => void): void {
  disconnectWS()
  messageCallback = onMessage
  statusCallback = onStatus || null
  reconnectAttempt = 0
  manualClose = false
  doConnect()
}

function doConnect(): void {
  if (manualClose || isConnecting || ws !== null) {
    return
  }

  let token = getToken()
  if (!token) {
    if (statusCallback) {
      statusCallback(false)
    }
    return
  }

  isConnecting = true
  let generation = ++connectionGeneration
  let base = getBaseUrl()
  let wsProtocol = base.startsWith('https') ? 'wss://' : 'ws://'
  let host = base.replace('https://', '').replace('http://', '')
  let url = `${wsProtocol}${host}${WEBSOCKET_REALTIME_PATH}?token=${token}`
  let socket = webSocket.createWebSocket()
  ws = socket

  socket.on('open', () => {
    if (manualClose || generation !== connectionGeneration) {
      closeSocket(socket)
      return
    }
    console.info('WebSocket connected')
    isConnecting = false
    reconnectAttempt = 0
    clearReconnectTimer()
    if (statusCallback) {
      statusCallback(true)
    }
  })

  socket.on('message', (err: BusinessError, data: string | ArrayBuffer) => {
    if (manualClose || generation !== connectionGeneration || (err && err.code)) {
      return
    }
    if (typeof data === 'string' && messageCallback) {
      messageCallback(data)
    }
  })

  socket.on('close', () => {
    if (generation !== connectionGeneration) {
      return
    }
    console.info('WebSocket closed')
    if (ws === socket) {
      ws = null
    }
    isConnecting = false
    if (statusCallback) {
      statusCallback(false)
    }
    scheduleReconnect()
  })

  socket.on('error', (err: BusinessError) => {
    if (generation !== connectionGeneration) {
      return
    }
    console.error('WebSocket error', err)
    if (ws === socket) {
      ws = null
    }
    isConnecting = false
    if (statusCallback) {
      statusCallback(false)
    }
    closeSocket(socket)
    scheduleReconnect()
  })

  socket.connect(url).catch((err: Error) => {
    if (generation !== connectionGeneration) {
      return
    }
    console.error('WebSocket connect failed', err)
    if (ws === socket) {
      ws = null
    }
    isConnecting = false
    scheduleReconnect()
  })
}

function scheduleReconnect(): void {
  if (manualClose || reconnectTimer > 0) {
    return
  }
  let index = reconnectAttempt < RECONNECT_DELAYS.length ? reconnectAttempt : RECONNECT_DELAYS.length - 1
  let delay = RECONNECT_DELAYS[index]
  reconnectAttempt++
  reconnectTimer = setTimeout(() => {
    reconnectTimer = -1
    doConnect()
  }, delay)
}

function clearReconnectTimer(): void {
  if (reconnectTimer > 0) {
    clearTimeout(reconnectTimer)
    reconnectTimer = -1
  }
}

function closeSocket(socket: webSocket.WebSocket): void {
  try {
    socket.close()
  } catch (err) {
    console.error('WebSocket close error', err)
  }
}

export function disconnectWS(): void {
  manualClose = true
  connectionGeneration++
  clearReconnectTimer()
  isConnecting = false
  let activeSocket = ws
  ws = null
  if (activeSocket) {
    closeSocket(activeSocket)
  }
  messageCallback = null
  statusCallback = null
}
