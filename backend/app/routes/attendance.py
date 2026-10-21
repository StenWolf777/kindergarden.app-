from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.database import get_connection
from app.telegram_bot import notify_attendance

router = APIRouter(prefix="/api/v1/attendance", tags=["Davomat"])

class AttendanceUpdateSchema(BaseModel):
    child_id: str
    status: str # 'PRESENT', 'ABSENT', 'EXCUSED', 'LATE'
    notes: Optional[str] = None

@router.get("")
def get_daily_attendance(group_name: Optional[str] = None, att_date: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()
    target_date = att_date or date.today().isoformat()

    query = """
    SELECT ch.id as child_id, ch.name, g.name as group_name, ch.parent_phone,
           att.status, att.check_in_time, att.notes
    FROM children ch
    JOIN groups g ON ch.group_id = g.id
    LEFT JOIN attendance att ON ch.id = att.child_id AND att.date = ?
    WHERE ch.status = 'ACTIVE'
    """
    params = [target_date]

    if group_name and group_name != "ALL":
        query += " AND g.name = ?"
        params.append(group_name)

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    return [
        {
            "child_id": r["child_id"],
            "name": r["name"],
            "group_name": r["group_name"],
            "parent_phone": r["parent_phone"],
            "status": r["status"] or "ABSENT",
            "check_in_time": r["check_in_time"],
            "notes": r["notes"]
        }
        for r in rows
    ]

@router.post("/mark")
async def mark_attendance(data: AttendanceUpdateSchema, background_tasks: BackgroundTasks):
    conn = get_connection()
    c = conn.cursor()

    # Get child info
    c.execute("""
    SELECT ch.name, ch.parent_phone, ch.parent_chat_id, g.name as group_name
    FROM children ch
    JOIN groups g ON ch.group_id = g.id
    WHERE ch.id = ?
    """, (data.child_id,))
    child = c.fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Bola topilmadi")

    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M") if data.status in ("PRESENT", "LATE") else None

    # Upsert attendance
    c.execute("""
    INSERT INTO attendance (id, org_id, child_id, group_name, date, status, check_in_time, notes)
    VALUES (?, 'org_smart_kids', ?, ?, ?, ?, ?, ?)
    ON CONFLICT(child_id, date) DO UPDATE SET
        status = excluded.status,
        check_in_time = excluded.check_in_time,
        notes = excluded.notes
    """, (f"att_{data.child_id}_{today}", data.child_id, child["group_name"], today, data.status, now_time, data.notes))

    # Log activity
    if data.status == "PRESENT":
        c.execute("""
        INSERT INTO activity_logs (org_id, icon, message)
        VALUES ('org_smart_kids', '🚀', ?)
        """, (f"{child['name']} bog'chaga keldi ({now_time}). Telegram xabarnoma jo'natildi.",))

    conn.commit()
    conn.close()

    # Trigger async Telegram Bot notification
    background_tasks.add_task(
        notify_attendance,
        child_name=child["name"],
        group_name=child["group_name"],
        status=data.status,
        check_in_time=now_time or "--:--",
        parent_phone=child["parent_phone"],
        chat_id=child["parent_chat_id"]
    )

    return {
        "success": True,
        "child_id": data.child_id,
        "status": data.status,
        "check_in_time": now_time,
        "telegram_notified": True
    }
