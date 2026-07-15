import cryptoFramework from '@ohos.security.cryptoFramework'
import util from '@ohos.util'

const AES_BLOCK_SIZE = 16
const AES_KEY_SIZE = 32

async function generateRandom(length: number): Promise<Uint8Array> {
  try {
    let rand = cryptoFramework.createRandom()
    let blob = await rand.generateRandom(length)
    return new Uint8Array(blob.data)
  } catch (e) {
    return new Uint8Array(length)
  }
}

async function createSymKey(keyBase64: string): Promise<cryptoFramework.SymKey> {
  try {
    let helper = new util.Base64Helper()
    let keyBytes = helper.decodeSync(keyBase64)
    let keyData = new Uint8Array(AES_KEY_SIZE)
    keyData.set(keyBytes.slice(0, AES_KEY_SIZE))
    let keyGenerator = cryptoFramework.createSymKeyGenerator('AES256')
    let keyBlob: cryptoFramework.DataBlob = { data: keyData }
    let symKey = await keyGenerator.convertKey(keyBlob)
    return symKey
  } catch (err) {
    throw new Error('sym_key_generation_failed')
  }
}

export async function aesEncrypt(plaintext: string, keyBase64: string): Promise<string> {
  if (!keyBase64 || !plaintext) {
    return ''
  }
  try {
    let symKey = await createSymKey(keyBase64)
    let ivData = await generateRandom(AES_BLOCK_SIZE)
    let ivBlob: cryptoFramework.DataBlob = { data: ivData }
    let cipher = cryptoFramework.createCipher('AES256|CBC|PKCS7')
    let ivParams: cryptoFramework.IvParamsSpec = {
      algName: 'IvParamsSpec',
      iv: ivBlob
    }
    await cipher.init(cryptoFramework.CryptoMode.ENCRYPT_MODE, symKey, ivParams)
    let encoder = util.TextEncoder.create('utf-8')
    let plainBytes = encoder.encodeInto(plaintext)
    let plainBlob: cryptoFramework.DataBlob = { data: new Uint8Array(plainBytes) }
    let output = await cipher.doFinal(plainBlob)
    let cipherBytes = new Uint8Array(output.data)
    let combined = new Uint8Array(AES_BLOCK_SIZE + cipherBytes.length)
    combined.set(ivData, 0)
    combined.set(cipherBytes, AES_BLOCK_SIZE)
    let base64Helper = new util.Base64Helper()
    let encoded = base64Helper.encodeToStringSync(combined)
    return encoded
  } catch (err) {
    return ''
  }
}

export async function generateAuthCode(keyBase64: string): Promise<string> {
  if (!keyBase64) {
    return 'demo-auth-code'
  }
  let timestamp = Date.now().toString()
  let randomSuffix = Math.random().toString(36).substring(2, 10)
  let authPayload = `smart-home|${timestamp}|${randomSuffix}`
  let encrypted = await aesEncrypt(authPayload, keyBase64)
  if (!encrypted) {
    return `plain:${authPayload}`
  }
  return encrypted
}
