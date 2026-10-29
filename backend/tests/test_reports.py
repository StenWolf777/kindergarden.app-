from app.database import get_connection
from tests.conftest import SEED_ORG


def _invoice(child_id, period, due, paid):
    inv_id = f"inv_t_{child_id}_{period}"
    conn = get_connection()
    conn.execute("""INSERT INTO invoices (id, org_id, child_id, invoice_number, billing_period, amount_due, amount_paid, status, due_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (inv_id, SEED_ORG, child_id, f"T-{period}-{child_id}", period, due, paid,
                  "PAID" if paid >= due else "DEBT", f"{period}-10"))
    conn.commit()
    conn.close()
    return inv_id


def _payment(child_id, inv_id, amount, paid_at, method="CASH"):
    conn = get_connection()
    conn.execute("""INSERT INTO payments (id, org_id, child_id, invoice_id, amount, method, paid_at, recorded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'u_acc')""",
                 (f"pay_t_{inv_id}_{paid_at}", SEED_ORG, child_id, inv_id, amount, method, paid_at))
    conn.commit()
    conn.close()


def _seed_2025():
    jan_c1 = _invoice("c1", "2025-01", 1_000_000, 1_000_000)
    jan_c2 = _invoice("c2", "2025-01", 800_000, 300_000)
    feb_c1 = _invoice("c1", "2025-02", 1_000_000, 0)
    _payment("c1", jan_c1, 1_000_000, "2025-01-05 10:00:00", "CLICK")
    _payment("c2", jan_c2, 300_000, "2025-02-03 09:00:00")
    return jan_c1, jan_c2, feb_c1


def test_monthly_revenue_for_a_past_year(client, auth_headers):
    _seed_2025()
    body = client.get("/api/v1/reports/revenue?year=2025", headers=auth_headers("accountant")).json()
    jan, feb = body["months"][0], body["months"][1]
    # Received is by payment date; billed/debt is by the month the bill is for.
    assert jan["received"] == 1_000_000 and jan["methods"] == {"CLICK": 1_000_000}
    assert feb["received"] == 300_000
    assert (jan["billed"], jan["billed_paid"], jan["debt"], jan["debtors"]) == (1_800_000, 1_300_000, 500_000, 1)
    assert jan["collection_percent"] == 72
    assert (feb["billed"], feb["debt"]) == (1_000_000, 1_000_000)
    assert body["totals"]["received"] == 1_300_000
    assert body["totals"]["debt"] == 1_500_000
    assert body["months"][5]["collection_percent"] is None


def test_period_balances_and_debtor_filter(client, auth_headers):
    _seed_2025()
    body = client.get("/api/v1/reports/period?period=2025-01", headers=auth_headers("accountant")).json()
    assert body["totals"] == {"due": 1_800_000, "paid": 1_300_000, "debt": 500_000, "debtors": 1, "children": 2}
    assert body["rows"][0]["child_id"] == "c2" and body["rows"][0]["debt"] == 500_000
    assert body["rows"][0]["overdue"] is True

    debtors = client.get("/api/v1/reports/period?period=2025-01&only_debtors=true",
                         headers=auth_headers("accountant")).json()["rows"]
    assert [r["child_id"] for r in debtors] == ["c2"]


def test_child_payment_history(client, auth_headers):
    _seed_2025()
    body = client.get("/api/v1/reports/child/c1", headers=auth_headers("super_admin")).json()
    periods = {p["period"]: p for p in body["periods"]}
    assert periods["2025-02"]["debt"] == 1_000_000 and periods["2025-02"]["payments"] == []
    jan = periods["2025-01"]
    assert jan["debt"] == 0
    assert jan["payments"][0]["amount"] == 1_000_000
    assert jan["payments"][0]["method"] == "CLICK"
    assert jan["payments"][0]["recorded_by"]
    assert body["totals"]["debt"] >= 1_000_000


def test_left_child_history_still_available(client, auth_headers):
    _seed_2025()
    conn = get_connection()
    conn.execute("UPDATE children SET status = 'ARCHIVED' WHERE id = 'c2'")
    conn.commit()
    conn.close()
    rows = client.get("/api/v1/reports/period?period=2025-01", headers=auth_headers("accountant")).json()["rows"]
    c2 = next(r for r in rows if r["child_id"] == "c2")
    assert c2["child_active"] is False
    assert client.get("/api/v1/reports/child/c2", headers=auth_headers("accountant")).status_code == 200


def test_years_include_history(client, auth_headers):
    _seed_2025()
    years = client.get("/api/v1/reports/years", headers=auth_headers("accountant")).json()
    assert 2025 in years


def test_bad_period_and_unknown_child(client, auth_headers):
    h = auth_headers("accountant")
    assert client.get("/api/v1/reports/period?period=2025-13", headers=h).status_code == 400
    assert client.get("/api/v1/reports/child/nope", headers=h).status_code == 404


def test_only_accountant_and_super_admin(client, auth_headers):
    for role in ("director", "teacher", "nurse"):
        for path in ("/api/v1/reports/revenue", "/api/v1/reports/period", "/api/v1/reports/child/c1"):
            assert client.get(path, headers=auth_headers(role)).status_code == 403
    me = client.get("/api/v1/auth/me", headers=auth_headers("director")).json()
    assert "finance.reports" not in me["permissions"]
