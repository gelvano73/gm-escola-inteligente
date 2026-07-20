from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import (
    Aluno,
    CategoriaNoticia,
    Disciplina,
    Escola,
    Evento,
    Falta,
    GravidadeOcorrencia,
    Matricula,
    Noticia,
    Nota,
    Ocorrencia,
    Permissao,
    Professor,
    Segmento,
    Serie,
    TipoEvento,
    TipoOcorrencia,
    Turma,
    User,
    UserRole,
)
from app.services.credenciais import senha_inicial_aluno

SERIES_SEED = [
    ("1º Ano Fundamental", Segmento.FUNDAMENTAL_I, 1),
    ("2º Ano Fundamental", Segmento.FUNDAMENTAL_I, 2),
    ("3º Ano Fundamental", Segmento.FUNDAMENTAL_I, 3),
    ("4º Ano Fundamental", Segmento.FUNDAMENTAL_I, 4),
    ("5º Ano Fundamental", Segmento.FUNDAMENTAL_I, 5),
    ("6º Ano Fundamental", Segmento.FUNDAMENTAL_II, 6),
    ("7º Ano Fundamental", Segmento.FUNDAMENTAL_II, 7),
    ("8º Ano Fundamental", Segmento.FUNDAMENTAL_II, 8),
    ("9º Ano Fundamental", Segmento.FUNDAMENTAL_II, 9),
    ("1º Ano Ensino Médio", Segmento.MEDIO, 10),
    ("2º Ano Ensino Médio", Segmento.MEDIO, 11),
    ("3º Ano Ensino Médio", Segmento.MEDIO, 12),
]


