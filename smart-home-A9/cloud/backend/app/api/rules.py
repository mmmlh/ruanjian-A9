"""
联动规则 CRUD
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.database.connection import get_db
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/rules", tags=["联动规则"])


class RuleCreate(BaseModel):
    name: str
    condition_json: str
    action_json: str
    enabled: int = 1


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    condition_json: Optional[str] = None
    action_json: Optional[str] = None
    enabled: Optional[int] = None


@router.get("")
def list_rules(user: dict = Depends(get_current_user)):
    """规则列表"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM automation_rules ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.post("")
def create_rule(req: RuleCreate, user: dict = Depends(get_current_user)):
    """创建规则"""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO automation_rules (name, condition_json, action_json, enabled) VALUES (?, ?, ?, ?)",
            (req.name, req.condition_json, req.action_json, req.enabled)
        )
        rule_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # 热加载规则
    from app.services.rule_engine import rule_engine
    rule_engine.reload_rules()
    return {"id": rule_id, "name": req.name, "enabled": req.enabled}


@router.put("/{rule_id}")
def update_rule(rule_id: int, req: RuleUpdate, user: dict = Depends(get_current_user)):
    """更新规则"""
    with get_db() as conn:
        rule = conn.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,)).fetchone()
        if rule is None:
            raise HTTPException(status_code=404, detail="规则不存在")
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            return dict(rule)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [rule_id]
        conn.execute(f"UPDATE automation_rules SET {set_clause} WHERE id = ?", values)
    from app.services.rule_engine import rule_engine
    rule_engine.reload_rules()
    return {"id": rule_id, **updates}


@router.delete("/{rule_id}")
def delete_rule(rule_id: int, user: dict = Depends(get_current_user)):
    """删除规则"""
    with get_db() as conn:
        rule = conn.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,)).fetchone()
        if rule is None:
            raise HTTPException(status_code=404, detail="规则不存在")
        conn.execute("DELETE FROM automation_rules WHERE id = ?", (rule_id,))
    from app.services.rule_engine import rule_engine
    rule_engine.reload_rules()
    return {"message": "删除成功"}


@router.post("/{rule_id}/toggle")
def toggle_rule(rule_id: int, user: dict = Depends(get_current_user)):
    """启用/禁用规则"""
    with get_db() as conn:
        rule = conn.execute("SELECT * FROM automation_rules WHERE id = ?", (rule_id,)).fetchone()
        if rule is None:
            raise HTTPException(status_code=404, detail="规则不存在")
        new_enabled = 0 if rule["enabled"] else 1
        conn.execute("UPDATE automation_rules SET enabled = ? WHERE id = ?", (new_enabled, rule_id))
    from app.services.rule_engine import rule_engine
    rule_engine.reload_rules()
    return {"id": rule_id, "enabled": new_enabled}
