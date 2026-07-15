import util from '@ohos.util'

function decodeBase64Url(str: string): string {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/')
  let pad = base64.length % 4
  if (pad === 2) {
    base64 += '=='
  } else if (pad === 3) {
    base64 += '='
  }
  try {
    let helper = new util.Base64Helper()
    let decoded = helper.decodeSync(base64)
    let textDecoder = util.TextDecoder.create('utf-8')
    let result = textDecoder.decodeToString(decoded)
    return result
  } catch (e) {
    return '{}'
  }
}

export function extractAesKey(token: string): string {
  try {
    let parts = token.split('.')
    if (parts.length !== 3) {
      return ''
    }
    let payloadJson = decodeBase64Url(parts[1])
    let payload: Record<string, Object> = JSON.parse(payloadJson) as Record<string, Object>
    let aesKeyVal = payload['aes_key']
    if (aesKeyVal !== undefined && aesKeyVal !== null) {
      return aesKeyVal as string
    }
    return ''
  } catch (err) {
    return ''
  }
}

export function extractUsername(token: string): string {
  try {
    let parts = token.split('.')
    if (parts.length !== 3) return ''
    let payloadJson = decodeBase64Url(parts[1])
    let payload: Record<string, Object> = JSON.parse(payloadJson) as Record<string, Object>
    let usernameVal = payload['username']
    if (usernameVal !== undefined && usernameVal !== null) {
      return usernameVal as string
    }
    return ''
  } catch (e) {
    return ''
  }
}
