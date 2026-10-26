from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
import re
import secrets
from app import finance
from app.database import get_connection
from app.security import require

router = APIRouter(prefix="/api/v1/billing", tags=["Moliya va To'lovlar"])

VALID_METHODS = {"CASH", "CLICK", "PAYME", "CARD", "TRANSFER", "APP", "UZUM"}
PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

class PaymentRecordSchema(BaseModel):
    child_id: str
    amount: float
    payment_method: str
    period: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=300)

class ReminderSettingsSchema(BaseModel):
    enabled: bool
    days_before: int = Field(ge=0, le=30)
    days_after: int = Field(ge=0, le=60)
    times: list[str]
    template: str = Field(min_length=5, max_length=1000)


def _period(value: Optional[str]) -> str:
    period = value or finance.current_period()
    if not PERIOD_RE.match(period):
        raise HTTPException(status_code=400, detail="Oy noto'g'ri ko'rsatilgan")
    return period


@router.get("/child/{child_id}")
def child_billing(child_id: str, period: Optional[str] = None, user: dict = Depends(require("billing.view"))):
    """Everything the payment window shows for one child and one month."""
    org, period = user["org"], _period(period)
    conn = get_connection()
    child = conn.execute("SELECT name FROM children WHERE id = ? AND org_id = ?", (child_id, org)).fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Bola topilmadi")
    inv = conn.execute("""
        SELECT amount_due, amount_paid, due_date FROM invoices
        WHERE child_id = ? AND billing_period = ? AND org_id = ?
    """, (child_id, period, org)).fetchone()
    fee = finance.child_fee(conn, child_id, org)
    total_debt = conn.execute("""
        SELECT COALESCE(SUM(amount_due - amount_paid), 0) FROM invoices
        WHERE child_id = ? AND org_id = ? AND amount_due > amount_paid
    """, (child_id, org)).fetchone()[0]
    conn.close()

    # A month without a bill owes nothing yet; paying it is a payment in advance.
    due = inv["amount_due"] if inv else fee
    paid = inv["amount_paid"] if inv else 0
    debt = max(0, due - paid) if inv else 0
    due_date = inv["due_date"] if inv else finance.period_due_date(period)
    return {
        "child": child["name"],
        "period": period,
        "fee": fee,
        "amount_due": due,
        "amount_paid": paid,
        "debt": debt,
        "due_date": due_date,
        "overdue": bool(debt and due_date < date.today().isoformat()),
        "has_invoice": inv is not None,
        "total_debt": total_debt,
    }


@router.get("/collection")
def get_collection(period: Optional[str] = None, user: dict = Depends(require("billing.view"))):
    conn = get_connection()
    data = finance.collection(conn, user["org"], _period(period), top=10)
    conn.close()
    return data

