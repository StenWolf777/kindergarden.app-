from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database import get_connection

router = APIRouter(prefix="/api/v1", tags=["Bolalar va Guruhlar"])

class ChildCreateSchema(BaseModel):
    first_name: str
    last_name: str
    birth_date: str
    group_name: str
    parent_name: str
    parent_phone: str
    allergies: Optional[str] = "Yo'q"

class HealthUpdateSchema(BaseModel):
    health: str

class PricingUpdateSchema(BaseModel):
    discount: Optional[str] = None
    note: Optional[str] = None
    monthly_fee: Optional[float] = None

@router.get("/groups")
def get_groups():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT g.id, g.name, g.age_category, g.capacity, g.teacher_name, g.monthly_fee,
           COUNT(ch.id) as current_count
    FROM groups g
    LEFT JOIN children ch ON g.id = ch.group_id AND ch.status = 'ACTIVE'
    GROUP BY g.id
    """)
    groups = [
        {
            "id": r["id"],
            "name": r["name"],
            "age": r["age_category"],
            "capacity": r["capacity"],
            "count": r["current_count"],
            "teacher": r["teacher_name"],
            "fee": r["monthly_fee"]
        }
        for r in c.fetchall()
    ]
    conn.close()
    return groups

@router.get("/children")
def get_children(group: Optional[str] = None, search: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()
    
    query = """
    SELECT ch.id, ch.name, g.name as group_name, ch.birth_date, ch.parent_name, ch.parent_phone,
           ch.allergies, ch.status, ch.monthly_fee as listed_price, ch.discount, ch.note,
           COALESCE(inv.status, 'PAID') as payment_status,
           COALESCE(inv.amount_due, g.monthly_fee) as fee,
           COALESCE(inv.amount_paid, g.monthly_fee) as paid,
           COALESCE(inv.amount_due - inv.amount_paid, 0) as debt,
           att.status as attendance_status,
           att.check_in_time
    FROM children ch
    JOIN groups g ON ch.group_id = g.id
    LEFT JOIN invoices inv ON ch.id = inv.child_id AND inv.billing_period = '2026-10'
    LEFT JOIN attendance att ON ch.id = att.child_id AND att.date = DATE('now')
    WHERE ch.status = 'ACTIVE'
    """
    params = []

    if group and group != "ALL":
        query += " AND g.name = ?"
        params.append(group)

    if search:
        query += " AND (ch.name LIKE ? OR ch.parent_name LIKE ? OR ch.parent_phone LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    query += " ORDER BY CAST(SUBSTR(ch.id, 2) AS INTEGER) ASC"
    c.execute(query, params)
    
    children = []
    for r in c.fetchall():
        children.append({
            "id": r["id"],
            "name": r["name"],
            "group": r["group_name"],
            "birthDate": r["birth_date"],
            "parentName": r["parent_name"],
            "parentPhone": r["parent_phone"],
            "allergies": r["allergies"],
            "status": r["status"],
            "listedPrice": r["listed_price"],
            "discount": r["discount"],
            "note": r["note"],
            "paymentStatus": r["payment_status"],
            "fee": r["fee"],
            "paid": r["paid"],
            "debt": r["debt"],
            "attendance": r["attendance_status"] or "ABSENT",
            "checkInTime": r["check_in_time"]
        })

    conn.close()
    return children

@router.post("/children")
def create_child(data: ChildCreateSchema):
    conn = get_connection()
    c = conn.cursor()

    # Find group id
    c.execute("SELECT id, monthly_fee FROM groups WHERE name = ?", (data.group_name,))
    group = c.fetchone()
    if not group:
        conn.close()
        raise HTTPException(status_code=400, detail="Guruh topilmadi")

    group_id = group["id"]
    monthly_fee = group["monthly_fee"]

    # Generate new ID
    c.execute("SELECT COUNT(*) FROM children")
    new_id = f"c{c.fetchone()[0] + 1}"
    full_name = f"{data.first_name} {data.last_name}"

    c.execute("""
    INSERT INTO children (id, org_id, group_id, name, birth_date, parent_name, parent_phone, allergies, status)
    VALUES (?, 'org_smart_kids', ?, ?, ?, ?, ?, ?, 'ACTIVE')
    """, (new_id, group_id, full_name, data.birth_date, data.parent_name, data.parent_phone, data.allergies or "Yo'q"))

    # Create first invoice
    inv_id = f"inv_{new_id}"
    c.execute("""
    INSERT INTO invoices (id, org_id, child_id, invoice_number, billing_period, amount_due, amount_paid, status, due_date)
    VALUES (?, 'org_smart_kids', ?, ?, '2026-10', ?, ?, 'PAID', '2026-10-15')
    """, (inv_id, new_id, f"INV-2026-10-{new_id.upper()}", monthly_fee, monthly_fee))

    # Log activity
    c.execute("""
    INSERT INTO activity_logs (org_id, icon, message)
    VALUES ('org_smart_kids', '👶', ?)
    """, (f"Yangi bola: {full_name} ({data.group_name}) ro'yxatdan o'tdi.",))

    conn.commit()
    conn.close()

    return {"success": True, "child_id": new_id, "name": full_name}

@router.delete("/children/{child_id}")
def delete_child(child_id: str):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT name FROM children WHERE id = ?", (child_id,))
    child = c.fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Bola topilmadi")

    for tbl in ["attendance", "invoices", "monthly_tabel", "payments", "child_clubs"]:
        c.execute(f"DELETE FROM {tbl} WHERE child_id = ?", (child_id,))
    c.execute("DELETE FROM children WHERE id = ?", (child_id,))

    c.execute("""
    INSERT INTO activity_logs (org_id, icon, message)
    VALUES ('org_smart_kids', '🗑️', ?)
    """, (f"{child['name']} ro'yxatdan o'chirildi.",))

    conn.commit()
    conn.close()

    return {"success": True, "child_id": child_id}

@router.patch("/children/{child_id}/health")
def update_child_health(child_id: str, data: HealthUpdateSchema):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT name FROM children WHERE id = ?", (child_id,))
    child = c.fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Bola topilmadi")

    c.execute("UPDATE children SET allergies = ? WHERE id = ?", (data.health, child_id))
    c.execute("""
    INSERT INTO activity_logs (org_id, icon, message)
    VALUES ('org_smart_kids', '🩺', ?)
    """, (f"{child['name']} uchun sog'liq holati yangilandi: {data.health}",))

    conn.commit()
    conn.close()

    return {"success": True, "child_id": child_id, "health": data.health}

@router.patch("/children/{child_id}/pricing")
def update_child_pricing(child_id: str, data: PricingUpdateSchema):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT name FROM children WHERE id = ?", (child_id,))
    child = c.fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Bola topilmadi")

    c.execute("""
    UPDATE children SET discount = ?, note = ?, monthly_fee = ? WHERE id = ?
    """, (data.discount, data.note, data.monthly_fee, child_id))

    if data.monthly_fee is not None:
        c.execute("""
        SELECT id, amount_paid FROM invoices WHERE child_id = ? AND billing_period = '2026-10'
        """, (child_id,))
        invoice = c.fetchone()
        if invoice:
            new_status = "DEBT" if data.monthly_fee > invoice["amount_paid"] else "PAID"
            c.execute("""
            UPDATE invoices SET amount_due = ?, status = ? WHERE id = ?
            """, (data.monthly_fee, new_status, invoice["id"]))
        else:
            new_status = "DEBT" if data.monthly_fee > 0 else "PAID"
            c.execute("""
            INSERT INTO invoices (id, org_id, child_id, invoice_number, billing_period, amount_due, amount_paid,
                                   compensation_discount, status, due_date)
            VALUES (?, 'org_smart_kids', ?, ?, '2026-10', ?, 0, 0, ?, '2026-10-10')
            """, (f"inv_{child_id}", child_id, f"INV-2026-10-{child_id.upper()}", data.monthly_fee, new_status))

    c.execute("""
    INSERT INTO activity_logs (org_id, icon, message)
    VALUES ('org_smart_kids', '✏️', ?)
    """, (f"{child['name']} uchun narx/chegirma/izoh yangilandi.",))

    conn.commit()
    conn.close()

    return {"success": True, "child_id": child_id, "discount": data.discount, "note": data.note, "monthly_fee": data.monthly_fee}