def _ensure_demo_credentials(db: Session) -> None:
    """Garante regras de 1º acesso nas contas de demonstração."""
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        admin.hashed_password = get_password_hash("123456")
        admin.must_change_password = True
        admin.role = UserRole.ADMIN

    professor = db.query(User).filter(User.username == "professor").first()
    if professor:
        professor.hashed_password = get_password_hash("prof123")
        professor.must_change_password = True

    aluno = db.query(Aluno).filter(Aluno.matricula == "A2026001").first()
    if aluno and aluno.user:
        if not aluno.data_nascimento:
            aluno.data_nascimento = datetime(2011, 5, 12).date()
        aluno.user.username = "A2026001"
        aluno.user.hashed_password = get_password_hash(senha_inicial_aluno(aluno.data_nascimento))
        aluno.user.must_change_password = True
        if not aluno.responsavel_cpf:
            aluno.responsavel_cpf = "12345678901"
        if not aluno.responsavel_telefone:
            aluno.responsavel_telefone = "11977770001"

    # Se a tabela de notas foi recriada, popular exemplo semestral do aluno demo
    if aluno and db.query(Nota).count() == 0:
        disciplinas = db.query(Disciplina).filter(Disciplina.turma_id == aluno.turma_id).all()
        if len(disciplinas) >= 2:
            disc_mat, disc_port = disciplinas[0], disciplinas[1]
            db.add_all(
                [
                    # Exemplo parcial: só Prova 1 (as demais ficam em branco até o lançamento)
                    Nota(
                        aluno_id=aluno.id,
                        disciplina_id=disc_mat.id,
                        semestre=1,
                        prova1=10,
                    ),
                    Nota(
                        aluno_id=aluno.id,
                        disciplina_id=disc_mat.id,
                        semestre=2,
                        prova1=12,
                    ),
                    Nota(
                        aluno_id=aluno.id,
                        disciplina_id=disc_port.id,
                        semestre=1,
                        prova1=8,
                    ),
                    Nota(
                        aluno_id=aluno.id,
                        disciplina_id=disc_port.id,
                        semestre=2,
                        prova1=7,
                    ),
                ]
            )
    elif aluno:
        # Migra notas demo antigas (semestre /100) para a escala /50
        notas_antigas = (
            db.query(Nota)
            .filter(Nota.aluno_id == aluno.id)
            .all()
        )
        if any(n.total > 50 for n in notas_antigas):
            for n in notas_antigas:
                db.delete(n)
            db.flush()
            disciplinas = db.query(Disciplina).filter(Disciplina.turma_id == aluno.turma_id).all()
            if len(disciplinas) >= 2:
                disc_mat, disc_port = disciplinas[0], disciplinas[1]
                db.add_all(
                    [
                        Nota(aluno_id=aluno.id, disciplina_id=disc_mat.id, semestre=1, prova1=10, prova2=8, trabalho=4, participacao=3),
                        Nota(aluno_id=aluno.id, disciplina_id=disc_mat.id, semestre=2, prova1=12, prova2=10, trabalho=8, participacao=5),
                        Nota(aluno_id=aluno.id, disciplina_id=disc_port.id, semestre=1, prova1=8, prova2=6, trabalho=3, participacao=2),
                        Nota(aluno_id=aluno.id, disciplina_id=disc_port.id, semestre=2, prova1=7, prova2=5, trabalho=3, participacao=2),
                    ]
                )

    if aluno and db.query(Falta).filter(Falta.aluno_id == aluno.id).count() == 0:
        disciplinas = db.query(Disciplina).filter(Disciplina.turma_id == aluno.turma_id).all()
        disc_id = disciplinas[0].id if disciplinas else None
        db.add_all(
            [
                Falta(
                    aluno_id=aluno.id,
                    disciplina_id=disc_id,
                    data_falta=datetime(2026, 4, 2).date(),
                    justificativa="Consulta médica",
                ),
                Falta(
                    aluno_id=aluno.id,
                    disciplina_id=disc_id,
                    data_falta=datetime(2026, 5, 8).date(),
                ),
            ]
        )

    if admin and db.query(Evento).count() == 0:
        db.add(
            Evento(
                tipo=TipoEvento.FEIRA_CIENCIA,
                titulo="Feira de Ciências 2026",
                descricao="Apresentação de projetos científicos de todas as séries.",
                data_evento=datetime(2026, 9, 15).date(),
                horario="08:00",
                local="Ginásio",
                publico=True,
                criado_por_id=admin.id,
            )
        )
    if admin and db.query(Noticia).count() == 0:
        db.add(
            Noticia(
                categoria=CategoriaNoticia.COMUNICADO,
                titulo="Bem-vindos ao ano letivo 2026",
                resumo="A G&M Escola Inteligente inicia o ano com novas ferramentas digitais.",
                conteudo="Portal acadêmico disponível para toda a comunidade escolar.",
                publicada=True,
                autor_id=admin.id,
            )
        )
    if aluno and professor and db.query(Ocorrencia).count() == 0:
        db.add(
            Ocorrencia(
                aluno_id=aluno.id,
                registrado_por_id=professor.id,
                tipo=TipoOcorrencia.ELOGIO,
                gravidade=GravidadeOcorrencia.BAIXA,
                descricao="Aluno colaborou ativamente na atividade em grupo.",
                data_ocorrencia=datetime(2026, 3, 10).date(),
            )
        )
    if aluno and aluno.turma_id and db.query(Matricula).count() == 0:
        db.add(Matricula(aluno_id=aluno.id, turma_id=aluno.turma_id, ano_letivo=2026, ativa=True))
    if db.query(Permissao).count() == 0:
        for role, recurso, c, r, u, d in [
            (UserRole.ADMIN, "dashboard", True, True, True, True),
            (UserRole.PROFESSOR, "notas", True, True, True, False),
            (UserRole.PROFESSOR, "ocorrencias", True, True, False, False),
            (UserRole.ALUNO, "notas", False, True, False, False),
        ]:
            db.add(Permissao(role=role, recurso=recurso, pode_criar=c, pode_ler=r, pode_atualizar=u, pode_excluir=d))

    db.commit()


