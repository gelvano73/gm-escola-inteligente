from __future__ import annotations

import random
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.core.security import verify_password
from app.models import Aluno, User, UserRole, WhatsAppPerfil, WhatsAppSession
from app.services.credenciais import normalizar_senha_nascimento


def get_or_create_session(db: Session, phone: str) -> WhatsAppSession:
    phone = "".join(ch for ch in phone if ch.isdigit())
    session = db.query(WhatsAppSession).filter(WhatsAppSession.phone == phone).first()
    if session:
        return session
    session = WhatsAppSession(phone=phone, estado="inicio", perfil=WhatsAppPerfil.DESCONHECIDO)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def reset_session(db: Session, session: WhatsAppSession) -> None:
    session.verificado = False
    session.user_id = None
    session.aluno_id = None
    session.perfil = WhatsAppPerfil.DESCONHECIDO
    session.estado = "inicio"
    session.codigo_verificacao = None
    session.tentativas = 0
    session.atualizado_em = datetime.utcnow()
    db.commit()


MENU = (
    "Olá! Sou o *Assistente Escolar IA*.\n"
    "Para proteger os dados, preciso confirmar sua identidade.\n\n"
    "Escolha seu perfil:\n"
    "1 - Aluno\n"
    "2 - Responsável\n"
    "3 - Professor\n"
    "4 - Administrador\n\n"
    "Digite o número da opção."
)


