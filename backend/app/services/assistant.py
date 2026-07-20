from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from app.models import (
    Aluno,
    Disciplina,
    Escola,
    Evento,
    Falta,
    Nota,
    Ocorrencia,
    Professor,
    Turma,
    User,
    UserRole,
    WhatsAppPerfil,
    WhatsAppSession,
)
from app.services.aprovacao import calcular_media_final, classificar_situacao, rotulo_situacao
from app.services.openai_client import chat_completion


def _escola_nome(db: Session) -> str:
    escola = db.query(Escola).first()
    return escola.nome if escola else "Escola"


def _boletim_aluno(db: Session, aluno: Aluno) -> str:
    notas = (
        db.query(Nota)
        .options(joinedload(Nota.disciplina))
        .filter(Nota.aluno_id == aluno.id)
        .all()
    )
    agrupado: dict[int, dict[int, float]] = defaultdict(dict)
    nomes: dict[int, str] = {}
    for n in notas:
        agrupado[n.disciplina_id][n.semestre] = n.total
        nomes[n.disciplina_id] = n.disciplina.nome if n.disciplina else str(n.disciplina_id)

    linhas = []
    medias = []
    for did, totais in agrupado.items():
        media = calcular_media_final(totais.get(1), totais.get(2))
        situacao = rotulo_situacao(classificar_situacao(media, tem_parcial=bool(totais) and media is None))
        if media is not None:
            medias.append(media)
        s1 = totais.get(1, "—")
        s2 = totais.get(2, "—")
        linhas.append(f"• {nomes[did]}: S1={s1} | S2={s2} | Total={media if media is not None else '—'} ({situacao})")

    turma = ""
    if aluno.turma:
        serie = aluno.turma.serie.nome if aluno.turma.serie else ""
        turma = f"{serie} {aluno.turma.nome}".strip()

    media_geral = round(sum(medias) / len(medias), 1) if medias else None
    faltas = db.query(Falta).filter(Falta.aluno_id == aluno.id).count()
    ocorrencias = db.query(Ocorrencia).filter(Ocorrencia.aluno_id == aluno.id).count()

    return (
        f"*{aluno.user.nome if aluno.user else 'Aluno'}*\n"
        f"Turma: {turma or '—'}\n"
        f"Matrícula: {aluno.matricula}\n\n"
        f"*Boletim*\n"
        + ("\n".join(linhas) if linhas else "Sem notas lançadas.")
        + f"\n\nPontuação geral (soma S1+S2): {media_geral if media_geral is not None else '—'}\n"
        f"Faltas: {faltas}\n"
        f"Ocorrências: {ocorrencias}"
    )


def _ocorrencias_aluno(db: Session, aluno: Aluno) -> str:
    itens = (
        db.query(Ocorrencia)
        .filter(Ocorrencia.aluno_id == aluno.id)
        .order_by(Ocorrencia.data_ocorrencia.desc())
        .limit(10)
        .all()
    )
    if not itens:
        return "Nenhuma ocorrência registrada."
    linhas = []
    for o in itens:
        linhas.append(f"• {o.data_ocorrencia.strftime('%d/%m/%Y')} — {o.tipo.value} ({o.gravidade.value}): {o.descricao}")
    return "*Ocorrências*\n" + "\n".join(linhas)


def _eventos(db: Session) -> str:
    hoje = date.today()
    eventos = (
        db.query(Evento)
        .filter(Evento.data_evento >= hoje, Evento.publico.is_(True))
        .order_by(Evento.data_evento)
        .limit(8)
        .all()
    )
    if not eventos:
        return "Não há eventos futuros cadastrados."
    linhas = [
        f"• {e.data_evento.strftime('%d/%m/%Y')} {e.horario} — {e.titulo} ({e.local or 'Local a definir'})"
        for e in eventos
    ]
    return "*Próximos eventos*\n" + "\n".join(linhas)


def _admin_resumo(db: Session) -> str:
    total_alunos = db.query(Aluno).count()
    total_prof = db.query(Professor).count()
    total_turmas = db.query(Turma).count()
    mes = datetime.utcnow().month
    ano = datetime.utcnow().year
    ocorrencias_mes = (
        db.query(Ocorrencia)
        .filter(Ocorrencia.data_ocorrencia >= date(ano, mes, 1))
        .count()
    )
    notas = db.query(Nota).all()
    agrupado: dict[tuple[int, int], dict[int, float]] = defaultdict(dict)
    for n in notas:
        agrupado[(n.aluno_id, n.disciplina_id)][n.semestre] = n.total
    recuperacao = 0
    for totais in agrupado.values():
        media = calcular_media_final(totais.get(1), totais.get(2))
        if media is not None and 30 <= media < 60:
            recuperacao += 1
    return (
        f"*Painel administrativo*\n"
        f"Alunos matriculados: {total_alunos}\n"
        f"Professores: {total_prof}\n"
        f"Turmas: {total_turmas}\n"
        f"Em recuperação (disciplinas): {recuperacao}\n"
        f"Ocorrências neste mês: {ocorrencias_mes}"
    )


