from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, PyEnum):
    ADMIN = "admin"
    PROFESSOR = "professor"
    ALUNO = "aluno"


class Segmento(str, PyEnum):
    FUNDAMENTAL_I = "fundamental_1"
    FUNDAMENTAL_II = "fundamental_2"
    MEDIO = "medio"


class TipoOcorrencia(str, PyEnum):
    INDISCIPLINA = "indisciplina"
    FALTA_ATIVIDADE = "falta_atividade"
    ADVERTENCIA = "advertencia"
    SUSPENSAO = "suspensao"
    ELOGIO = "elogio"


class GravidadeOcorrencia(str, PyEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class TipoEvento(str, PyEnum):
    REUNIAO = "reuniao"
    FESTA = "festa"
    JOGO = "jogo"
    FEIRA_CIENCIA = "feira_ciencia"
    FORMATURA = "formatura"


class CategoriaNoticia(str, PyEnum):
    COMUNICADO = "comunicado"
    AVISO = "aviso"
    CALENDARIO = "calendario"
    INFORMACAO_GERAL = "informacao_geral"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # Aceite de Termos de Uso + Política de Privacidade (LGPD) no login
    termos_aceitos: Mapped[bool] = mapped_column(Boolean, default=False)
    termos_aceitos_em: Mapped[datetime | None] = mapped_column(DateTime)
    termos_versao: Mapped[str | None] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    professor: Mapped["Professor | None"] = relationship(back_populates="user", uselist=False)
    aluno: Mapped["Aluno | None"] = relationship(back_populates="user", uselist=False)


class Serie(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    segmento: Mapped[Segmento] = mapped_column(Enum(Segmento), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    turmas: Mapped[list["Turma"]] = relationship(back_populates="serie")


class Turma(Base):
    __tablename__ = "turmas"
    __table_args__ = (UniqueConstraint("serie_id", "nome", "ano_letivo", name="uq_turma"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(20), nullable=False)
    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey("series.id"), nullable=False)
    turno: Mapped[str] = mapped_column(String(20), default="manhã")

    serie: Mapped["Serie"] = relationship(back_populates="turmas")
    alunos: Mapped[list["Aluno"]] = relationship(back_populates="turma")
    disciplinas: Mapped[list["Disciplina"]] = relationship(back_populates="turma")


class Professor(Base):
    __tablename__ = "professores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    matricula: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    formacao: Mapped[str | None] = mapped_column(String(200))
    telefone: Mapped[str | None] = mapped_column(String(30))

    user: Mapped["User"] = relationship(back_populates="professor")
    disciplinas: Mapped[list["Disciplina"]] = relationship(back_populates="professor")


class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    matricula: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    responsavel_nome: Mapped[str | None] = mapped_column(String(200))
    responsavel_telefone: Mapped[str | None] = mapped_column(String(30))
    responsavel_cpf: Mapped[str | None] = mapped_column(String(14))
    turma_id: Mapped[int | None] = mapped_column(ForeignKey("turmas.id"))
    # LGPD — consentimento do responsável para tratamento de dados do menor
    lgpd_consentimento: Mapped[bool] = mapped_column(Boolean, default=False)
    lgpd_consentimento_em: Mapped[datetime | None] = mapped_column(DateTime)
    lgpd_consentimento_por: Mapped[str | None] = mapped_column(String(200))

    user: Mapped["User"] = relationship(back_populates="aluno")
    turma: Mapped["Turma | None"] = relationship(back_populates="alunos")
    notas: Mapped[list["Nota"]] = relationship(back_populates="aluno")
    ocorrencias: Mapped[list["Ocorrencia"]] = relationship(back_populates="aluno")


class Disciplina(Base):
    __tablename__ = "disciplinas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    carga_horaria: Mapped[int] = mapped_column(Integer, default=80)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id"), nullable=False)
    professor_id: Mapped[int | None] = mapped_column(ForeignKey("professores.id"))

    turma: Mapped["Turma"] = relationship(back_populates="disciplinas")
    professor: Mapped["Professor | None"] = relationship(back_populates="disciplinas")
    notas: Mapped[list["Nota"]] = relationship(back_populates="disciplina")


class Nota(Base):
    """Nota por semestre: Prova1(15) + Prova2(15) + Trabalho(10) + Participação(10) = 50.
    Pontuação anual = S1 + S2 (máx. 100). Aprovado se soma ≥ 60."""

    __tablename__ = "notas"
    __table_args__ = (
        UniqueConstraint("aluno_id", "disciplina_id", "semestre", name="uq_nota_semestre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    disciplina_id: Mapped[int] = mapped_column(ForeignKey("disciplinas.id"), nullable=False)
    semestre: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 ou 2
    # None = ainda não lançada (não confundir com nota zero)
    prova1: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    prova2: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    trabalho: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    participacao: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    observacao: Mapped[str | None] = mapped_column(String(300))
    lancado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aluno: Mapped["Aluno"] = relationship(back_populates="notas")
    disciplina: Mapped["Disciplina"] = relationship(back_populates="notas")

    @property
    def total(self) -> float:
        partes = (self.prova1, self.prova2, self.trabalho, self.participacao)
        return round(sum(v or 0.0 for v in partes), 2)


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tipo: Mapped[TipoOcorrencia] = mapped_column(Enum(TipoOcorrencia), nullable=False)
    gravidade: Mapped[GravidadeOcorrencia] = mapped_column(
        Enum(GravidadeOcorrencia), nullable=False, default=GravidadeOcorrencia.MEDIA
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data_ocorrencia: Mapped[date] = mapped_column(Date, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aluno: Mapped["Aluno"] = relationship(back_populates="ocorrencias")
    registrado_por: Mapped["User"] = relationship()


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[TipoEvento] = mapped_column(Enum(TipoEvento), nullable=False, default=TipoEvento.REUNIAO)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data_evento: Mapped[date] = mapped_column(Date, nullable=False)
    horario: Mapped[str] = mapped_column(String(10), nullable=False, default="08:00")
    local: Mapped[str | None] = mapped_column(String(200))
    publico: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_por_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    criado_por: Mapped["User"] = relationship()


class Noticia(Base):
    __tablename__ = "noticias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    categoria: Mapped[CategoriaNoticia] = mapped_column(
        Enum(CategoriaNoticia), nullable=False, default=CategoriaNoticia.COMUNICADO
    )
    titulo: Mapped[str] = mapped_column(String(250), nullable=False)
    resumo: Mapped[str] = mapped_column(String(500), nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    publicada: Mapped[bool] = mapped_column(Boolean, default=True)
    autor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    publicado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    autor: Mapped["User"] = relationship()


class Matricula(Base):
    __tablename__ = "matriculas"
    __table_args__ = (UniqueConstraint("aluno_id", "turma_id", "ano_letivo", name="uq_matricula"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id"), nullable=False)
    ano_letivo: Mapped[int] = mapped_column(Integer, nullable=False)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    data_matricula: Mapped[date] = mapped_column(Date, default=date.today)

    aluno: Mapped["Aluno"] = relationship()
    turma: Mapped["Turma"] = relationship()


class Permissao(Base):
    __tablename__ = "permissoes"
    __table_args__ = (UniqueConstraint("role", "recurso", name="uq_permissao"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    recurso: Mapped[str] = mapped_column(String(80), nullable=False)
    pode_criar: Mapped[bool] = mapped_column(Boolean, default=False)
    pode_ler: Mapped[bool] = mapped_column(Boolean, default=True)
    pode_atualizar: Mapped[bool] = mapped_column(Boolean, default=False)
    pode_excluir: Mapped[bool] = mapped_column(Boolean, default=False)


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    acao: Mapped[str] = mapped_column(String(120), nullable=False)
    detalhe: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User | None"] = relationship()


class Escola(Base):
    """Personalização e identidade visual da escola (singleton lógico)."""

    __tablename__ = "escola"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    slogan: Mapped[str | None] = mapped_column(String(300))
    logo: Mapped[str | None] = mapped_column(String(500))
    cnpj: Mapped[str | None] = mapped_column(String(20))
    telefone: Mapped[str | None] = mapped_column(String(30))
    whatsapp: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    site: Mapped[str | None] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(String(300))
    cidade: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[str | None] = mapped_column(String(2))
    cep: Mapped[str | None] = mapped_column(String(12))
    diretor: Mapped[str | None] = mapped_column(String(200))
    vice_diretor: Mapped[str | None] = mapped_column(String(200))
    cor_primaria: Mapped[str] = mapped_column(String(20), default="#0f6e7c")
    cor_secundaria: Mapped[str] = mapped_column(String(20), default="#0a4f59")
    cor_botoes: Mapped[str] = mapped_column(String(20), default="#0f6e7c")
    cor_menu: Mapped[str] = mapped_column(String(20), default="#0b1f2a")
    tema: Mapped[str] = mapped_column(String(20), default="claro")  # claro | escuro
    logo_fundo_login: Mapped[str | None] = mapped_column(String(500))
    facebook: Mapped[str | None] = mapped_column(String(255))
    instagram: Mapped[str | None] = mapped_column(String(255))
    youtube: Mapped[str | None] = mapped_column(String(255))
    rodape_impressao: Mapped[str | None] = mapped_column(String(500))
    mostrar_cnpj_impressao: Mapped[bool] = mapped_column(Boolean, default=True)
    setup_completo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WhatsAppPerfil(str, PyEnum):
    DESCONHECIDO = "desconhecido"
    ALUNO = "aluno"
    RESPONSAVEL = "responsavel"
    PROFESSOR = "professor"
    ADMIN = "admin"


class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    perfil: Mapped[WhatsAppPerfil] = mapped_column(
        Enum(WhatsAppPerfil, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=WhatsAppPerfil.DESCONHECIDO,
    )
    verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    aluno_id: Mapped[int | None] = mapped_column(ForeignKey("alunos.id"))
    estado: Mapped[str] = mapped_column(String(40), default="inicio")  # inicio|perfil|credenciais|codigo|pronto
    codigo_verificacao: Mapped[str | None] = mapped_column(String(10))
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    contexto_json: Mapped[str | None] = mapped_column(Text)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User | None"] = relationship()
    aluno: Mapped["Aluno | None"] = relationship()


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_mensagens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    direcao: Mapped[str] = mapped_column(String(10), nullable=False)  # in|out
    tipo: Mapped[str] = mapped_column(String(20), default="text")  # text|audio
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificacaoWhatsApp(Base):
    __tablename__ = "whatsapp_notificacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    evento: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)
    enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Falta(Base):
    __tablename__ = "faltas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), nullable=False)
    disciplina_id: Mapped[int | None] = mapped_column(ForeignKey("disciplinas.id"))
    data_falta: Mapped[date] = mapped_column(Date, nullable=False)
    justificativa: Mapped[str | None] = mapped_column(String(300))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    aluno: Mapped["Aluno"] = relationship()
