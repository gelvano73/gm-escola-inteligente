from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Aluno, Escola, NotificacaoWhatsApp
from app.services.whatsapp_client import send_whatsapp_text_sync


def _escola_nome(db: Session) -> str:
    escola = db.query(Escola).first()
    return escola.nome if escola else "Escola"


def _phones_for_aluno(db: Session, aluno_id: int) -> list[str]:
    aluno = db.get(Aluno, aluno_id)
    if not aluno:
        return []
    phones = []
    if aluno.responsavel_telefone:
        phones.append("".join(ch for ch in aluno.responsavel_telefone if ch.isdigit()))
    return [p for p in phones if p]


def notify_event(db: Session, phone: str, evento: str, message: str, payload: dict | None = None) -> None:
    phone = "".join(ch for ch in phone if ch.isdigit())
    registro = NotificacaoWhatsApp(
        phone=phone,
        evento=evento,
        payload=json.dumps(payload or {}, ensure_ascii=False),
        enviado=False,
        criado_em=datetime.utcnow(),
    )
    db.add(registro)
    db.commit()
    try:
        send_whatsapp_text_sync(phone, message)
        registro.enviado = True
        db.commit()
    except Exception:
        db.commit()


def notify_nota_lancada(db: Session, aluno_id: int, disciplina: str, total: float) -> None:
    aluno = db.get(Aluno, aluno_id)
    if not aluno:
        return
    nome = aluno.user.nome if aluno.user else aluno.matricula
    escola = _escola_nome(db)
    msg = (
        f"*{escola}*\n"
        f"Nova nota lançada:\n"
        f"Aluno: {nome}\n"
        f"Disciplina: {disciplina}\n"
        f"Total do semestre: {total}\n"
        f"Consulte o boletim completo no portal."
    )
    for phone in _phones_for_aluno(db, aluno_id):
        notify_event(db, phone, "nota_lancada", msg, {"aluno_id": aluno_id, "disciplina": disciplina, "total": total})


def notify_ocorrencia(db: Session, aluno_id: int, tipo: str, descricao: str) -> None:
    aluno = db.get(Aluno, aluno_id)
    if not aluno:
        return
    nome = aluno.user.nome if aluno.user else aluno.matricula
    escola = _escola_nome(db)
    msg = (
        f"*{escola}*\n"
        f"Ocorrência registrada:\n"
        f"Aluno: {nome}\n"
        f"Tipo: {tipo}\n"
        f"Descrição: {descricao}"
    )
    for phone in _phones_for_aluno(db, aluno_id):
        notify_event(db, phone, "ocorrencia", msg, {"aluno_id": aluno_id, "tipo": tipo})


def notify_evento_criado(db: Session, titulo: str, data: str, horario: str, local: str | None) -> None:
    escola = _escola_nome(db)
    msg = (
        f"*{escola}*\n"
        f"Novo evento:\n"
        f"{titulo}\n"
        f"{data} às {horario}\n"
        f"Local: {local or 'a definir'}"
    )
    # Notifica responsáveis com telefone cadastrado
    alunos = db.query(Aluno).filter(Aluno.responsavel_telefone.isnot(None)).limit(200).all()
    for aluno in alunos:
        phone = "".join(ch for ch in (aluno.responsavel_telefone or "") if ch.isdigit())
        if phone:
            notify_event(db, phone, "evento_criado", msg, {"titulo": titulo})


def notify_recuperacao(db: Session, aluno_id: int, disciplina: str, media: float) -> None:
    aluno = db.get(Aluno, aluno_id)
    if not aluno:
        return
    nome = aluno.user.nome if aluno.user else aluno.matricula
    escola = _escola_nome(db)
    msg = (
        f"*{escola}*\n"
        f"Atenção — recuperação necessária:\n"
        f"Aluno: {nome}\n"
        f"Disciplina: {disciplina}\n"
        f"Média: {media}"
    )
    for phone in _phones_for_aluno(db, aluno_id):
        notify_event(db, phone, "recuperacao", msg, {"aluno_id": aluno_id, "media": media})
