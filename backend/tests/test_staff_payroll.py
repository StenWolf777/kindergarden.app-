from datetime import date

from app import payroll
from app.database import get_connection
from tests.conftest import SEED_ORG

# March 2025: 21 weekdays (Mon-Fri), Navro'z on Friday the 21st.
MARCH = [f"2025-03-{d:02d}" for d in range(1, 32) if date(2025, 3, d).weekday() < 5]
RULES = {"late_penalty_pct": 25, "deduction_start": "2025-01-01"}
AFTER_MARCH = "2025-04-15"


def _full_month(status_by_day=None):
    marks = {d: "PRESENT" for d in MARCH}
    marks.update(status_by_day or {})
    return marks


def test_day_rate_is_salary_over_working_days():
    b = payroll.breakdown(2_100_000, None, _full_month(), MARCH, RULES, AFTER_MARCH)
    assert b["working_days"] == 21
    assert b["day_rate"] == 100_000
    assert b["absence_deduction"] == 0 and b["late_deduction"] == 0


def test_unexcused_absence_deducts_a_day_excused_does_not():
    marks = _full_month({"2025-03-03": "ABSENT", "2025-03-04": "EXCUSED"})
    b = payroll.breakdown(2_100_000, None, marks, MARCH, RULES, AFTER_MARCH)
    assert (b["absent_days"], b["excused_days"]) == (1, 1)
    assert b["absence_deduction"] == 100_000


def test_late_deducts_percentage_of_day():
    marks = _full_month({"2025-03-03": "LATE", "2025-03-04": "LATE"})
    b = payroll.breakdown(2_100_000, None, marks, MARCH, RULES, AFTER_MARCH)
    assert b["late_days"] == 2
    assert b["late_deduction"] == 50_000


def test_unmarked_past_working_day_counts_as_absent():
    marks = _full_month()
    del marks["2025-03-05"]
    b = payroll.breakdown(2_100_000, None, marks, MARCH, RULES, AFTER_MARCH)
    assert (b["absent_days"], b["unmarked_days"]) == (1, 1)
    assert b["absence_deduction"] == 100_000


def test_today_and_future_are_not_deducted_until_marked():
    b = payroll.breakdown(2_100_000, None, {}, MARCH, RULES, "2025-03-10")
    # 3,4,5,6,7 are past and unmarked; the 10th (today) and later are not counted yet.
    assert b["absent_days"] == 5


def test_nothing_before_deduction_start_or_hire_date():
    rules = {**RULES, "deduction_start": "2025-03-17"}
    assert payroll.breakdown(2_100_000, None, {}, MARCH, rules, AFTER_MARCH)["absent_days"] == 11
    assert payroll.breakdown(2_100_000, "2025-03-24", {}, MARCH, RULES, AFTER_MARCH)["absent_days"] == 6


def test_holidays_are_not_working_days():
    work = payroll.working_days(2025, 3, {"2025-03-21"})
    assert len(work) == 20 and "2025-03-21" not in work


# ---- API ---------------------------------------------------------------

def _set_rules(client, auth_headers, **overrides):
    body = {"late_penalty_pct": 25, "deduction_start": "2025-01-01", "holidays": [], **overrides}
    res = client.put("/api/v1/settings/payroll", json=body, headers=auth_headers("director"))
    assert res.status_code == 200, res.text
    return res.json()


def _mark_month(staff_id, overrides=None):
    conn = get_connection()
    for d in MARCH:
        status = (overrides or {}).get(d, "PRESENT")
        if status is None:
            continue
        conn.execute("INSERT OR REPLACE INTO staff_attendance (id, org_id, staff_id, date, status) VALUES (?, ?, ?, ?, ?)",
                     (f"sa_{staff_id}_{d}", SEED_ORG, staff_id, d, status))
    conn.commit()
    conn.close()


def _payroll_row(client, auth_headers, staff_id, month="2025-03"):
    body = client.get(f"/api/v1/staff/payroll?month={month}", headers=auth_headers("accountant")).json()
    return next(r for r in body["rows"] if r["staff_id"] == staff_id)


