def test_director_can_update_org_info(client, auth_headers):
    res = client.patch("/api/v1/settings/org", json={
        "name": "EXKLUZIV DELUXE", "phone": "+998901234567", "address": "Toshkent sh., Yunusobod",
    }, headers=auth_headers("director"))
    assert res.status_code == 200
    me = client.get("/api/v1/auth/me", headers=auth_headers("director")).json()
    assert me["org"]["name"] == "EXKLUZIV DELUXE"
    assert me["org"]["phone"] == "+998901234567"
    assert me["org"]["address"] == "Toshkent sh., Yunusobod"


def test_empty_name_is_rejected(client, auth_headers):
    res = client.patch("/api/v1/settings/org", json={
        "name": "", "phone": "+998901234567", "address": None,
    }, headers=auth_headers("director"))
    assert res.status_code == 422


def test_only_management_can_update_org_info(client, auth_headers):
    for role in ("accountant", "teacher", "nurse"):
        res = client.patch("/api/v1/settings/org", json={
            "name": "Boshqa nom", "phone": "+998900000000", "address": None,
        }, headers=auth_headers(role))
        assert res.status_code == 403


def test_org_update_is_recorded_in_audit_log(client, auth_headers):
    client.patch("/api/v1/settings/org", json={
        "name": "Yangi Nom", "phone": "+998901234567", "address": None,
    }, headers=auth_headers("super_admin"))
    log = client.get("/api/v1/audit/log", headers=auth_headers("director")).json()
    entry = log[0]
    assert entry["action"] == "settings.update"
    assert entry["changes"]["name"]["new"] == "Yangi Nom"


def test_resubmitting_the_same_values_does_not_add_an_audit_entry(client, auth_headers):
    headers = auth_headers("director")
    current = client.get("/api/v1/auth/me", headers=headers).json()["org"]
    client.patch("/api/v1/settings/org", json={
        "name": current["name"], "phone": current["phone"], "address": current["address"],
    }, headers=headers)
    before = client.get("/api/v1/audit/log", headers=headers).json()
    client.patch("/api/v1/settings/org", json={
        "name": current["name"], "phone": current["phone"], "address": current["address"],
    }, headers=headers)
    after = client.get("/api/v1/audit/log", headers=headers).json()
    assert len(after) == len(before)
