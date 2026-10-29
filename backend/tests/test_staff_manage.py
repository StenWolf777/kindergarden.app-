NEW_STAFF = {"name": "Malika Yusupova", "role": "Тарбиячи", "phone": "+998901234500", "base_salary": 3500000}


def _payroll_names(client, headers):
    return [p["staff_name"] for p in client.get("/api/v1/staff/payroll", headers=headers).json()]


def test_accountant_can_add_staff_and_they_appear_in_payroll(client, auth_headers):
    headers = auth_headers("accountant")
    res = client.post("/api/v1/staff", json=NEW_STAFF, headers=headers)
    assert res.status_code == 200
    assert "Malika Yusupova" in _payroll_names(client, headers)
    assert any(s["name"] == "Malika Yusupova" for s in client.get("/api/v1/staff", headers=headers).json())


def test_removed_staff_disappear_from_lists_and_attendance(client, auth_headers):
    headers = auth_headers("super_admin")
    staff_id = client.post("/api/v1/staff", json=NEW_STAFF, headers=headers).json()["staff_id"]
    assert client.delete(f"/api/v1/staff/{staff_id}", headers=headers).status_code == 200

    assert "Malika Yusupova" not in _payroll_names(client, headers)
    assert all(s["id"] != staff_id for s in client.get("/api/v1/staff", headers=headers).json())
    att = client.get("/api/v1/staff/attendance", headers=headers).json()["staff"]
    assert all(s["id"] != staff_id for s in att)
    assert client.delete(f"/api/v1/staff/{staff_id}", headers=headers).status_code == 404


def test_only_super_admin_and_accountant_can_add_or_remove_staff(client, auth_headers):
    for role in ("director", "teacher", "nurse"):
        assert client.post("/api/v1/staff", json=NEW_STAFF, headers=auth_headers(role)).status_code == 403
    staff_id = client.post("/api/v1/staff", json=NEW_STAFF, headers=auth_headers("accountant")).json()["staff_id"]
    for role in ("director", "teacher", "nurse"):
        assert client.delete(f"/api/v1/staff/{staff_id}", headers=auth_headers(role)).status_code == 403


def test_invalid_staff_input_is_rejected(client, auth_headers):
    headers = auth_headers("accountant")
    assert client.post("/api/v1/staff", json={**NEW_STAFF, "name": ""}, headers=headers).status_code == 422
    assert client.post("/api/v1/staff", json={**NEW_STAFF, "base_salary": -1}, headers=headers).status_code == 422
    assert client.post("/api/v1/staff", json={**NEW_STAFF, "hire_date": "yesterday"}, headers=headers).status_code == 400


def test_add_and_remove_are_audited(client, auth_headers):
    headers = auth_headers("accountant")
    staff_id = client.post("/api/v1/staff", json=NEW_STAFF, headers=headers).json()["staff_id"]
    client.delete(f"/api/v1/staff/{staff_id}", headers=headers)
    actions = [e["action"] for e in client.get("/api/v1/audit/log", headers=auth_headers("director")).json()]
    assert actions[:2] == ["staff.delete", "staff.create"]
