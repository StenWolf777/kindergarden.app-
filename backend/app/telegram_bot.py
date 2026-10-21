"""
Bog'chaOS Telegram Bot & Notifikatsiya Xizmati
Ota-onalarga bolaning davomati, kelgan vaqti, ovqatlanish menyusi va to'lov eslatmalarini yuboradi.
"""
import os
import logging
import httpx
from datetime import datetime

logger = logging.getLogger("bogcha_bot")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "SIMULATED_BOT_TOKEN")

async def send_telegram_message(chat_id: int | str, text: str, parse_mode: str = "HTML") -> bool:
    """
    Telegram Bot API orqali xabar yuborish.
    Agar real BOT_TOKEN berilmagan bo'lsa, xabarni simulyatsiya qilib log qiladi.
    """
    if not BOT_TOKEN or BOT_TOKEN == "SIMULATED_BOT_TOKEN":
        logger.info(f"[SIMULATED TELEGRAM SEND] -> Chat ID: {chat_id} | Xabar: {text[:80]}...")
        return True

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Telegram xabari muvaffaqiyatli yuborildi: {chat_id}")
                return True
            else:
                logger.warning(f"Telegram API xatosi ({resp.status_code}): {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram yuborishda xatolik: {e}")
        return False

async def notify_attendance(child_name: str, group_name: str, status: str, check_in_time: str, parent_phone: str, chat_id: int | None = None):
    """
    Davomat belgilanganda ota-onaga yuboriladigan chiroyli shablon xabarnoma
    """
    target_chat = chat_id or parent_phone

    if status == "PRESENT":
        text = (
            f"🎉 <b>Assalomu alaykum!</b>\n\n"
            f"Farzandingiz <b>{child_name}</b> soat <b>{check_in_time}</b> da <b>{group_name}</b> guruhiga yetib keldi.\n\n"
            f"🥣 <i>Bugungi nonushta: Suli kashasi & pishloqli non.</i>\n"
            f"Kuningiz xayrli va unumli o'tsin!"
        )
    elif status == "ABSENT":
        text = (
            f"⚠️ <b>Bog'chaOS Davomat Eslatmasi</b>\n\n"
            f"Farzandingiz <b>{child_name}</b> bugun bog'chaga kelmadi deb belgilandi.\n"
            f"Agar biror sabab bilan kela olmagan bo'lsangiz, iltimos tarbiyachiga xabar bering."
        )
    elif status == "LATE":
        text = (
            f"🔵 <b>Bog'chaOS Davomat Eslatmasi</b>\n\n"
            f"Farzandingiz <b>{child_name}</b> soat <b>{check_in_time}</b> da <b>{group_name}</b> guruhiga kech keldi."
        )
    else: # EXCUSED
        text = (
            f"ℹ️ <b>Bog'chaOS Ma'lumot</b>\n\n"
            f"Farzandingiz <b>{child_name}</b> bugungi kun uchun sababli kelmadi deb qayd etildi."
        )

    return await send_telegram_message(target_chat, text)

async def notify_debt_reminder(parent_name: str, child_name: str, debt_amount: float, phone: str, chat_id: int | None = None):
    """
    Ota-onaga to'lov muddati haqida xushmuomala eslatma
    """
    target_chat = chat_id or phone
    amount_str = f"{int(debt_amount):,} UZS".replace(",", " ")
    text = (
        f"📋 <b>Bog'cha To'lovi Eslatmasi</b>\n\n"
        f"Hurmatli <b>{parent_name}</b>!\n"
        f"Farzandingiz <b>{child_name}</b>ning joriy oy uchun to'lovi bo'yicha <b>{amount_str}</b> miqdorida to'lov kutilmoqda.\n\n"
        f"To'lovni Click yoki Payme orqali 1 daqiqada onlayn amalga oshirishingiz mumkin:\n"
        f"👉 <a href='https://bogchaos.uz/pay/{child_name}'>Click / Payme orqali to'lash</a>\n\n"
        f"<i>Rahmat! Smart Kids Academy.</i>"
    )
    return await send_telegram_message(target_chat, text)
