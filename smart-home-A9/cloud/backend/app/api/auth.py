"""
认证模块：登录 / 注册 / 获取当前用户
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional

from app.database.connection import get_db
from app.services.security import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ── 请求模型 ──
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


# ── 依赖：从 Header 提取当前用户 ──
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """解析 Authorization: Bearer <token>，返回用户信息"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    return payload


# ── 路由 ──
@router.post("/login")
def login(req: LoginRequest):
    """用户登录，返回 JWT token"""
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


@router.post("/register")
def register(req: RegisterRequest):
    """用户注册"""
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (req.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (req.username, hash_password(req.password))
        )
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    token = create_token(user_id, req.username)
    return {
        "token": token,
        "user": {"id": user_id, "username": req.username, "role": "user"}
    }


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, role, created_at FROM users WHERE id = ?",
            (int(user["sub"]),)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return dict(row)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.put("/change-password")
def change_password(req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """修改密码"""
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    with get_db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (int(user["sub"]),)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not verify_password(req.old_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="原密码错误")
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(req.new_password), int(user["sub"]))
        )
    return {"success": True, "message": "密码修改成功"}
