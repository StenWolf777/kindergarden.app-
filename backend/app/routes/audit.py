import json

from fastapi import APIRouter, Depends

from app.database import get_connection
from app.security import require

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])


@router.get("/log")
def list_audit_log(limit: int = 100, user: dict = Depends(require("audit.view"))):
    limit = max(1, min(limit, 500))
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, actor_name, actor_role, action, target_type, target_id, target_label, changes, created_at
        FROM audit_log
        WHERE org_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user["org"], limit)).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "actor_name": r["actor_name"],
            "actor_role": r["actor_role"],
            "action": r["action"],
            "target_type": r["target_type"],
            "target_id": r["target_id"],
            "target_label": r["target_label"],
            "changes": json.loads(r["changes"]) if r["changes"] else None,
            "created_at": r["created_at"],
        }
        for r in rows
    ]
