import calendar
import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.database import get_connection
from app.security import require

router = APIRouter(prefix="/api/v1/tabel", tags=["Oylik Tabel"])

DEFAULT_FOOD_NORM = 25000
LETTER_STATUS = {"P": "PRESENT", "E": "EXCUSED", "A": "ABSENT", "L": "LATE"}


def _children_for_period(c, org: str, start: str, end: str, group_name: Optional[str]):
    # Children who have since left still appear for the periods they attended.
    query = """
    SELECT ch.id, ch.name, g.name AS group_name
    FROM children ch
    JOIN groups g ON ch.group_id = g.id
    WHERE ch.org_id = ?
      AND (ch.status = 'ACTIVE'
           OR EXISTS (SELECT 1 FROM attendance a
                      WHERE a.child_id = ch.id AND a.date BETWEEN ? AND ?))
    """
    params = [org, start, end]
    if group_name and group_name != "ALL":
        query += " AND g.name = ?"
        params.append(group_name)
    query += " ORDER BY g.name, ch.name"
    return c.execute(query, params).fetchall()


def _attendance_days(c, org: str, start: str, end: str) -> dict:
    """{child_id: {'YYYY-MM-DD': status}} from the daily attendance records."""
    out: dict = {}
    for r in c.execute(
        "SELECT child_id, date, status FROM attendance WHERE org_id = ? AND date BETWEEN ? AND ?",
        (org, start, end),
    ):
        out.setdefault(r["child_id"], {})[r["date"]] = r["status"]
    return out


def _legacy_tabel(c, org: str, months: list[str]) -> dict:
    """{(child_id, 'YYYY-MM'): (days_dict, food_norm)} from the older monthly_tabel sheet."""
    marks = ",".join("?" * len(months))
    out = {}
    for r in c.execute(
        f"SELECT child_id, month, days_json, food_daily_norm FROM monthly_tabel "
        f"WHERE org_id = ? AND month IN ({marks})",
        (org, *months),
    ):
        try:
            days = {int(k): LETTER_STATUS.get(v, v) for k, v in json.loads(r["days_json"]).items()}
        except (TypeError, ValueError):
            days = {}
        out[(r["child_id"], r["month"])] = (days, r["food_daily_norm"] or DEFAULT_FOOD_NORM)
    return out


def _month_days(child_id: str, year: int, month: int, att: dict, legacy: dict):
    """Returns ({day: status}, food_norm). Daily records win; legacy sheet only fills months with none."""
    key = f"{year:04d}-{month:02d}"
    prefix = key + "-"
    days = {int(d[8:]): s for d, s in att.get(child_id, {}).items() if d.startswith(prefix)}
    legacy_days, norm = legacy.get((child_id, key), ({}, DEFAULT_FOOD_NORM))
    if not days:
        days = dict(legacy_days)
    return days, norm


def _summary(days: dict, norm: float) -> dict:
    statuses = list(days.values())
    excused = statuses.count("EXCUSED")
    return {
        "days_present": statuses.count("PRESENT") + statuses.count("LATE"),
        "days_late": statuses.count("LATE"),
        "days_absent": statuses.count("ABSENT"),
        "days_excused": excused,
        "food_norm": norm,
        "compensation": excused * norm,
    }


@router.get("")
def get_monthly_tabel(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    group_name: str = "ALL",
    user: dict = Depends(require("tabel.view")),
):
    today = date.today()
    year, month = year or today.year, month or today.month
    org = user["org"]
    last_day = calendar.monthrange(year, month)[1]
    start, end = f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"

    conn = get_connection()
    c = conn.cursor()
    children = _children_for_period(c, org, start, end, group_name)
    att = _attendance_days(c, org, start, end)
    legacy = _legacy_tabel(c, org, [f"{year:04d}-{month:02d}"])
    conn.close()

    result = []
    for ch in children:
        days, norm = _month_days(ch["id"], year, month, att, legacy)
        result.append({
            "child_id": ch["id"],
            "name": ch["name"],
            "group_name": ch["group_name"],
            "days": {str(d): s for d, s in sorted(days.items())},
            **_summary(days, norm),
        })
    return {"year": year, "month": month, "days_in_month": last_day, "rows": result}


@router.get("/year")
def get_yearly_tabel(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    group_name: str = "ALL",
    user: dict = Depends(require("tabel.view")),
):
    year = year or date.today().year
    org = user["org"]
    start, end = f"{year:04d}-01-01", f"{year:04d}-12-31"

    conn = get_connection()
    c = conn.cursor()
    children = _children_for_period(c, org, start, end, group_name)
    att = _attendance_days(c, org, start, end)
    legacy = _legacy_tabel(c, org, [f"{year:04d}-{m:02d}" for m in range(1, 13)])
    conn.close()

    result = []
    for ch in children:
        months, totals = {}, {"days_present": 0, "days_late": 0, "days_absent": 0, "days_excused": 0, "compensation": 0}
        for m in range(1, 13):
            days, norm = _month_days(ch["id"], year, m, att, legacy)
            if not days:
                continue
            s = _summary(days, norm)
            months[str(m)] = s
            for k in totals:
                totals[k] += s[k]
        result.append({"child_id": ch["id"], "name": ch["name"], "group_name": ch["group_name"],
                       "months": months, "totals": totals})
    return {"year": year, "rows": result}


@router.get("/years")
def get_available_years(user: dict = Depends(require("tabel.view"))):
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT substr(date, 1, 4) AS y FROM attendance WHERE org_id = ?
           UNION SELECT DISTINCT substr(month, 1, 4) FROM monthly_tabel WHERE org_id = ?""",
        (user["org"], user["org"]),
    ).fetchall()
    conn.close()
    years = {int(r["y"]) for r in rows if r["y"] and r["y"].isdigit()}
    years.add(date.today().year)
    return sorted(years, reverse=True)
