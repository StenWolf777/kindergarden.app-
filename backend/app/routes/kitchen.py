"""
Ошхона харажатлари (weekly kitchen/food expense reports).

Each report logs one week's food purchases, item by item, the same way the
kindergarten's own paper/Excel weekly report does: a product list with quantity
and price, a total, and a cost per child for that week.
"""
import secrets
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import get_connection
from app.security import require

router = APIRouter(prefix="/api/v1/kitchen", tags=["Ошхона"])

MAX_ITEMS = 100


class ExpenseItemSchema(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)


class ExpenseReportSchema(BaseModel):
    week_start: str
    week_end: str
    child_count: int = Field(gt=0)
    items: list[ExpenseItemSchema]


def _validate_dates(week_start: str, week_end: str):
    try:
        start, end = date.fromisoformat(week_start), date.fromisoformat(week_end)
    except ValueError:
        raise HTTPException(status_code=400, detail="Sana noto'g'ri formatda")
    if end < start:
        raise HTTPException(status_code=400, detail="Oxirgi sana boshlang'ich sanadan oldin bo'lishi mumkin emas")


@router.get("/reports")
def list_reports(user: dict = Depends(require("kitchen.view"))):
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.id, r.week_start, r.week_end, r.child_count, r.total_amount,
               COUNT(i.id) AS item_count
        FROM food_expense_reports r
        LEFT JOIN food_expense_items i ON i.report_id = r.id
        WHERE r.org_id = ?
        GROUP BY r.id
        ORDER BY r.week_start DESC
    """, (user["org"],)).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "week_start": r["week_start"],
            "week_end": r["week_end"],
            "child_count": r["child_count"],
            "total_amount": r["total_amount"],
            "cost_per_child": round(r["total_amount"] / r["child_count"], 2) if r["child_count"] else 0,
            "item_count": r["item_count"],
        }
        for r in rows
    ]


@router.get("/reports/{report_id}")
def get_report(report_id: str, user: dict = Depends(require("kitchen.view"))):
    conn = get_connection()
    report = conn.execute(
        "SELECT * FROM food_expense_reports WHERE id = ? AND org_id = ?", (report_id, user["org"])
    ).fetchone()
    if not report:
        conn.close()
        raise HTTPException(status_code=404, detail="Hisobot topilmadi")
    items = conn.execute(
        "SELECT name, quantity, unit_price, line_total FROM food_expense_items WHERE report_id = ? ORDER BY position",
        (report_id,),
    ).fetchall()
    conn.close()
    return {
        "id": report["id"],
        "week_start": report["week_start"],
        "week_end": report["week_end"],
        "child_count": report["child_count"],
        "total_amount": report["total_amount"],
        "cost_per_child": round(report["total_amount"] / report["child_count"], 2) if report["child_count"] else 0,
        "items": [dict(i) for i in items],
    }


@router.post("/reports")
def create_report(data: ExpenseReportSchema, user: dict = Depends(require("kitchen.manage"))):
    _validate_dates(data.week_start, data.week_end)
    if not 1 <= len(data.items) <= MAX_ITEMS:
        raise HTTPException(status_code=400, detail=f"1 dan {MAX_ITEMS} tagacha mahsulot kiriting")

    org = user["org"]
    conn = get_connection()
    if conn.execute(
        "SELECT 1 FROM food_expense_reports WHERE org_id = ? AND week_start = ?", (org, data.week_start)
    ).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Bu hafta uchun hisobot allaqachon mavjud")

    total = round(sum(i.quantity * i.unit_price for i in data.items), 2)
    report_id = f"food_{secrets.token_hex(4)}"
    conn.execute("""
        INSERT INTO food_expense_reports (id, org_id, week_start, week_end, child_count, total_amount, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (report_id, org, data.week_start, data.week_end, data.child_count, total, user["id"]))
    for pos, item in enumerate(data.items, start=1):
        line_total = round(item.quantity * item.unit_price, 2)
        conn.execute("""
            INSERT INTO food_expense_items (id, report_id, position, name, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (f"foodi_{secrets.token_hex(4)}", report_id, pos, item.name.strip(), item.quantity, item.unit_price, line_total))

    conn.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '🍲', ?)",
                 (org, f"Ошхона харажати qo'shildi: {data.week_start} – {data.week_end}, {total:,.0f} so'm.".replace(",", " ")))
    conn.commit()
    conn.close()
    return {"success": True, "id": report_id, "total_amount": total,
            "cost_per_child": round(total / data.child_count, 2)}


@router.put("/reports/{report_id}")
def update_report(report_id: str, data: ExpenseReportSchema, user: dict = Depends(require("kitchen.manage"))):
    _validate_dates(data.week_start, data.week_end)
    if not 1 <= len(data.items) <= MAX_ITEMS:
        raise HTTPException(status_code=400, detail=f"1 dan {MAX_ITEMS} tagacha mahsulot kiriting")

    org = user["org"]
    conn = get_connection()
    report = conn.execute(
        "SELECT week_start FROM food_expense_reports WHERE id = ? AND org_id = ?", (report_id, org)
    ).fetchone()
    if not report:
        conn.close()
        raise HTTPException(status_code=404, detail="Hisobot topilmadi")

    # Changing the week is allowed, but never onto a week another report already owns.
    if data.week_start != report["week_start"]:
        clash = conn.execute(
            "SELECT 1 FROM food_expense_reports WHERE org_id = ? AND week_start = ? AND id != ?",
            (org, data.week_start, report_id),
        ).fetchone()
        if clash:
            conn.close()
            raise HTTPException(status_code=400, detail="Bu hafta uchun boshqa hisobot allaqachon mavjud")

    total = round(sum(i.quantity * i.unit_price for i in data.items), 2)
    conn.execute("""
        UPDATE food_expense_reports SET week_start = ?, week_end = ?, child_count = ?, total_amount = ?
        WHERE id = ?
    """, (data.week_start, data.week_end, data.child_count, total, report_id))
    conn.execute("DELETE FROM food_expense_items WHERE report_id = ?", (report_id,))
    for pos, item in enumerate(data.items, start=1):
        line_total = round(item.quantity * item.unit_price, 2)
        conn.execute("""
            INSERT INTO food_expense_items (id, report_id, position, name, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (f"foodi_{secrets.token_hex(4)}", report_id, pos, item.name.strip(), item.quantity, item.unit_price, line_total))

    conn.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '✏️', ?)",
                 (org, f"Ошхона харажати tahrirlandi: {data.week_start} – {data.week_end}, {total:,.0f} so'm.".replace(",", " ")))
    conn.commit()
    conn.close()
    return {"success": True, "id": report_id, "total_amount": total,
            "cost_per_child": round(total / data.child_count, 2)}


@router.delete("/reports/{report_id}")
def delete_report(report_id: str, user: dict = Depends(require("kitchen.manage"))):
    conn = get_connection()
    report = conn.execute(
        "SELECT week_start, week_end FROM food_expense_reports WHERE id = ? AND org_id = ?",
        (report_id, user["org"]),
    ).fetchone()
    if not report:
        conn.close()
        raise HTTPException(status_code=404, detail="Hisobot topilmadi")
    conn.execute("DELETE FROM food_expense_items WHERE report_id = ?", (report_id,))
    conn.execute("DELETE FROM food_expense_reports WHERE id = ?", (report_id,))
    conn.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '🗑️', ?)",
                 (user["org"], f"Ошхона харажати o'chirildi: {report['week_start']} – {report['week_end']}."))
    conn.commit()
    conn.close()
    return {"success": True}
