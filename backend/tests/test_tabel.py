from app.database import get_connection
from tests.conftest import SEED_ORG


def _att(child_id, day, status):
    conn = get_connection()
    conn.execute(
        "INSERT INTO attendance (id, org_id, child_id, group_name, date, status) VALUES (?, ?, ?, 'G', ?, ?)",
        (f"att_{child_id}_{day}", SEED_ORG, child_id, day, status),
    )
    conn.commit()
    conn.close()


def _row(rows, child_id):
    return next(r for r in rows if r["child_id"] == child_id)


def test_month_is_built_from_daily_attendance(client, auth_headers):
    _att("c1", "2025-03-03", "PRESENT")
    _att("c1", "2025-03-04", "LATE")
    _att("c1", "2025-03-05", "EXCUSED")
    _att("c1", "2025-03-06", "ABSENT")
    res = client.get("/api/v1/tabel?year=2025&month=3", headers=auth_headers("accountant"))
    assert res.status_code == 200
    body = res.json()
    assert body["days_in_month"] == 31
    row = _row(body["rows"], "c1")
    assert row["days"] == {"3": "PRESENT", "4": "LATE", "5": "EXCUSED", "6": "ABSENT"}
    assert (row["days_present"], row["days_excused"], row["days_absent"]) == (2, 1, 1)
    assert row["compensation"] == 25000


def test_unmarked_month_is_empty_not_invented(client, auth_headers):
    body = client.get("/api/v1/tabel?year=2024&month=2", headers=auth_headers("accountant")).json()
    assert body["days_in_month"] == 29
    for row in body["rows"]:
        assert row["days"] == {}
        assert row["days_present"] == 0


def test_previous_months_stay_separate(client, auth_headers):
    _att("c1", "2025-01-10", "PRESENT")
    _att("c1", "2025-02-10", "EXCUSED")
    jan = _row(client.get("/api/v1/tabel?year=2025&month=1", headers=auth_headers("accountant")).json()["rows"], "c1")
    feb = _row(client.get("/api/v1/tabel?year=2025&month=2", headers=auth_headers("accountant")).json()["rows"], "c1")
    assert jan["days"] == {"10": "PRESENT"}
    assert feb["days"] == {"10": "EXCUSED"}


def test_left_child_still_shows_in_past_period(client, auth_headers):
    _att("c2", "2025-05-12", "PRESENT")
    conn = get_connection()
    conn.execute("UPDATE children SET status = 'ARCHIVED' WHERE id = 'c2'")
    conn.commit()
    conn.close()
    may = client.get("/api/v1/tabel?year=2025&month=5", headers=auth_headers("accountant")).json()["rows"]
    june = client.get("/api/v1/tabel?year=2025&month=6", headers=auth_headers("accountant")).json()["rows"]
    assert any(r["child_id"] == "c2" for r in may)
    assert not any(r["child_id"] == "c2" for r in june)


def test_yearly_summary(client, auth_headers):
    _att("c1", "2025-01-10", "PRESENT")
    _att("c1", "2025-01-11", "EXCUSED")
    _att("c1", "2025-07-01", "PRESENT")
    res = client.get("/api/v1/tabel/year?year=2025", headers=auth_headers("accountant"))
    assert res.status_code == 200
    row = _row(res.json()["rows"], "c1")
    assert set(row["months"]) == {"1", "7"}
    assert row["totals"]["days_present"] == 2
    assert row["totals"]["days_excused"] == 1
    assert row["totals"]["compensation"] == 25000


def test_available_years_include_history(client, auth_headers):
    _att("c1", "2023-09-01", "PRESENT")
    years = client.get("/api/v1/tabel/years", headers=auth_headers("accountant")).json()
    assert 2023 in years
    assert years == sorted(years, reverse=True)


def test_invalid_period_rejected(client, auth_headers):
    assert client.get("/api/v1/tabel?year=2025&month=13", headers=auth_headers("accountant")).status_code == 422


def test_teacher_cannot_view_tabel(client, auth_headers):
    assert client.get("/api/v1/tabel", headers=auth_headers("teacher")).status_code == 403
    assert client.get("/api/v1/tabel/year", headers=auth_headers("teacher")).status_code == 403