def _professor_resumo(db: Session, user: User) -> str:
    if not user.professor:
        return "Perfil de professor não encontrado."
    disciplinas = db.query(Disciplina).filter(Disciplina.professor_id == user.professor.id).all()
    if not disciplinas:
        return "Você não possui disciplinas vinculadas."
    linhas = []
    for d in disciplinas:
        turma = db.get(Turma, d.turma_id)
        nome_turma = f"{turma.serie.nome if turma and turma.serie else ''} {turma.nome if turma else ''}".strip()
        linhas.append(f"• {d.nome} — {nome_turma or 'Turma'}")
    return "*Suas turmas/disciplinas*\n" + "\n".join(linhas)


def _detect_intent(text: str) -> str:
    t = text.lower()
    if "ocorr" in t:
        return "ocorrencias"
    if any(k in t for k in ["evento", "festa", "reunião", "reuniao", "feira"]):
        return "eventos"
    if "falta" in t:
        return "faltas"
    if any(k in t for k in ["quantos alunos", "matriculados", "melhor desempenho", "painel"]):
        return "admin"
    if any(k in t for k in ["lecion", "notas ainda faltam", "faltam lançar"]):
        return "professor"
    if any(k in t for k in ["média", "media", "boletim", "nota", "desempenho", "aprovado", "recuperação", "recuperacao"]):
        return "boletim"
    if any(k in t for k in ["turma", "disciplina"]):
        return "professor"
    if any(k in t for k in ["explique", "estudar", "ajuda", "tutor", "fração", "fracao", "história", "historia"]):
        return "tutor"
    if any(k in t for k in ["uniforme", "transporte", "calendário", "calendario", "horário", "horario", "documento", "matrícula", "matricula"]):
        return "institucional"
    return "geral"


async def answer_question(db: Session, session: WhatsAppSession, text: str) -> str:
    intent = _detect_intent(text)
    escola = _escola_nome(db)

    # Tutor / institucional / geral com OpenAI quando disponível
    if intent in {"tutor", "institucional", "geral"}:
        system = (
            f"Você é o Assistente Escolar IA da {escola}. "
            "Responda em português, de forma clara e objetiva. "
            "Para dúvidas pedagógicas, atue como tutor. "
            "Para dúvidas institucionais (matrícula, uniforme, transporte, calendário), oriente com base em práticas escolares brasileiras comuns "
            "e sugira confirmar no portal/secretaria."
        )
        ai = await chat_completion(system, text)
        if ai:
            return ai
        if intent == "tutor":
            return (
                "Posso ajudar como tutor! Descreva o tema (ex.: frações, Revolução Francesa) "
                "e eu explico passo a passo. Com OpenAI configurada, as respostas ficam ainda mais ricas."
            )
        if intent == "institucional":
            return (
                f"*{escola}*\n"
                "Para matrículas, calendário, uniforme, transporte e documentos, "
                "consulte a secretaria ou o portal da escola. Posso também buscar eventos cadastrados — pergunte: 'Quais eventos?'."
            )

    if session.perfil in {WhatsAppPerfil.ALUNO, WhatsAppPerfil.RESPONSAVEL} and session.aluno_id:
        aluno = (
            db.query(Aluno)
            .options(joinedload(Aluno.user), joinedload(Aluno.turma).joinedload(Turma.serie))
            .filter(Aluno.id == session.aluno_id)
            .first()
        )
        if not aluno:
            return "Não encontrei o aluno vinculado a esta conversa."
        if intent == "boletim":
            return _boletim_aluno(db, aluno)
        if intent == "ocorrencias":
            return _ocorrencias_aluno(db, aluno)
        if intent == "faltas":
            qtd = db.query(Falta).filter(Falta.aluno_id == aluno.id).count()
            return f"{aluno.user.nome if aluno.user else 'Aluno'} possui *{qtd}* falta(s) registradas."
        if intent == "eventos":
            return _eventos(db)
        # fallback contextual
        return _boletim_aluno(db, aluno) + "\n\n" + _eventos(db)

    if session.perfil == WhatsAppPerfil.PROFESSOR and session.user_id:
        user = db.query(User).options(joinedload(User.professor)).filter(User.id == session.user_id).first()
        if intent in {"professor", "geral", "boletim"}:
            return _professor_resumo(db, user) if user else "Professor não encontrado."
        if intent == "eventos":
            return _eventos(db)
        return _professor_resumo(db, user) if user else "Sem dados."

    if session.perfil == WhatsAppPerfil.ADMIN:
        if intent in {"admin", "geral", "boletim"}:
            return _admin_resumo(db)
        if intent == "eventos":
            return _eventos(db)
        return _admin_resumo(db)

    return "Sessão não verificada. Digite *menu* para autenticar."
