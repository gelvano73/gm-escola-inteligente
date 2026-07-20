# G&M Escola Inteligente

Sistema escolar completo para gestão acadêmica do **1º Ano do Ensino Fundamental** ao **3º Ano do Ensino Médio**.

## Demo online

**URL pública:** https://web-production-6127a.up.railway.app

| Área | Link |
|------|------|
| Alunos (boletim) | https://web-production-6127a.up.railway.app/ |
| Equipe (admin/professor) | https://web-production-6127a.up.railway.app/admin |
| API docs | https://web-production-6127a.up.railway.app/docs |

Contas demo:

| Perfil | Login | Senha |
|--------|-------|-------|
| Admin | `admin` | `123456` |
| Professor | `professor` | `prof123` |
| Aluno | `A2026001` | `12052011` |

> No 1º acesso o sistema pede troca de senha. Em planos gratuitos o app pode “dormir” após inatividade e demorar ~30s para acordar.

Código no GitHub: https://github.com/gelvano73/gm-escola-inteligente

## Como testar localmente

1. Clone o repositório:
   ```bash
   git clone https://github.com/gelvano73/gm-escola-inteligente.git
   cd gm-escola-inteligente/backend
   ```
2. Crie o ambiente e instale as dependências:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   # source .venv/bin/activate
   pip install -r requirements.txt
   copy .env.example .env   # Windows
   # cp .env.example .env   # Linux/macOS
   ```
3. Suba o servidor:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
   ```
4. Abra no navegador:
   - **Alunos (boletim):** http://127.0.0.1:8080  
   - **Equipe (admin / professor):** http://127.0.0.1:8080/admin  
   - **API (docs):** http://127.0.0.1:8080/docs  

### Contas de demonstração

| Perfil | Login | Senha |
|--------|-------|-------|
| Admin | `admin` | `123456` (troca obrigatória no 1º acesso) |
| Professor | `professor` | `prof123` |
| Aluno | `A2026001` | `12052011` |

> No primeiro login o sistema pede troca de senha. Depois use a senha que você definir.

## Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | HTML5, Tailwind CSS, JavaScript |
| Backend | Python FastAPI |
| Banco | PostgreSQL (produção) / SQLite (dev local) / MySQL compatível |
| Auth | JWT |
| API | REST |

## Funcionalidades

- Autenticação JWT por perfil: **Admin**, **Professor**, **Aluno**
- Cadastro de alunos e professores
- Séries e turmas (Fundamental I/II + Médio)
- Lançamento de notas **por avaliação** (Prova 1, Prova 2, Trabalho, Participação)
- Ocorrências (indisciplina, advertência, suspensão, elogio…)
- Eventos e notícias institucionais
- Dashboard administrativo
- Personalização da escola (logo, cores, slogan)
- **Assistente Escolar IA via WhatsApp** (Meta Cloud API + OpenAI opcional)
- Interface responsiva (smartphone, tablet, desktop)

## Início rápido (Windows / sem Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

Abra:
- **Alunos (boletim):** [http://127.0.0.1:8080](http://127.0.0.1:8080) ou `/boletim`
- **Equipe (admin / professor):** [http://127.0.0.1:8080/admin](http://127.0.0.1:8080/admin) ou `/equipe`

Documentação da API: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

### Cadastro e senha provisória

- Ao cadastrar **professor** ou **aluno**, o sistema **gera senha provisória** automaticamente.
- Tenta enviar por **WhatsApp** (telefone do professor ou do responsável).
- A senha também é **exibida ao administrador** (para copiar/entregar).
- No **primeiro acesso**, a troca de senha é obrigatória.
- Em caso de **esquecimento**, o usuário contacta o admin → **Controle de acesso → Reset senha** (nova provisória).

## Perfis e permissões

### Administrador
Dashboard, cadastros (professores, alunos, turmas, disciplinas, eventos, notícias, ocorrências), relatórios e controle de acesso.

### Professor
Recebe senha provisória do admin; troca obrigatória no 1º acesso. Pode lançar/editar notas, registrar ocorrências e visualizar turmas/alunos.

### Aluno
Login pela matrícula; senha inicial = data de nascimento. Troca obrigatória no 1º acesso. Somente visualiza: notas, ocorrências, eventos, notícias e perfil pessoal.

## Regras de aprovação (escala 0–100 no ano)

### Composição do semestre (máx. 50 pontos)
| Avaliação | Pontos |
|-----------|--------|
| Prova 1 | 0 a 15 |
| Prova 2 | 0 a 15 |
| Trabalho | 0 a 10 |
| Participação | 0 a 10 |
| **Total do semestre** | **50** |

O 2º semestre segue a mesma estrutura. Os dois semestres somam **100 pontos** no ano.

### Pontuação final (soma, não média)
`Pontuação Final = 1º Semestre + 2º Semestre`

Exemplo: 25 + 35 → total **60** → **Aprovado**

| Situação | Critério |
|----------|----------|
| Aprovado | Soma ≥ 60 |
| Recuperação | Soma entre 30 e 59 |
| Reprovado | Soma < 30 |

## PostgreSQL

No arquivo `backend/.env`:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/escola_inteligente
```

## MySQL

```env
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/escola_inteligente
```

## Docker Compose

```bash
docker compose up --build
```

API em `http://localhost:8000` com PostgreSQL.

## Estrutura

```
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── seed.py
│   │   ├── routers/
│   │   └── core/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── pages/dashboard.html
│   ├── css/styles.css
│   └── js/
└── docker-compose.yml
```

## Personalização da escola

Tabela `escola` com identidade visual e dados institucionais.

- **Assistente de 1º acesso:** `/pages/setup.html` (quando `setup_completo = false`)
- **Menu admin:** Configurações da Escola (dados, logo, cores, redes, impressão)
- Login, cabeçalho e relatórios usam nome, slogan, logo e cores

Para testar o assistente em ambiente limpo, remova o registro da tabela `escola` ou inicie com banco vazio sem seed completo.

## Assistente WhatsApp IA

O responsável, aluno, professor ou administrador conversa pelo WhatsApp; a IA responde com dados do sistema (notas, faltas, ocorrências, eventos, painel admin).

Sem Meta/OpenAI, use o **simulador** no menu admin *Assistente WhatsApp* ou `POST /api/whatsapp/simulate`.

### Configuração (`.env`)

```env
WHATSAPP_ENABLED=true
WHATSAPP_TOKEN=seu_token_meta
WHATSAPP_PHONE_NUMBER_ID=id_do_numero
WHATSAPP_VERIFY_TOKEN=gm-escola-verify-token

OPENAI_ENABLED=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Webhook na Meta: `https://seu-dominio/api/whatsapp/webhook` (verify token igual ao `.env`).

## Licença

Projeto educacional / demonstração. Use e adapte conforme a necessidade da sua escola.
