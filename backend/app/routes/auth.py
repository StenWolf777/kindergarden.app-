from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_connection
from app.security import create_token, current_user, permissions_for, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Autentifikatsiya"])


class LoginSchema(BaseModel):
    phone: str
    password: str


def clean_phone(p: str) -> str:
    cleaned = "".join(c for c in p if c.isdigit() or c == "+")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def _find_user(phone: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, org_id, role, full_name, phone, password_hash, avatar FROM users WHERE phone = ? AND is_active = 1",
        (phone,),
    ).fetchone()
    conn.close()
    return row


def _session(user) -> dict:
    role = user["role"].lower()
    return {
        "success": True,
        "token": create_token(user["id"], role, user["org_id"]),
        "user": {
            "id": user["id"],
            "role": role,
            "name": user["full_name"],
            "phone": user["phone"],
            "avatar": user["avatar"],
            "permissions": permissions_for(role),
        },
    }


@router.post("/login")
def login(data: LoginSchema):
    user = _find_user(clean_phone(data.phone))
    # Same message for unknown phone and wrong password, so phone numbers can't be probed.
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Telefon raqam yoki parol noto'g'ri.")
    return _session(user)


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {
        "id": user["id"],
        "role": user["role"],
        "name": user["name"],
        "phone": user["phone"],
        "avatar": user["avatar"],
        "permissions": sorted(user["permissions"]),
    }
