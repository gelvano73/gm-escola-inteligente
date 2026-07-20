from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Aluno, Disciplina, Nota, User, UserRole
from app.schemas import BoletimDisciplina, NotaCreate, NotaOut, NotaUpdate
from app.services.aprovacao import SEMESTRE_MAX, calcular_media_final, classificar_situacao, rotulo_situacao

router = APIRouter(prefix="/notas", tags=["Notas"])


def _serialize_nota(nota: Nota) -> NotaOut:
    return NotaOut(
        id=nota.id,
        aluno_id=nota.aluno_id,
        disciplina_id=nota.disciplina_id,
        semestre=nota.semestre,
        prova1=nota.prova1,
        prova2=nota.prova2,
        trabalho=nota.trabalho,
        participacao=nota.participacao,
        total=nota.total,
        observacao=nota.observacao,
        lancado_em=nota.lancado_em,
        disciplina=nota.disciplina,
    )


def _detalhe(nota: Nota) -> dict[str, float | None]:
    return {
        "prova1": nota.prova1,
        "prova2": nota.prova2,
        "trabalho": nota.trabalho,
        "participacao": nota.participacao,
        "total": nota.total,
    }


@router.get("", response_model=list[NotaOut])
def listar_notas(
    aluno_id: int | None = None,
    disciplina_id: int | None = None,
    semestre: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Nota).options(joinedload(Nota.disciplina))

    if current_user.role == UserRole.ALUNO:
        if not current_user.aluno:
            return []
        query = query.filter(Nota.aluno_id == current_user.aluno.id)
    elif aluno_id:
        query = query.filter(Nota.aluno_id == aluno_id)

    if disciplina_id:
        query = query.filter(Nota.disciplina_id == disciplina_id)
    if semestre:
        query = query.filter(Nota.semestre == semestre)

    if current_user.role == UserRole.PROFESSOR:
        query = query.join(Disciplina).filter(Disciplina.professor_id == current_user.professor.id)

    return [_serialize_nota(n) for n in query.order_by(Nota.semestre, Nota.id).all()]


@router.get("/boletim", response_model=list[BoletimDisciplina])
def boletim(
    aluno_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Nota).options(
        joinedload(Nota.disciplina),
        joinedload(Nota.aluno).joinedload(Aluno.user),
    )

    if current_user.role == UserRole.ALUNO:
        if not current_user.aluno:
            return []
        query = query.filter(Nota.aluno_id == current_user.aluno.id)
    elif aluno_id:
        query = query.filter(Nota.aluno_id == aluno_id)

    if current_user.role == UserRole.PROFESSOR:
        query = query.join(Disciplina).filter(Disciplina.professor_id == current_user.professor.id)

    notas = query.all()
    agrupado: dict[tuple[int, int], list[Nota]] = defaultdict(list)
    for nota in notas:
        agrupado[(nota.aluno_id, nota.disciplina_id)].append(nota)

    resultado: list[BoletimDisciplina] = []
    for (aid, did), itens in agrupado.items():
        s1 = next((n for n in itens if n.semestre == 1), None)
        s2 = next((n for n in itens if n.semestre == 2), None)
        total1 = s1.total if s1 else None
        total2 = s2.total if s2 else None
        media = calcular_media_final(total1, total2)
        situacao = classificar_situacao(media, tem_parcial=bool(s1 or s2) and media is None)
        aluno = itens[0].aluno
        disciplina = itens[0].disciplina
        resultado.append(
            BoletimDisciplina(
                aluno_id=aid,
                aluno_nome=aluno.user.nome if aluno and aluno.user else None,
                disciplina_id=did,
                disciplina_nome=disciplina.nome if disciplina else str(did),
                semestre1=total1,
                semestre2=total2,
                detalhe_semestre1=_detalhe(s1) if s1 else None,
                detalhe_semestre2=_detalhe(s2) if s2 else None,
                media_final=media,
                situacao=situacao,
                situacao_label=rotulo_situacao(situacao),
            )
        )

    resultado.sort(key=lambda x: (x.aluno_nome or "", x.disciplina_nome))
    return resultado


