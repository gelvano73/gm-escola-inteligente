from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import Base, engine


def _drop_if_outdated(table: str, required: set[str], forbidden: set[str] | None = None) -> bool:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return False
    colunas = {c["name"] for c in inspector.get_columns(table)}
    if forbidden and forbidden & colunas:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        return True
    if not required.issubset(colunas):
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        return True
    return False


def _safe_create_all() -> None:
    """create_all idempotente (evita race em reload/SQLite)."""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except OperationalError as exc:
        if "already exists" not in str(exc).lower():
            raise


def ensure_schema_upgrades() -> bool:
    """Recria tabelas cujo schema mudou e cria tabelas novas."""
    dropped = False
    dropped |= _drop_if_outdated("notas", {"semestre", "prova1"}, {"bimestre"})
    dropped |= _drop_if_outdated("ocorrencias", {"gravidade", "tipo"}, {"titulo"})
    dropped |= _drop_if_outdated("eventos", {"tipo", "data_evento", "horario"}, {"data_inicio"})
    dropped |= _drop_if_outdated("noticias", {"categoria"})
    _safe_create_all()

    # Notas: componentes podem ficar NULL até serem lançados (SQLite NOT NULL → rebuild)
    _ensure_notas_components_nullable()

    # colunas novas em tabelas existentes (SQLite)
    inspector = inspect(engine)
    if "alunos" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("alunos")}
        with engine.begin() as conn:
            if "responsavel_cpf" not in cols:
                conn.execute(text("ALTER TABLE alunos ADD COLUMN responsavel_cpf VARCHAR(14)"))
            if "lgpd_consentimento" not in cols:
                conn.execute(text("ALTER TABLE alunos ADD COLUMN lgpd_consentimento BOOLEAN DEFAULT 0"))
            if "lgpd_consentimento_em" not in cols:
                conn.execute(text("ALTER TABLE alunos ADD COLUMN lgpd_consentimento_em DATETIME"))
            if "lgpd_consentimento_por" not in cols:
                conn.execute(text("ALTER TABLE alunos ADD COLUMN lgpd_consentimento_por VARCHAR(200)"))
    return dropped


def _ensure_notas_components_nullable() -> None:
    """Permite NULL em prova1/prova2/trabalho/participacao (nota ainda não lançada)."""
    inspector = inspect(engine)
    if "notas" not in inspector.get_table_names():
        return
    cols = {c["name"]: c for c in inspector.get_columns("notas")}
    precisa_rebuild = False
    for name in ("prova1", "prova2", "trabalho", "participacao"):
        info = cols.get(name)
        if info is None:
            return
        if info.get("nullable") is False:
            precisa_rebuild = True
            break

    if precisa_rebuild:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE notas__nullable (
                        id INTEGER NOT NULL PRIMARY KEY,
                        aluno_id INTEGER NOT NULL,
                        disciplina_id INTEGER NOT NULL,
                        semestre INTEGER NOT NULL,
                        prova1 FLOAT,
                        prova2 FLOAT,
                        trabalho FLOAT,
                        participacao FLOAT,
                        observacao VARCHAR(300),
                        lancado_em DATETIME,
                        FOREIGN KEY(aluno_id) REFERENCES alunos (id),
                        FOREIGN KEY(disciplina_id) REFERENCES disciplinas (id),
                        UNIQUE (aluno_id, disciplina_id, semestre)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO notas__nullable
                        (id, aluno_id, disciplina_id, semestre, prova1, prova2, trabalho, participacao, observacao, lancado_em)
                    SELECT id, aluno_id, disciplina_id, semestre, prova1, prova2, trabalho, participacao, observacao, lancado_em
                    FROM notas
                    """
                )
            )
            conn.execute(text("DROP TABLE notas"))
            conn.execute(text("ALTER TABLE notas__nullable RENAME TO notas"))

    # Zeros fantasma de lançamento parcial: se 1–3 avaliações têm valor > 0
    # e outras estão em 0, limpa os 0 para NULL (nota zero real em semestre completo não é afetada).
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE notas SET
                    prova1 = CASE WHEN prova1 = 0 THEN NULL ELSE prova1 END,
                    prova2 = CASE WHEN prova2 = 0 THEN NULL ELSE prova2 END,
                    trabalho = CASE WHEN trabalho = 0 THEN NULL ELSE trabalho END,
                    participacao = CASE WHEN participacao = 0 THEN NULL ELSE participacao END
                WHERE (
                    (CASE WHEN prova1 IS NOT NULL AND prova1 != 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN prova2 IS NOT NULL AND prova2 != 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN trabalho IS NOT NULL AND trabalho != 0 THEN 1 ELSE 0 END) +
                    (CASE WHEN participacao IS NOT NULL AND participacao != 0 THEN 1 ELSE 0 END)
                ) BETWEEN 1 AND 3
                """
            )
        )

    # Remove valores do seed antigo (P2/Trab/Part preenchidos juntos) que grudavam no upsert parcial
    with engine.begin() as conn:
        for p2, trab, part in ((8, 4, 3), (10, 8, 5), (6, 3, 2), (5, 3, 2)):
            conn.execute(
                text(
                    """
                    UPDATE notas
                    SET prova2 = NULL, trabalho = NULL, participacao = NULL
                    WHERE prova2 = :p2 AND trabalho = :trab AND participacao = :part
                    """
                ),
                {"p2": p2, "trab": trab, "part": part},
            )
