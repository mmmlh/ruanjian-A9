export namespace UiText {
  export const networkRequestFailed: string = '网络请求失败'
  export const requestTimedOut: string = '请求超时，请检查服务器连接。'
  export const connectionRefused: string = '连接被拒绝，请检查服务器地址和端口。'
  export const tlsValidationFailed: string = 'TLS 或证书校验失败。'
  export const emptyResponseBody: string = '响应内容为空'
  export const invalidAuthResponse: string = '登录响应缺少有效凭据，请稍后重试。'
  export const sessionExpired: string = '登录状态已失效，请重新登录。'
  export const secureCommandUnavailable: string = '安全凭据不可用，已阻止设备指令。请重新登录后再试。'
  export const passwordChangeRejected: string = '密码修改未生效，请确认当前密码后重试。'

  export function mapTransportMessage(message: string): string {
    if (!message) {
      return networkRequestFailed
    }

    let lower = message.toLowerCase()
    if (lower.indexOf('timeout') >= 0) {
      return requestTimedOut
    }
    if (lower.indexOf('refused') >= 0 || lower.indexOf('failed to connect') >= 0) {
      return connectionRefused
    }
    if (lower.indexOf('certificate') >= 0 || lower.indexOf('ssl') >= 0 || lower.indexOf('tls') >= 0) {
      return tlsValidationFailed
    }
    if (lower.indexOf('network request failed') >= 0
      || lower.indexOf('network error') >= 0
      || lower.indexOf('failed to fetch') >= 0
      || lower.indexOf('unable to resolve host') >= 0
      || lower.indexOf('could not resolve host') >= 0) {
      return networkRequestFailed
    }
    return message
  }

  export function requestFailed(statusCode: number): string {
    return `请求失败：${statusCode}`
  }

  export function mapApiDetail(detail: string): string {
    switch (detail) {
      case 'device_offline':
        return '设备当前离线，请恢复连接后再发送指令。'
      case 'command_dispatch_failed':
        return '指令下发失败，请检查设备连接和 MQTT 服务。'
      case 'entity_id_not_found':
        return '当前设备已无法与此控制面板匹配。'
      default:
        return detail
    }
  }
}
