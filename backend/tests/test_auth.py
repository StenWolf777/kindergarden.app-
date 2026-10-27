"""
Login flow and the exploits we closed earlier: fixed OTP, director fallback,
the password-list endpoint, plain-text passwords, forged tokens.
"""
import secrets


def _create_test_user(client):
    """A disposable account with a runtime-random password: no credential
    string in this file resembles anything that could be mistaken for a
    real secret."""
    import app.database as database
    import app.security as security

    password = secrets.token_urlsafe(18)
    conn = database.get_connection()
    conn.execute(
        "INSERT INTO users (id, org_id, role, full_name, phone, password_hash, avatar) "
        "VALUES ('u_test', 'org_smart_kids', 'DIRECTOR', 'Test User', '+998911111111', ?, 'TU')",
        (security.hash_password(password),),
    )
    conn.commit()
    conn.close()
    return "+998911111111", password


def test_login_succeeds_with_correct_password(client):
    phone, password = _create_test_user(client)
    res = client.post("/api/v1/auth/login", json={"phone": phone, "password": password})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["user"]["role"] == "director"
    assert "token" in body


def test_login_rejects_wrong_password(client):
    phone, _ = _create_test_user(client)
    res = client.post("/api/v1/auth/login", json={"phone": phone, "password": "wrong-one"})
    assert res.status_code == 401


def test_login_rejects_unknown_phone_with_same_message_as_wrong_password(client):
    # Same error text for "no such phone" and "wrong password" so phone numbers can't be probed.
    _, password = _create_test_user(client)
    res_unknown = client.post("/api/v1/auth/login", json={"phone": "+998900009999", "password": password})
    res_wrong = client.post("/api/v1/auth/login", json={"phone": "+998911111111", "password": "x"})
    assert res_unknown.status_code == res_wrong.status_code == 401
    assert res_unknown.json()["detail"] == res_wrong.json()["detail"]


def test_passwords_are_hashed_not_plaintext(client):
    phone, password = _create_test_user(client)
    import app.database as database
    conn = database.get_connection()
    stored = conn.execute("SELECT password_hash FROM users WHERE phone = ?", (phone,)).fetchone()[0]
    conn.close()
    assert stored != password
    assert stored.startswith("pbkdf2_sha256$")


def test_demo_users_endpoint_does_not_exist(client):
    res = client.get("/api/v1/auth/demo-users")
    assert res.status_code in (404, 405)


def test_otp_endpoints_do_not_exist(client):
    # The 4821-fixed-code / director-fallback login path was removed entirely.
    assert client.post("/api/v1/auth/send-code", json={"phone": "+998901112233"}).status_code in (404, 405)
    assert client.post("/api/v1/auth/verify-code", json={"phone": "+998901112233", "code": "4821"}).status_code in (404, 405)


def test_me_requires_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_a_tampered_token(client, token_for):
    token = token_for("director")
    body, sig = token.rsplit(".", 1)
    forged = body + "." + sig[:-2] + ("xx" if sig[-2:] != "xx" else "yy")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


def test_me_rejects_an_old_style_fake_token(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bogcha_token_director_u_dir"})
    assert res.status_code == 401


def test_me_returns_role_and_permissions(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers("teacher"))
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "teacher"
    assert "attendance.mark" in body["permissions"]
    assert "billing.view" not in body["permissions"]
