from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.database import get_connection
from app.telegram_bot import notify_debt_reminder

router = APIRouter(prefix="/api/v1/billing", tags=["Moliya va To'lovlar"])

class PaymentRecordSchema(BaseModel):
    child_id: str
    amount: float
    payment_method: str = "CLICK" # CASH, CLICK, PAYME

@router.get("/invoices")
def get_invoices(status: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()

    query = """
    SELECT inv.id, inv.invoice_number, inv.billing_period, inv.amount_due, inv.amount_paid,
           inv.status, inv.due_date, ch.id as child_id, ch.name as child_name,
           g.name as group_name, ch.parent_name, ch.parent_phone
    FROM invoices inv
    JOIN children ch ON inv.child_id = ch.id
    JOIN groups g ON ch.group_id = g.id
    """
    params = []

    if status and status != "ALL":
        query += " WHERE inv.status = ?"
        params.append(status)

    query += " ORDER BY inv.amount_due DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    return [
        {
            "invoice_id": r["id"],
            "invoice_number": r["invoice_number"],
            "child_id": r["child_id"],
            "child_name": r["child_name"],
            "group_name": r["group_name"],
            "parent_name": r["parent_name"],
            "parent_phone": r["parent_phone"],
            "amount_due": r["amount_due"],
            "amount_paid": r["amount_paid"],
            "debt": max(0, r["amount_due"] - r["amount_paid"]),
            "status": r["status"],
            "due_date": r["due_date"]
        }
        for r in rows
    ]

@router.post("/record-payment")
def record_payment(data: PaymentRecordSchema):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    SELECT id, amount_due, amount_paid FROM invoices
    WHERE child_id = ? AND billing_period = '2026-10'
    """, (data.child_id,))
    invoice = c.fetchone()
    if not invoice:
        conn.close()
        raise HTTPException(status_code=404, detail="Ushbu bola uchun joriy oy invoysi topilmadi")

    new_paid = invoice["amount_paid"] + data.amount
    new_status = "PAID" if new_paid >= invoice["amount_due"] else "DEBT"

    c.execute("""
    UPDATE invoices SET amount_paid = ?, status = ? WHERE id = ?
    """, (new_paid, new_status, invoice["id"]))

    payment_id = f"pay_{invoice['id']}_{int(date.today().toordinal())}_{data.child_id}"
    c.execute("""
    INSERT INTO payments (id, org_id, child_id, invoice_id, amount, method, paid_at)
    VALUES (?, 'org_smart_kids', ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (payment_id, data.child_id, invoice["id"], data.amount, data.payment_method))

    c.execute("SELECT name FROM children WHERE id = ?", (data.child_id,))
    child = c.fetchone()
    if child:
        c.execute("""
        INSERT INTO activity_logs (org_id, icon, message)
        VALUES ('org_smart_kids', '💰', ?)
        """, (f"{child['name']} uchun {data.amount:,.0f} UZS to'lov qabul qilindi ({data.payment_method}).",))

    conn.commit()
    conn.close()

    return {"success": True, "child_id": data.child_id, "amount_paid": new_paid, "status": new_status}

@router.get("/stats")
def get_finance_stats():
    conn = get_connection()
    c = conn.cursor()

    today = date.today().isoformat()
    year_month = today[:7]
    year = today[:4]

    def sum_payments(date_filter_sql, param):
        c.execute(f"SELECT COALESCE(SUM(amount), 0) FROM payments WHERE {date_filter_sql}", (param,))
        return c.fetchone()[0]

    income_daily = sum_payments("DATE(paid_at) = ?", today)
    income_monthly = sum_payments("strftime('%Y-%m', paid_at) = ?", year_month)
    income_yearly = sum_payments("strftime('%Y', paid_at) = ?", year)

    def sum_expenses(date_filter_sql, param):
        c.execute(f"""
        SELECT COALESCE(SUM(final_paid), 0) FROM staff_payroll
        WHERE status = 'PAID' AND {date_filter_sql}
        """, (param,))
        return c.fetchone()[0]

    expense_daily = sum_expenses("paid_date = ?", today)
    expense_monthly = sum_expenses("strftime('%Y-%m', paid_date) = ?", year_month)
    expense_yearly = sum_expenses("strftime('%Y', paid_date) = ?", year)

    conn.close()

    return {
        "income": {"daily": income_daily, "monthly": income_monthly, "yearly": income_yearly},
        "expenses": {"daily": expense_daily, "monthly": expense_monthly, "yearly": expense_yearly},
        "net": {
            "daily": income_daily - expense_daily,
            "monthly": income_monthly - expense_monthly,
            "yearly": income_yearly - expense_yearly,
        }
    }

@router.post("/remind-debtors")
async def remind_debtors(background_tasks: BackgroundTasks):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    SELECT inv.amount_due - inv.amount_paid as debt, ch.name as child_name,
           ch.parent_name, ch.parent_phone, ch.parent_chat_id
    FROM invoices inv
    JOIN children ch ON inv.child_id = ch.id
    WHERE inv.status = 'DEBT'
    """)
    debtors = c.fetchall()
    conn.close()

    count = 0
    for d in debtors:
        background_tasks.add_task(
            notify_debt_reminder,
            parent_name=d["parent_name"],
            child_name=d["child_name"],
            debt_amount=d["debt"],
            phone=d["parent_phone"],
            chat_id=d["parent_chat_id"]
        )
        count += 1

    return {"success": True, "notified_count": count}
