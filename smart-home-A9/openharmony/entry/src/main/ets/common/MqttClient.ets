/**
 * WebSocket 实时数据客户端
 * 通过 WebSocket 接收后端推送的传感器数据和设备状态
 */
import { webSocket } from '@kit.NetworkKit'
import { getBaseUrl, getToken } from './ApiClient'

let ws: webSocket.WebSocket | null = null
let messageCallback: ((msg: Object) => void) | null = null
let reconnectTimer: number = -1
let isConnecting: boolean = false

/**
 * 连接 WebSocket
 */
export function connectWS(onMessage: (msg: Object) => void): void {
  messageCallback = onMessage
  _doConnect()
}

function _doConnect(): void {
  if (isConnecting) return
  isConnecting = true

  const token = getToken()
  const baseUrl = getBaseUrl().replace('http://', 'ws://')
  const url = `${baseUrl}/ws/realtime?token=${token}`

  ws = webSocket.createWebSocket()
  ws!.on('open', () => {
    console.info('WebSocket 已连接')
    isConnecting = false
    if (reconnectTimer > 0) {
      clearInterval(reconnectTimer)
      reconnectTimer = -1
    }
  })

  ws!.on('message', (err: Error, data: string | ArrayBuffer) => {
    if (typeof data === 'string') {
      try {
        const msg = JSON.parse(data)
        if (messageCallback) {
          messageCallback(msg)
        }
      } catch (e) {
        console.error('WebSocket 消息解析失败', e)
      }
    }
  })

  ws!.on('close', () => {
    console.info('WebSocket 已断开')
    isConnecting = false
    _scheduleReconnect()
  })

  ws!.on('error', (err: Error) => {
    console.error('WebSocket 错误', err)
    isConnecting = false
  })

  ws!.connect(url).catch((err: Error) => {
    console.error('WebSocket 连接失败', err)
    isConnecting = false
    _scheduleReconnect()
  })
}

function _scheduleReconnect(): void {
  if (reconnectTimer > 0) return
  reconnectTimer = setInterval(() => {
    console.info('WebSocket 尝试重连...')
    _doConnect()
  }, 5000)
}

/**
 * 断开 WebSocket
 */
export function disconnectWS(): void {
  if (reconnectTimer > 0) {
    clearInterval(reconnectTimer)
    reconnectTimer = -1
  }
  if (ws) {
    ws.close()
    ws = null
  }
  messageCallback = null
}
