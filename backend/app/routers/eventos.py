from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Evento, User, UserRole
from app.schemas import EventoCreate, EventoOut
from app.services.logs import registrar_log

router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.get("", response_model=list[EventoOut])
def listar_eventos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Evento)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Evento.publico.is_(True))
    return query.order_by(Evento.data_evento.desc(), Evento.horario.desc()).all()


@router.post("", response_model=EventoOut, status_code=status.HTTP_201_CREATED)
def criar_evento(
    payload: EventoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    evento = Evento(**payload.model_dump(), criado_por_id=current_user.id)
    db.add(evento)
    db.commit()
    db.refresh(evento)
    registrar_log(db, current_user.id, "evento_criar", payload.titulo)
    try:
        from app.services.notifications import notify_evento_criado

        notify_evento_criado(
            db,
            evento.titulo,
            evento.data_evento.strftime("%d/%m/%Y"),
            evento.horario,
            evento.local,
        )
    except Exception:
        pass
    return evento


@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_evento(
    evento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    evento = db.get(Evento, evento_id)
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    db.delete(evento)
    db.commit()
    registrar_log(db, current_user.id, "evento_excluir", f"id={evento_id}")
