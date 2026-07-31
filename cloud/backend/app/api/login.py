"""
/api/login — 登录获取 Token
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database.connection import get_db
from app.services.security import hash_password, verify_password, create_token

router = APIRouter(prefix="/api/login", tags=["登录"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("")
def login(req: LoginRequest):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = ?",
            (req.username,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(row["id"], row["username"], row["role"])
    return {
        "token": token,
        "user": {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
        }
    }
