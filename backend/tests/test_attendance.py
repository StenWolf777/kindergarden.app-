from datetime import date


def test_mark_present_sets_check_in_time(client, auth_headers):
    res = client.post("/api/v1/attendance/mark", json={"child_id": "c1", "status": "PRESENT"},
                       headers=auth_headers("teacher"))
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "PRESENT"
    assert body["check_in_time"] is not None


def test_mark_absent_has_no_check_in_time(client, auth_headers):
    res = client.post("/api/v1/attendance/mark", json={"child_id": "c1", "status": "ABSENT"},
                       headers=auth_headers("teacher"))
    assert res.status_code == 200
    assert res.json()["check_in_time"] is None


def test_unknown_status_is_rejected(client, auth_headers):
    res = client.post("/api/v1/attendance/mark", json={"child_id": "c1", "status": "SLEEPING"},
                       headers=auth_headers("teacher"))
    assert res.status_code == 400


def test_unknown_child_is_rejected(client, auth_headers):
    res = client.post("/api/v1/attendance/mark", json={"child_id": "does-not-exist", "status": "PRESENT"},
                       headers=auth_headers("teacher"))
    assert res.status_code == 404


def test_accountant_can_view_but_not_mark(client, auth_headers):
    assert client.get("/api/v1/attendance", headers=auth_headers("accountant")).status_code == 200
    res = client.post("/api/v1/attendance/mark", json={"child_id": "c1", "status": "PRESENT"},
                       headers=auth_headers("accountant"))
    assert res.status_code == 403


def test_marking_present_twice_updates_in_place_not_duplicates(client, auth_headers):
    headers = auth_headers("teacher")
    client.post("/api/v1/attendance/mark", json={"child_id": "c1", "status": "ABSENT"}, headers=headers)
    client.post("/api/v1/attendance/mark", json={"child_id": "c1", "status": "PRESENT"}, headers=headers)
    rows = client.get(f"/api/v1/attendance?att_date={date.today().isoformat()}", headers=headers).json()
    matching = [r for r in rows if r["child_id"] == "c1"]
    assert len(matching) == 1
    assert matching[0]["status"] == "PRESENT"


def test_attendance_is_scoped_to_requested_date(client, auth_headers):
    headers = auth_headers("teacher")
    rows = client.get("/api/v1/attendance?att_date=2020-01-01", headers=headers).json()
    assert all(r["status"] is None for r in rows)
