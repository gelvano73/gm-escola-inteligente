from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.deps import require_roles
from app.models import Aluno, Disciplina, Nota, Ocorrencia, Professor, Turma, User, UserRole
from app.schemas import RelatorioGeral
from app.services.aprovacao import SituacaoAcademica, calcular_media_final, classificar_situacao

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@router.get("/geral", response_model=RelatorioGeral)
def relatorio_geral(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    notas = db.query(Nota).all()
    agrupado: dict[tuple[int, int], dict[int, float]] = defaultdict(dict)
    for n in notas:
        agrupado[(n.aluno_id, n.disciplina_id)][n.semestre] = n.total

    contagem = {
        SituacaoAcademica.APROVADO: 0,
        SituacaoAcademica.RECUPERACAO: 0,
        SituacaoAcademica.REPROVADO: 0,
        SituacaoAcademica.SEM_NOTAS: 0,
        SituacaoAcademica.INCOMPLETO: 0,
    }
    for totais in agrupado.values():
        media = calcular_media_final(totais.get(1), totais.get(2))
        situacao = classificar_situacao(media, tem_parcial=bool(totais) and media is None)
        contagem[situacao] += 1

    alunos_com_nota = {aid for (aid, _) in agrupado}
    sem_notas = db.query(Aluno).count() - len(alunos_com_nota)

    return RelatorioGeral(
        total_alunos=db.query(Aluno).count(),
        total_professores=db.query(Professor).count(),
        total_turmas=db.query(Turma).count(),
        total_disciplinas=db.query(Disciplina).count(),
        total_ocorrencias=db.query(Ocorrencia).count(),
        aprovados=contagem[SituacaoAcademica.APROVADO],
        recuperacao=contagem[SituacaoAcademica.RECUPERACAO],
        reprovados=contagem[SituacaoAcademica.REPROVADO],
        sem_notas=max(sem_notas, 0) + contagem[SituacaoAcademica.SEM_NOTAS] + contagem[SituacaoAcademica.INCOMPLETO],
    )
