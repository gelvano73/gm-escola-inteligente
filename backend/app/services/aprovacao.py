from enum import Enum


class SituacaoAcademica(str, Enum):
    APROVADO = "aprovado"
    RECUPERACAO = "recuperacao"
    REPROVADO = "reprovado"
    SEM_NOTAS = "sem_notas"
    INCOMPLETO = "incompleto"


# Pontuação final do ano = S1 + S2 (máx. 100). Aprovado por soma, não por média.
PONTOS_APROVACAO = 60.0
PONTOS_RECUPERACAO = 30.0
TOTAL_ANO_MAX = 100.0

# Cada semestre fecha em 50 pontos (os dois somam 100)
PROVA_MAX = 15.0
TRABALHO_MAX = 10.0
PARTICIPACAO_MAX = 10.0
SEMESTRE_MAX = 50.0

# Compatibilidade com nomes antigos
MEDIA_APROVACAO = PONTOS_APROVACAO
MEDIA_RECUPERACAO = PONTOS_RECUPERACAO


def total_semestre(
    prova1: float | None,
    prova2: float | None,
    trabalho: float | None,
    participacao: float | None,
) -> float:
    """Soma só o que já foi lançado; None conta como 0 no total parcial."""
    return round(sum(v or 0.0 for v in (prova1, prova2, trabalho, participacao)), 2)


def calcular_pontuacao_final(total_1: float | None, total_2: float | None) -> float | None:
    """Pontuação final = 1º Semestre + 2º Semestre (máx. 100). Exige os dois semestres."""
    if total_1 is None or total_2 is None:
        return None
    return round(total_1 + total_2, 2)


def calcular_media_final(total_1: float | None, total_2: float | None) -> float | None:
    """Alias: retorna a soma dos semestres (não é média aritmética)."""
    return calcular_pontuacao_final(total_1, total_2)


def classificar_situacao(pontuacao_final: float | None, tem_parcial: bool = False) -> SituacaoAcademica:
    if pontuacao_final is None:
        return SituacaoAcademica.INCOMPLETO if tem_parcial else SituacaoAcademica.SEM_NOTAS
    if pontuacao_final >= PONTOS_APROVACAO:
        return SituacaoAcademica.APROVADO
    if pontuacao_final >= PONTOS_RECUPERACAO:
        return SituacaoAcademica.RECUPERACAO
    return SituacaoAcademica.REPROVADO


def rotulo_situacao(situacao: SituacaoAcademica) -> str:
    return {
        SituacaoAcademica.APROVADO: "Aprovado",
        SituacaoAcademica.RECUPERACAO: "Recuperação",
        SituacaoAcademica.REPROVADO: "Reprovado",
        SituacaoAcademica.SEM_NOTAS: "Sem notas",
        SituacaoAcademica.INCOMPLETO: "Aguardando 2º semestre",
    }[situacao]
