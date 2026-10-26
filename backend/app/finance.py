"""
Billing helpers shared by the dashboard, the payment window and automatic debt reminders.
"""
import asyncio
import html
import json
import logging
from datetime import date, datetime, timedelta

from app.database import get_connection

logger = logging.getLogger("bogcha_finance")

MONTHS_UZ = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
             "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
MONTHS_SHORT = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"]

DEFAULT_TEMPLATE = (
    "Hurmatli ota-ona! {childName} uchun {amount} to'lov muddati {dueDate}. "
    "Iltimos, to'lovni amalga oshiring."
)
TEMPLATE_FIELDS = ("childName", "parentName", "amount", "dueDate", "group")
MAX_SEND_TIMES = 6


def current_period() -> str:
    return date.today().strftime("%Y-%m")


def period_due_date(period: str) -> str:
    return f"{period}-10"


def format_money(amount: float) -> str:
    return f"{int(round(amount or 0)):,}".replace(",", " ") + " so'm"


def format_due(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return f"{d.day}-{MONTHS_UZ[d.month - 1]}"


def child_fee(conn, child_id: str, org: str) -> float:
    row = conn.execute("""
        SELECT COALESCE(ch.monthly_fee, g.monthly_fee) AS fee
        FROM children ch JOIN groups g ON ch.group_id = g.id
        WHERE ch.id = ? AND ch.org_id = ?
    """, (child_id, org)).fetchone()
    return row["fee"] if row else 0


def collection(conn, org: str, period: str | None = None, top: int = 5) -> dict:
    period = period or current_period()
    today = date.today().isoformat()
    totals = conn.execute("""
        SELECT COALESCE(SUM(amount_due), 0) AS due, COALESCE(SUM(amount_paid), 0) AS paid
        FROM invoices WHERE org_id = ? AND billing_period = ?
    """, (org, period)).fetchone()
    overdue = conn.execute("""
        SELECT COUNT(*) AS n, COALESCE(SUM(amount_due - amount_paid), 0) AS amount
        FROM invoices WHERE org_id = ? AND amount_due > amount_paid AND due_date < ?
    """, (org, today)).fetchone()
    debtors = conn.execute("""
        SELECT ch.id, ch.name, g.name AS group_name,
               SUM(inv.amount_due - inv.amount_paid) AS debt, MIN(inv.due_date) AS due_date
        FROM invoices inv
        JOIN children ch ON inv.child_id = ch.id
        JOIN groups g ON ch.group_id = g.id
        WHERE inv.org_id = ? AND inv.amount_due > inv.amount_paid
        GROUP BY ch.id ORDER BY debt DESC LIMIT ?
    """, (org, top)).fetchall()
    due, paid = totals["due"], min(totals["paid"], totals["due"]) if totals["due"] else totals["paid"]
    return {
        "period": period,
        "due": totals["due"],
        "collected": paid,
        "left": max(0, totals["due"] - paid),
        "percent": round(paid / totals["due"] * 100) if totals["due"] else 0,
        "overdue_count": overdue["n"],
        "overdue_amount": overdue["amount"],
        "top_debtors": [
            {"child_id": d["id"], "name": d["name"], "group": d["group_name"], "debt": d["debt"],
             "overdue": bool(d["due_date"] and d["due_date"] < today)}
            for d in debtors
        ],
    }


def income_history(conn, org: str, months: int = 6) -> list[dict]:
    today = date.today().replace(day=1)
    result = []
    for i in range(months - 1, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y:04d}-{m:02d}"
        total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE org_id = ? AND strftime('%Y-%m', paid_at) = ?",
            (org, key),
        ).fetchone()[0]
        result.append({"period": key, "label": MONTHS_SHORT[m - 1], "amount": total})
    return result


# ---------------------------------------------------------------------------
# Automatic debt reminders (sent through the Telegram bot)
# ---------------------------------------------------------------------------

def get_reminder_settings(conn, org: str) -> dict:
    row = conn.execute("SELECT * FROM reminder_settings WHERE org_id = ?", (org,)).fetchone()
    if not row:
        return {"enabled": False, "days_before": 5, "days_after": 5, "times": ["09:00"], "template": DEFAULT_TEMPLATE}
    try:
        times = json.loads(row["times"] or "[]")
    except ValueError:
        times = ["09:00"]
    return {
        "enabled": bool(row["enabled"]),
        "days_before": row["days_before"],
        "days_after": row["days_after"],
        "times": times,
        "template": row["template"] or DEFAULT_TEMPLATE,
    }


