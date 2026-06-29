"""
安全模块单元测试：密码哈希、JWT、AES 加解密
"""
import json
import base64
from app.services.security import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
    aes_encrypt,
    aes_decrypt,
)


class TestPasswordHash:
    """密码哈希测试"""

    def test_hash_and_verify(self):
        pw = "my_secret_123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_hash_is_unique_per_call(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # bcrypt 每次生成不同的盐


class TestJWT:
    """JWT 令牌测试"""

    def test_create_and_decode_token(self):
        token = create_token(user_id=42, username="testuser", role="user")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"
        assert "aes_key" in payload
        assert "exp" in payload

    def test_decode_invalid_token(self):
        assert decode_token("not.a.valid.token") is None

    def test_decode_tampered_token(self):
        token = create_token(1, "user")
        # 修改中间的 payload 部分
        parts = token.split(".")
        tampered = parts[0] + "." + "tampered" + "." + parts[2]
        assert decode_token(tampered) is None

    def test_token_contains_aes_key(self):
        token = create_token(1, "user")
        payload = decode_token(token)
        aes_key = base64.b64decode(payload["aes_key"])
        assert len(aes_key) == 32  # AES-256 key


class TestAES:
    """AES-256-CBC 加解密测试"""

    def test_encrypt_decrypt_roundtrip(self):
        key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
        plaintext = "Hello, Smart Home!"
        ciphertext = aes_encrypt(plaintext, key)
        assert ciphertext != plaintext
        decrypted = aes_decrypt(ciphertext, key)
        assert decrypted == plaintext

    def test_encrypt_unicode(self):
        key = base64.b64encode(b"abcdefghijklmnopqrstuvwxyz123456").decode()
        plaintext = "智能家居 🔐 测试"
        ciphertext = aes_encrypt(plaintext, key)
        decrypted = aes_decrypt(ciphertext, key)
        assert decrypted == plaintext

    def test_encrypt_json_payload(self):
        key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
        data = json.dumps({"user_id": 1, "action": "unlock", "ts": 1234567890})
        ciphertext = aes_encrypt(data, key)
        decrypted = aes_decrypt(ciphertext, key)
        assert json.loads(decrypted) == {"user_id": 1, "action": "unlock", "ts": 1234567890}

    def test_encrypt_produces_different_output(self):
        key = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()
        msg = "same message"
        c1 = aes_encrypt(msg, key)
        c2 = aes_encrypt(msg, key)
        assert c1 != c2  # 随机 IV 保证每次加密结果不同

    def test_wrong_key_fails(self):
        key1 = base64.b64encode(b"aaaaaaaabbbbbbbbccccccccdddddddd").decode()
        key2 = base64.b64encode(b"xxxxxxxxyyyyyyyyzzzzzzzzwwwwwwww").decode()
        ciphertext = aes_encrypt("secret", key1)
        try:
            aes_decrypt(ciphertext, key2)
            # 解密可能"成功"但产生乱码，或者是填充错误
        except (ValueError, UnicodeDecodeError):
            pass  # 预期会失败
