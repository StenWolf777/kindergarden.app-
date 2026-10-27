"""
Test-only login shortcut for the e2e suite: mints a session token for a
seeded demo role without a password, the same way conftest.py does for the
pytest suite. This router is only ever registered when BOGCHA_TEST_MODE=1
(see app/main.py) — the real app never sets that, so this endpoint never
exists outside of a test run against an isolated throwaway database.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.security import create_token

router = APIRouter(prefix="/api/v1/test", tags=["test"])

SEED_USERS = {
    "director": "u_dir",
    "teacher": "u_teacher",
    "accountant": "u_acc",
    "super_admin": "u_superadmin",
    "nurse": "u_nurse2",
}
SEED_ORG = "org_smart_kids"


class LoginRequest(BaseModel):
    role: str


@router.post("/login")
def test_login(data: LoginRequest):
    user_id = SEED_USERS.get(data.role)
    if not user_id:
        raise HTTPException(status_code=400, detail="Unknown role")
    return {"token": create_token(user_id, data.role, SEED_ORG)}
