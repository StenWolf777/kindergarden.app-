from fastapi import APIRouter
from app.database import get_connection
import json

router = APIRouter(prefix="/api/v1/tabel", tags=["Oylik Tabel"])

@router.get("")
def get_monthly_tabel(group_name: str = "Yulduzcha", month: str = "2026-10"):
    conn = get_connection()
    c = conn.cursor()

    query = """
    SELECT ch.id as child_id, ch.name, g.name as group_name,
           COALESCE(tb.days_json, '{}') as days_json,
           COALESCE(tb.days_present, 20) as days_present,
           COALESCE(tb.days_absent, 0) as days_absent,
           COALESCE(tb.days_excused, 0) as days_excused,
           COALESCE(tb.food_daily_norm, 25000) as food_norm,
           COALESCE(tb.compensation_amount, 0) as compensation
    FROM children ch
    JOIN groups g ON ch.group_id = g.id
    LEFT JOIN monthly_tabel tb ON ch.id = tb.child_id AND tb.month = ?
    WHERE ch.status = 'ACTIVE'
    """
    params = [month]

    if group_name and group_name != "ALL":
        query += " AND g.name = ?"
        params.append(group_name)

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    result = []
    for r in rows:
        try:
            days_dict = json.loads(r["days_json"])
        except:
            days_dict = {}

        result.append({
            "child_id": r["child_id"],
            "name": r["name"],
            "group_name": r["group_name"],
            "days": days_dict,
            "days_present": r["days_present"],
            "days_absent": r["days_absent"],
            "days_excused": r["days_excused"],
            "food_norm": r["food_norm"],
            "compensation": r["compensation"]
        })

    return result
