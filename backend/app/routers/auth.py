from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.compliance import TERMOS_VERSAO
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.deps import get_current_user
from app.models import Aluno, User
from app.schemas import ChangePasswordRequest, LoginRequest, MeResponse, Token, UserOut
from app.services.credenciais import normalizar_senha_nascimento, senha_inicial_aluno
from app.services.logs import registrar_log

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _find_user_by_login(db: Session, login: str) -> User | None:
    valor = login.strip()
    user = (
        db.query(User)
        .options(joinedload(User.aluno), joinedload(User.professor))
        .filter(or_(User.username == valor, User.email == valor))
        .first()
    )
    if user:
        return user

    aluno = db.query(Aluno).filter(Aluno.matricula == valor).first()
    if not aluno:
        return None
    return (
        db.query(User)
        .options(joinedload(User.aluno), joinedload(User.professor))
        .filter(User.id == aluno.user_id)
        .first()
    )


def _password_matches(user: User, password: str) -> bool:
    if verify_password(password, user.hashed_password):
        return True
    if user.role.value == "aluno" and user.aluno and user.aluno.data_nascimento and user.must_change_password:
        normalizada = normalizar_senha_nascimento(password)
        if normalizada and verify_password(normalizada, user.hashed_password):
            return True
    return False


def _authenticate(db: Session, login: str, password: str) -> User:
    user = _find_user_by_login(db, login)
    if not user or not _password_matches(user, password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos")
    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário desativado")
    return user


def _registrar_aceite_termos(db: Session, user: User) -> None:
    user.termos_aceitos = True
    user.termos_aceitos_em = datetime.utcnow()
    user.termos_versao = TERMOS_VERSAO
    db.add(user)
    db.commit()
    registrar_log(db, user.id, "aceite_termos_lgpd", f"versao={TERMOS_VERSAO}")


def _exigir_aceite(aceite_termos: bool, aceite_privacidade: bool) -> None:
    if not aceite_termos or not aceite_privacidade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para entrar, aceite os Termos de Uso e a Política de Privacidade (LGPD).",
        )


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login form (Swagger). Aceite deve ser feito pelo login-json da interface."""
    user = _authenticate(db, form_data.username, form_data.password)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    registrar_log(db, user.id, "login", f"perfil={user.role.value};canal=form")
    return Token(access_token=token, must_change_password=user.must_change_password)


@router.post("/login-json", response_model=Token)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    _exigir_aceite(payload.aceite_termos, payload.aceite_privacidade)
    user = _authenticate(db, payload.usuario, payload.password)
    _registrar_aceite_termos(db, user)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    registrar_log(db, user.id, "login", f"perfil={user.role.value};aceite={TERMOS_VERSAO}")
    return Token(access_token=token, must_change_password=user.must_change_password)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(
            joinedload(User.professor),
            joinedload(User.aluno).joinedload(Aluno.turma),
        )
        .filter(User.id == current_user.id)
        .one()
    )
    turma_nome = None
    if user.aluno and user.aluno.turma:
        turma_nome = f"{user.aluno.turma.nome}"
    return MeResponse(
        user=UserOut.model_validate(user),
        perfil=user.role.value,
        professor_id=user.professor.id if user.professor else None,
        aluno_id=user.aluno.id if user.aluno else None,
        must_change_password=user.must_change_password,
        matricula=user.aluno.matricula if user.aluno else (user.professor.matricula if user.professor else None),
        data_nascimento=user.aluno.data_nascimento.isoformat() if user.aluno and user.aluno.data_nascimento else None,
        turma_nome=turma_nome,
        termos_aceitos=bool(user.termos_aceitos),
        termos_versao=user.termos_versao,
        termos_versao_atual=TERMOS_VERSAO,
    )


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _password_matches(current_user, payload.senha_atual):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if payload.nova_senha == payload.senha_atual:
        raise HTTPException(status_code=400, detail="A nova senha deve ser diferente da atual")
    if current_user.username == "admin" and payload.nova_senha == "123456":
        raise HTTPException(status_code=400, detail="Escolha uma senha diferente da senha padrão")

    if current_user.role.value == "aluno" and current_user.aluno and current_user.aluno.data_nascimento:
        inicial = senha_inicial_aluno(current_user.aluno.data_nascimento)
        normalizada = normalizar_senha_nascimento(payload.nova_senha)
        if payload.nova_senha == inicial or normalizada == inicial:
            raise HTTPException(
                status_code=400,
                detail="A nova senha não pode ser a data de nascimento",
            )

    current_user.hashed_password = get_password_hash(payload.nova_senha)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()
    return {"ok": True, "message": "Senha alterada com sucesso"}
