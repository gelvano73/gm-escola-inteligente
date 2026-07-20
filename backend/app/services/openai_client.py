from __future__ import annotations

import httpx

from app.core.config import get_settings


async def chat_completion(system: str, user: str) -> str | None:
    settings = get_settings()
    if not settings.OPENAI_ENABLED or not settings.OPENAI_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.ogg") -> str | None:
    settings = get_settings()
    if not settings.OPENAI_ENABLED or not settings.OPENAI_API_KEY:
        return None
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    files = {"file": (filename, audio_bytes, "audio/ogg"), "model": (None, "whisper-1")}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files)
        response.raise_for_status()
        return response.json().get("text")
