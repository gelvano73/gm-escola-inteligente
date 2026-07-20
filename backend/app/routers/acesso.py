from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_password_hash
from app.deps import require_roles
from app.models import Escola, User, UserRole
from app.schemas import AcessoToggle, AcessoUsuarioOut, EntregaCredencial, ResetSenhaOut, ResetSenhaRequest
from app.services.credenciais import entregar_senha_provisoria, gerar_senha_provisoria

router = APIRouter(prefix="/acesso", tags=["Controle de Acesso"])


@router.get("/usuarios", response_model=list[AcessoUsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    users = db.query(User).order_by(User.role, User.nome).all()
    return [
        AcessoUsuarioOut(
            id=u.id,
            username=u.username,
            email=u.email,
            nome=u.nome,
            role=u.role,
            ativo=u.ativo,
            must_change_password=u.must_change_password,
        )
        for u in users
    ]


@router.patch("/usuarios/{user_id}", response_model=AcessoUsuarioOut)
def alternar_acesso(
    user_id: int,
    payload: AcessoToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == current_user.id and not payload.ativo:
        raise HTTPException(status_code=400, detail="Você não pode desativar a si mesmo")
    user.ativo = payload.ativo
    db.commit()
    db.refresh(user)
    return AcessoUsuarioOut(
        id=user.id,
        username=user.username,
        email=user.email,
        nome=user.nome,
        role=user.role,
        ativo=user.ativo,
        must_change_password=user.must_change_password,
    )


@router.post("/usuarios/{user_id}/reset-senha", response_model=ResetSenhaOut)
def resetar_senha(
    user_id: int,
    payload: ResetSenhaRequest = ResetSenhaRequest(),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = (
        db.query(User)
        .options(joinedload(User.aluno), joinedload(User.professor))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Admin pode informar senha manual; caso contrário o sistema gera
    senha = (payload.nova_senha_provisoria or "").strip() or gerar_senha_provisoria()

    user.hashed_password = get_password_hash(senha)
    user.must_change_password = True
    db.commit()

    telefone = None
    if user.role == UserRole.ALUNO and user.aluno:
        telefone = user.aluno.responsavel_telefone
    elif user.role == UserRole.PROFESSOR and user.professor:
        telefone = user.professor.telefone

    escola = db.query(Escola).first()
    entrega = entregar_senha_provisoria(
        destinatario_nome=user.nome,
        login=user.username,
        senha=senha,
        telefone=telefone,
        escola_nome=escola.nome if escola else "Escola",
    )
    return ResetSenhaOut(
        user_id=user.id,
        nome=user.nome,
        role=user.role,
        login=user.username,
        senha_provisoria=senha,
        must_change_password=True,
        entrega=EntregaCredencial(**{k: entrega[k] for k in ("enviado", "canal", "destino", "motivo")}),
        message="Senha provisória gerada. O usuário deverá alterá-la no próximo login.",
    )
