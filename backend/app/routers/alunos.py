from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_password_hash
from app.deps import get_current_user, require_roles
from app.models import Aluno, Escola, Matricula, Turma, User, UserRole
from app.schemas import AlunoCreate, AlunoOut, AlunoUpdate, CadastroAlunoOut, EntregaCredencial
from app.services.credenciais import entregar_senha_provisoria, gerar_senha_provisoria
from app.services.logs import registrar_log

router = APIRouter(prefix="/alunos", tags=["Alunos"])


@router.get("", response_model=list[AlunoOut])
def listar_alunos(
    turma_id: int | None = None,
    q: str | None = Query(None, description="Busca por nome ou matrícula"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR)),
):
    query = db.query(Aluno).options(joinedload(Aluno.user), joinedload(Aluno.turma).joinedload(Turma.serie))
    if turma_id:
        query = query.filter(Aluno.turma_id == turma_id)
    alunos = query.order_by(Aluno.id).all()
    if q:
        termo = q.lower()
        alunos = [
            a
            for a in alunos
            if termo in a.matricula.lower() or termo in a.user.nome.lower()
        ]
    return alunos


@router.get("/{aluno_id}", response_model=AlunoOut)
def obter_aluno(
    aluno_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    aluno = (
        db.query(Aluno)
        .options(joinedload(Aluno.user), joinedload(Aluno.turma).joinedload(Turma.serie))
        .filter(Aluno.id == aluno_id)
        .first()
    )
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    if current_user.role == UserRole.ALUNO and (not current_user.aluno or current_user.aluno.id != aluno_id):
        raise HTTPException(status_code=403, detail="Sem permissão")
    return aluno


@router.post("", response_model=CadastroAlunoOut, status_code=status.HTTP_201_CREATED)
def criar_aluno(
    payload: AlunoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    if not payload.lgpd_consentimento:
        raise HTTPException(
            status_code=400,
            detail="É obrigatório o consentimento LGPD do responsável para cadastrar o aluno.",
        )
    consent_por = (payload.lgpd_consentimento_por or payload.responsavel_nome or "").strip()
    if not consent_por:
        raise HTTPException(
            status_code=400,
            detail="Informe o nome de quem autorizou o tratamento dos dados (responsável).",
        )

    username = (payload.username or payload.matricula).strip()
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username já cadastrado")
    if db.query(Aluno).filter(Aluno.matricula == payload.matricula).first():
        raise HTTPException(status_code=400, detail="Matrícula já cadastrada")

    senha = gerar_senha_provisoria()
    user = User(
        username=username,
        email=payload.email,
        nome=payload.nome,
        hashed_password=get_password_hash(senha),
        role=UserRole.ALUNO,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    aluno = Aluno(
        user_id=user.id,
        matricula=payload.matricula,
        data_nascimento=payload.data_nascimento,
        responsavel_nome=payload.responsavel_nome,
        responsavel_telefone=payload.responsavel_telefone,
        turma_id=payload.turma_id,
        lgpd_consentimento=True,
        lgpd_consentimento_em=datetime.utcnow(),
        lgpd_consentimento_por=consent_por,
    )
    db.add(aluno)
    db.flush()
    if payload.turma_id:
        turma = db.get(Turma, payload.turma_id)
        ano = turma.ano_letivo if turma else 2026
        db.add(
            Matricula(
                aluno_id=aluno.id,
                turma_id=payload.turma_id,
                ano_letivo=ano,
                ativa=True,
            )
        )
    db.commit()
    registrar_log(db, current_user.id, "aluno_criar", payload.matricula)
    aluno = (
        db.query(Aluno)
        .options(joinedload(Aluno.user), joinedload(Aluno.turma).joinedload(Turma.serie))
        .filter(Aluno.id == aluno.id)
        .one()
    )

    escola = db.query(Escola).first()
    # Preferência: telefone do responsável; fallback e-mail só na mensagem ao admin
    telefone_envio = payload.responsavel_telefone
    entrega = entregar_senha_provisoria(
        destinatario_nome=payload.nome,
        login=username,
        senha=senha,
        telefone=telefone_envio,
        escola_nome=escola.nome if escola else "Escola",
    )
    return CadastroAlunoOut(
        aluno=aluno,
        senha_provisoria=senha,
        login=username,
        must_change_password=True,
        entrega=EntregaCredencial(**{k: entrega[k] for k in ("enviado", "canal", "destino", "motivo")}),
    )


@router.patch("/{aluno_id}", response_model=AlunoOut)
def atualizar_aluno(
    aluno_id: int,
    payload: AlunoUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    aluno = db.query(Aluno).options(joinedload(Aluno.user)).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "nome" in data:
        aluno.user.nome = data.pop("nome")
    if "ativo" in data:
        aluno.user.ativo = data.pop("ativo")
    for key, value in data.items():
        setattr(aluno, key, value)
    db.commit()
    return (
        db.query(Aluno)
        .options(joinedload(Aluno.user), joinedload(Aluno.turma).joinedload(Turma.serie))
        .filter(Aluno.id == aluno_id)
        .one()
    )


@router.delete("/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_aluno(
    aluno_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    aluno = db.query(Aluno).options(joinedload(Aluno.user)).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    aluno.user.ativo = False
    db.commit()
