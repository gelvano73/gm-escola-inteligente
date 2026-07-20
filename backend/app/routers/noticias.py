from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Noticia, User, UserRole
from app.schemas import NoticiaCreate, NoticiaOut
from app.services.logs import registrar_log

router = APIRouter(prefix="/noticias", tags=["Notícias"])


@router.get("", response_model=list[NoticiaOut])
def listar_noticias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Noticia)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Noticia.publicada.is_(True))
    return query.order_by(Noticia.publicado_em.desc()).all()


@router.get("/{noticia_id}", response_model=NoticiaOut)
def obter_noticia(
    noticia_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    noticia = db.get(Noticia, noticia_id)
    if not noticia:
        raise HTTPException(status_code=404, detail="Notícia não encontrada")
    if current_user.role != UserRole.ADMIN and not noticia.publicada:
        raise HTTPException(status_code=404, detail="Notícia não encontrada")
    return noticia


@router.post("", response_model=NoticiaOut, status_code=status.HTTP_201_CREATED)
def criar_noticia(
    payload: NoticiaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    noticia = Noticia(**payload.model_dump(), autor_id=current_user.id)
    db.add(noticia)
    db.commit()
    db.refresh(noticia)
    registrar_log(db, current_user.id, "noticia_criar", payload.titulo)
    return noticia


@router.delete("/{noticia_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_noticia(
    noticia_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    noticia = db.get(Noticia, noticia_id)
    if not noticia:
        raise HTTPException(status_code=404, detail="Notícia não encontrada")
    db.delete(noticia)
    db.commit()
    registrar_log(db, current_user.id, "noticia_excluir", f"id={noticia_id}")