def save_reminder_settings(conn, org: str, s: dict) -> None:
    conn.execute("""
        INSERT INTO reminder_settings (org_id, enabled, days_before, days_after, times, template)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(org_id) DO UPDATE SET enabled = excluded.enabled, days_before = excluded.days_before,
            days_after = excluded.days_after, times = excluded.times, template = excluded.template
    """, (org, int(s["enabled"]), s["days_before"], s["days_after"], json.dumps(s["times"]), s["template"]))


def reminder_targets(conn, org: str, settings: dict, today: date | None = None) -> list[dict]:
    """Unpaid invoices whose due date falls inside the reminder window around today."""
    today = today or date.today()
    rows = conn.execute("""
        SELECT inv.id AS invoice_id, inv.due_date, inv.amount_due - inv.amount_paid AS debt,
               ch.name AS child_name, ch.parent_name, ch.parent_chat_id, g.name AS group_name
        FROM invoices inv
        JOIN children ch ON inv.child_id = ch.id
        JOIN groups g ON ch.group_id = g.id
        WHERE inv.org_id = ? AND inv.amount_due > inv.amount_paid AND ch.status = 'ACTIVE'
    """, (org,)).fetchall()
    targets = []
    for r in rows:
        try:
            due = date.fromisoformat(r["due_date"])
        except (TypeError, ValueError):
            continue
        if due - timedelta(days=settings["days_before"]) <= today <= due + timedelta(days=settings["days_after"]):
            targets.append({**dict(r), "overdue": today > due})
    return targets


def reminder_stats(conn, org: str) -> dict:
    settings = get_reminder_settings(conn, org)
    targets = reminder_targets(conn, org, settings)
    total_left = conn.execute(
        "SELECT COALESCE(SUM(amount_due - amount_paid), 0) FROM invoices WHERE org_id = ? AND amount_due > amount_paid",
        (org,),
    ).fetchone()[0]
    return {
        "due_soon": sum(1 for t in targets if not t["overdue"]),
        "overdue": sum(1 for t in targets if t["overdue"]),
        "linked": sum(1 for t in targets if t["parent_chat_id"]),
        "total_left": total_left,
    }


def render_template(template: str, target: dict) -> str:
    values = {
        "childName": target["child_name"],
        "parentName": target["parent_name"] or "ota-ona",
        "amount": format_money(target["debt"]),
        "dueDate": format_due(target["due_date"]),
        "group": target["group_name"],
    }
    text = template
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


async def send_reminders(org: str, slot: str | None = None) -> dict:
    """Send reminders for one organisation. With a slot, each invoice gets at most one message per slot per day."""
    from app import telegram_bot

    conn = get_connection()
    settings = get_reminder_settings(conn, org)
    targets = reminder_targets(conn, org, settings)
    today = date.today().isoformat()
    sent = skipped_unlinked = 0
    for t in targets:
        if not t["parent_chat_id"]:
            skipped_unlinked += 1
            continue
        if slot and conn.execute(
            "SELECT 1 FROM reminder_log WHERE invoice_id = ? AND sent_date = ? AND slot = ?",
            (t["invoice_id"], today, slot),
        ).fetchone():
            continue
        text = html.escape(render_template(settings["template"], t))
        if await telegram_bot.send_telegram_message(t["parent_chat_id"], f"📋 {text}"):
            sent += 1
            conn.execute("INSERT OR IGNORE INTO reminder_log (org_id, invoice_id, sent_date, slot) VALUES (?, ?, ?, ?)",
                         (org, t["invoice_id"], today, slot or "manual"))
    if sent:
        conn.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '📋', ?)",
                     (org, f"To'lov eslatmasi {sent} ta ota-onaga Telegram orqali yuborildi."))
    conn.commit()
    conn.close()
    return {"targets": len(targets), "sent": sent, "unlinked": skipped_unlinked}


async def run_reminder_scheduler(stop: asyncio.Event) -> None:
    """Every 30 s, send due reminders for organisations whose send time has arrived."""
    while not stop.is_set():
        try:
            now = datetime.now().strftime("%H:%M")
            conn = get_connection()
            orgs = conn.execute("SELECT org_id FROM reminder_settings WHERE enabled = 1").fetchall()
            conn.close()
            for row in orgs:
                conn = get_connection()
                settings = get_reminder_settings(conn, row["org_id"])
                conn.close()
                if now in settings["times"]:
                    await send_reminders(row["org_id"], slot=now)
        except Exception:
            logger.exception("Eslatma rejalashtiruvchisida xatolik")
        try:
            await asyncio.wait_for(stop.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass
