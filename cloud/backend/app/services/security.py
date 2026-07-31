"""
安全模块：JWT 令牌 + AES-256-CBC 加密 + 密码哈希
"""
import os
import json
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional

import jwt
from passlib.context import CryptContext

from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS, AES_KEY_SIZE, AES_BLOCK_SIZE

# ── 密码哈希 ──
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ──
def create_token(user_id: int, username: str, role: str = "user") -> str:
    """生成 JWT token，payload 包含用户信息和 AES 密钥"""
    aes_key = base64.b64encode(os.urandom(AES_KEY_SIZE)).decode()
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "aes_key": aes_key,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解码 JWT token，返回 payload 或 None"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── AES-256-CBC ──
def _pad(data: bytes) -> bytes:
    """PKCS7 填充"""
    pad_len = AES_BLOCK_SIZE - (len(data) % AES_BLOCK_SIZE)
    return data + bytes([pad_len] * pad_len)


def _unpad(data: bytes) -> bytes:
    """PKCS7 去填充"""
    pad_len = data[-1]
    return data[:-pad_len]


def aes_encrypt(plaintext: str, key_b64: str) -> str:
    """AES-256-CBC 加密，返回 base64 编码的密文"""
    from Crypto.Cipher import AES
    key = base64.b64decode(key_b64)[:AES_KEY_SIZE]
    iv = os.urandom(AES_BLOCK_SIZE)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(_pad(plaintext.encode("utf-8")))
    return base64.b64encode(iv + encrypted).decode()


def aes_decrypt(ciphertext_b64: str, key_b64: str) -> str:
    """AES-256-CBC 解密"""
    from Crypto.Cipher import AES
    key = base64.b64decode(key_b64)[:AES_KEY_SIZE]
    raw = base64.b64decode(ciphertext_b64)
    iv = raw[:AES_BLOCK_SIZE]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = _unpad(cipher.decrypt(raw[AES_BLOCK_SIZE:]))
    return decrypted.decode("utf-8")
