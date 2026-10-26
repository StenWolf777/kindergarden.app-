from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.database import get_connection
from app.security import require

router = APIRouter(prefix="/api/v1/staff", tags=["Xodimlar va Ish Haqi"])

class PaySalarySchema(BaseModel):
    payroll_id: str
    amount: float
    bonus: Optional[float] = 0

class StaffAttendanceSchema(BaseModel):
    staff_id: str
    status: str

STAFF_STATUSES = {"PRESENT", "ABSENT", "EXCUSED", "LATE"}


@router.get("/attendance")
def staff_attendance(att_date: Optional[str] = None, user: dict = Depends(require("staff.view"))):
    target = att_date or date.today().isoformat()
    conn = get_connection()
    rows = conn.execute("""
    SELECT s.id, s.name, s.role, sa.status, sa.check_in_time
    FROM staff s
    LEFT JOIN staff_attendance sa ON sa.staff_id = s.id AND sa.date = ?
    WHERE s.org_id = ? AND s.status = 'ACTIVE'
    ORDER BY s.role ASC, s.name ASC
    """, (target, user["org"])).fetchall()
    conn.close()
    return {
        "date": target,
        "editable": target == date.today().isoformat() and "staff.attendance.mark" in user["permissions"],
        "staff": [
            {"id": r["id"], "name": r["name"], "role": r["role"], "status": r["status"], "check_in_time": r["check_in_time"]}
            for r in rows
        ],
    }


@router.post("/attendance/mark")
def mark_staff_attendance(data: StaffAttendanceSchema, user: dict = Depends(require("staff.attendance.mark"))):
    if data.status not in STAFF_STATUSES:
        raise HTTPException(status_code=400, detail="Noma'lum davomat holati")
    org = user["org"]
    conn = get_connection()
    staff = conn.execute("SELECT name FROM staff WHERE id = ? AND org_id = ?", (data.staff_id, org)).fetchone()
    if not staff:
        conn.close()
        raise HTTPException(status_code=404, detail="Xodim topilmadi")
    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M") if data.status in ("PRESENT", "LATE") else None
    conn.execute("""
    INSERT INTO staff_attendance (id, org_id, staff_id, date, status, check_in_time)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(staff_id, date) DO UPDATE SET status = excluded.status, check_in_time = excluded.check_in_time
    """, (f"sa_{data.staff_id}_{today}", org, data.staff_id, today, data.status, now_time))
    conn.commit()
    conn.close()
    return {"success": True, "staff_id": data.staff_id, "status": data.status, "check_in_time": now_time}

@router.get("")
def get_staff_list(user: dict = Depends(require("staff.view"))):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT id, name, role, phone, base_salary, hire_date, status
    FROM staff
    WHERE org_id = ?
    ORDER BY role ASC, name ASC
    """, (user["org"],))
    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "role": r["role"],
            "phone": r["phone"],
            "salary": r["base_salary"],
            "hire_date": r["hire_date"],
            "status": r["status"]
        }
        for r in rows
    ]

@router.get("/payroll")
def get_payroll(month: str = "2026-10", user: dict = Depends(require("staff.view"))):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT pr.id, pr.month, pr.base_salary, pr.bonus, pr.advance_paid, pr.final_paid,
           pr.status, pr.paid_date, s.name as staff_name, s.role, s.phone
    FROM staff_payroll pr
    JOIN staff s ON pr.staff_id = s.id
    WHERE pr.month = ? AND pr.org_id = ?
    ORDER BY pr.status DESC, s.name ASC
    """, (month, user["org"]))
    rows = c.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "staff_name": r["staff_name"],
            "role": r["role"],
            "phone": r["phone"],
            "month": r["month"],
            "base_salary": r["base_salary"],
            "bonus": r["bonus"],
            "advance_paid": r["advance_paid"],
            "final_paid": r["final_paid"],
            "status": r["status"],
            "paid_date": r["paid_date"],
            "total_to_pay": r["base_salary"] + r["bonus"] - r["advance_paid"]
        }
        for r in rows
    ]

@router.post("/pay")
def pay_salary(data: PaySalarySchema, user: dict = Depends(require("staff.pay"))):
    if data.amount < 0:
        raise HTTPException(status_code=400, detail="Summa manfiy bo'lishi mumkin emas")

    org = user["org"]
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    SELECT pr.status, s.name, s.role FROM staff_payroll pr
    JOIN staff s ON pr.staff_id = s.id
    WHERE pr.id = ? AND pr.org_id = ?
    """, (data.payroll_id, org))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Maosh yozuvi topilmadi")
    if row["status"] == "PAID":
        conn.close()
        raise HTTPException(status_code=400, detail="Bu oylik allaqachon to'langan")

    today = date.today().isoformat()
    c.execute("""
    UPDATE staff_payroll
    SET status = 'PAID', paid_date = ?, final_paid = ?
    WHERE id = ? AND org_id = ?
    """, (today, data.amount, data.payroll_id, org))

    c.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '💵', ?)",
              (org, f"{row['name']} ({row['role']}) uchun oylik maosh to'landi."))

    conn.commit()
    conn.close()

    return {"success": True}
