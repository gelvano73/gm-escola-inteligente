from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_password_hash
from app.deps import get_current_user, require_roles
from app.models import Aluno, Log, Nota, Ocorrencia, Turma, User, UserRole
from app.services.logs import registrar_log

router = APIRouter(prefix="/lgpd", tags=["LGPD"])


class AnonimizarRequest(BaseModel):
    motivo: str | None = None


@router.get("/meus-dados")
def exportar_meus_dados(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Portabilidade / acesso aos dados pessoais (art. 18 LGPD)."""
    user = (
        db.query(User)
        .options(
            joinedload(User.aluno).joinedload(Aluno.turma).joinedload(Turma.serie),
            joinedload(User.professor),
        )
        .filter(User.id == current_user.id)
        .one()
    )
    dados: dict = {
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "base_legal": "Execução de contrato / legítimo interesse educacional e consentimento do responsável (quando aplicável).",
        "usuario": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "username": user.username,
            "perfil": user.role.value,
            "ativo": user.ativo,
            "criado_em": user.criado_em.isoformat() if user.criado_em else None,
        },
    }
    if user.aluno:
        a = user.aluno
        notas = (
            db.query(Nota)
            .filter(Nota.aluno_id == a.id)
            .order_by(Nota.semestre)
            .all()
        )
        ocorrencias = db.query(Ocorrencia).filter(Ocorrencia.aluno_id == a.id).all()
        dados["aluno"] = {
            "matricula": a.matricula,
            "data_nascimento": a.data_nascimento.isoformat() if a.data_nascimento else None,
            "responsavel_nome": a.responsavel_nome,
            "responsavel_telefone": a.responsavel_telefone,
            "turma": f"{a.turma.serie.nome if a.turma and a.turma.serie else ''} {a.turma.nome if a.turma else ''}".strip() or None,
            "lgpd_consentimento": a.lgpd_consentimento,
            "lgpd_consentimento_em": a.lgpd_consentimento_em.isoformat() if a.lgpd_consentimento_em else None,
            "lgpd_consentimento_por": a.lgpd_consentimento_por,
            "notas": [
                {
                    "disciplina_id": n.disciplina_id,
                    "semestre": n.semestre,
                    "prova1": n.prova1,
                    "prova2": n.prova2,
                    "trabalho": n.trabalho,
                    "participacao": n.participacao,
                    "total": n.total,
                }
                for n in notas
            ],
            "ocorrencias": [
                {
                    "tipo": o.tipo.value if hasattr(o.tipo, "value") else str(o.tipo),
                    "data": o.data_ocorrencia.isoformat() if o.data_ocorrencia else None,
                    "descricao": o.descricao,
                }
                for o in ocorrencias
            ],
        }
    if user.professor:
        p = user.professor
        dados["professor"] = {
            "matricula": p.matricula,
            "formacao": p.formacao,
            "telefone": p.telefone,
        }
    registrar_log(db, current_user.id, "lgpd_exportar_dados", f"user={current_user.id}")
    return dados


@router.post("/anonimizar/{user_id}")
def anonimizar_titular(
    user_id: int,
    payload: AnonimizarRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Eliminação / anonimização de dados identificáveis (art. 18, VI LGPD)."""
    user = db.query(User).options(joinedload(User.aluno), joinedload(User.professor)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.role == UserRole.ADMIN and user.username == "admin":
        raise HTTPException(status_code=400, detail="Não é permitido anonimizar a conta admin principal")

    marca = f"ANON{user.id}"
    user.nome = f"Titular anonimizado {marca}"
    user.email = f"{marca.lower()}@anonimizado.local"
    user.username = marca.lower()
    user.hashed_password = get_password_hash(gerar_token_inutil())
    user.ativo = False
    user.must_change_password = False

    if user.aluno:
        a = user.aluno
        a.matricula = marca
        a.data_nascimento = None
        a.responsavel_nome = None
        a.responsavel_telefone = None
        a.responsavel_cpf = None
        a.lgpd_consentimento_por = None

    if user.professor:
        p = user.professor
        p.telefone = None
        p.formacao = None
        p.matricula = marca

    db.commit()
    registrar_log(
        db,
        current_user.id,
        "lgpd_anonimizar",
        f"user_id={user_id}; motivo={payload.motivo or 'solicitação do titular'}",
    )
    return {"ok": True, "mensagem": "Dados pessoais anonimizados. Registros acadêmicos preservados sem identificação."}


def gerar_token_inutil() -> str:
    return f"bloqueado-{datetime.utcnow().timestamp()}"


@router.get("/logs")
def listar_logs_lgpd(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Trilha de auditoria (acessos e ações relevantes à LGPD)."""
    limit = max(1, min(limit, 500))
    logs = db.query(Log).order_by(Log.criado_em.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "acao": log.acao,
            "detalhe": log.detalhe,
            "criado_em": log.criado_em.isoformat() if log.criado_em else None,
        }
        for log in logs
    ]
