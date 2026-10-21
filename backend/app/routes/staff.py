from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.database import get_connection

router = APIRouter(prefix="/api/v1/staff", tags=["Xodimlar va Ish Haqi"])

class PaySalarySchema(BaseModel):
    payroll_id: str
    amount: float
    bonus: Optional[float] = 0

@router.get("")
def get_staff_list():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT id, name, role, phone, base_salary, hire_date, status
    FROM staff
    ORDER BY role ASC, name ASC
    """)
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
def get_payroll(month: str = "2026-10"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT pr.id, pr.month, pr.base_salary, pr.bonus, pr.advance_paid, pr.final_paid,
           pr.status, pr.paid_date, s.name as staff_name, s.role, s.phone
    FROM staff_payroll pr
    JOIN staff s ON pr.staff_id = s.id
    WHERE pr.month = ?
    ORDER BY pr.status DESC, s.name ASC
    """, (month,))
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
def pay_salary(data: PaySalarySchema):
    conn = get_connection()
    c = conn.cursor()

    today = date.today().isoformat()
    c.execute("""
    UPDATE staff_payroll
    SET status = 'PAID', paid_date = ?, final_paid = ?
    WHERE id = ?
    """, (today, data.amount, data.payroll_id))

    c.execute("""
    SELECT s.name, s.role FROM staff_payroll pr
    JOIN staff s ON pr.staff_id = s.id
    WHERE pr.id = ?
    """, (data.payroll_id,))
    row = c.fetchone()
    if row:
        c.execute("""
        INSERT INTO activity_logs (org_id, icon, message)
        VALUES ('org_smart_kids', '💵', ?)
        """, (f"{row['name']} ({row['role']}) uchun oylik maosh to'landi.",))

    conn.commit()
    conn.close()

    return {"success": True}
