from sqlalchemy.orm import Session

from app.models import Log


def registrar_log(db: Session, user_id: int | None, acao: str, detalhe: str | None = None) -> None:
    db.add(Log(user_id=user_id, acao=acao, detalhe=detalhe))
    db.commit()
