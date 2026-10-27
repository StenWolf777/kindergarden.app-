REPORT = {
    "week_start": "2026-10-19", "week_end": "2026-10-23", "child_count": 90,
    "items": [
        {"name": "Ун", "quantity": 8, "unit_price": 12000},
        {"name": "Нон", "quantity": 60, "unit_price": 3500},
    ],
}


def test_create_report_computes_total_and_cost_per_child(client, auth_headers):
    res = client.post("/api/v1/kitchen/reports", json=REPORT, headers=auth_headers("accountant"))
    assert res.status_code == 200
    body = res.json()
    assert body["total_amount"] == 8 * 12000 + 60 * 3500
    assert body["cost_per_child"] == round(body["total_amount"] / 90, 2)


def test_duplicate_week_is_rejected(client, auth_headers):
    headers = auth_headers("accountant")
    client.post("/api/v1/kitchen/reports", json=REPORT, headers=headers)
    res = client.post("/api/v1/kitchen/reports", json=REPORT, headers=headers)
    assert res.status_code == 400


def test_end_date_before_start_date_is_rejected(client, auth_headers):
    bad = {**REPORT, "week_start": "2026-10-23", "week_end": "2026-10-19"}
    res = client.post("/api/v1/kitchen/reports", json=bad, headers=auth_headers("accountant"))
    assert res.status_code == 400


def test_empty_items_list_is_rejected(client, auth_headers):
    bad = {**REPORT, "items": []}
    res = client.post("/api/v1/kitchen/reports", json=bad, headers=auth_headers("accountant"))
    assert res.status_code == 400


def test_update_recomputes_total_and_keeps_history_to_one_row_per_week(client, auth_headers):
    headers = auth_headers("accountant")
    created = client.post("/api/v1/kitchen/reports", json=REPORT, headers=headers).json()
    updated = {
        **REPORT,
        "child_count": 100,
        "items": [{"name": "Ун", "quantity": 10, "unit_price": 12000}],
    }
    res = client.put(f"/api/v1/kitchen/reports/{created['id']}", json=updated, headers=headers)
    assert res.status_code == 200
    assert res.json()["total_amount"] == 120000
    detail = client.get(f"/api/v1/kitchen/reports/{created['id']}", headers=headers).json()
    assert detail["child_count"] == 100
    assert len(detail["items"]) == 1
    assert len(client.get("/api/v1/kitchen/reports", headers=headers).json()) == 1


def test_only_super_admin_and_accountant_can_manage(client, auth_headers):
    for role in ("director", "teacher", "nurse"):
        res = client.post("/api/v1/kitchen/reports", json=REPORT, headers=auth_headers(role))
        assert res.status_code == 403, f"{role} should not be able to create a report"
    for role in ("director", "nurse", "accountant", "super_admin"):
        res = client.get("/api/v1/kitchen/reports", headers=auth_headers(role))
        assert res.status_code == 200, f"{role} should be able to view reports"
    res = client.get("/api/v1/kitchen/reports", headers=auth_headers("teacher"))
    assert res.status_code == 403


def test_delete_removes_report_and_its_items(client, auth_headers):
    headers = auth_headers("accountant")
    created = client.post("/api/v1/kitchen/reports", json=REPORT, headers=headers).json()
    res = client.delete(f"/api/v1/kitchen/reports/{created['id']}", headers=headers)
    assert res.status_code == 200
    assert client.get(f"/api/v1/kitchen/reports/{created['id']}", headers=headers).status_code == 404