def _ensure_escola(db: Session) -> None:
    escola = db.query(Escola).first()
    if escola:
        return
    db.add(
        Escola(
            nome="G&M Escola Inteligente",
            slogan="Educação que transforma vidas",
            email="contato@gm.edu.br",
            telefone="(11) 3000-0000",
            whatsapp="(11) 99000-0000",
            cidade="São Paulo",
            estado="SP",
            diretor="Direção Geral",
            vice_diretor="Vice-Direção",
            cor_primaria="#0f6e7c",
            cor_secundaria="#0a4f59",
            cor_botoes="#0f6e7c",
            cor_menu="#0b1f2a",
            tema="claro",
            rodape_impressao="Documento gerado pelo portal acadêmico",
            mostrar_cnpj_impressao=True,
            setup_completo=True,
        )
    )
    db.commit()


def seed_database(db: Session) -> None:
    _ensure_escola(db)

    for nome, segmento, ordem in SERIES_SEED:
        if not db.query(Serie).filter(Serie.nome == nome).first():
            db.add(Serie(nome=nome, segmento=segmento, ordem=ordem))
    db.flush()

    if db.query(User).filter(User.username == "admin").first():
        _ensure_demo_credentials(db)
        return

    admin = User(
        username="admin",
        email="admin@gm.edu.br",
        nome="Administrador G&M",
        hashed_password=get_password_hash("123456"),
        role=UserRole.ADMIN,
        must_change_password=True,
    )
    db.add(admin)
    db.flush()

    serie_9 = db.query(Serie).filter(Serie.ordem == 9).one()
    serie_1m = db.query(Serie).filter(Serie.ordem == 10).one()

    turma_9a = db.query(Turma).filter(Turma.serie_id == serie_9.id, Turma.nome == "A").first()
    if not turma_9a:
        turma_9a = Turma(nome="A", ano_letivo=2026, serie_id=serie_9.id, turno="manhã")
        db.add(turma_9a)
    turma_1ma = db.query(Turma).filter(Turma.serie_id == serie_1m.id, Turma.nome == "A").first()
    if not turma_1ma:
        turma_1ma = Turma(nome="A", ano_letivo=2026, serie_id=serie_1m.id, turno="manhã")
        db.add(turma_1ma)
    db.flush()

    prof_user = User(
        username="professor",
        email="professor@gm.edu.br",
        nome="Ana Professora",
        hashed_password=get_password_hash("prof123"),
        role=UserRole.PROFESSOR,
        must_change_password=True,
    )
    db.add(prof_user)
    db.flush()
    professor = Professor(
        user_id=prof_user.id,
        matricula="P2026001",
        formacao="Licenciatura em Matemática",
        telefone="(11) 98888-0001",
    )
    db.add(professor)
    db.flush()

    data_nasc = datetime(2011, 5, 12).date()
    aluno_user = User(
        username="A2026001",
        email="aluno@gm.edu.br",
        nome="João Aluno",
        hashed_password=get_password_hash(senha_inicial_aluno(data_nasc)),
        role=UserRole.ALUNO,
        must_change_password=True,
    )
    db.add(aluno_user)
    db.flush()
    aluno = Aluno(
        user_id=aluno_user.id,
        matricula="A2026001",
        data_nascimento=data_nasc,
        responsavel_nome="Maria Responsável",
        responsavel_telefone="11977770001",
        responsavel_cpf="12345678901",
        turma_id=turma_9a.id,
    )
    db.add(aluno)
    db.flush()

    disc_mat = Disciplina(nome="Matemática", carga_horaria=120, turma_id=turma_9a.id, professor_id=professor.id)
    disc_port = Disciplina(nome="Português", carga_horaria=120, turma_id=turma_9a.id, professor_id=professor.id)
    db.add_all([disc_mat, disc_port])
    db.flush()

    db.add_all(
        [
            Nota(
                aluno_id=aluno.id,
                disciplina_id=disc_mat.id,
                semestre=1,
                prova1=10,
            ),
            Nota(
                aluno_id=aluno.id,
                disciplina_id=disc_mat.id,
                semestre=2,
                prova1=12,
            ),
            Nota(
                aluno_id=aluno.id,
                disciplina_id=disc_port.id,
                semestre=1,
                prova1=8,
            ),
            Nota(
                aluno_id=aluno.id,
                disciplina_id=disc_port.id,
                semestre=2,
                prova1=7,
            ),
        ]
    )

    db.add(
        Evento(
            tipo=TipoEvento.FEIRA_CIENCIA,
            titulo="Feira de Ciências 2026",
            descricao="Apresentação de projetos científicos de todas as séries.",
            data_evento=datetime(2026, 9, 15).date(),
            horario="08:00",
            local="Ginásio",
            publico=True,
            criado_por_id=admin.id,
        )
    )
    db.add(
        Noticia(
            categoria=CategoriaNoticia.COMUNICADO,
            titulo="Bem-vindos ao ano letivo 2026",
            resumo="A G&M Escola Inteligente inicia o ano com novas ferramentas digitais.",
            conteudo=(
                "Estamos felizes em apresentar o novo portal acadêmico. "
                "Alunos, professores e responsáveis poderão acompanhar notas, "
                "ocorrências, eventos e notícias em um só lugar."
            ),
            publicada=True,
            autor_id=admin.id,
        )
    )
    db.add(
        Ocorrencia(
            aluno_id=aluno.id,
            registrado_por_id=prof_user.id,
            tipo=TipoOcorrencia.ELOGIO,
            gravidade=GravidadeOcorrencia.BAIXA,
            descricao="Aluno colaborou ativamente na atividade em grupo.",
            data_ocorrencia=datetime(2026, 3, 10).date(),
        )
    )
    db.add_all(
        [
            Falta(
                aluno_id=aluno.id,
                disciplina_id=disc_mat.id,
                data_falta=datetime(2026, 4, 2).date(),
                justificativa="Consulta médica",
            ),
            Falta(
                aluno_id=aluno.id,
                disciplina_id=disc_port.id,
                data_falta=datetime(2026, 5, 8).date(),
            ),
        ]
    )

    db.add(
        Matricula(
            aluno_id=aluno.id,
            turma_id=turma_9a.id,
            ano_letivo=2026,
            ativa=True,
        )
    )

    permissoes_seed = [
        (UserRole.ADMIN, "dashboard", True, True, True, True),
        (UserRole.ADMIN, "alunos", True, True, True, True),
        (UserRole.ADMIN, "professores", True, True, True, True),
        (UserRole.ADMIN, "turmas", True, True, True, True),
        (UserRole.ADMIN, "disciplinas", True, True, True, True),
        (UserRole.ADMIN, "notas", True, True, True, True),
        (UserRole.ADMIN, "ocorrencias", True, True, True, True),
        (UserRole.ADMIN, "eventos", True, True, True, True),
        (UserRole.ADMIN, "noticias", True, True, True, True),
        (UserRole.PROFESSOR, "notas", True, True, True, False),
        (UserRole.PROFESSOR, "ocorrencias", True, True, False, False),
        (UserRole.PROFESSOR, "alunos", False, True, False, False),
        (UserRole.PROFESSOR, "turmas", False, True, False, False),
        (UserRole.ALUNO, "notas", False, True, False, False),
        (UserRole.ALUNO, "ocorrencias", False, True, False, False),
        (UserRole.ALUNO, "eventos", False, True, False, False),
        (UserRole.ALUNO, "noticias", False, True, False, False),
    ]
    for role, recurso, c, r, u, d in permissoes_seed:
        db.add(
            Permissao(
                role=role,
                recurso=recurso,
                pode_criar=c,
                pode_ler=r,
                pode_atualizar=u,
                pode_excluir=d,
            )
        )

    db.commit()
