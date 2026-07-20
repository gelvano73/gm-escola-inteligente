from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.deps import get_current_user, require_roles
from app.models import User, UserRole, WhatsAppMessage, WhatsAppPerfil, WhatsAppSession
from app.services.assistant import answer_question
from app.services.openai_client import transcribe_audio
from app.services.whatsapp_auth import get_or_create_session, handle_auth_flow
from app.services.whatsapp_client import send_whatsapp_text

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp IA"])


class SimulateRequest(BaseModel):
    phone: str = Field(min_length=8)
    message: str = Field(min_length=1)


class SimulateResponse(BaseModel):
    phone: str
    reply: str
    verificado: bool
    perfil: str
    estado: str


class AlunoChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AlunoChatResponse(BaseModel):
    reply: str


def _log_message(db: Session, phone: str, direcao: str, conteudo: str, tipo: str = "text") -> None:
    db.add(WhatsAppMessage(phone=phone, direcao=direcao, tipo=tipo, conteudo=conteudo, criado_em=datetime.utcnow()))
    db.commit()


def _portal_phone_for_aluno(user: User) -> str:
    # Prefixo 999 evita colisão com telefones reais; só dígitos (exigido pela sessão)
    return f"999{user.id:07d}"


def _ensure_aluno_portal_session(db: Session, user: User) -> WhatsAppSession:
    if not user.aluno:
        raise HTTPException(status_code=400, detail="Perfil de aluno não encontrado")
    phone = _portal_phone_for_aluno(user)
    session = get_or_create_session(db, phone)
    session.perfil = WhatsAppPerfil.ALUNO
    session.verificado = True
    session.estado = "pronto"
    session.user_id = user.id
    session.aluno_id = user.aluno.id
    session.atualizado_em = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


async def process_incoming(
    db: Session, phone: str, text: str, tipo: str = "text", *, deliver: bool = True
) -> str:
    phone = "".join(ch for ch in phone if ch.isdigit())
    _log_message(db, phone, "in", text, tipo)
    session = get_or_create_session(db, phone)
    auth_reply = handle_auth_flow(db, session, text)
    if auth_reply is not None:
        reply = auth_reply
    else:
        reply = await answer_question(db, session, text)
    _log_message(db, phone, "out", reply, "text")
    if deliver:
        await send_whatsapp_text(phone, reply)
    db.refresh(session)
    return reply


@router.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge or 0)
    raise HTTPException(status_code=403, detail="Verificação WhatsApp falhou")


@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    phone = msg.get("from")
                    msg_type = msg.get("type", "text")
                    text = ""
                    if msg_type == "text":
                        text = msg.get("text", {}).get("body", "")
                    elif msg_type == "audio":
                        # Sem download Media ID completo aqui: responde pedindo texto se Whisper não configurado
                        text = "Como meu filho está na escola?"
                        transcribed = None
                        try:
                            # Placeholder: em produção baixar mídia Meta e transcrever
                            transcribed = await transcribe_audio(b"", "audio.ogg")
                        except Exception:
                            transcribed = None
                        if transcribed:
                            text = transcribed
                        else:
                            text = (
                                "[áudio recebido] Ainda não consegui transcrever. "
                                "Envie a pergunta em texto ou configure OPENAI_API_KEY."
                            )
                    if phone and text:
                        await process_incoming(db, phone, text, msg_type)
    except Exception:
        # Sempre 200 para a Meta não reenviar em loop agressivo
        pass
    return {"status": "ok"}


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_chat(payload: SimulateRequest, db: Session = Depends(get_db)):
    """Simulador local do assistente (sem Meta). Útil para testes."""
    phone = "".join(ch for ch in payload.phone if ch.isdigit())
    reply = await process_incoming(db, phone, payload.message, deliver=False)
    session = db.query(WhatsAppSession).filter(WhatsAppSession.phone == phone).first()
    return SimulateResponse(
        phone=phone,
        reply=reply,
        verificado=bool(session and session.verificado),
        perfil=(session.perfil.value if session else "desconhecido"),
        estado=(session.estado if session else "inicio"),
    )


@router.post("/aluno-chat", response_model=AlunoChatResponse)
async def aluno_chat(
    payload: AlunoChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ALUNO)),
):
    """Chat do assistente no portal do aluno (já autenticado via JWT)."""
    session = _ensure_aluno_portal_session(db, current_user)
    phone = session.phone
    text = payload.message.strip()
    _log_message(db, phone, "in", text, "text")
    reply = await answer_question(db, session, text)
    _log_message(db, phone, "out", reply, "text")
    return AlunoChatResponse(reply=reply)


@router.get("/status")
def whatsapp_status(_: User = Depends(require_roles(UserRole.ADMIN))):
    settings = get_settings()
    return {
        "whatsapp_enabled": settings.WHATSAPP_ENABLED,
        "openai_enabled": settings.OPENAI_ENABLED and bool(settings.OPENAI_API_KEY),
        "verify_token_configured": bool(settings.WHATSAPP_VERIFY_TOKEN),
        "phone_number_id": bool(settings.WHATSAPP_PHONE_NUMBER_ID),
        "webhook_path": "/api/whatsapp/webhook",
        "simulate_path": "/api/whatsapp/simulate",
    }


@router.get("/mensagens")
def listar_mensagens(
    phone: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = db.query(WhatsAppMessage).order_by(WhatsAppMessage.id.desc())
    if phone:
        p = "".join(ch for ch in phone if ch.isdigit())
        query = query.filter(WhatsAppMessage.phone == p)
    itens = query.limit(100).all()
    return [
        {
            "id": m.id,
            "phone": m.phone,
            "direcao": m.direcao,
            "tipo": m.tipo,
            "conteudo": m.conteudo,
            "criado_em": m.criado_em.isoformat(),
        }
        for m in itens
    ]
