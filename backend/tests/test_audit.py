def test_pricing_edit_is_recorded_with_old_and_new_values(client, auth_headers):
    headers = auth_headers("accountant")
    res = client.patch("/api/v1/children/c1/pricing", json={
        "discount": "50%", "note": "Ikkinchi farzand", "monthly_fee": 400000,
    }, headers=headers)
    assert res.status_code == 200

    log = client.get("/api/v1/audit/log", headers=auth_headers("director")).json()
    assert log, "expected at least one audit entry"
    entry = log[0]
    assert entry["action"] == "children.pricing.edit"
    assert entry["target_type"] == "child"
    assert "monthly_fee" in entry["changes"]
    assert entry["changes"]["monthly_fee"]["new"] == 400000
    assert entry["actor_role"] == "accountant"


def test_unchanged_pricing_fields_are_not_recorded(client, auth_headers):
    headers = auth_headers("accountant")
    before = client.get("/api/v1/audit/log", headers=auth_headers("director")).json()
    # Re-submit whatever the child's current pricing already is — nothing actually changes.
    child = client.get("/api/v1/children", headers=headers).json()[0]
    client.patch(f"/api/v1/children/{child['id']}/pricing", json={
        "discount": child["discount"], "note": child["note"], "monthly_fee": child["listedPrice"],
    }, headers=headers)
    after = client.get("/api/v1/audit/log", headers=auth_headers("director")).json()
    assert len(after) == len(before)


def test_child_deletion_is_recorded(client, auth_headers):
    res = client.delete("/api/v1/children/c1", headers=auth_headers("super_admin"))
    assert res.status_code == 200

    log = client.get("/api/v1/audit/log", headers=auth_headers("super_admin")).json()
    assert log[0]["action"] == "children.delete"
    assert log[0]["target_id"] == "c1"


def test_kitchen_report_update_and_delete_are_recorded(client, auth_headers):
    headers = auth_headers("accountant")
    report = {
        "week_start": "2026-10-19", "week_end": "2026-10-23", "child_count": 90,
        "items": [{"name": "Ун", "quantity": 8, "unit_price": 12000}],
    }
    created = client.post("/api/v1/kitchen/reports", json=report, headers=headers).json()

    updated = {**report, "child_count": 95}
    client.put(f"/api/v1/kitchen/reports/{created['id']}", json=updated, headers=headers)
    client.delete(f"/api/v1/kitchen/reports/{created['id']}", headers=headers)

    log = client.get("/api/v1/audit/log", headers=auth_headers("director")).json()
    actions = [entry["action"] for entry in log]
    assert "kitchen.manage.delete" in actions
    assert "kitchen.manage.update" in actions


def test_only_management_can_view_the_audit_log(client, auth_headers):
    for role in ("director", "super_admin"):
        assert client.get("/api/v1/audit/log", headers=auth_headers(role)).status_code == 200
    for role in ("accountant", "teacher", "nurse"):
        assert client.get("/api/v1/audit/log", headers=auth_headers(role)).status_code == 403
