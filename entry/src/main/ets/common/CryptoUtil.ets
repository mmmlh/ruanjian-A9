import cryptoFramework from '@ohos.security.cryptoFramework'
import util from '@ohos.util'

const AES_BLOCK_SIZE = 16
const AES_KEY_SIZE = 32

async function generateRandom(length: number): Promise<Uint8Array> {
  try {
    let rand = cryptoFramework.createRandom()
    let blob = await rand.generateRandom(length)
    let randomBytes = new Uint8Array(blob.data)
    if (randomBytes.length !== length) {
      throw new Error('random_length_mismatch')
    }
    return randomBytes
  } catch (e) {
    throw new Error('secure_random_generation_failed')
  }
}

async function createSymKey(keyBase64: string): Promise<cryptoFramework.SymKey> {
  try {
    let helper = new util.Base64Helper()
    let keyBytes = helper.decodeSync(keyBase64)
    if (keyBytes.length !== AES_KEY_SIZE) {
      throw new Error('invalid_aes_key_length')
    }
    let keyGenerator = cryptoFramework.createSymKeyGenerator('AES256')
    let keyBlob: cryptoFramework.DataBlob = { data: new Uint8Array(keyBytes) }
    let symKey = await keyGenerator.convertKey(keyBlob)
    return symKey
  } catch (err) {
    throw new Error('sym_key_generation_failed')
  }
}

export async function aesEncrypt(plaintext: string, keyBase64: string): Promise<string> {
  if (!keyBase64 || !plaintext) {
    throw new Error('encryption_input_missing')
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
    throw new Error('encryption_failed')
  }
}

export async function generateAuthCode(keyBase64: string): Promise<string> {
  if (!keyBase64) {
    throw new Error('auth_key_missing')
  }
  try {
    let timestamp = Date.now().toString()
    let helper = new util.Base64Helper()
    let randomSuffix = helper.encodeToStringSync(await generateRandom(16))
    let authPayload = `smart-home|${timestamp}|${randomSuffix}`
    return await aesEncrypt(authPayload, keyBase64)
  } catch (err) {
    throw new Error('auth_code_generation_failed')
  }
}