def test_payroll_applies_deductions(client, auth_headers):
    _set_rules(client, auth_headers)
    _mark_month("st_1", {"2025-03-03": "ABSENT", "2025-03-04": "LATE"})
    row = _payroll_row(client, auth_headers, "st_1")
    day = row["base_salary"] / 21
    assert row["absent_days"] == 1 and row["late_days"] == 1
    assert row["absence_deduction"] == round(day)
    assert row["late_deduction"] == round(day * 0.25)
    assert row["total_to_pay"] == row["base_salary"] - row["absence_deduction"] - row["late_deduction"]


def test_paid_month_keeps_its_deduction_and_locks_attendance(client, auth_headers):
    _set_rules(client, auth_headers)
    _mark_month("st_1", {"2025-03-03": "ABSENT"})
    row = _payroll_row(client, auth_headers, "st_1")
    paid = client.post("/api/v1/staff/pay", json={"payroll_id": row["id"], "amount": row["total_to_pay"]},
                       headers=auth_headers("accountant"))
    assert paid.status_code == 200

    res = client.post("/api/v1/staff/attendance/mark", json={"staff_id": "st_1", "status": "PRESENT", "date": "2025-03-03"},
                      headers=auth_headers("accountant"))
    assert res.status_code == 400
    _set_rules(client, auth_headers, late_penalty_pct=90, deduction_start="2025-03-20")
    assert _payroll_row(client, auth_headers, "st_1")["absence_deduction"] == row["absence_deduction"]


def test_past_day_can_be_corrected_and_is_audited(client, auth_headers):
    _set_rules(client, auth_headers)
    _mark_month("st_2", {"2025-03-03": None})
    assert _payroll_row(client, auth_headers, "st_2")["absent_days"] == 1

    res = client.post("/api/v1/staff/attendance/mark", json={"staff_id": "st_2", "status": "EXCUSED", "date": "2025-03-03"},
                      headers=auth_headers("accountant"))
    assert res.status_code == 200
    assert _payroll_row(client, auth_headers, "st_2")["absent_days"] == 0
    log = client.get("/api/v1/audit/log", headers=auth_headers("director")).json()
    assert log[0]["action"] == "staff.attendance.edit"


def test_future_day_cannot_be_marked(client, auth_headers):
    res = client.post("/api/v1/staff/attendance/mark", json={"staff_id": "st_1", "status": "ABSENT", "date": "2999-01-01"},
                      headers=auth_headers("accountant"))
    assert res.status_code == 400


def test_holiday_reduces_working_days_in_payroll(client, auth_headers):
    _set_rules(client, auth_headers, holidays=[{"date": "2025-03-21", "name": "Navro'z"}])
    _mark_month("st_1", {"2025-03-21": None})
    row = _payroll_row(client, auth_headers, "st_1")
    assert row["working_days"] == 20
    assert row["absent_days"] == 0


def test_monthly_staff_sheet(client, auth_headers):
    _set_rules(client, auth_headers)
    _mark_month("st_1", {"2025-03-03": "ABSENT"})
    body = client.get("/api/v1/staff/attendance/month?month=2025-03", headers=auth_headers("accountant")).json()
    st1 = next(s for s in body["staff"] if s["id"] == "st_1")
    assert body["days_in_month"] == 31 and body["working_days"] == 21
    assert st1["days"]["3"] == "ABSENT" and st1["absent_days"] == 1


def test_only_management_can_change_payroll_rules(client, auth_headers):
    body = {"late_penalty_pct": 10, "deduction_start": "2025-01-01", "holidays": []}
    for role in ("accountant", "teacher", "nurse"):
        assert client.put("/api/v1/settings/payroll", json=body, headers=auth_headers(role)).status_code == 403
    assert client.get("/api/v1/settings/payroll", headers=auth_headers("accountant")).status_code == 200
    assert client.put("/api/v1/settings/payroll", json={**body, "late_penalty_pct": 150},
                      headers=auth_headers("director")).status_code == 422


def test_new_database_defaults_protect_untracked_history(client, auth_headers):
    rules = client.get("/api/v1/settings/payroll", headers=auth_headers("director")).json()
    assert rules["late_penalty_pct"] == 25
    assert rules["deduction_start"] > date.today().isoformat()
    assert any(h["date"].endswith("-12-08") for h in rules["holidays"])
