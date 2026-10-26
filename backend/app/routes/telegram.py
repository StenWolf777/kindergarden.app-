import base64
import binascii
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import telegram_bot
from app.database import get_connection
from app.security import require

router = APIRouter(prefix="/api/v1/telegram", tags=["Telegram"])

MAX_PHOTOS = 10  # Telegram album limit
MAX_PHOTO_BYTES = 8 * 1024 * 1024


class ChannelSchema(BaseModel):
    address: str


class PhotosSchema(BaseModel):
    target: Literal["channel", "child"]
    child_id: Optional[str] = None
    caption: str = ""
    images: list[str]  # data URLs or bare base64, already resized in the browser


def _channel(org: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT telegram_group_id, telegram_group_title, telegram_group_username FROM organizations WHERE id = ?", (org,)
    ).fetchone()
    conn.close()
    return row


def _decode_image(data: str) -> bytes:
    if data.startswith("data:"):
        data = data.split(",", 1)[-1]
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Rasm fayli buzilgan.")
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Rasm hajmi juda katta (8 MB dan oshmasin).")
    if not (raw.startswith(b"\xff\xd8\xff") or raw.startswith(b"\x89PNG\r\n\x1a\n")):
        raise HTTPException(status_code=400, detail="Faqat JPG yoki PNG rasm yuborish mumkin.")
    return raw


@router.get("/status")
async def status(user: dict = Depends(require("photos.send"))):
    row = _channel(user["org"])
    return {
        "bot": f"@{await telegram_bot.bot_username()}" if telegram_bot.bot_enabled() else None,
        "channel": {
            "linked": bool(row and row["telegram_group_id"]),
            "title": row["telegram_group_title"] if row else None,
            "public": bool(row and row["telegram_group_username"]),
            "username": row["telegram_group_username"] if row else None,
        },
        "can_manage": "telegram.group.manage" in user["permissions"],
    }


@router.post("/channel")
async def connect_channel(data: ChannelSchema, user: dict = Depends(require("telegram.group.manage"))):
    try:
        chat = await telegram_bot.inspect_chat(data.address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    conn = get_connection()
    conn.execute(
        "UPDATE organizations SET telegram_group_id = ?, telegram_group_title = ?, telegram_group_username = ? WHERE id = ?",
        (chat["id"], chat["title"], chat["username"], user["org"]),
    )
    conn.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '📢', ?)",
                 (user["org"], f"Telegram kanal ulandi: {chat['title']}."))
    conn.commit()
    conn.close()
    return {"success": True, "title": chat["title"], "public": bool(chat["username"]), "type": chat["type"]}


@router.post("/photos")
async def send_photos(data: PhotosSchema, user: dict = Depends(require("photos.send"))):
    if not 1 <= len(data.images) <= MAX_PHOTOS:
        raise HTTPException(status_code=400, detail=f"1 dan {MAX_PHOTOS} tagacha rasm tanlang.")
    if len(data.caption) > 1024:
        raise HTTPException(status_code=400, detail="Izoh 1024 belgidan oshmasin.")
    images = [_decode_image(img) for img in data.images]
    org = user["org"]

    if data.target == "channel":
        row = _channel(org)
        if not row or not row["telegram_group_id"]:
            raise HTTPException(status_code=400, detail="Telegram kanal hali ulanmagan.")
        chat_id, where = row["telegram_group_id"], row["telegram_group_title"]
    else:
        conn = get_connection()
        child = conn.execute(
            "SELECT name, parent_chat_id FROM children WHERE id = ? AND org_id = ?", (data.child_id, org)
        ).fetchone()
        conn.close()
        if not child:
            raise HTTPException(status_code=404, detail="Bola topilmadi")
        if not child["parent_chat_id"]:
            raise HTTPException(status_code=400, detail="Bu bolaning ota-onasi Telegram botga ulanmagan.")
        chat_id, where = child["parent_chat_id"], f"{child['name']} ota-onasi"

    ok, error = await telegram_bot.send_photos(chat_id, images, data.caption.strip())
    if not ok:
        raise HTTPException(status_code=502, detail=f"Telegram rasmni qabul qilmadi: {error}")

    conn = get_connection()
    conn.execute("INSERT INTO activity_logs (org_id, icon, message) VALUES (?, '📷', ?)",
                 (org, f"{len(images)} ta rasm yuborildi: {where} ({user['name']})."))
    conn.commit()
    conn.close()
    return {"success": True, "sent": len(images), "to": where}
