from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_connection
from app.security import require
from app import audit

router = APIRouter(prefix="/api/v1/settings", tags=["Sozlamalar"])


class OrgUpdateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=1, max_length=40)
    address: str | None = None


@router.patch("/org")
def update_org(data: OrgUpdateSchema, user: dict = Depends(require("settings.manage"))):
    org = user["org"]
    conn = get_connection()
    before = conn.execute(
        "SELECT name, phone, address FROM organizations WHERE id = ?", (org,)
    ).fetchone()
    if not before:
        conn.close()
        raise HTTPException(status_code=404, detail="Tashkilot topilmadi")

    name = data.name.strip()
    phone = data.phone.strip()
    address = (data.address or "").strip() or None

    conn.execute(
        "UPDATE organizations SET name = ?, phone = ?, address = ? WHERE id = ?",
        (name, phone, address, org),
    )
    changes = audit.diff(dict(before), {"name": name, "phone": phone, "address": address})
    if changes:
        conn.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '⚙️', ?)",
                     (org, "Tashkilot ma'lumotlari yangilandi."))
        audit.record(conn, user, "settings.update", "organization", org, name, changes)

    conn.commit()
    conn.close()
    return {"success": True, "name": name, "phone": phone, "address": address}
