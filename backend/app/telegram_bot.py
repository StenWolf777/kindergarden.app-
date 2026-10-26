"""
Bog'chaOS Telegram bot.

Sends parents a message when their child's attendance is marked, and links parents to
their children: a parent opens the bot, presses /start and shares their own phone number;
every child whose parent_phone matches gets that parent's chat id. Telegram cannot
message a phone number directly, so unlinked parents receive nothing.
"""
import asyncio
import base64
import hashlib
import hmac
import html
import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger("bogcha_bot")

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_token() -> str | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token and _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "TELEGRAM_BOT_TOKEN":
                token = value.strip()
    if not token or token == "SIMULATED_BOT_TOKEN":
        return None
    return token


BOT_TOKEN = _load_token()
API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None


def bot_enabled() -> bool:
    return BOT_TOKEN is not None


_bot_username: str | None = None


async def bot_username() -> str | None:
    global _bot_username
    if _bot_username or not bot_enabled():
        return _bot_username
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            data = (await client.get(f"{API}/getMe")).json()
        if data.get("ok"):
            _bot_username = data["result"]["username"]
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("getMe xatosi: %s", e)
    return _bot_username


def _invite_signature(child_id: str) -> str:
    from app.security import SECRET_KEY
    digest = hmac.new(SECRET_KEY, f"invite:{child_id}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[:12]).rstrip(b"=").decode()


def invite_payload(child_id: str) -> str:
    """Signed /start payload (Telegram allows 64 chars of [A-Za-z0-9_-])."""
    return f"{child_id}-{_invite_signature(child_id)}"


def _child_from_payload(payload: str) -> str | None:
    child_id, _, sig = payload.rpartition("-")
    if child_id and hmac.compare_digest(sig, _invite_signature(child_id)):
        return child_id
    return None


def _is_chat_id(value) -> bool:
    return value is not None and str(value).lstrip("-").isdigit()


async def send_telegram_message(chat_id, text: str, reply_markup: dict | None = None) -> bool:
    if not bot_enabled():
        logger.info("[TELEGRAM O'CHIRILGAN] %s: %s", chat_id, text[:80])
        return False
    if not _is_chat_id(chat_id):
        return False

    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{API}/sendMessage", json=payload)
        if resp.status_code == 200:
            return True
        logger.warning("Telegram API xatosi (%s): %s", resp.status_code, resp.text[:200])
    except httpx.HTTPError as e:
        logger.error("Telegram yuborishda xatolik: %s", e)
    return False


async def _api(method: str, **params) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(f"{API}/{method}", json=params)
    return resp.json()


async def inspect_chat(address: str) -> dict:
    """Resolve a channel/group (@name, t.me link or numeric id) and check the bot may post there."""
    if not bot_enabled():
        raise ValueError("Telegram bot tokeni sozlanmagan.")
    address = address.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if address.startswith(prefix):
            address = address[len(prefix):].split("/")[0].split("?")[0]
    if not address.lstrip("-").isdigit() and not address.startswith("@"):
        address = "@" + address

    chat = await _api("getChat", chat_id=address)
    if not chat.get("ok"):
        raise ValueError("Kanal yoki guruh topilmadi. Avval botni u yerga qo'shing.")
    chat = chat["result"]
    bot_id = int(BOT_TOKEN.split(":")[0])
    member = await _api("getChatMember", chat_id=chat["id"], user_id=bot_id)
    member = member.get("result", {})
    status = member.get("status")
    if chat["type"] == "channel":
        allowed = status == "creator" or (status == "administrator" and member.get("can_post_messages"))
    else:
        allowed = status in ("creator", "administrator") or (status == "member" and member.get("can_send_photos", True))
    if not allowed:
        raise ValueError("Bot bu yerda xabar yubora olmaydi. Botni administrator qilib, xabar yuborish ruxsatini bering.")
    return {"id": str(chat["id"]), "title": chat.get("title") or address, "username": chat.get("username"), "type": chat["type"]}


async def send_photos(chat_id, images: list[bytes], caption: str = "") -> tuple[bool, str]:
    """Send 1–10 JPEG/PNG images as one post (an album when there are several)."""
    if not bot_enabled():
        return False, "Telegram bot tokeni sozlanmagan."
    caption = caption[:1024]
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            if len(images) == 1:
                data = {"chat_id": str(chat_id)}
                if caption:
                    data["caption"] = caption
                resp = await client.post(f"{API}/sendPhoto", data=data, files={"photo": ("photo.jpg", images[0], "image/jpeg")})
            else:
                media = [{"type": "photo", "media": f"attach://p{i}"} for i in range(len(images))]
                if caption:
                    media[0]["caption"] = caption
                files = {f"p{i}": (f"p{i}.jpg", img, "image/jpeg") for i, img in enumerate(images)}
                resp = await client.post(f"{API}/sendMediaGroup",
                                         data={"chat_id": str(chat_id), "media": json.dumps(media)}, files=files)
        body = resp.json()
        if body.get("ok"):
            return True, ""
        logger.warning("Rasm yuborishda Telegram xatosi: %s", str(body)[:300])
        return False, body.get("description", "Telegram xatosi")
    except (httpx.HTTPError, ValueError) as e:
        logger.error("Rasm yuborishda xatolik: %s", e)
        return False, "Telegram bilan aloqa yo'q."


async def notify_attendance(child_name: str, group_name: str, status: str, check_in_time: str,
                            parent_phone: str, chat_id: int | None = None) -> bool:
    name = html.escape(child_name)
    group = html.escape(group_name)
    messages = {
        "PRESENT": f"✅ <b>Assalomu alaykum!</b>\n\nFarzandingiz <b>{name}</b> soat <b>{check_in_time}</b> da <b>{group}</b> guruhiga yetib keldi.",
        "LATE": f"🕒 <b>Davomat</b>\n\nFarzandingiz <b>{name}</b> soat <b>{check_in_time}</b> da <b>{group}</b> guruhiga kech keldi.",
        "ABSENT": f"❌ <b>Davomat</b>\n\nFarzandingiz <b>{name}</b> bugun bog'chaga kelmadi deb belgilandi.\nAgar sababi bo'lsa, tarbiyachiga xabar bering.",
        "EXCUSED": f"📄 <b>Davomat</b>\n\nFarzandingiz <b>{name}</b> bugun sababli kelmadi deb qayd etildi.",
    }
    text = messages.get(status)
    if not text:
        return False
    return await send_telegram_message(chat_id, text)


async def notify_debt_reminder(parent_name: str, child_name: str, debt_amount: float,
                               phone: str, chat_id: int | None = None) -> bool:
    amount_str = f"{int(debt_amount):,} UZS".replace(",", " ")
    text = (
        f"📋 <b>Bog'cha to'lovi eslatmasi</b>\n\n"
        f"Hurmatli <b>{html.escape(parent_name)}</b>!\n"
        f"Farzandingiz <b>{html.escape(child_name)}</b> uchun joriy oy bo'yicha <b>{amount_str}</b> to'lov kutilmoqda.\n\n"
        f"To'lovni bog'cha kassasida yoki Click / Payme orqali amalga oshirishingiz mumkin. Rahmat!"
    )
    return await send_telegram_message(chat_id, text)


# ---------------------------------------------------------------------------
# Linking parents: /start -> share contact -> chat id saved on their children
# ---------------------------------------------------------------------------

CONTACT_KEYBOARD = {
    "keyboard": [[{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}


def _phone_key(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits[-9:] if len(digits) >= 9 else ""


def link_parent(phone: str, chat_id: int) -> list[str]:
    """Attach chat_id to every child whose parent_phone matches; returns the children's names."""
    from app.database import get_connection

    key = _phone_key(phone)
    if not key:
        return []
    conn = get_connection()
    rows = conn.execute("SELECT id, name, parent_phone FROM children WHERE status = 'ACTIVE'").fetchall()
    matched = [r for r in rows if _phone_key(r["parent_phone"]) == key]
    for r in matched:
        conn.execute("UPDATE children SET parent_chat_id = ? WHERE id = ?", (chat_id, r["id"]))
    conn.commit()
    conn.close()
    return [r["name"] for r in matched]


async def _handle_update(update: dict) -> None:
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    sender = (message.get("from") or {}).get("id")
    if not chat_id or (message.get("chat") or {}).get("type") != "private":
        return

    contact = message.get("contact")
    if contact:
        # Only accept the sender's own number, so nobody can subscribe to someone else's child.
        if contact.get("user_id") != sender:
            await send_telegram_message(chat_id, "Iltimos, o'zingizning telefon raqamingizni tugma orqali yuboring.", CONTACT_KEYBOARD)
            return
        names = link_parent(contact.get("phone_number", ""), chat_id)
        if names:
            listed = "\n".join(f"• {html.escape(n)}" for n in names)
            await send_telegram_message(
                chat_id,
                f"✅ Rahmat! Siz quyidagi farzand(lar)ingiz davomatini olasiz:\n{listed}\n\nFarzandingiz bog'chaga kelganda shu yerga xabar keladi.",
                {"remove_keyboard": True},
            )
        else:
            await send_telegram_message(
                chat_id,
                "Bu raqam bog'cha ro'yxatida topilmadi. Iltimos, bog'cha ma'muriyatiga ota-ona telefon raqamingizni to'g'ri yozib qo'yishlarini so'rang.",
                {"remove_keyboard": True},
            )
        return

    text = (message.get("text") or "").strip()

    # Invite link from the kindergarten: t.me/<bot>?start=<child>-<signature>
    if text.startswith("/start ") and len(text.split(maxsplit=1)) == 2:
        child_id = _child_from_payload(text.split(maxsplit=1)[1].strip())
        if child_id:
            from app.database import get_connection
            conn = get_connection()
            row = conn.execute("SELECT name FROM children WHERE id = ? AND status = 'ACTIVE'", (child_id,)).fetchone()
            if row:
                conn.execute("UPDATE children SET parent_chat_id = ? WHERE id = ?", (chat_id, child_id))
                conn.commit()
            conn.close()
            if row:
                await send_telegram_message(
                    chat_id,
                    f"✅ Ulandingiz! Endi <b>{html.escape(row['name'])}</b> davomati haqida shu yerga xabar keladi.",
                    {"remove_keyboard": True},
                )
                return
        await send_telegram_message(chat_id, "Havola yaroqsiz yoki eskirgan. Bog'chadan yangi havola so'rang.")
        return

    if text:
        await send_telegram_message(
            chat_id,
            "Assalomu alaykum! Bu <b>Bog'chaOS</b> davomat boti.\n\n"
            "Farzandingiz bog'chaga kelgan-kelmagani haqida xabar olish uchun pastdagi tugma orqali telefon raqamingizni yuboring.",
            CONTACT_KEYBOARD,
        )


async def run_polling(stop: asyncio.Event) -> None:
    """Long-poll Telegram for parent messages while the server runs."""
    if not bot_enabled():
        return
    offset = None
    async with httpx.AsyncClient(timeout=40.0) as client:
        while not stop.is_set():
            try:
                params = {"timeout": 25, "allowed_updates": '["message"]'}
                if offset is not None:
                    params["offset"] = offset
                resp = await client.get(f"{API}/getUpdates", params=params)
                data = resp.json()
                if not data.get("ok"):
                    logger.warning("getUpdates xatosi: %s", str(data)[:200])
                    await asyncio.sleep(5)
                    continue
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        await _handle_update(update)
                    except Exception:
                        logger.exception("Telegram xabarini qayta ishlashda xatolik")
            except (httpx.HTTPError, ValueError) as e:
                logger.warning("Telegram bilan aloqa uzildi: %s", e)
                await asyncio.sleep(5)
