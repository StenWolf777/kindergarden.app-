from fastapi import APIRouter
from app.database import get_connection
from datetime import date

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats():
    conn = get_connection()
    c = conn.cursor()

    # Total children
    c.execute("SELECT COUNT(*) FROM children WHERE status = 'ACTIVE'")
    total_children = c.fetchone()[0]

    # Attendance today
    today = date.today().isoformat()
    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'PRESENT'", (today,))
    present_today = c.fetchone()[0]

    # Revenue
    c.execute("SELECT SUM(amount_paid) FROM invoices WHERE billing_period = '2026-10'")
    revenue = c.fetchone()[0] or 0

    # Debts
    c.execute("SELECT SUM(amount_due - amount_paid) FROM invoices WHERE status = 'DEBT'")
    debts = c.fetchone()[0] or 0

    # Recent activities
    c.execute("SELECT icon, message, created_at FROM activity_logs ORDER BY id DESC LIMIT 5")
    activities = [
        {"icon": row["icon"], "text": row["message"], "time": row["created_at"][-8:-3] if row["created_at"] else "09:00"}
        for row in c.fetchall()
    ]

    conn.close()

    att_rate = round((present_today / total_children * 100), 1) if total_children > 0 else 0

    return {
        "total_children": total_children,
        "present_today": present_today,
        "attendance_rate": att_rate,
        "monthly_revenue": revenue,
        "total_debts": debts,
        "activities": activities,
        "weekly_dynamic": [
            {"day": "Dush", "percent": 92},
            {"day": "Sesh", "percent": 89},
            {"day": "Chor", "percent": 94},
            {"day": "Pay", "percent": 90},
            {"day": "Jum", "percent": 91},
            {"day": "Shan", "percent": 78},
        ]
    }
