from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_password_hash
from app.deps import require_roles
from app.models import Escola, Professor, User, UserRole
from app.schemas import CadastroProfessorOut, EntregaCredencial, ProfessorCreate, ProfessorOut
from app.services.credenciais import entregar_senha_provisoria, gerar_senha_provisoria

router = APIRouter(prefix="/professores", tags=["Professores"])


@router.get("", response_model=list[ProfessorOut])
def listar_professores(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.query(Professor).options(joinedload(Professor.user)).order_by(Professor.id).all()


@router.get("/{professor_id}", response_model=ProfessorOut)
def obter_professor(
    professor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR)),
):
    professor = (
        db.query(Professor).options(joinedload(Professor.user)).filter(Professor.id == professor_id).first()
    )
    if not professor:
        raise HTTPException(status_code=404, detail="Professor não encontrado")
    return professor


@router.post("", response_model=CadastroProfessorOut, status_code=status.HTTP_201_CREATED)
def criar_professor(
    payload: ProfessorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    username = (payload.username or payload.matricula).strip().lower()
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username já cadastrado")
    if db.query(Professor).filter(Professor.matricula == payload.matricula).first():
        raise HTTPException(status_code=400, detail="Matrícula já cadastrada")

    senha = (payload.password or "").strip() or gerar_senha_provisoria()
    user = User(
        username=username,
        email=payload.email,
        nome=payload.nome,
        hashed_password=get_password_hash(senha),
        role=UserRole.PROFESSOR,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    professor = Professor(
        user_id=user.id,
        matricula=payload.matricula,
        formacao=payload.formacao,
        telefone=payload.telefone,
    )
    db.add(professor)
    db.commit()
    professor = db.query(Professor).options(joinedload(Professor.user)).filter(Professor.id == professor.id).one()

    escola = db.query(Escola).first()
    entrega = entregar_senha_provisoria(
        destinatario_nome=payload.nome,
        login=username,
        senha=senha,
        telefone=payload.telefone,
        escola_nome=escola.nome if escola else "Escola",
    )
    return CadastroProfessorOut(
        professor=professor,
        senha_provisoria=senha,
        login=username,
        must_change_password=True,
        entrega=EntregaCredencial(**{k: entrega[k] for k in ("enviado", "canal", "destino", "motivo")}),
    )
