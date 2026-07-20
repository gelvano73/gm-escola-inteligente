from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import CategoriaNoticia, GravidadeOcorrencia, Segmento, TipoEvento, TipoOcorrencia, UserRole
from app.services.aprovacao import SituacaoAcademica


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1, description="Username ou e-mail")
    password: str
    aceite_termos: bool = False
    aceite_privacidade: bool = False


class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=6)
    confirmar_senha: str = Field(min_length=6)

    @field_validator("confirmar_senha")
    @classmethod
    def senhas_iguais(cls, value: str, info):
        if "nova_senha" in info.data and value != info.data["nova_senha"]:
            raise ValueError("A confirmação da senha não confere")
        return value


class UserBase(BaseModel):
    username: str
    email: EmailStr
    nome: str
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    must_change_password: bool
    termos_aceitos: bool = False
    termos_versao: str | None = None
    criado_em: datetime


class SerieCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    segmento: Segmento
    ordem: int = Field(ge=1, le=99)


class SerieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    segmento: Segmento
    ordem: int


class TurmaCreate(BaseModel):
    nome: str
    ano_letivo: int
    serie_id: int
    turno: str = "manhã"


class TurmaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    ano_letivo: int
    serie_id: int
    turno: str
    serie: SerieOut | None = None


class AlunoCreate(BaseModel):
    email: EmailStr
    nome: str
    matricula: str
    data_nascimento: date
    responsavel_nome: str | None = None
    responsavel_telefone: str | None = None
    turma_id: int | None = None
    username: str | None = None
    lgpd_consentimento: bool = False
    lgpd_consentimento_por: str | None = None


class AlunoUpdate(BaseModel):
    nome: str | None = None
    data_nascimento: date | None = None
    responsavel_nome: str | None = None
    responsavel_telefone: str | None = None
    turma_id: int | None = None
    ativo: bool | None = None


class AlunoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricula: str
    data_nascimento: date | None
    responsavel_nome: str | None
    responsavel_telefone: str | None
    turma_id: int | None
    lgpd_consentimento: bool = False
    lgpd_consentimento_em: datetime | None = None
    lgpd_consentimento_por: str | None = None
    user: UserOut
    turma: TurmaOut | None = None


class ProfessorCreate(BaseModel):
    email: EmailStr
    nome: str
    password: str | None = Field(
        default=None,
        min_length=6,
        description="Opcional. Se omitida, o sistema gera senha provisória automaticamente.",
    )
    matricula: str
    formacao: str | None = None
    telefone: str | None = None
    username: str | None = None


class ProfessorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricula: str
    formacao: str | None
    telefone: str | None
    user: UserOut


class EntregaCredencial(BaseModel):
    enviado: bool
    canal: str | None = None
    destino: str | None = None
    motivo: str


class CadastroComSenhaOut(BaseModel):
    """Resposta de cadastro/reset com senha provisória (exibida uma vez ao admin)."""

    senha_provisoria: str
    login: str
    must_change_password: bool = True
    entrega: EntregaCredencial


class CadastroAlunoOut(CadastroComSenhaOut):
    aluno: AlunoOut


class CadastroProfessorOut(CadastroComSenhaOut):
    professor: ProfessorOut


class ResetSenhaOut(CadastroComSenhaOut):
    user_id: int
    nome: str
    role: UserRole
    message: str


class AcessoUsuarioOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    nome: str
    role: UserRole
    ativo: bool
    must_change_password: bool


class AcessoToggle(BaseModel):
    ativo: bool


class ResetSenhaRequest(BaseModel):
    nova_senha_provisoria: str | None = None


class RelatorioGeral(BaseModel):
    total_alunos: int
    total_professores: int
    total_turmas: int
    total_disciplinas: int
    total_ocorrencias: int
    aprovados: int
    recuperacao: int
    reprovados: int
    sem_notas: int


class MeResponse(BaseModel):
    user: UserOut
    perfil: Literal["admin", "professor", "aluno"]
    professor_id: int | None = None
    aluno_id: int | None = None
    must_change_password: bool = False
    matricula: str | None = None
    data_nascimento: str | None = None
    turma_nome: str | None = None
    termos_aceitos: bool = False
    termos_versao: str | None = None
    termos_versao_atual: str = "2026-07"


class DisciplinaCreate(BaseModel):
    nome: str
    carga_horaria: int = 80
    turma_id: int
    professor_id: int | None = None


class DisciplinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    carga_horaria: int
    turma_id: int
    professor_id: int | None


class NotaCreate(BaseModel):
    """Lançamento parcial: informe só as avaliações que deseja salvar agora."""

    aluno_id: int
    disciplina_id: int
    semestre: int = Field(ge=1, le=2)
    prova1: float | None = Field(default=None, ge=0, le=15)
    prova2: float | None = Field(default=None, ge=0, le=15)
    trabalho: float | None = Field(default=None, ge=0, le=10)
    participacao: float | None = Field(default=None, ge=0, le=10)
    observacao: str | None = None


