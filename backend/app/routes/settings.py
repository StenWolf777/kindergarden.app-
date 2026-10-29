from datetime import date

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


class HolidaySchema(BaseModel):
    date: str
    name: str | None = Field(default=None, max_length=120)


class PayrollRulesSchema(BaseModel):
    late_penalty_pct: float = Field(ge=0, le=100)
    deduction_start: str
    holidays: list[HolidaySchema] = Field(default_factory=list, max_length=200)


def _valid_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Sana noto'g'ri formatda: {value}")


def _payroll_rules(conn, org: str) -> dict:
    row = conn.execute(
        "SELECT staff_late_penalty_pct, staff_deduction_start FROM organizations WHERE id = ?", (org,)
    ).fetchone()
    holidays = conn.execute(
        "SELECT date, name FROM org_holidays WHERE org_id = ? ORDER BY date", (org,)
    ).fetchall()
    return {
        "late_penalty_pct": row["staff_late_penalty_pct"],
        "deduction_start": row["staff_deduction_start"],
        "holidays": [{"date": h["date"], "name": h["name"]} for h in holidays],
    }


@router.get("/payroll")
def get_payroll_rules(user: dict = Depends(require("staff.view"))):
    conn = get_connection()
    rules = _payroll_rules(conn, user["org"])
    conn.close()
    return rules


@router.put("/payroll")
def update_payroll_rules(data: PayrollRulesSchema, user: dict = Depends(require("settings.manage"))):
    org = user["org"]
    start = _valid_date(data.deduction_start)
    holidays = {}
    for h in data.holidays:
        holidays[_valid_date(h.date)] = (h.name or "").strip() or None

    conn = get_connection()
    before = _payroll_rules(conn, org)
    conn.execute(
        "UPDATE organizations SET staff_late_penalty_pct = ?, staff_deduction_start = ? WHERE id = ?",
        (data.late_penalty_pct, start, org),
    )
    conn.execute("DELETE FROM org_holidays WHERE org_id = ?", (org,))
    conn.executemany("INSERT INTO org_holidays (org_id, date, name) VALUES (?, ?, ?)",
                     [(org, d, n) for d, n in sorted(holidays.items())])

    changes = audit.diff(
        {"late_penalty_pct": before["late_penalty_pct"], "deduction_start": before["deduction_start"],
         "holidays": ", ".join(h["date"] for h in before["holidays"])},
        {"late_penalty_pct": data.late_penalty_pct, "deduction_start": start,
         "holidays": ", ".join(sorted(holidays))},
    )
    if changes:
        audit.record(conn, user, "settings.payroll", "organization", org, "Maosh qoidalari", changes)
    conn.commit()
    rules = _payroll_rules(conn, org)
    conn.close()
    return rules
