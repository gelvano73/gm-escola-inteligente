from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Aluno, Ocorrencia, User, UserRole
from app.schemas import OcorrenciaCreate, OcorrenciaOut
from app.services.logs import registrar_log

router = APIRouter(prefix="/ocorrencias", tags=["Ocorrências"])

TIPO_LABEL = {
    "indisciplina": "Indisciplina",
    "falta_atividade": "Falta de atividade",
    "advertencia": "Advertência",
    "suspensao": "Suspensão",
    "elogio": "Elogio",
}


@router.get("", response_model=list[OcorrenciaOut])
def listar_ocorrencias(
    aluno_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Ocorrencia).options(joinedload(Ocorrencia.registrado_por))
    if current_user.role == UserRole.ALUNO:
        if not current_user.aluno:
            return []
        query = query.filter(Ocorrencia.aluno_id == current_user.aluno.id)
    elif aluno_id:
        query = query.filter(Ocorrencia.aluno_id == aluno_id)
    itens = query.order_by(Ocorrencia.data_ocorrencia.desc()).all()
    return [
        OcorrenciaOut(
            id=o.id,
            aluno_id=o.aluno_id,
            registrado_por_id=o.registrado_por_id,
            professor_nome=o.registrado_por.nome if o.registrado_por else None,
            tipo=o.tipo,
            gravidade=o.gravidade,
            descricao=o.descricao,
            data_ocorrencia=o.data_ocorrencia,
            criado_em=o.criado_em,
        )
        for o in itens
    ]


@router.post("", response_model=OcorrenciaOut, status_code=status.HTTP_201_CREATED)
def criar_ocorrencia(
    payload: OcorrenciaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR)),
):
    if not db.get(Aluno, payload.aluno_id):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    ocorrencia = Ocorrencia(**payload.model_dump(), registrado_por_id=current_user.id)
    db.add(ocorrencia)
    db.commit()
    registrar_log(
        db,
        current_user.id,
        "ocorrencia_criar",
        f"{TIPO_LABEL.get(payload.tipo.value, payload.tipo.value)} aluno={payload.aluno_id}",
    )
    try:
        from app.services.notifications import notify_ocorrencia

        notify_ocorrencia(db, payload.aluno_id, payload.tipo.value, payload.descricao)
    except Exception:
        pass
    o = (
        db.query(Ocorrencia)
        .options(joinedload(Ocorrencia.registrado_por))
        .filter(Ocorrencia.id == ocorrencia.id)
        .one()
    )
    return OcorrenciaOut(
        id=o.id,
        aluno_id=o.aluno_id,
        registrado_por_id=o.registrado_por_id,
        professor_nome=o.registrado_por.nome if o.registrado_por else None,
        tipo=o.tipo,
        gravidade=o.gravidade,
        descricao=o.descricao,
        data_ocorrencia=o.data_ocorrencia,
        criado_em=o.criado_em,
    )


@router.delete("/{ocorrencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_ocorrencia(
    ocorrencia_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    ocorrencia = db.get(Ocorrencia, ocorrencia_id)
    if not ocorrencia:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    db.delete(ocorrencia)
    db.commit()
    registrar_log(db, current_user.id, "ocorrencia_excluir", f"id={ocorrencia_id}")