class NotaUpdate(BaseModel):
    prova1: float | None = Field(default=None, ge=0, le=15)
    prova2: float | None = Field(default=None, ge=0, le=15)
    trabalho: float | None = Field(default=None, ge=0, le=10)
    participacao: float | None = Field(default=None, ge=0, le=10)
    observacao: str | None = None


class NotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    disciplina_id: int
    semestre: int
    prova1: float | None = None
    prova2: float | None = None
    trabalho: float | None = None
    participacao: float | None = None
    total: float
    observacao: str | None
    lancado_em: datetime
    disciplina: DisciplinaOut | None = None


class BoletimDisciplina(BaseModel):
    aluno_id: int
    aluno_nome: str | None = None
    disciplina_id: int
    disciplina_nome: str
    semestre1: float | None
    semestre2: float | None
    detalhe_semestre1: dict[str, float | None] | None = None
    detalhe_semestre2: dict[str, float | None] | None = None
    media_final: float | None
    situacao: SituacaoAcademica
    situacao_label: str


class OcorrenciaCreate(BaseModel):
    aluno_id: int
    tipo: TipoOcorrencia
    gravidade: GravidadeOcorrencia = GravidadeOcorrencia.MEDIA
    descricao: str
    data_ocorrencia: date


class OcorrenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    registrado_por_id: int
    professor_nome: str | None = None
    tipo: TipoOcorrencia
    gravidade: GravidadeOcorrencia
    descricao: str
    data_ocorrencia: date
    criado_em: datetime


class EventoCreate(BaseModel):
    tipo: TipoEvento
    titulo: str
    descricao: str
    data_evento: date
    horario: str = "08:00"
    local: str | None = None
    publico: bool = True


class EventoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoEvento
    titulo: str
    descricao: str
    data_evento: date
    horario: str
    local: str | None
    publico: bool
    criado_por_id: int
    criado_em: datetime


class NoticiaCreate(BaseModel):
    categoria: CategoriaNoticia = CategoriaNoticia.COMUNICADO
    titulo: str
    resumo: str
    conteudo: str
    publicada: bool = True


class NoticiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    categoria: CategoriaNoticia
    titulo: str
    resumo: str
    conteudo: str
    publicada: bool
    autor_id: int
    publicado_em: datetime


class ChartPoint(BaseModel):
    label: str
    value: float


class DashboardStats(BaseModel):
    total_alunos: int
    total_professores: int
    total_turmas: int
    total_ocorrencias: int
    media_geral: float | None
    aprovacoes: int
    recuperacoes: int
    reprovacoes: int
    desempenho_turmas: list[ChartPoint]
    aprovacao_series: list[ChartPoint]
    evolucao_semestral: list[ChartPoint]


class EscolaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    slogan: str | None = None
    logo: str | None = None
    cnpj: str | None = None
    telefone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    site: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    diretor: str | None = None
    vice_diretor: str | None = None
    cor_primaria: str
    cor_secundaria: str
    cor_botoes: str
    cor_menu: str
    tema: str
    logo_fundo_login: str | None = None
    facebook: str | None = None
    instagram: str | None = None
    youtube: str | None = None
    rodape_impressao: str | None = None
    mostrar_cnpj_impressao: bool
    setup_completo: bool
    created_at: datetime
    updated_at: datetime


class EscolaUpdate(BaseModel):
    nome: str | None = None
    slogan: str | None = None
    cnpj: str | None = None
    telefone: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    site: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None
    cep: str | None = None
    diretor: str | None = None
    vice_diretor: str | None = None
    cor_primaria: str | None = None
    cor_secundaria: str | None = None
    cor_botoes: str | None = None
    cor_menu: str | None = None
    tema: str | None = None
    facebook: str | None = None
    instagram: str | None = None
    youtube: str | None = None
    rodape_impressao: str | None = None
    mostrar_cnpj_impressao: bool | None = None


class EscolaSetupRequest(BaseModel):
    nome: str = Field(min_length=2)
    slogan: str | None = None
    cor_primaria: str = "#0f6e7c"
    cor_secundaria: str = "#0a4f59"
    cor_botoes: str = "#0f6e7c"
    cor_menu: str = "#0b1f2a"
    tema: str = "claro"
    admin_nome: str = Field(min_length=2)
    admin_email: EmailStr
    admin_username: str = Field(min_length=3)
    admin_password: str = Field(min_length=6)


class EscolaStatus(BaseModel):
    needs_setup: bool
    setup_completo: bool
    escola: EscolaOut | None = None
