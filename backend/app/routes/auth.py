from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database import get_connection
from app.telegram_bot import send_telegram_message

router = APIRouter(prefix="/api/v1/auth", tags=["Autentifikatsiya"])

# In-memory OTP storage for SMS / Telegram login
OTP_STORAGE = {
    "+998901112233": "4821",
    "+998934445566": "4821",
    "+998941112233": "4821",
}

class LoginSchema(BaseModel):
    phone: str
    password: str

class PhoneSchema(BaseModel):
    phone: str

class VerifyCodeSchema(BaseModel):
    phone: str
    code: str

def clean_phone(p: str) -> str:
    cleaned = "".join(c for c in p if c.isdigit() or c == "+")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned

@router.get("/demo-users")
def get_demo_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, role, full_name, phone, password_hash, avatar FROM users WHERE is_active = 1")
    rows = c.fetchall()
    conn.close()

    role_labels = {
        "DIRECTOR": "👑 Boshqaruvchi (Direktor)",
        "TEACHER": "👩‍🏫 Katta Tarbiyachi",
        "ACCOUNTANT": "💼 Bosh Buxgalter",
    }

    return [
        {
            "id": r["id"],
            "role": r["role"],
            "role_label": role_labels.get(r["role"], r["role"]),
            "name": r["full_name"],
            "phone": r["phone"],
            "password": r["password_hash"],
            "avatar": r["avatar"]
        }
        for r in rows
    ]

@router.post("/login")
def login(data: LoginSchema):
    phone_clean = clean_phone(data.phone)
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    SELECT id, role, full_name, phone, password_hash, avatar
    FROM users
    WHERE phone = ? AND is_active = 1
    """, (phone_clean,))
    user = c.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Ushbu telefon raqam bilan ro'yxatdan o'tgan foydalanuvchi topilmadi")

    if user["password_hash"] != data.password:
        raise HTTPException(status_code=401, detail="Parol noto'g'ri kiritildi")

    # Generate token
    token = f"bogcha_token_{user['role'].lower()}_{user['id']}"

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "role": user["role"].lower(),
            "name": user["full_name"],
            "phone": user["phone"],
            "avatar": user["avatar"]
        }
    }

@router.post("/send-code")
async def send_code(data: PhoneSchema):
    phone_clean = clean_phone(data.phone)
    code = "4821" # Demo fixed OTP
    OTP_STORAGE[phone_clean] = code

    # Send telegram alert simulation
    await send_telegram_message(
        phone_clean,
        f"🔐 <b>Bog'chaOS Kirish Kodi:</b> <code>{code}</code>\nUshbu kodni hech kimga bermang."
    )

    return {
        "success": True,
        "message": f"{phone_clean} raqamiga 4 xonali tasdiq kodi yuborildi.",
        "demo_code": code
    }

@router.post("/verify-code")
def verify_code(data: VerifyCodeSchema):
    phone_clean = clean_phone(data.phone)
    expected_code = OTP_STORAGE.get(phone_clean, "4821")

    if data.code != expected_code:
        raise HTTPException(status_code=400, detail="Tasdiq kodi noto'g'ri")

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT id, role, full_name, phone, avatar
    FROM users
    WHERE phone = ? AND is_active = 1
    """, (phone_clean,))
    user = c.fetchone()
    conn.close()

    if not user:
        # Default fallback to director if new number
        user = {
            "id": "u_dir",
            "role": "DIRECTOR",
            "full_name": "Nodira Azimova",
            "phone": phone_clean,
            "avatar": "NA"
        }

    token = f"bogcha_token_{user['role'].lower()}_{user['id']}"

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "role": user["role"].lower(),
            "name": user["full_name"],
            "phone": user["phone"],
            "avatar": user["avatar"]
        }
    }