@router.post("", response_model=NotaOut, status_code=status.HTTP_201_CREATED)
def lancar_nota(
    payload: NotaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR)),
):
    """Cria ou atualiza o semestre, permitindo lançar uma avaliação por vez."""
    if not db.get(Aluno, payload.aluno_id):
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    disciplina = db.get(Disciplina, payload.disciplina_id)
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada")
    if current_user.role == UserRole.PROFESSOR and disciplina.professor_id != current_user.professor.id:
        raise HTTPException(status_code=403, detail="Você não leciona esta disciplina")

    componentes = {
        "prova1": payload.prova1,
        "prova2": payload.prova2,
        "trabalho": payload.trabalho,
        "participacao": payload.participacao,
    }
    informados = {k: v for k, v in componentes.items() if v is not None}
    if not informados and payload.observacao is None:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos uma avaliação (Prova 1, Prova 2, Trabalho ou Participação).",
        )

    existente = (
        db.query(Nota)
        .filter(
            Nota.aluno_id == payload.aluno_id,
            Nota.disciplina_id == payload.disciplina_id,
            Nota.semestre == payload.semestre,
        )
        .first()
    )

    if existente:
        for key, value in informados.items():
            setattr(existente, key, value)
        if payload.observacao is not None:
            existente.observacao = payload.observacao
        nota = existente
    else:
        nota = Nota(
            aluno_id=payload.aluno_id,
            disciplina_id=payload.disciplina_id,
            semestre=payload.semestre,
            prova1=informados.get("prova1"),
            prova2=informados.get("prova2"),
            trabalho=informados.get("trabalho"),
            participacao=informados.get("participacao"),
            observacao=payload.observacao,
        )
        db.add(nota)

    if nota.total > SEMESTRE_MAX:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"A soma do semestre não pode ultrapassar {SEMESTRE_MAX:.0f} pontos",
        )

    db.commit()
    nota = db.query(Nota).options(joinedload(Nota.disciplina)).filter(Nota.id == nota.id).one()
    try:
        from app.services.aprovacao import calcular_media_final, classificar_situacao
        from app.services.notifications import notify_nota_lancada, notify_recuperacao

        labels = {
            "prova1": "Prova 1",
            "prova2": "Prova 2",
            "trabalho": "Trabalho",
            "participacao": "Participação",
        }
        detalhe = ", ".join(f"{labels[k]}={v}" for k, v in informados.items()) or "atualização"
        nome_disc = nota.disciplina.nome if nota.disciplina else "Disciplina"
        notify_nota_lancada(db, nota.aluno_id, f"{nome_disc} ({detalhe})", nota.total)
        outras = (
            db.query(Nota)
            .filter(Nota.aluno_id == nota.aluno_id, Nota.disciplina_id == nota.disciplina_id)
            .all()
        )
        totais = {n.semestre: n.total for n in outras}
        media = calcular_media_final(totais.get(1), totais.get(2))
        if media is not None and classificar_situacao(media).value == "recuperacao":
            notify_recuperacao(db, nota.aluno_id, nome_disc, media)
    except Exception:
        pass

    return _serialize_nota(nota)


@router.patch("/{nota_id}", response_model=NotaOut)
def atualizar_nota(
    nota_id: int,
    payload: NotaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR)),
):
    nota = db.query(Nota).options(joinedload(Nota.disciplina)).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    if current_user.role == UserRole.PROFESSOR and nota.disciplina.professor_id != current_user.professor.id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(nota, key, value)
    if nota.total > SEMESTRE_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"A soma do semestre não pode ultrapassar {SEMESTRE_MAX:.0f} pontos",
        )
    db.commit()
    db.refresh(nota)
    return _serialize_nota(nota)


@router.delete("/{nota_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_nota(
    nota_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PROFESSOR)),
):
    nota = db.query(Nota).options(joinedload(Nota.disciplina)).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    if current_user.role == UserRole.PROFESSOR and nota.disciplina.professor_id != current_user.professor.id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    db.delete(nota)
    db.commit()
