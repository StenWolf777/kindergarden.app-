def test_child_billing_shows_current_month_fee_with_no_invoice_yet(client, auth_headers):
    res = client.get("/api/v1/billing/child/c1", headers=auth_headers("accountant"))
    assert res.status_code == 200
    body = res.json()
    assert body["debt"] == 0
    assert body["has_invoice"] is False
    assert body["fee"] > 0


def test_record_payment_for_an_unbilled_month_is_an_advance(client, auth_headers):
    headers = auth_headers("accountant")
    before = client.get("/api/v1/billing/child/c1?period=2030-06", headers=headers).json()
    res = client.post("/api/v1/billing/record-payment", json={
        "child_id": "c1", "amount": 100000, "payment_method": "CASH", "period": "2030-06",
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["advance"] is True
    after = client.get("/api/v1/billing/child/c1?period=2030-06", headers=headers).json()
    assert after["amount_paid"] == 100000
    assert before["has_invoice"] is False and after["has_invoice"] is True


def test_record_payment_rejects_negative_amount(client, auth_headers):
    res = client.post("/api/v1/billing/record-payment", json={
        "child_id": "c1", "amount": -5, "payment_method": "CASH", "period": "2030-06",
    }, headers=auth_headers("accountant"))
    assert res.status_code == 400


def test_record_payment_rejects_unknown_method(client, auth_headers):
    res = client.post("/api/v1/billing/record-payment", json={
        "child_id": "c1", "amount": 1000, "payment_method": "BITCOIN", "period": "2030-06",
    }, headers=auth_headers("accountant"))
    assert res.status_code == 400


def test_record_payment_rejects_unknown_child(client, auth_headers):
    res = client.post("/api/v1/billing/record-payment", json={
        "child_id": "does-not-exist", "amount": 1000, "payment_method": "CASH", "period": "2030-06",
    }, headers=auth_headers("accountant"))
    assert res.status_code == 404


def test_a_second_payment_same_month_tops_up_not_replaces(client, auth_headers):
    headers = auth_headers("accountant")
    client.post("/api/v1/billing/record-payment", json={
        "child_id": "c1", "amount": 50000, "payment_method": "CASH", "period": "2030-07",
    }, headers=headers)
    client.post("/api/v1/billing/record-payment", json={
        "child_id": "c1", "amount": 30000, "payment_method": "CLICK", "period": "2030-07",
    }, headers=headers)
    after = client.get("/api/v1/billing/child/c1?period=2030-07", headers=headers).json()
    assert after["amount_paid"] == 80000


def test_teacher_cannot_view_or_record_billing(client, auth_headers):
    headers = auth_headers("teacher")
    assert client.get("/api/v1/billing/child/c1", headers=headers).status_code == 403
    assert client.post("/api/v1/billing/record-payment", json={
        "child_id": "c1", "amount": 1, "payment_method": "CASH",
    }, headers=headers).status_code == 403
