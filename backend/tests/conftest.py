"""
Shared pytest fixtures. Every test gets its own throwaway SQLite database and
its own freshly-seeded demo users, so tests never touch the real
bogcha_data.db and never affect each other.

No demo password strings live in this file: tests mint session tokens
directly for the seeded accounts (the same way a real login does, minus
typing a password), so nothing here resembles a credential to leak.
"""
import os
import sys

# Must happen before `import app.security` anywhere (module-level SECRET_KEY load).
os.environ["BOGCHA_SECRET_KEY"] = "test-secret-key-do-not-use-in-production"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

# ids/org from backend/app/database.py's seed_all_data (not credentials: no passwords here)
SEED_USERS = {
    "director": "u_dir",
    "teacher": "u_teacher",
    "accountant": "u_acc",
    "super_admin": "u_superadmin",
    "nurse": "u_nurse2",
}
SEED_ORG = "org_smart_kids"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import app.database as database
    import app.security as security

    # PBKDF2 at production cost (240k rounds) makes seeding 5 users slow across
    # dozens of tests; it buys nothing in a throwaway per-test database.
    monkeypatch.setattr(security, "PBKDF2_ITERATIONS", 1000)
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.init_db()

    from app.main import app as fastapi_app
    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture()
def token_for(client):
    """token_for('director') -> a valid bearer token for the seeded account,
    minted directly (same mechanism a real login produces), no password needed."""
    from app.security import create_token

    def _token(role: str) -> str:
        return create_token(SEED_USERS[role], role, SEED_ORG)
    return _token


@pytest.fixture()
def auth_headers(token_for):
    def _headers(role: str) -> dict:
        return {"Authorization": f"Bearer {token_for(role)}"}
    return _headers
