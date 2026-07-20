import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash
from app.deps import require_roles
from app.models import Escola, User, UserRole
from app.schemas import EscolaOut, EscolaSetupRequest, EscolaStatus, EscolaUpdate
from app.services.logs import registrar_log

router = APIRouter(prefix="/escola", tags=["Escola"])

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "escola"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _get_escola(db: Session) -> Escola | None:
    return db.query(Escola).order_by(Escola.id).first()


def _logo_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http") or path.startswith("data:"):
        return path
    return f"/uploads/escola/{Path(path).name}"


def _serialize(escola: Escola) -> EscolaOut:
    data = EscolaOut.model_validate(escola)
    data.logo = _logo_url(escola.logo)
    data.logo_fundo_login = _logo_url(escola.logo_fundo_login)
    return data


@router.get("/status", response_model=EscolaStatus)
def status_escola(db: Session = Depends(get_db)):
    escola = _get_escola(db)
    if not escola or not escola.setup_completo:
        return EscolaStatus(needs_setup=True, setup_completo=False, escola=_serialize(escola) if escola else None)
    return EscolaStatus(needs_setup=False, setup_completo=True, escola=_serialize(escola))


@router.get("", response_model=EscolaOut)
def obter_escola(db: Session = Depends(get_db)):
    escola = _get_escola(db)
    if not escola:
        raise HTTPException(status_code=404, detail="Escola ainda não configurada")
    return _serialize(escola)


@router.post("/setup", response_model=EscolaOut)
def setup_inicial(payload: EscolaSetupRequest, db: Session = Depends(get_db)):
    escola = _get_escola(db)
    if escola and escola.setup_completo and db.query(User).filter(User.role == UserRole.ADMIN).first():
        raise HTTPException(status_code=400, detail="Configuração inicial já concluída")

    if db.query(User).filter(User.username == payload.admin_username).first():
        raise HTTPException(status_code=400, detail="Username do administrador já existe")
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(status_code=400, detail="E-mail do administrador já existe")

    if not escola:
        escola = Escola(nome=payload.nome)
        db.add(escola)

    escola.nome = payload.nome
    escola.slogan = payload.slogan
    escola.cor_primaria = payload.cor_primaria
    escola.cor_secundaria = payload.cor_secundaria
    escola.cor_botoes = payload.cor_botoes
    escola.cor_menu = payload.cor_menu
    escola.tema = payload.tema if payload.tema in ("claro", "escuro") else "claro"
    escola.setup_completo = True
    escola.updated_at = datetime.utcnow()

    admin = User(
        username=payload.admin_username.strip(),
        email=payload.admin_email,
        nome=payload.admin_nome,
        hashed_password=get_password_hash(payload.admin_password),
        role=UserRole.ADMIN,
        must_change_password=False,
    )
    db.add(admin)
    db.commit()
    db.refresh(escola)
    registrar_log(db, admin.id, "escola_setup", escola.nome)
    return _serialize(escola)


@router.put("", response_model=EscolaOut)
def atualizar_escola(
    payload: EscolaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    escola = _get_escola(db)
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    data = payload.model_dump(exclude_unset=True)
    if "tema" in data and data["tema"] not in ("claro", "escuro"):
        raise HTTPException(status_code=400, detail="Tema deve ser 'claro' ou 'escuro'")
    for key, value in data.items():
        setattr(escola, key, value)
    escola.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(escola)
    registrar_log(db, current_user.id, "escola_atualizar", escola.nome)
    return _serialize(escola)


def _save_upload(file: UploadFile, prefix: str) -> str:
    content = file.file.read()
    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo maior que 3MB")
    ext = Path(file.filename or "logo.png").suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        raise HTTPException(status_code=400, detail="Formato de imagem inválido")
    name = f"{prefix}_{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / name
    path.write_bytes(content)
    return name


@router.post("/logo", response_model=EscolaOut)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    escola = _get_escola(db)
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    escola.logo = _save_upload(file, "logo")
    escola.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(escola)
    registrar_log(db, current_user.id, "escola_logo", escola.logo)
    return _serialize(escola)


@router.post("/fundo-login", response_model=EscolaOut)
async def upload_fundo_login(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    escola = _get_escola(db)
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    escola.logo_fundo_login = _save_upload(file, "fundo")
    escola.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(escola)
    return _serialize(escola)


@router.post("/setup/logo")
async def setup_upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload de logo durante o assistente (antes do setup completo)."""
    escola = _get_escola(db)
    if escola and escola.setup_completo:
        raise HTTPException(status_code=400, detail="Use o endpoint autenticado /escola/logo")
    if not escola:
        escola = Escola(nome="Escola em configuração", setup_completo=False)
        db.add(escola)
        db.flush()
    escola.logo = _save_upload(file, "logo")
    escola.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(escola)
    return {"ok": True, "logo": _logo_url(escola.logo)}
