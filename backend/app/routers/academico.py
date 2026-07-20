from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.deps import require_roles
from app.models import Disciplina, Serie, Turma, User, UserRole
from app.schemas import DisciplinaCreate, DisciplinaOut, SerieOut, TurmaCreate, TurmaOut

router = APIRouter(tags=["Acadêmico"])


@router.get("/series", response_model=list[SerieOut])
def listar_series(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR, UserRole.ALUNO)),
):
    return db.query(Serie).order_by(Serie.ordem).all()


@router.get("/turmas", response_model=list[TurmaOut])
def listar_turmas(
    ano_letivo: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR)),
):
    query = db.query(Turma).options(joinedload(Turma.serie))
    if ano_letivo:
        query = query.filter(Turma.ano_letivo == ano_letivo)
    return query.order_by(Turma.ano_letivo.desc(), Turma.id).all()


@router.post("/turmas", response_model=TurmaOut, status_code=status.HTTP_201_CREATED)
def criar_turma(
    payload: TurmaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if not db.get(Serie, payload.serie_id):
        raise HTTPException(status_code=404, detail="Série não encontrada")
    turma = Turma(**payload.model_dump())
    db.add(turma)
    db.commit()
    return db.query(Turma).options(joinedload(Turma.serie)).filter(Turma.id == turma.id).one()


@router.get("/disciplinas", response_model=list[DisciplinaOut])
def listar_disciplinas(
    turma_id: int | None = None,
    professor_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR, UserRole.ALUNO)),
):
    query = db.query(Disciplina)
    if turma_id:
        query = query.filter(Disciplina.turma_id == turma_id)
    if professor_id:
        query = query.filter(Disciplina.professor_id == professor_id)
    return query.order_by(Disciplina.nome).all()


@router.post("/disciplinas", response_model=DisciplinaOut, status_code=status.HTTP_201_CREATED)
def criar_disciplina(
    payload: DisciplinaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if not db.get(Turma, payload.turma_id):
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    disciplina = Disciplina(**payload.model_dump())
    db.add(disciplina)
    db.commit()
    db.refresh(disciplina)
    return disciplina
