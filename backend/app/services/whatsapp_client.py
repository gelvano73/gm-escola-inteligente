from __future__ import annotations

import httpx

from app.core.config import get_settings


async def send_whatsapp_text(phone: str, message: str) -> dict:
    """Envia texto via Meta Cloud API. Em modo demo, apenas registra sucesso local."""
    settings = get_settings()
    phone = "".join(ch for ch in phone if ch.isdigit())
    if not settings.WHATSAPP_ENABLED or not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        return {"ok": True, "mode": "demo", "to": phone, "message": message}

    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message[:4000]},
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def send_whatsapp_text_sync(phone: str, message: str) -> dict:
    settings = get_settings()
    phone = "".join(ch for ch in phone if ch.isdigit())
    if not settings.WHATSAPP_ENABLED or not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        return {"ok": True, "mode": "demo", "to": phone, "message": message}

    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message[:4000]},
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
