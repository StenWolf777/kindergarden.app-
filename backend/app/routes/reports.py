from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app import finance
from app.database import get_connection
from app.security import require

router = APIRouter(prefix="/api/v1/reports", tags=["Moliyaviy hisobotlar"])


def _period(value: Optional[str]) -> str:
    period = value or finance.current_period()
    try:
        y, m = period.split("-")
        date(int(y), int(m), 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Oy noto'g'ri ko'rsatilgan (YYYY-MM)")
    return f"{int(y):04d}-{int(m):02d}"


@router.get("/years")
def report_years(user: dict = Depends(require("finance.reports"))):
    org = user["org"]
    conn = get_connection()
    rows = conn.execute("""
        SELECT substr(paid_at, 1, 4) AS y FROM payments WHERE org_id = ?
        UNION SELECT substr(billing_period, 1, 4) FROM invoices WHERE org_id = ?
    """, (org, org)).fetchall()
    conn.close()
    years = {int(r["y"]) for r in rows if r["y"] and r["y"].isdigit()}
    years.add(date.today().year)
    return sorted(years, reverse=True)


@router.get("/revenue")
def monthly_revenue(year: Optional[int] = Query(None, ge=2000, le=2100),
                    user: dict = Depends(require("finance.reports"))):
    """Per month: money actually received that month, and what was billed for that month and is still owed."""
    year = year or date.today().year
    org = user["org"]
    conn = get_connection()
    received = {r["m"]: r for r in conn.execute("""
        SELECT strftime('%m', paid_at) AS m, SUM(amount) AS total, COUNT(*) AS n
        FROM payments WHERE org_id = ? AND strftime('%Y', paid_at) = ?
        GROUP BY m
    """, (org, f"{year:04d}"))}
    methods: dict = {}
    for r in conn.execute("""
        SELECT strftime('%m', paid_at) AS m, method, SUM(amount) AS total
        FROM payments WHERE org_id = ? AND strftime('%Y', paid_at) = ?
        GROUP BY m, method
    """, (org, f"{year:04d}")):
        methods.setdefault(r["m"], {})[r["method"] or "—"] = r["total"]
    billed = {r["m"]: r for r in conn.execute("""
        SELECT substr(billing_period, 6, 2) AS m, SUM(amount_due) AS due,
               SUM(MIN(amount_paid, amount_due)) AS paid,
               SUM(MAX(amount_due - amount_paid, 0)) AS debt,
               SUM(amount_due > amount_paid) AS debtors, COUNT(*) AS invoices
        FROM invoices WHERE org_id = ? AND substr(billing_period, 1, 4) = ?
        GROUP BY m
    """, (org, f"{year:04d}"))}
    conn.close()

    months = []
    totals = {"received": 0, "payments": 0, "billed": 0, "billed_paid": 0, "debt": 0}
    for m in range(1, 13):
        key = f"{m:02d}"
        rc, bl = received.get(key), billed.get(key)
        row = {
            "period": f"{year:04d}-{key}",
            "month": m,
            "received": rc["total"] if rc else 0,
            "payments": rc["n"] if rc else 0,
            "methods": methods.get(key, {}),
            "billed": bl["due"] if bl else 0,
            "billed_paid": bl["paid"] if bl else 0,
            "debt": bl["debt"] if bl else 0,
            "debtors": bl["debtors"] if bl else 0,
            "invoices": bl["invoices"] if bl else 0,
        }
        row["collection_percent"] = round(row["billed_paid"] / row["billed"] * 100) if row["billed"] else None
        months.append(row)
        for k in totals:
            totals[k] += row[k]
    return {"year": year, "months": months, "totals": totals}


@router.get("/period")
def period_balances(period: Optional[str] = None, group_name: str = "ALL", only_debtors: bool = False,
                    user: dict = Depends(require("finance.reports"))):
    """Every child billed for one month: what was due, what has been paid, what is still owed."""
    period = _period(period)
    org = user["org"]
    query = """
        SELECT inv.id AS invoice_id, inv.amount_due, inv.amount_paid, inv.due_date, inv.status,
               ch.id AS child_id, ch.name, ch.status AS child_status, ch.parent_name, ch.parent_phone,
               g.name AS group_name,
               (SELECT MAX(p.paid_at) FROM payments p WHERE p.invoice_id = inv.id) AS last_paid_at
        FROM invoices inv
        JOIN children ch ON inv.child_id = ch.id
        JOIN groups g ON ch.group_id = g.id
        WHERE inv.org_id = ? AND inv.billing_period = ?
    """
    params: list = [org, period]
    if group_name and group_name != "ALL":
        query += " AND g.name = ?"
        params.append(group_name)
    if only_debtors:
        query += " AND inv.amount_due > inv.amount_paid"
    query += " ORDER BY (inv.amount_due - inv.amount_paid) DESC, ch.name"

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    today = date.today().isoformat()
    result = [
        {
            "invoice_id": r["invoice_id"],
            "child_id": r["child_id"],
            "name": r["name"],
            "child_active": r["child_status"] == "ACTIVE",
            "group_name": r["group_name"],
            "parent_name": r["parent_name"],
            "parent_phone": r["parent_phone"],
            "amount_due": r["amount_due"],
            "amount_paid": r["amount_paid"],
            "debt": max(0, r["amount_due"] - r["amount_paid"]),
            "due_date": r["due_date"],
            "overdue": r["amount_due"] > r["amount_paid"] and (r["due_date"] or "") < today,
            "last_paid_at": r["last_paid_at"],
        }
        for r in rows
    ]
    return {
        "period": period,
        "totals": {
            "due": sum(r["amount_due"] for r in result),
            "paid": sum(min(r["amount_paid"], r["amount_due"]) for r in result),
            "debt": sum(r["debt"] for r in result),
            "debtors": sum(1 for r in result if r["debt"] > 0),
            "children": len(result),
        },
        "rows": result,
    }


@router.get("/child/{child_id}")
def child_history(child_id: str, user: dict = Depends(require("finance.reports"))):
    """Full billing history of one child: each month's bill and every payment made against it."""
    org = user["org"]
    conn = get_connection()
    child = conn.execute("""
        SELECT ch.id, ch.name, ch.status, ch.parent_name, ch.parent_phone, g.name AS group_name
        FROM children ch JOIN groups g ON ch.group_id = g.id
        WHERE ch.id = ? AND ch.org_id = ?
    """, (child_id, org)).fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Bola topilmadi")
    invoices = conn.execute("""
        SELECT id, billing_period, amount_due, amount_paid, due_date FROM invoices
        WHERE child_id = ? AND org_id = ? ORDER BY billing_period DESC
    """, (child_id, org)).fetchall()
    payments = conn.execute("""
        SELECT p.id, p.invoice_id, p.amount, p.method, p.paid_at, p.note, u.full_name AS recorded_by
        FROM payments p LEFT JOIN users u ON u.id = p.recorded_by
        WHERE p.child_id = ? AND p.org_id = ? ORDER BY p.paid_at DESC
    """, (child_id, org)).fetchall()
    conn.close()

    by_invoice: dict = {}
    for p in payments:
        by_invoice.setdefault(p["invoice_id"], []).append({
            "id": p["id"], "amount": p["amount"], "method": p["method"], "paid_at": p["paid_at"],
            "note": p["note"], "recorded_by": p["recorded_by"],
        })
    today = date.today().isoformat()
    periods = [
        {
            "period": inv["billing_period"],
            "amount_due": inv["amount_due"],
            "amount_paid": inv["amount_paid"],
            "debt": max(0, inv["amount_due"] - inv["amount_paid"]),
            "due_date": inv["due_date"],
            "overdue": inv["amount_due"] > inv["amount_paid"] and (inv["due_date"] or "") < today,
            "payments": by_invoice.get(inv["id"], []),
        }
        for inv in invoices
    ]
    return {
        "child": {"id": child["id"], "name": child["name"], "active": child["status"] == "ACTIVE",
                  "group_name": child["group_name"], "parent_name": child["parent_name"],
                  "parent_phone": child["parent_phone"]},
        "totals": {
            "due": sum(p["amount_due"] for p in periods),
            "paid": sum(p["amount_paid"] for p in periods),
            "debt": sum(p["debt"] for p in periods),
        },
        "periods": periods,
    }