@router.get("/invoices")
def get_invoices(status: Optional[str] = None, user: dict = Depends(require("billing.view"))):
    conn = get_connection()
    c = conn.cursor()

    query = """
    SELECT inv.id, inv.invoice_number, inv.billing_period, inv.amount_due, inv.amount_paid,
           inv.status, inv.due_date, ch.id as child_id, ch.name as child_name,
           g.name as group_name, ch.parent_name, ch.parent_phone
    FROM invoices inv
    JOIN children ch ON inv.child_id = ch.id
    JOIN groups g ON ch.group_id = g.id
    WHERE inv.org_id = ?
    """
    params = [user["org"]]

    if status and status != "ALL":
        query += " AND inv.status = ?"
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
def record_payment(data: PaymentRecordSchema, user: dict = Depends(require("billing.record"))):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="To'lov summasi musbat bo'lishi kerak")
    method = data.payment_method.upper()
    if method not in VALID_METHODS:
        raise HTTPException(status_code=400, detail="Noma'lum to'lov usuli")

    org = user["org"]
    period = _period(data.period)
    conn = get_connection()
    c = conn.cursor()

    child = c.execute("SELECT name FROM children WHERE id = ? AND org_id = ?", (data.child_id, org)).fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Bola topilmadi")

    c.execute("""
    SELECT id, amount_due, amount_paid FROM invoices
    WHERE child_id = ? AND billing_period = ? AND org_id = ?
    """, (data.child_id, period, org))
    invoice = c.fetchone()
    advance = invoice is None
    if advance:
        # Paying for a month that has no bill yet: open it at the child's fee.
        inv_id = f"inv_{data.child_id}_{period.replace('-', '')}"
        fee = finance.child_fee(conn, data.child_id, org)
        c.execute("""
        INSERT INTO invoices (id, org_id, child_id, invoice_number, billing_period, amount_due, amount_paid, status, due_date)
        VALUES (?, ?, ?, ?, ?, ?, 0, 'DEBT', ?)
        """, (inv_id, org, data.child_id, f"INV-{period}-{data.child_id.upper()}", period, fee, finance.period_due_date(period)))
        invoice = {"id": inv_id, "amount_due": fee, "amount_paid": 0}

    new_paid = invoice["amount_paid"] + data.amount
    new_status = "PAID" if new_paid >= invoice["amount_due"] else "DEBT"
    c.execute("UPDATE invoices SET amount_paid = ?, status = ? WHERE id = ?", (new_paid, new_status, invoice["id"]))

    note = (data.note or "").strip() or None
    payment_id = f"pay_{invoice['id']}_{secrets.token_hex(4)}"
    c.execute("""
    INSERT INTO payments (id, org_id, child_id, invoice_id, amount, method, paid_at, period, note, recorded_by)
    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
    """, (payment_id, org, data.child_id, invoice["id"], data.amount, method, period, note, user["id"]))

    c.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '💰', ?)",
              (org, f"{child['name']} uchun {data.amount:,.0f} UZS to'lov qabul qilindi ({method}, {period})."))

    conn.commit()
    conn.close()

    return {"success": True, "child_id": data.child_id, "period": period, "amount_paid": new_paid,
            "status": new_status, "advance": advance}

@router.get("/stats")
def get_finance_stats(user: dict = Depends(require("billing.view"))):
    org = user["org"]
    conn = get_connection()
    c = conn.cursor()

    today = date.today().isoformat()
    year_month = today[:7]
    year = today[:4]

    def sum_payments(date_filter_sql, param):
        c.execute(f"SELECT COALESCE(SUM(amount), 0) FROM payments WHERE org_id = ? AND {date_filter_sql}", (org, param))
        return c.fetchone()[0]

    income_daily = sum_payments("DATE(paid_at) = ?", today)
    income_monthly = sum_payments("strftime('%Y-%m', paid_at) = ?", year_month)
    income_yearly = sum_payments("strftime('%Y', paid_at) = ?", year)

    def sum_expenses(date_filter_sql, param):
        c.execute(f"""
        SELECT COALESCE(SUM(final_paid), 0) FROM staff_payroll
        WHERE status = 'PAID' AND org_id = ? AND {date_filter_sql}
        """, (org, param))
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

@router.get("/reminders")
def get_reminders(user: dict = Depends(require("billing.remind"))):
    conn = get_connection()
    settings = finance.get_reminder_settings(conn, user["org"])
    stats = finance.reminder_stats(conn, user["org"])
    conn.close()
    return {"settings": settings, "stats": stats, "fields": list(finance.TEMPLATE_FIELDS),
            "max_times": finance.MAX_SEND_TIMES}


@router.put("/reminders")
def save_reminders(data: ReminderSettingsSchema, user: dict = Depends(require("billing.remind"))):
    times = sorted(set(t.strip() for t in data.times))
    if not 1 <= len(times) <= finance.MAX_SEND_TIMES or not all(TIME_RE.match(t) for t in times):
        raise HTTPException(status_code=400, detail=f"1 dan {finance.MAX_SEND_TIMES} tagacha to'g'ri vaqt kiriting (masalan 09:00).")
    settings = {"enabled": data.enabled, "days_before": data.days_before, "days_after": data.days_after,
                "times": times, "template": data.template.strip()}
    conn = get_connection()
    finance.save_reminder_settings(conn, user["org"], settings)
    conn.commit()
    stats = finance.reminder_stats(conn, user["org"])
    conn.close()
    return {"success": True, "settings": settings, "stats": stats}


@router.post("/remind-debtors")
async def remind_debtors(user: dict = Depends(require("billing.remind"))):
    """Send the reminder now to every parent in the current window (ignores the schedule)."""
    result = await finance.send_reminders(user["org"])
    return {"success": True, **result}
