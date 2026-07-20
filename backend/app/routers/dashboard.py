from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.deps import require_roles
from app.models import Aluno, Nota, Ocorrencia, Professor, Serie, Turma, User, UserRole
from app.schemas import ChartPoint, DashboardStats
from app.services.aprovacao import SituacaoAcademica, calcular_media_final, classificar_situacao

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _medias_por_disciplina(db: Session) -> list[tuple[Nota, float | None, SituacaoAcademica]]:
    notas = db.query(Nota).options(
        joinedload(Nota.aluno).joinedload(Aluno.turma).joinedload(Turma.serie),
        joinedload(Nota.disciplina),
    ).all()
    agrupado: dict[tuple[int, int], dict[int, float]] = defaultdict(dict)
    meta: dict[tuple[int, int], Nota] = {}
    for n in notas:
        key = (n.aluno_id, n.disciplina_id)
        agrupado[key][n.semestre] = n.total
        meta[key] = n

    resultado = []
    for key, totais in agrupado.items():
        media = calcular_media_final(totais.get(1), totais.get(2))
        situacao = classificar_situacao(media, tem_parcial=bool(totais) and media is None)
        resultado.append((meta[key], media, situacao))
    return resultado


@router.get("/stats", response_model=DashboardStats)
def estatisticas(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    itens = _medias_por_disciplina(db)
    medias_validas = [m for _, m, _ in itens if m is not None]
    aprovacoes = sum(1 for _, _, s in itens if s == SituacaoAcademica.APROVADO)
    recuperacoes = sum(1 for _, _, s in itens if s == SituacaoAcademica.RECUPERACAO)
    reprovacoes = sum(1 for _, _, s in itens if s == SituacaoAcademica.REPROVADO)

    # Desempenho por turma
    soma_turma: dict[str, list[float]] = defaultdict(list)
    # Aprovação por série
    serie_stats: dict[str, list[bool]] = defaultdict(list)
    # Evolução semestral
    sem1: list[float] = []
    sem2: list[float] = []

    notas = db.query(Nota).options(
        joinedload(Nota.aluno).joinedload(Aluno.turma).joinedload(Turma.serie)
    ).all()
    for n in notas:
        if n.semestre == 1:
            sem1.append(n.total)
        elif n.semestre == 2:
            sem2.append(n.total)

    for nota, media, situacao in itens:
        aluno = nota.aluno
        if not aluno or not aluno.turma:
            continue
        turma_label = f"{aluno.turma.serie.nome if aluno.turma.serie else 'Turma'} {aluno.turma.nome}"
        if media is not None:
            soma_turma[turma_label].append(media)
        serie_nome = aluno.turma.serie.nome if aluno.turma.serie else "Sem série"
        serie_stats[serie_nome].append(situacao == SituacaoAcademica.APROVADO)

    desempenho_turmas = [
        ChartPoint(label=k, value=round(sum(v) / len(v), 1))
        for k, v in sorted(soma_turma.items())
        if v
    ]
    aprovacao_series = [
        ChartPoint(label=k, value=round(100 * sum(1 for x in v if x) / len(v), 1) if v else 0)
        for k, v in sorted(serie_stats.items())
    ]
    evolucao = [
        ChartPoint(label="1º Semestre", value=round(sum(sem1) / len(sem1), 1) if sem1 else 0),
        ChartPoint(label="2º Semestre", value=round(sum(sem2) / len(sem2), 1) if sem2 else 0),
    ]

    return DashboardStats(
        total_alunos=db.query(Aluno).count(),
        total_professores=db.query(Professor).count(),
        total_turmas=db.query(Turma).count(),
        total_ocorrencias=db.query(Ocorrencia).count(),
        media_geral=round(sum(medias_validas) / len(medias_validas), 1) if medias_validas else None,
        aprovacoes=aprovacoes,
        recuperacoes=recuperacoes,
        reprovacoes=reprovacoes,
        desempenho_turmas=desempenho_turmas,
        aprovacao_series=aprovacao_series,
        evolucao_semestral=evolucao,
    )