def handle_auth_flow(db: Session, session: WhatsAppSession, text: str) -> str | None:
    """Retorna mensagem se ainda estiver no fluxo de autenticação; None se já verificado e pronto."""
    raw = text.strip()
    lower = raw.lower()

    if lower in {"menu", "oi", "olá", "ola", "inicio", "começar", "comecar", "sair", "logout"}:
        reset_session(db, session)
        session.estado = "perfil"
        db.commit()
        return MENU

    if session.verificado and session.estado == "pronto":
        return None

    if session.estado in {"inicio", "perfil"}:
        session.estado = "perfil"
        mapping = {
            "1": WhatsAppPerfil.ALUNO,
            "2": WhatsAppPerfil.RESPONSAVEL,
            "3": WhatsAppPerfil.PROFESSOR,
            "4": WhatsAppPerfil.ADMIN,
            "aluno": WhatsAppPerfil.ALUNO,
            "responsável": WhatsAppPerfil.RESPONSAVEL,
            "responsavel": WhatsAppPerfil.RESPONSAVEL,
            "professor": WhatsAppPerfil.PROFESSOR,
            "admin": WhatsAppPerfil.ADMIN,
            "administrador": WhatsAppPerfil.ADMIN,
        }
        escolha = mapping.get(lower)
        if not escolha:
            db.commit()
            return MENU
        session.perfil = escolha
        session.estado = "credenciais"
        db.commit()
        if escolha == WhatsAppPerfil.ALUNO:
            return "Envie: *matrícula* e *senha* separados por espaço.\nEx.: `A2026001 12052011`"
        if escolha == WhatsAppPerfil.RESPONSAVEL:
            return (
                "Envie: *CPF* e *matrícula do aluno* separados por espaço.\n"
                "Ex.: `12345678901 A2026001`\n"
                "Ou digite *codigo* para receber verificação por e-mail/WhatsApp (demo)."
            )
        if escolha == WhatsAppPerfil.PROFESSOR:
            return "Envie: *e-mail institucional* e *senha* separados por espaço."
        return "Envie: *usuário/e-mail* e *senha* de administrador separados por espaço."

    if session.estado == "codigo":
        if raw == session.codigo_verificacao:
            session.verificado = True
            session.estado = "pronto"
            session.codigo_verificacao = None
            session.atualizado_em = datetime.utcnow()
            db.commit()
            return "Identidade confirmada ✅\nPode perguntar sobre o desempenho do aluno."
        session.tentativas += 1
        db.commit()
        return "Código inválido. Tente novamente ou digite *menu*."

    if session.estado == "credenciais":
        partes = raw.split()
        if session.perfil == WhatsAppPerfil.RESPONSAVEL and lower == "codigo":
            # fluxo código: precisa matrícula depois — pede matrícula
            session.estado = "aguarda_matricula_codigo"
            db.commit()
            return "Envie a *matrícula do aluno* para gerarmos o código."

        if session.perfil == WhatsAppPerfil.ALUNO:
            if len(partes) < 2:
                return "Formato inválido. Ex.: `A2026001 12052011`"
            matricula, senha = partes[0], " ".join(partes[1:])
            aluno = (
                db.query(Aluno)
                .options(joinedload(Aluno.user))
                .filter(Aluno.matricula == matricula)
                .first()
            )
            if not aluno or not aluno.user:
                return "Matrícula não encontrada."
            ok = verify_password(senha, aluno.user.hashed_password)
            if not ok:
                normalizada = normalizar_senha_nascimento(senha)
                ok = bool(normalizada and verify_password(normalizada, aluno.user.hashed_password))
            if not ok:
                return "Senha incorreta."
            session.aluno_id = aluno.id
            session.user_id = aluno.user_id
            session.verificado = True
            session.estado = "pronto"
            db.commit()
            return f"Olá, {aluno.user.nome}! Autenticado como aluno ✅\nPergunte: média, ocorrências, eventos..."

        if session.perfil == WhatsAppPerfil.RESPONSAVEL:
            if len(partes) < 2:
                return "Formato: `CPF MATRICULA`"
            cpf = "".join(ch for ch in partes[0] if ch.isdigit())
            matricula = partes[1]
            aluno = (
                db.query(Aluno)
                .options(joinedload(Aluno.user))
                .filter(Aluno.matricula == matricula)
                .first()
            )
            if not aluno:
                return "Matrícula não encontrada."
            cpf_aluno = "".join(ch for ch in (aluno.responsavel_cpf or "") if ch.isdigit())
            # Aceita CPF cadastrado OU, em demo, qualquer CPF com 11 dígitos se responsavel_cpf vazio
            if cpf_aluno and cpf != cpf_aluno:
                return "CPF não confere com o responsável cadastrado."
            if not cpf_aluno and len(cpf) != 11:
                return "Informe um CPF válido (11 dígitos)."
            session.aluno_id = aluno.id
            session.verificado = True
            session.estado = "pronto"
            db.commit()
            nome = aluno.user.nome if aluno.user else matricula
            return f"Responsável autenticado ✅\nAluno vinculado: *{nome}*\nPode consultar desempenho, faltas e ocorrências."

        if session.perfil in {WhatsAppPerfil.PROFESSOR, WhatsAppPerfil.ADMIN}:
            if len(partes) < 2:
                return "Envie login e senha separados por espaço."
            login, senha = partes[0], " ".join(partes[1:])
            user = (
                db.query(User)
                .options(joinedload(User.professor), joinedload(User.aluno))
                .filter((User.email == login) | (User.username == login))
                .first()
            )
            if not user or not verify_password(senha, user.hashed_password):
                return "Credenciais inválidas."
            if session.perfil == WhatsAppPerfil.PROFESSOR and user.role != UserRole.PROFESSOR:
                return "Esta conta não é de professor."
            if session.perfil == WhatsAppPerfil.ADMIN and user.role != UserRole.ADMIN:
                return "Esta conta não é de administrador."
            session.user_id = user.id
            session.verificado = True
            session.estado = "pronto"
            db.commit()
            return f"Olá, {user.nome}! Autenticado ✅\nPode consultar informações do seu perfil."

    if session.estado == "aguarda_matricula_codigo":
        matricula = raw.strip()
        aluno = db.query(Aluno).options(joinedload(Aluno.user)).filter(Aluno.matricula == matricula).first()
        if not aluno:
            return "Matrícula não encontrada."
        codigo = f"{random.randint(100000, 999999)}"
        session.aluno_id = aluno.id
        session.codigo_verificacao = codigo
        session.estado = "codigo"
        db.commit()
        # Em produção enviaria SMS/e-mail; no demo devolvemos o código na resposta
        return (
            f"Código gerado para o responsável de *{aluno.user.nome if aluno.user else matricula}*.\n"
            f"(Demo) Seu código é: *{codigo}*\nDigite o código para confirmar."
        )

    return MENU
