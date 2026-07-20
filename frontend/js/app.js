const state = {
  me: null,
  view: "inicio",
  cache: {},
};

const roleLabel = {
  admin: "Administrador",
  professor: "Professor",
  aluno: "Aluno",
};

const menus = {
  admin: [
    { id: "inicio", label: "Dashboard" },
    { id: "alunos", label: "Alunos" },
    { id: "professores", label: "Professores" },
    { id: "series", label: "Séries" },
    { id: "turmas", label: "Turmas" },
    { id: "disciplinas", label: "Disciplinas" },
    { id: "notas", label: "Notas" },
    { id: "ocorrencias", label: "Ocorrências" },
    { id: "eventos", label: "Eventos" },
    { id: "noticias", label: "Notícias" },
    { id: "relatorios", label: "Relatórios" },
    { id: "acesso", label: "Controle de acesso" },
    { id: "lgpd", label: "LGPD" },
    { id: "assistente", label: "Assistente WhatsApp" },
    { id: "configuracoes", label: "Configurações da Escola" },
  ],
  professor: [
    { id: "inicio", label: "Início" },
    { id: "turmas", label: "Turmas" },
    { id: "alunos", label: "Alunos" },
    { id: "notas", label: "Notas" },
    { id: "ocorrencias", label: "Ocorrências" },
  ],
  aluno: [
    { id: "boletim", label: "Boletim" },
    { id: "eventos", label: "Eventos" },
    { id: "ocorrencias", label: "Ocorrências" },
    { id: "noticias", label: "Notícias" },
  ],
};

function toast(message) {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function closeModal() {
  document.getElementById("modal-root").innerHTML = "";
}

function showCredenciais({ titulo, login, senha, entrega, extraHtml = "" }) {
  const root = document.getElementById("modal-root");
  const canal = entrega?.enviado
    ? `${entrega.canal || "WhatsApp"} → ${entrega.destino || "—"}`
    : "Não enviado automaticamente";
  root.innerHTML = `
    <div class="modal-backdrop fade-in">
      <div class="panel modal p-5 slide-up">
        <div class="flex items-start justify-between gap-3 mb-3">
          <h3 class="font-display text-2xl">${titulo}</h3>
          <button type="button" class="btn-ghost" id="cred-close">Fechar</button>
        </div>
        <p class="text-sm text-[rgba(11,31,42,0.7)] mb-3">
          Anote e entregue estas credenciais. A senha provisória exige troca no primeiro acesso.
        </p>
        <div class="panel p-4 space-y-2 text-sm">
          <p><strong>Login:</strong> <code id="cred-login">${login}</code></p>
          <p><strong>Senha provisória:</strong> <code id="cred-senha">${senha}</code></p>
          <p><strong>Entrega:</strong> ${canal}</p>
          <p class="text-[rgba(11,31,42,0.65)]">${entrega?.motivo || ""}</p>
        </div>
        ${extraHtml}
        <div class="mt-4 flex flex-wrap gap-2 justify-end">
          <button type="button" class="btn-ghost" id="cred-copy">Copiar senha</button>
          <button type="button" class="btn-primary" id="cred-ok">Entendi</button>
        </div>
      </div>
    </div>`;
  const close = () => {
    root.innerHTML = "";
  };
  document.getElementById("cred-close").onclick = close;
  document.getElementById("cred-ok").onclick = close;
  document.getElementById("cred-copy").onclick = async () => {
    try {
      await navigator.clipboard.writeText(senha);
      toast("Senha copiada");
    } catch {
      toast("Não foi possível copiar. Selecione a senha manualmente.");
    }
  };
}

function openModal(title, bodyHtml, onSubmit) {
  const root = document.getElementById("modal-root");
  root.innerHTML = `
    <div class="modal-backdrop fade-in">
      <form class="panel modal p-5 slide-up" id="modal-form">
        <div class="flex items-start justify-between gap-3 mb-4">
          <h3 class="font-display text-2xl">${title}</h3>
          <button type="button" class="btn-ghost" id="modal-close">Fechar</button>
        </div>
        <div class="space-y-3">${bodyHtml}</div>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" class="btn-ghost" id="modal-cancel">Cancelar</button>
          <button type="submit" class="btn-primary">Salvar</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById("modal-close").onclick = closeModal;
  document.getElementById("modal-cancel").onclick = closeModal;
  document.getElementById("modal-form").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const result = await onSubmit(new FormData(e.target));
      closeModal();
      await renderView(state.view);
      if (result?.credenciais) {
        showCredenciais(result.credenciais);
      } else {
        toast("Salvo com sucesso");
      }
    } catch (err) {
      toast(err.message);
    }
  };
}

function fmtDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  return d.toLocaleDateString("pt-BR");
}

function fmtDateTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function setMeta(title, subtitle) {
  document.getElementById("page-title").textContent = title;
  document.getElementById("page-subtitle").textContent = subtitle;
}

function applyBrandChrome() {
  const side = document.getElementById("sidebar-brand");
  const head = document.getElementById("header-brand");
  if (side) {
    const e = Branding.escola || { nome: "Escola", slogan: "" };
    side.innerHTML = `
      ${Branding.logoHtml("2.75rem")}
      <div class="brand-text">
        <p class="font-display text-lg leading-tight">${e.nome}</p>
        <p class="text-xs opacity-70">${e.slogan || "Portal acadêmico"}</p>
      </div>`;
  }
  if (head) head.innerHTML = Branding.headerBrandHtml();
}

function renderNav() {
  const nav = document.getElementById("nav");
  const items = menus[state.me.perfil] || [];
  nav.innerHTML = items
    .map(
      (item) => `
      <a href="#${item.id}" class="nav-link ${state.view === item.id ? "active" : ""}" data-view="${item.id}">
        <span>${item.label}</span>
      </a>`
    )
    .join("");
  nav.querySelectorAll("[data-view]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      document.getElementById("sidebar").classList.remove("open");
      document.getElementById("sidebar-overlay")?.classList.remove("show");
      renderView(el.dataset.view);
    });
  });
}

async function viewInicio() {
  setMeta(state.me.perfil === "admin" ? "Dashboard administrativo" : "Início", "Indicadores e visão geral");
  const content = document.getElementById("content");

  if (state.me.perfil === "admin") {
    const stats = await GMApi.api("/dashboard/stats");
    content.innerHTML = `
      <section class="stats-grid slide-up">
        ${cardStat("Alunos", stats.total_alunos)}
        ${cardStat("Professores", stats.total_professores)}
        ${cardStat("Turmas", stats.total_turmas)}
        ${cardStat("Ocorrências", stats.total_ocorrencias)}
        ${cardStat("Média geral", stats.media_geral ?? "—")}
        ${cardStat("Aprovações", stats.aprovacoes)}
        ${cardStat("Recuperações", stats.recuperacoes)}
        ${cardStat("Reprovações", stats.reprovacoes)}
      </section>
      <section class="charts-grid mt-4">
        <div class="panel p-4 slide-up"><h3 class="font-display text-lg mb-3">Desempenho por turma</h3><canvas id="chart-turmas" height="180"></canvas></div>
        <div class="panel p-4 slide-up"><h3 class="font-display text-lg mb-3">Aprovação por série (%)</h3><canvas id="chart-series" height="180"></canvas></div>
        <div class="panel p-4 slide-up md:col-span-2 xl:col-span-1"><h3 class="font-display text-lg mb-3">Evolução semestral</h3><canvas id="chart-semestres" height="180"></canvas></div>
      </section>`;
    renderCharts(stats);
    return;
  }

  if (state.me.perfil === "professor") {
    content.innerHTML = `
      <section class="panel p-5 slide-up">
        <h2 class="font-display text-2xl">Olá, ${state.me.user.nome.split(" ")[0]}</h2>
        <p class="mt-2 text-[rgba(11,31,42,0.68)]">Lance notas, registre ocorrências e visualize turmas e alunos.</p>
      </section>`;
    return;
  }

  content.innerHTML = `
    <section class="panel p-5 slide-up">
      <h2 class="font-display text-2xl">Olá, ${state.me.user.nome.split(" ")[0]}</h2>
      <p class="mt-2 text-[rgba(11,31,42,0.68)]">Acompanhe suas notas, ocorrências, eventos e notícias. Perfil somente leitura.</p>
    </section>`;
}

function renderCharts(stats) {
  if (typeof Chart === "undefined") return;
  const color = "#0f6e7c";
  const colorSoft = "rgba(15,110,124,0.25)";
  const mk = (id, type, labels, data, label) => {
    const el = document.getElementById(id);
    if (!el) return;
    new Chart(el, {
      type,
      data: {
        labels,
        datasets: [{ label, data, backgroundColor: colorSoft, borderColor: color, borderWidth: 2, tension: 0.3 }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: type === "doughnut" ? {} : { y: { beginAtZero: true, max: type === "bar" && id === "chart-series" ? 100 : undefined } },
      },
    });
  };
  mk(
    "chart-turmas",
    "bar",
    (stats.desempenho_turmas || []).map((x) => x.label),
    (stats.desempenho_turmas || []).map((x) => x.value),
    "Média"
  );
  mk(
    "chart-series",
    "bar",
    (stats.aprovacao_series || []).map((x) => x.label),
    (stats.aprovacao_series || []).map((x) => x.value),
    "% Aprovação"
  );
  mk(
    "chart-semestres",
    "line",
    (stats.evolucao_semestral || []).map((x) => x.label),
    (stats.evolucao_semestral || []).map((x) => x.value),
    "Média"
  );
}

async function viewPerfil() {
  setMeta("Meu perfil", "Informações pessoais (somente leitura)");
  const content = document.getElementById("content");
  const me = state.me;
  let alunoExtra = "";
  if (me.aluno_id) {
    const aluno = await GMApi.api(`/alunos/${me.aluno_id}`);
    alunoExtra = `
      <p><strong>Matrícula:</strong> ${aluno.matricula}</p>
      <p><strong>Nascimento:</strong> ${fmtDate(aluno.data_nascimento)}</p>
      <p><strong>Turma:</strong> ${aluno.turma ? `${aluno.turma.serie?.nome || ""} ${aluno.turma.nome}` : "—"}</p>
      <p><strong>Responsável:</strong> ${aluno.responsavel_nome || "—"}</p>
      <p><strong>Telefone responsável:</strong> ${aluno.responsavel_telefone || "—"}</p>
    `;
  }
  content.innerHTML = `
    <section class="panel p-5 slide-up space-y-2">
      <h2 class="font-display text-2xl">${me.user.nome}</h2>
      <p><strong>Usuário:</strong> ${me.user.username}</p>
      <p><strong>E-mail:</strong> ${me.user.email}</p>
      <p><strong>Perfil:</strong> Aluno</p>
      ${alunoExtra}
      <p class="text-sm text-[rgba(11,31,42,0.55)] mt-4">Você não pode editar estas informações. Solicite alterações à secretaria.</p>
    </section>`;
}

function cardStat(label, value) {
  return `<div class="panel p-4 md:p-5"><p class="text-sm text-[rgba(11,31,42,0.6)]">${label}</p><p class="stat-value mt-2">${value}</p></div>`;
}

async function viewAlunos() {
  setMeta("Alunos", state.me.perfil === "admin" ? "Cadastro de alunos" : "Visualização de alunos");
  const alunos = await GMApi.api("/alunos");
  const content = document.getElementById("content");
  const canCreate = state.me.perfil === "admin";

  content.innerHTML = `
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-[rgba(11,31,42,0.65)]">${alunos.length} aluno(s)</p>
      ${canCreate ? `<button class="btn-primary" id="btn-novo-aluno">Novo aluno</button>` : ""}
    </div>
    <div class="panel table-wrap">
      <table class="data">
        <thead><tr><th>Nome</th><th>Matrícula</th><th>Nascimento</th><th>Turma</th><th>Responsável</th><th>Status</th></tr></thead>
        <tbody>
          ${alunos
            .map(
              (a) => `<tr>
              <td>${a.user.nome}<div class="text-xs text-[rgba(11,31,42,0.55)]">${a.user.email}</div></td>
              <td>${a.matricula}</td>
              <td>${fmtDate(a.data_nascimento)}</td>
              <td>${a.turma ? `${a.turma.serie?.nome || ""} ${a.turma.nome}` : "—"}</td>
              <td>${a.responsavel_nome || "—"}</td>
              <td><span class="badge ${a.user.ativo ? "success" : "warning"}">${a.user.ativo ? "Ativo" : "Inativo"}</span></td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;

  if (canCreate) {
    document.getElementById("btn-novo-aluno").onclick = async () => {
      const turmas = await GMApi.api("/turmas");
      openModal(
        "Novo aluno",
        `
        <p class="text-sm text-[rgba(11,31,42,0.65)]">
          O sistema gera uma <strong>senha provisória</strong> e tenta enviá-la por WhatsApp ao responsável (se houver telefone).
          O aluno deve trocar a senha no primeiro acesso.
        </p>
        <input class="input-field" name="nome" placeholder="Nome completo" required />
        <input class="input-field" name="email" type="email" placeholder="E-mail" required />
        <input class="input-field" name="matricula" placeholder="Matrícula (login)" required />
        <label class="text-sm font-semibold">Data de nascimento</label>
        <input class="input-field" name="data_nascimento" type="date" required />
        <input class="input-field" name="responsavel_nome" placeholder="Nome do responsável" />
        <input class="input-field" name="responsavel_telefone" placeholder="WhatsApp do responsável (com DDD)" />
        <select class="input-field" name="turma_id">
          <option value="">Sem turma</option>
          ${turmas.map((t) => `<option value="${t.id}">${t.serie?.nome || ""} ${t.nome} (${t.ano_letivo})</option>`).join("")}
        </select>
        <label class="flex items-start gap-2 text-sm text-[rgba(11,31,42,0.8)]">
          <input type="checkbox" name="lgpd_consentimento" value="true" required class="mt-1" />
          <span>
            Declaro que o responsável autorizou o tratamento dos dados do aluno conforme a
            <a href="/pages/privacidade.html" target="_blank" rel="noopener">Política de Privacidade (LGPD)</a>.
          </span>
        </label>
        <input class="input-field" name="lgpd_consentimento_por" placeholder="Nome de quem autorizou (responsável)" required />
        `,
        async (fd) => {
          const payload = Object.fromEntries(fd.entries());
          payload.turma_id = payload.turma_id ? Number(payload.turma_id) : null;
          payload.lgpd_consentimento = fd.get("lgpd_consentimento") === "true";
          const res = await GMApi.api("/alunos", { method: "POST", body: payload });
          return {
            credenciais: {
              titulo: "Aluno cadastrado",
              login: res.login,
              senha: res.senha_provisoria,
              entrega: res.entrega,
            },
          };
        }
      );
    };
  }
}

async function viewProfessores() {
  setMeta("Professores", "Corpo docente");
  const professores = await GMApi.api("/professores");
  const content = document.getElementById("content");
  content.innerHTML = `
    <div class="flex justify-end"><button class="btn-primary" id="btn-novo-prof">Novo professor</button></div>
    <div class="panel table-wrap">
      <table class="data">
        <thead><tr><th>Nome</th><th>Matrícula</th><th>Formação</th><th>Telefone</th></tr></thead>
        <tbody>
          ${professores
            .map(
              (p) => `<tr>
              <td>${p.user.nome}<div class="text-xs text-[rgba(11,31,42,0.55)]">${p.user.email}</div></td>
              <td>${p.matricula}</td>
              <td>${p.formacao || "—"}</td>
              <td>${p.telefone || "—"}</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;

  document.getElementById("btn-novo-prof").onclick = () => {
    openModal(
      "Novo professor",
      `
      <p class="text-sm text-[rgba(11,31,42,0.65)]">
        O sistema gera uma <strong>senha provisória</strong> automaticamente e tenta enviá-la por WhatsApp (se o telefone for informado).
        Troca obrigatória no primeiro acesso.
      </p>
      <input class="input-field" name="nome" placeholder="Nome completo" required />
      <input class="input-field" name="email" type="email" placeholder="E-mail institucional" required />
      <input class="input-field" name="username" placeholder="Usuário de login (opcional)" />
      <input class="input-field" name="matricula" placeholder="Matrícula" required />
      <input class="input-field" name="formacao" placeholder="Formação" />
      <input class="input-field" name="telefone" placeholder="WhatsApp (com DDD)" />
      `,
      async (fd) => {
        const payload = Object.fromEntries(fd.entries());
        if (!payload.username) delete payload.username;
        const res = await GMApi.api("/professores", { method: "POST", body: payload });
        return {
          credenciais: {
            titulo: "Professor cadastrado",
            login: res.login,
            senha: res.senha_provisoria,
            entrega: res.entrega,
          },
        };
      }
    );
  };
}
async function viewSeries() {
  setMeta("Séries", "Cadastro de séries (Fundamental e Médio)");
  const series = await GMApi.api("/series");
  const content = document.getElementById("content");
  const segmentoLabel = {
    fundamental_1: "Fundamental I",
    fundamental_2: "Fundamental II",
    medio: "Ensino Médio",
  };
  const canCreate = state.me.perfil === "admin";
  content.innerHTML = `
    <div class="flex justify-between items-center gap-3 flex-wrap mb-3">
      <p class="text-sm text-[rgba(11,31,42,0.65)]">Cadastre a série e depois vincule as turmas (A, B, C…).</p>
      ${canCreate ? `<button class="btn-primary" id="btn-nova-serie">Nova série</button>` : ""}
    </div>
    <div class="panel table-wrap">
      <table class="data">
        <thead><tr><th>Ordem</th><th>Nome</th><th>Segmento</th></tr></thead>
        <tbody>
          ${series
            .map(
              (s) => `<tr>
              <td>${s.ordem}</td>
              <td>${s.nome}</td>
              <td>${segmentoLabel[s.segmento] || s.segmento}</td>
            </tr>`
            )
            .join("") || `<tr><td colspan="3">Nenhuma série cadastrada.</td></tr>`}
        </tbody>
      </table>
    </div>`;

  if (canCreate) {
    document.getElementById("btn-nova-serie").onclick = () => {
      openModal(
        "Nova série",
        `
        <input class="input-field" name="nome" placeholder="Ex: 1º Ano Fundamental" required />
        <select class="input-field" name="segmento" required>
          <option value="fundamental_1">Fundamental I (1º–5º)</option>
          <option value="fundamental_2">Fundamental II (6º–9º)</option>
          <option value="medio">Ensino Médio</option>
        </select>
        <input class="input-field" name="ordem" type="number" min="1" max="99" placeholder="Ordem (ex: 1)" required />
        `,
        async (fd) => {
          const payload = Object.fromEntries(fd.entries());
          payload.ordem = Number(payload.ordem);
          await GMApi.api("/series", { method: "POST", body: payload });
        }
      );
    };
  }
}

async function viewTurmas() {
  setMeta("Turmas", state.me.perfil === "admin" ? "Cadastro de turmas" : "Visualização de turmas");
  const [turmas, series] = await Promise.all([GMApi.api("/turmas"), GMApi.api("/series")]);
  const content = document.getElementById("content");
  const canCreate = state.me.perfil === "admin";
  content.innerHTML = `
    <div class="flex justify-between items-center gap-3 flex-wrap mb-3">
      <p class="text-sm text-[rgba(11,31,42,0.65)]">
        ${series.length ? "Selecione a série e informe a turma (A, B…)." : "Cadastre uma série em <strong>Séries</strong> antes de criar turmas."}
      </p>
      ${canCreate ? `<button class="btn-primary" id="btn-nova-turma" ${series.length ? "" : "disabled"}>Nova turma</button>` : ""}
    </div>
    <div class="panel table-wrap">
      <table class="data">
        <thead><tr><th>Série</th><th>Turma</th><th>Ano</th><th>Turno</th></tr></thead>
        <tbody>
          ${turmas
            .map(
              (t) => `<tr>
              <td>${t.serie?.nome || t.serie_id}</td>
              <td>${t.nome}</td>
              <td>${t.ano_letivo}</td>
              <td>${t.turno}</td>
            </tr>`
            )
            .join("") || `<tr><td colspan="4">Nenhuma turma cadastrada.</td></tr>`}
        </tbody>
      </table>
    </div>`;

  if (canCreate) {
    const btn = document.getElementById("btn-nova-turma");
    if (btn && !btn.disabled) {
      btn.onclick = () => {
        openModal(
          "Nova turma",
          `
          <label class="text-sm font-semibold">Série</label>
          <select class="input-field" name="serie_id" required>
            ${series.map((s) => `<option value="${s.id}">${s.nome}</option>`).join("")}
          </select>
          <input class="input-field" name="nome" placeholder="Turma (ex: A)" required />
          <input class="input-field" name="ano_letivo" type="number" value="${new Date().getFullYear()}" required />
          <select class="input-field" name="turno">
            <option value="manhã">Manhã</option>
            <option value="tarde">Tarde</option>
            <option value="noite">Noite</option>
          </select>
          `,
          async (fd) => {
            const payload = Object.fromEntries(fd.entries());
            payload.serie_id = Number(payload.serie_id);
            payload.ano_letivo = Number(payload.ano_letivo);
            await GMApi.api("/turmas", { method: "POST", body: payload });
          }
        );
      };
    }
  }
}

async function viewDisciplinas() {
  setMeta("Disciplinas", "Cadastro de disciplinas");
  const [disciplinas, turmas, professores] = await Promise.all([
    GMApi.api("/disciplinas"),
    GMApi.api("/turmas"),
    GMApi.api("/professores"),
  ]);
  const turmaMap = Object.fromEntries(turmas.map((t) => [t.id, `${t.serie?.nome || ""} ${t.nome}`]));
  const profMap = Object.fromEntries(professores.map((p) => [p.id, p.user.nome]));
  const content = document.getElementById("content");
  content.innerHTML = `
    <div class="flex justify-end"><button class="btn-primary" id="btn-nova-disc">Nova disciplina</button></div>
    <div class="panel table-wrap">
      <table class="data">
        <thead><tr><th>Nome</th><th>Turma</th><th>Professor</th><th>Carga horária</th></tr></thead>
        <tbody>
          ${disciplinas
            .map(
              (d) => `<tr>
              <td>${d.nome}</td>
              <td>${turmaMap[d.turma_id] || d.turma_id}</td>
              <td>${d.professor_id ? profMap[d.professor_id] || d.professor_id : "—"}</td>
              <td>${d.carga_horaria}h</td>
            </tr>`
            )
            .join("") || `<tr><td colspan="4">Nenhuma disciplina.</td></tr>`}
        </tbody>
      </table>
    </div>`;

  document.getElementById("btn-nova-disc").onclick = () => {
    openModal(
      "Nova disciplina",
      `
      <input class="input-field" name="nome" placeholder="Nome da disciplina" required />
      <input class="input-field" name="carga_horaria" type="number" value="80" required />
      <select class="input-field" name="turma_id" required>
        ${turmas.map((t) => `<option value="${t.id}">${t.serie?.nome || ""} ${t.nome}</option>`).join("")}
      </select>
      <select class="input-field" name="professor_id">
        <option value="">Sem professor</option>
        ${professores.map((p) => `<option value="${p.id}">${p.user.nome}</option>`).join("")}
      </select>
      `,
      async (fd) => {
        const payload = Object.fromEntries(fd.entries());
        payload.carga_horaria = Number(payload.carga_horaria);
        payload.turma_id = Number(payload.turma_id);
        payload.professor_id = payload.professor_id ? Number(payload.professor_id) : null;
        await GMApi.api("/disciplinas", { method: "POST", body: payload });
      }
    );
  };
}

async function viewNotas() {
  setMeta(
    state.me.perfil === "aluno" ? "Minhas notas" : "Notas",
    "1º e 2º semestre · Total = S1 + S2 (máx. 100)"
  );
  const [notas, boletim] = await Promise.all([
    GMApi.api("/notas"),
    GMApi.api("/notas/boletim"),
  ]);
  const content = document.getElementById("content");
  const canLaunch = state.me.perfil === "admin" || state.me.perfil === "professor";

  const badgeSituacao = (s) => {
    if (s === "aprovado") return "success";
    if (s === "recuperacao") return "warning";
    if (s === "reprovado") return "danger";
    return "";
  };

  const parseNota = (raw) => {
    if (raw === undefined || raw === null || String(raw).trim() === "") return null;
    const n = Number(String(raw).replace(",", "."));
    return Number.isFinite(n) ? n : null;
  };

  const fmtComp = (v) => (v === null || v === undefined ? "—" : v);
  const valComp = (v) => (v === null || v === undefined ? "" : v);

  content.innerHTML = `
    <section class="panel p-4 text-sm text-[rgba(11,31,42,0.7)] space-y-1">
      <p><strong>Semestre:</strong> Prova 1 (15) + Prova 2 (15) + Trabalho (10) + Participação (10) = 50</p>
      <p><strong>Pontuação final:</strong> 1º Semestre + 2º Semestre (máximo 100)</p>
      <p><strong>Status:</strong> Aprovado ≥ 60 · Recuperação 30–59 · Reprovado &lt; 30</p>
      <p>Você pode lançar <strong>uma avaliação por vez</strong> (ex.: só a Prova 1) e completar as demais depois.</p>
    </section>
    <div class="flex justify-between items-center gap-3 flex-wrap">
      <p class="text-[rgba(11,31,42,0.65)]">Boletim por disciplina</p>
      ${canLaunch ? `<button class="btn-primary" id="btn-nova-nota">Lançar avaliação</button>` : ""}
    </div>
    <div class="panel table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th>Aluno</th><th>Disciplina</th>
            <th>1º Semestre</th><th>2º Semestre</th>
            <th>Total (S1+S2)</th><th>Situação</th>
          </tr>
        </thead>
        <tbody>
          ${boletim
            .map(
              (b) => `<tr>
                <td>${b.aluno_nome || "#" + b.aluno_id}</td>
                <td>${b.disciplina_nome}</td>
                <td>${b.semestre1 ?? "—"}</td>
                <td>${b.semestre2 ?? "—"}</td>
                <td><strong>${b.media_final ?? "—"}</strong></td>
                <td><span class="badge ${badgeSituacao(b.situacao)}">${b.situacao_label}</span></td>
              </tr>`
            )
            .join("") || `<tr><td colspan="6">Nenhuma nota encontrada.</td></tr>`}
        </tbody>
      </table>
    </div>
    <details class="panel p-4">
      <summary class="font-semibold cursor-pointer">Detalhe dos lançamentos (${notas.length})</summary>
      <div class="table-wrap mt-3">
        <table class="data">
          <thead>
            <tr>
              <th>Aluno</th><th>Disciplina</th><th>Semestre</th>
              <th>P1</th><th>P2</th><th>Trab.</th><th>Part.</th><th>Total</th>
              ${canLaunch ? "<th></th>" : ""}
            </tr>
          </thead>
          <tbody>
            ${notas
              .map(
                (n) => `<tr>
                <td>#${n.aluno_id}</td>
                <td>${n.disciplina?.nome || n.disciplina_id}</td>
                <td>${n.semestre}º</td>
                <td>${fmtComp(n.prova1)}</td>
                <td>${fmtComp(n.prova2)}</td>
                <td>${fmtComp(n.trabalho)}</td>
                <td>${fmtComp(n.participacao)}</td>
                <td><span class="badge">${n.total}</span></td>
                ${
                  canLaunch
                    ? `<td class="whitespace-nowrap">
                        <button class="btn-ghost" data-edit-nota='${JSON.stringify({
                          id: n.id,
                          prova1: n.prova1,
                          prova2: n.prova2,
                          trabalho: n.trabalho,
                          participacao: n.participacao,
                          observacao: n.observacao || "",
                        })}'>Editar</button>
                        <button class="btn-ghost" data-del-nota="${n.id}">Excluir</button>
                      </td>`
                    : ""
                }
              </tr>`
              )
              .join("") || `<tr><td colspan="9">Sem lançamentos.</td></tr>`}
          </tbody>
        </table>
      </div>
    </details>`;

  if (canLaunch) {
    document.getElementById("btn-nova-nota").onclick = async () => {
      const [alunos, disciplinas] = await Promise.all([
        GMApi.api("/alunos"),
        GMApi.api("/disciplinas" + (state.me.professor_id ? `?professor_id=${state.me.professor_id}` : "")),
      ]);
      openModal(
        "Lançar avaliação",
        `
        <p class="text-sm text-[rgba(11,31,42,0.65)]">Escolha a avaliação e informe só essa nota. As demais podem ser lançadas depois.</p>
        <select class="input-field" name="aluno_id" required>
          ${alunos.map((a) => `<option value="${a.id}">${a.user.nome} (${a.matricula})</option>`).join("")}
        </select>
        <select class="input-field" name="disciplina_id" required>
          ${disciplinas.map((d) => `<option value="${d.id}">${d.nome}</option>`).join("")}
        </select>
        <select class="input-field" name="semestre" required>
          <option value="1">1º Semestre</option>
          <option value="2">2º Semestre</option>
        </select>
        <label class="text-sm font-semibold">Avaliação</label>
        <select class="input-field" name="componente" id="nota-componente" required>
          <option value="prova1">Prova 1 (0–15)</option>
          <option value="prova2">Prova 2 (0–15)</option>
          <option value="trabalho">Trabalho (0–10)</option>
          <option value="participacao">Participação (0–10)</option>
        </select>
        <label class="text-sm font-semibold">Nota</label>
        <input class="input-field" name="valor" id="nota-valor" type="number" min="0" max="15" step="0.1" required />
        <input class="input-field" name="observacao" placeholder="Observação (opcional)" />
        `,
        async (fd) => {
          const raw = Object.fromEntries(fd.entries());
          const valor = parseNota(raw.valor);
          if (valor === null) throw new Error("Informe a nota");
          const max = raw.componente === "prova1" || raw.componente === "prova2" ? 15 : 10;
          if (valor < 0 || valor > max) throw new Error(`Nota deve estar entre 0 e ${max}`);
          const payload = {
            aluno_id: Number(raw.aluno_id),
            disciplina_id: Number(raw.disciplina_id),
            semestre: Number(raw.semestre),
            [raw.componente]: valor,
          };
          if (raw.observacao) payload.observacao = raw.observacao;
          await GMApi.api("/notas", { method: "POST", body: payload });
        }
      );
      const syncMax = () => {
        const comp = document.getElementById("nota-componente")?.value;
        const input = document.getElementById("nota-valor");
        if (!input) return;
        input.max = comp === "prova1" || comp === "prova2" ? "15" : "10";
      };
      document.getElementById("nota-componente")?.addEventListener("change", syncMax);
      syncMax();
    };

    document.querySelectorAll("[data-edit-nota]").forEach((btn) => {
      btn.onclick = () => {
        const data = JSON.parse(btn.dataset.editNota);
        openModal(
          "Atualizar avaliação",
          `
          <p class="text-sm text-[rgba(11,31,42,0.65)]">Altere só o que precisar. Deixe em branco as avaliações ainda não lançadas.</p>
          <label class="text-sm">Prova 1 (0–15)</label>
          <input class="input-field" name="prova1" type="number" min="0" max="15" step="0.1" value="${valComp(data.prova1)}" />
          <label class="text-sm">Prova 2 (0–15)</label>
          <input class="input-field" name="prova2" type="number" min="0" max="15" step="0.1" value="${valComp(data.prova2)}" />
          <label class="text-sm">Trabalho (0–10)</label>
          <input class="input-field" name="trabalho" type="number" min="0" max="10" step="0.1" value="${valComp(data.trabalho)}" />
          <label class="text-sm">Participação (0–10)</label>
          <input class="input-field" name="participacao" type="number" min="0" max="10" step="0.1" value="${valComp(data.participacao)}" />
          <input class="input-field" name="observacao" value="${data.observacao}" placeholder="Observação" />
          `,
          async (fd) => {
            const raw = Object.fromEntries(fd.entries());
            const payload = {
              prova1: parseNota(raw.prova1),
              prova2: parseNota(raw.prova2),
              trabalho: parseNota(raw.trabalho),
              participacao: parseNota(raw.participacao),
              observacao: raw.observacao || null,
            };
            await GMApi.api(`/notas/${data.id}`, { method: "PATCH", body: payload });
          }
        );
      };
    });

    document.querySelectorAll("[data-del-nota]").forEach((btn) => {
      btn.onclick = async () => {
        if (!confirm("Excluir este lançamento do semestre?")) return;
        try {
          await GMApi.api(`/notas/${btn.dataset.delNota}`, { method: "DELETE" });
          toast("Lançamento excluído");
          await renderView(state.view);
        } catch (err) {
          toast(err.message);
        }
      };
    });
  }
}

async function viewOcorrencias() {
  setMeta("Ocorrências", "Registro pelo professor");
  const ocorrencias = await GMApi.api("/ocorrencias");
  const content = document.getElementById("content");
  const canCreate = state.me.perfil === "admin" || state.me.perfil === "professor";
  const tipoLabel = {
    indisciplina: "Indisciplina",
    falta_atividade: "Falta de atividade",
    advertencia: "Advertência",
    suspensao: "Suspensão",
    elogio: "Elogio",
  };

  content.innerHTML = `
    <div class="flex justify-end">${canCreate ? `<button class="btn-primary" id="btn-nova-ocor">Nova ocorrência</button>` : ""}</div>
    <div class="panel table-wrap">
      <table class="data">
        <thead><tr><th>Data</th><th>Professor</th><th>Aluno</th><th>Tipo</th><th>Gravidade</th><th>Descrição</th></tr></thead>
        <tbody>
          ${ocorrencias
            .map(
              (o) => `<tr>
              <td>${fmtDate(o.data_ocorrencia)}</td>
              <td>${o.professor_nome || "—"}</td>
              <td>#${o.aluno_id}</td>
              <td><span class="badge">${tipoLabel[o.tipo] || o.tipo}</span></td>
              <td><span class="badge ${o.gravidade === "alta" ? "danger" : o.gravidade === "media" ? "warning" : "success"}">${o.gravidade}</span></td>
              <td>${o.descricao}</td>
            </tr>`
            )
            .join("") || `<tr><td colspan="6">Nenhuma ocorrência.</td></tr>`}
        </tbody>
      </table>
    </div>`;

  if (canCreate) {
    document.getElementById("btn-nova-ocor").onclick = async () => {
      const alunos = await GMApi.api("/alunos");
      openModal(
        "Nova ocorrência",
        `
        <select class="input-field" name="aluno_id" required>
          ${alunos.map((a) => `<option value="${a.id}">${a.user.nome}</option>`).join("")}
        </select>
        <select class="input-field" name="tipo" required>
          <option value="indisciplina">Indisciplina</option>
          <option value="falta_atividade">Falta de atividade</option>
          <option value="advertencia">Advertência</option>
          <option value="suspensao">Suspensão</option>
          <option value="elogio">Elogio</option>
        </select>
        <select class="input-field" name="gravidade" required>
          <option value="baixa">Baixa</option>
          <option value="media" selected>Média</option>
          <option value="alta">Alta</option>
        </select>
        <textarea class="input-field" name="descricao" rows="4" placeholder="Descrição" required></textarea>
        <input class="input-field" name="data_ocorrencia" type="date" required />
        `,
        async (fd) => {
          const payload = Object.fromEntries(fd.entries());
          payload.aluno_id = Number(payload.aluno_id);
          await GMApi.api("/ocorrencias", { method: "POST", body: payload });
        }
      );
    };
  }
}

async function viewEventos() {
  setMeta("Eventos", "Cadastro administrativo");
  const eventos = await GMApi.api("/eventos");
  const content = document.getElementById("content");
  const canCreate = state.me.perfil === "admin";
  const tipoLabel = {
    reuniao: "Reunião",
    festa: "Festa escolar",
    jogo: "Jogo",
    feira_ciencia: "Feira de ciência",
    formatura: "Formatura",
  };

  content.innerHTML = `
    <div class="flex justify-end">${canCreate ? `<button class="btn-primary" id="btn-novo-evento">Novo evento</button>` : ""}</div>
    <div class="cards-grid">
      ${eventos
        .map(
          (e) => `<article class="panel p-5 slide-up">
          <p class="text-xs uppercase tracking-wide text-[var(--sea)]">${tipoLabel[e.tipo] || e.tipo}</p>
          <h3 class="font-display text-xl mt-1">${e.titulo}</h3>
          <p class="mt-2 text-sm">${fmtDate(e.data_evento)} · ${e.horario} · ${e.local || "Local a definir"}</p>
          <p class="mt-2 text-[rgba(11,31,42,0.7)]">${e.descricao}</p>
        </article>`
        )
        .join("") || `<p class="panel p-5">Nenhum evento cadastrado.</p>`}
    </div>`;

  if (canCreate) {
    document.getElementById("btn-novo-evento").onclick = () => {
      openModal(
        "Novo evento",
        `
        <select class="input-field" name="tipo" required>
          <option value="reuniao">Reunião</option>
          <option value="festa">Festa escolar</option>
          <option value="jogo">Jogo</option>
          <option value="feira_ciencia">Feira de ciência</option>
          <option value="formatura">Formatura</option>
        </select>
        <input class="input-field" name="titulo" placeholder="Título" required />
        <input class="input-field" name="data_evento" type="date" required />
        <input class="input-field" name="horario" type="time" value="08:00" required />
        <input class="input-field" name="local" placeholder="Local" required />
        <textarea class="input-field" name="descricao" rows="4" placeholder="Descrição" required></textarea>
        `,
        async (fd) => {
          const payload = Object.fromEntries(fd.entries());
          payload.publico = true;
          await GMApi.api("/eventos", { method: "POST", body: payload });
        }
      );
    };
  }
}

async function viewNoticias() {
  setMeta("Notícias", "Comunicados e avisos");
  const noticias = await GMApi.api("/noticias");
  const content = document.getElementById("content");
  const canCreate = state.me.perfil === "admin";
  const catLabel = {
    comunicado: "Comunicado",
    aviso: "Aviso",
    calendario: "Calendário escolar",
    informacao_geral: "Informação geral",
  };

  content.innerHTML = `
    <div class="flex justify-end">${canCreate ? `<button class="btn-primary" id="btn-nova-noticia">Nova notícia</button>` : ""}</div>
    <div class="space-y-4">
      ${noticias
        .map(
          (n) => `<article class="panel p-5 slide-up">
          <p class="text-xs uppercase tracking-wide text-[var(--sea)]">${catLabel[n.categoria] || n.categoria} · ${fmtDateTime(n.publicado_em)}</p>
          <h3 class="font-display text-2xl mt-1">${n.titulo}</h3>
          <p class="mt-2 font-semibold text-[rgba(11,31,42,0.75)]">${n.resumo}</p>
          <p class="mt-3 text-[rgba(11,31,42,0.7)] whitespace-pre-line">${n.conteudo}</p>
        </article>`
        )
        .join("") || `<p class="panel p-5">Nenhuma notícia.</p>`}
    </div>`;

  if (canCreate) {
    document.getElementById("btn-nova-noticia").onclick = () => {
      openModal(
        "Nova notícia",
        `
        <select class="input-field" name="categoria" required>
          <option value="comunicado">Comunicado</option>
          <option value="aviso">Aviso</option>
          <option value="calendario">Calendário escolar</option>
          <option value="informacao_geral">Informação geral</option>
        </select>
        <input class="input-field" name="titulo" placeholder="Título" required />
        <input class="input-field" name="resumo" placeholder="Resumo" required />
        <textarea class="input-field" name="conteudo" rows="6" placeholder="Conteúdo" required></textarea>
        `,
        async (fd) => {
          await GMApi.api("/noticias", {
            method: "POST",
            body: { ...Object.fromEntries(fd.entries()), publicada: true },
          });
        }
      );
    };
  }
}

const views = {
  inicio: viewInicio,
  perfil: viewPerfil,
  alunos: viewAlunos,
  professores: viewProfessores,
  series: viewSeries,
  turmas: viewTurmas,
  disciplinas: viewDisciplinas,
  notas: viewNotas,
  ocorrencias: viewOcorrencias,
  eventos: viewEventos,
  noticias: viewNoticias,
  relatorios: viewRelatorios,
  acesso: viewAcesso,
  lgpd: viewLgpd,
  assistente: viewAssistente,
  configuracoes: viewConfiguracoes,
};

async function viewRelatorios() {
  setMeta("Relatórios", "Emissão de indicadores acadêmicos");
  const rel = await GMApi.api("/relatorios/geral");
  const content = document.getElementById("content");
  content.innerHTML = `
    ${Branding.printHeaderHtml()}
    <section class="panel p-5 slide-up">
      <div class="flex flex-wrap justify-between gap-3 items-center">
        <h2 class="font-display text-2xl">Relatório geral</h2>
        <button class="btn-primary" id="btn-print">Imprimir / PDF</button>
      </div>
      <div id="relatorio-print" class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        ${cardStat("Alunos", rel.total_alunos)}
        ${cardStat("Professores", rel.total_professores)}
        ${cardStat("Turmas", rel.total_turmas)}
        ${cardStat("Disciplinas", rel.total_disciplinas)}
        ${cardStat("Aprovados*", rel.aprovados)}
        ${cardStat("Recuperação*", rel.recuperacao)}
        ${cardStat("Reprovados*", rel.reprovados)}
        ${cardStat("Ocorrências", rel.total_ocorrencias)}
      </div>
      <p class="text-sm text-[rgba(11,31,42,0.55)] mt-4">* Contagem por disciplina (médias finais lançadas).</p>
    </section>
    ${Branding.printFooterHtml()}`;
  document.getElementById("btn-print").onclick = () => window.print();
}

async function viewConfiguracoes() {
  setMeta("Configurações da Escola", "Administração · identidade e dados institucionais");
  const escola = await GMApi.api("/escola");
  const content = document.getElementById("content");
  content.innerHTML = `
    <div class="grid lg:grid-cols-2 gap-4">
      <form id="form-dados" class="panel p-5 space-y-3">
        <h3 class="font-display text-xl">Dados da escola</h3>
        <input class="input-field" name="nome" value="${escola.nome || ""}" placeholder="Nome" required />
        <input class="input-field" name="slogan" value="${escola.slogan || ""}" placeholder="Slogan" />
        <input class="input-field" name="cnpj" value="${escola.cnpj || ""}" placeholder="CNPJ" />
        <input class="input-field" name="endereco" value="${escola.endereco || ""}" placeholder="Endereço" />
        <div class="grid grid-cols-2 gap-2">
          <input class="input-field" name="cidade" value="${escola.cidade || ""}" placeholder="Cidade" />
          <input class="input-field" name="estado" value="${escola.estado || ""}" maxlength="2" placeholder="UF" />
        </div>
        <input class="input-field" name="cep" value="${escola.cep || ""}" placeholder="CEP" />
        <input class="input-field" name="telefone" value="${escola.telefone || ""}" placeholder="Telefone" />
        <input class="input-field" name="whatsapp" value="${escola.whatsapp || ""}" placeholder="WhatsApp" />
        <input class="input-field" name="email" value="${escola.email || ""}" placeholder="E-mail" />
        <input class="input-field" name="site" value="${escola.site || ""}" placeholder="Site" />
        <input class="input-field" name="diretor" value="${escola.diretor || ""}" placeholder="Diretor(a)" />
        <input class="input-field" name="vice_diretor" value="${escola.vice_diretor || ""}" placeholder="Vice-diretor(a)" />
        <button class="btn-primary" type="submit">Salvar dados</button>
      </form>

      <div class="space-y-4">
        <form id="form-cores" class="panel p-5 space-y-3">
          <h3 class="font-display text-xl">Cores do sistema</h3>
          <label class="text-sm">Cor principal</label>
          <input class="input-field" name="cor_primaria" type="color" value="${escola.cor_primaria}" />
          <label class="text-sm">Cor secundária</label>
          <input class="input-field" name="cor_secundaria" type="color" value="${escola.cor_secundaria}" />
          <label class="text-sm">Cor dos botões</label>
          <input class="input-field" name="cor_botoes" type="color" value="${escola.cor_botoes}" />
          <label class="text-sm">Cor do menu lateral</label>
          <input class="input-field" name="cor_menu" type="color" value="${escola.cor_menu}" />
          <select class="input-field" name="tema">
            <option value="claro" ${escola.tema === "claro" ? "selected" : ""}>Tema claro</option>
            <option value="escuro" ${escola.tema === "escuro" ? "selected" : ""}>Tema escuro</option>
          </select>
          <button class="btn-primary" type="submit">Salvar cores</button>
        </form>

        <form id="form-logo" class="panel p-5 space-y-3">
          <h3 class="font-display text-xl">Logomarca</h3>
          ${escola.logo ? `<img src="${escola.logo}" alt="Logo" class="h-16 object-contain" />` : "<p class='text-sm'>Nenhuma logo enviada.</p>"}
          <input class="input-field" name="file" type="file" accept="image/*" required />
          <button class="btn-primary" type="submit">Enviar logo</button>
        </form>

        <form id="form-redes" class="panel p-5 space-y-3">
          <h3 class="font-display text-xl">Redes sociais</h3>
          <input class="input-field" name="facebook" value="${escola.facebook || ""}" placeholder="Facebook URL" />
          <input class="input-field" name="instagram" value="${escola.instagram || ""}" placeholder="Instagram URL" />
          <input class="input-field" name="youtube" value="${escola.youtube || ""}" placeholder="YouTube URL" />
          <button class="btn-primary" type="submit">Salvar redes</button>
        </form>

        <form id="form-impressao" class="panel p-5 space-y-3">
          <h3 class="font-display text-xl">Configurações de impressão</h3>
          <input class="input-field" name="rodape_impressao" value="${escola.rodape_impressao || ""}" placeholder="Rodapé dos documentos" />
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" name="mostrar_cnpj_impressao" ${escola.mostrar_cnpj_impressao ? "checked" : ""} />
            Mostrar CNPJ nos documentos
          </label>
          <button class="btn-primary" type="submit">Salvar impressão</button>
        </form>

        <form id="form-fundo" class="panel p-5 space-y-3">
          <h3 class="font-display text-xl">Fundo do login (opcional)</h3>
          <input class="input-field" name="file" type="file" accept="image/*" required />
          <button class="btn-primary" type="submit">Enviar imagem de fundo</button>
        </form>
      </div>
    </div>`;

  const savePartial = async (formId) => {
    const form = document.getElementById(formId);
    form.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const fd = new FormData(form);
        const body = Object.fromEntries(fd.entries());
        if ("mostrar_cnpj_impressao" in body) {
          body.mostrar_cnpj_impressao = !!form.mostrar_cnpj_impressao?.checked;
        }
        const updated = await GMApi.api("/escola", { method: "PUT", body });
        Branding.escola = updated;
        Branding.apply(updated);
        applyBrandChrome();
        toast("Configurações salvas");
      } catch (err) {
        toast(err.message);
      }
    };
  };
  await Promise.all(["form-dados", "form-cores", "form-redes", "form-impressao"].map(savePartial));

  document.getElementById("form-logo").onsubmit = async (e) => {
    e.preventDefault();
    const file = e.target.file.files[0];
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${GMApi.API_BASE}/escola/logo`, {
        method: "POST",
        headers: { Authorization: `Bearer ${Auth.getToken()}` },
        body: fd,
      });
      if (!res.ok) throw new Error("Falha no upload");
      Branding.escola = await res.json();
      Branding.apply(Branding.escola);
      applyBrandChrome();
      toast("Logo atualizada");
      await renderView("configuracoes");
    } catch (err) {
      toast(err.message);
    }
  };

  document.getElementById("form-fundo").onsubmit = async (e) => {
    e.preventDefault();
    const file = e.target.file.files[0];
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${GMApi.API_BASE}/escola/fundo-login`, {
        method: "POST",
        headers: { Authorization: `Bearer ${Auth.getToken()}` },
        body: fd,
      });
      if (!res.ok) throw new Error("Falha no upload");
      Branding.escola = await res.json();
      toast("Fundo do login atualizado");
    } catch (err) {
      toast(err.message);
    }
  };
}

async function viewAssistente() {
  setMeta("Assistente WhatsApp", "IA escolar via WhatsApp · simulador e status");
  const status = await GMApi.api("/whatsapp/status");
  const content = document.getElementById("content");
  content.innerHTML = `
    <section class="stats-grid slide-up">
      ${cardStat("WhatsApp API", status.whatsapp_enabled ? "Ativo" : "Demo")}
      ${cardStat("OpenAI", status.openai_enabled ? "Ativo" : "Regras locais")}
      ${cardStat("Webhook", "/api/whatsapp/webhook")}
      ${cardStat("Verify token", status.verify_token_configured ? "OK" : "—")}
    </section>
    <section class="grid lg:grid-cols-2 gap-4 mt-4">
      <div class="panel p-5">
        <h3 class="font-display text-xl mb-2">Simulador de conversa</h3>
        <p class="text-sm text-[rgba(11,31,42,0.65)] mb-3">Teste autenticação e perguntas sem a Meta. Comece com <strong>menu</strong>.</p>
        <input class="input-field mb-2" id="wa-phone" value="55119977770001" placeholder="Telefone" />
        <div id="wa-chat" class="h-72 overflow-y-auto border border-[var(--line)] rounded-xl p-3 mb-3 bg-white/60 text-sm space-y-2"></div>
        <div class="flex gap-2">
          <input class="input-field" id="wa-msg" placeholder="Digite a mensagem..." />
          <button class="btn-primary" id="wa-send" type="button">Enviar</button>
        </div>
        <div class="mt-3 flex flex-wrap gap-2 text-xs">
          <button class="btn-ghost" data-quick="menu">menu</button>
          <button class="btn-ghost" data-quick="2">sou responsável</button>
          <button class="btn-ghost" data-quick="12345678901 A2026001">CPF + matrícula</button>
          <button class="btn-ghost" data-quick="Como está o desempenho do meu filho?">desempenho</button>
        </div>
      </div>
      <div class="panel p-5 space-y-3 text-sm">
        <h3 class="font-display text-xl">Como configurar</h3>
        <ol class="list-decimal pl-5 space-y-2 text-[rgba(11,31,42,0.75)]">
          <li>Crie app no Meta for Developers e ative WhatsApp Cloud API.</li>
          <li>No <code>.env</code>: <code>WHATSAPP_ENABLED=true</code>, token, phone_number_id e verify_token.</li>
          <li>Webhook: <code>https://seu-dominio/api/whatsapp/webhook</code></li>
          <li>Opcional: <code>OPENAI_ENABLED=true</code> + <code>OPENAI_API_KEY</code> (GPT + Whisper).</li>
        </ol>
        <h4 class="font-semibold mt-4">Segurança</h4>
        <ul class="list-disc pl-5 space-y-1 text-[rgba(11,31,42,0.75)]">
          <li>Aluno: matrícula + senha</li>
          <li>Responsável: CPF + matrícula (ou código)</li>
          <li>Professor/Admin: e-mail/usuário + senha</li>
        </ul>
        <h4 class="font-semibold mt-4">Notificações automáticas</h4>
        <p>Nota lançada, ocorrência, evento e recuperação disparam aviso ao WhatsApp do responsável (quando cadastrado).</p>
      </div>
    </section>`;

  const chat = document.getElementById("wa-chat");
  const append = (who, text) => {
    const div = document.createElement("div");
    div.className = who === "you" ? "text-right" : "text-left";
    div.innerHTML = `<span class="inline-block max-w-[90%] rounded-xl px-3 py-2 ${who === "you" ? "bg-[var(--sea)] text-white" : "bg-[rgba(11,31,42,0.08)]"}">${text.replace(/\n/g, "<br>")}</span>`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  };

  const send = async (message) => {
    const phone = document.getElementById("wa-phone").value.trim();
    append("you", message);
    try {
      const res = await GMApi.api("/whatsapp/simulate", {
        method: "POST",
        body: { phone, message },
      });
      append("bot", res.reply);
    } catch (err) {
      append("bot", "Erro: " + err.message);
    }
  };

  document.getElementById("wa-send").onclick = async () => {
    const input = document.getElementById("wa-msg");
    const msg = input.value.trim();
    if (!msg) return;
    input.value = "";
    await send(msg);
  };
  document.getElementById("wa-msg").addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      document.getElementById("wa-send").click();
    }
  });
  document.querySelectorAll("[data-quick]").forEach((btn) => {
    btn.onclick = () => send(btn.dataset.quick);
  });
}

async function viewLgpd() {
  setMeta("LGPD", "Privacidade, consentimento e direitos do titular");
  const [logs, alunos] = await Promise.all([
    GMApi.api("/lgpd/logs?limit=80"),
    GMApi.api("/alunos"),
  ]);
  const content = document.getElementById("content");
  const comConsent = alunos.filter((a) => a.lgpd_consentimento).length;
  content.innerHTML = `
    <section class="panel p-4 text-sm text-[rgba(11,31,42,0.75)] space-y-2">
      <p>Este painel apoia a conformidade com a <strong>Lei Geral de Proteção de Dados (LGPD)</strong>.</p>
      <p>
        Documentos:
        <a class="text-[var(--sea)] font-semibold" href="/pages/privacidade.html" target="_blank">Política de Privacidade</a>
        ·
        <a class="text-[var(--sea)] font-semibold" href="/pages/termos.html" target="_blank">Termos de Uso</a>
      </p>
      <div class="flex flex-wrap gap-2 mt-2">
        <button class="btn-primary" id="btn-exportar-meus">Exportar meus dados</button>
      </div>
    </section>
    <section class="stats-grid mt-4">
      ${cardStat("Alunos com consentimento", `${comConsent}/${alunos.length}`)}
      ${cardStat("Eventos de auditoria", logs.length)}
    </section>
    <section class="panel p-4 mt-4">
      <h3 class="font-display text-xl mb-3">Consentimento nos cadastros</h3>
      <div class="table-wrap">
        <table class="data">
          <thead><tr><th>Aluno</th><th>Consentimento</th><th>Autorizado por</th><th>Data</th><th></th></tr></thead>
          <tbody>
            ${alunos
              .map(
                (a) => `<tr>
                <td>${a.user.nome}<div class="text-xs text-[rgba(11,31,42,0.55)]">${a.matricula}</div></td>
                <td><span class="badge ${a.lgpd_consentimento ? "success" : "warning"}">${a.lgpd_consentimento ? "Sim" : "Pendente"}</span></td>
                <td>${a.lgpd_consentimento_por || "—"}</td>
                <td>${a.lgpd_consentimento_em ? fmtDateTime(a.lgpd_consentimento_em) : "—"}</td>
                <td><button class="btn-ghost" data-anon="${a.user.id}" data-nome="${a.user.nome}">Anonimizar</button></td>
              </tr>`
              )
              .join("") || `<tr><td colspan="5">Nenhum aluno.</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
    <section class="panel p-4 mt-4">
      <h3 class="font-display text-xl mb-3">Trilha de auditoria</h3>
      <div class="table-wrap">
        <table class="data">
          <thead><tr><th>Quando</th><th>Usuário</th><th>Ação</th><th>Detalhe</th></tr></thead>
          <tbody>
            ${logs
              .map(
                (l) => `<tr>
                <td>${fmtDateTime(l.criado_em)}</td>
                <td>#${l.user_id ?? "—"}</td>
                <td>${l.acao}</td>
                <td>${l.detalhe || "—"}</td>
              </tr>`
              )
              .join("") || `<tr><td colspan="4">Sem registros.</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>`;

  document.getElementById("btn-exportar-meus").onclick = async () => {
    try {
      const dados = await GMApi.api("/lgpd/meus-dados");
      const blob = new Blob([JSON.stringify(dados, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `meus-dados-lgpd-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast("Arquivo gerado");
    } catch (err) {
      toast(err.message);
    }
  };

  document.querySelectorAll("[data-anon]").forEach((btn) => {
    btn.onclick = async () => {
      if (!confirm(`Anonimizar dados de "${btn.dataset.nome}"? Esta ação não pode ser desfeita.`)) return;
      try {
        await GMApi.api(`/lgpd/anonimizar/${btn.dataset.anon}`, {
          method: "POST",
          body: { motivo: "Solicitação LGPD / administração" },
        });
        toast("Dados anonimizados");
        await renderView("lgpd");
      } catch (err) {
        toast(err.message);
      }
    };
  });
}

async function viewAcesso() {
  setMeta("Controle de acesso", "Ativar/desativar usuários e gerar nova senha provisória");
  const usuarios = await GMApi.api("/acesso/usuarios");
  const content = document.getElementById("content");
  content.innerHTML = `
    <section class="panel p-4 text-sm text-[rgba(11,31,42,0.7)]">
      Em caso de esquecimento de senha, o usuário deve contactar a administração.
      Use <strong>Reset senha</strong> para gerar uma nova senha provisória (com troca obrigatória no próximo login).
    </section>
    <div class="panel table-wrap">
      <table class="data">
        <thead><tr><th>Nome</th><th>Usuário</th><th>Perfil</th><th>Status</th><th>1º acesso</th><th>Ações</th></tr></thead>
        <tbody>
          ${usuarios
            .map(
              (u) => `<tr>
              <td>${u.nome}<div class="text-xs text-[rgba(11,31,42,0.55)]">${u.email}</div></td>
              <td>${u.username}</td>
              <td>${u.role}</td>
              <td><span class="badge ${u.ativo ? "success" : "warning"}">${u.ativo ? "Ativo" : "Inativo"}</span></td>
              <td>${u.must_change_password ? "Senha provisória" : "OK"}</td>
              <td class="space-x-2">
                <button class="btn-ghost" data-toggle="${u.id}" data-ativo="${u.ativo}">${u.ativo ? "Desativar" : "Ativar"}</button>
                <button class="btn-ghost" data-reset="${u.id}" data-nome="${u.nome}">Reset senha</button>
              </td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>`;

  document.querySelectorAll("[data-toggle]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await GMApi.api(`/acesso/usuarios/${btn.dataset.toggle}`, {
          method: "PATCH",
          body: { ativo: btn.dataset.ativo !== "true" },
        });
        toast("Acesso atualizado");
        await renderView("acesso");
      } catch (err) {
        toast(err.message);
      }
    };
  });

  document.querySelectorAll("[data-reset]").forEach((btn) => {
    btn.onclick = async () => {
      if (!confirm(`Gerar nova senha provisória para ${btn.dataset.nome}?`)) return;
      try {
        const res = await GMApi.api(`/acesso/usuarios/${btn.dataset.reset}/reset-senha`, {
          method: "POST",
          body: {},
        });
        await renderView("acesso");
        showCredenciais({
          titulo: "Nova senha provisória",
          login: res.login,
          senha: res.senha_provisoria,
          entrega: res.entrega,
          extraHtml: `<p class="text-sm mt-3 text-[rgba(11,31,42,0.65)]">${res.message}</p>`,
        });
      } catch (err) {
        toast(err.message);
      }
    };
  });
}

async function renderView(viewId) {
  const allowed = (menus[state.me.perfil] || []).some((m) => m.id === viewId);
  const fallback = state.me.perfil === "aluno" ? "perfil" : "inicio";
  state.view = allowed ? viewId : fallback;
  location.hash = state.view;
  renderNav();
  const content = document.getElementById("content");
  content.innerHTML = `<div class="panel p-5">Carregando...</div>`;
  try {
    await views[state.view]();
  } catch (err) {
    content.innerHTML = `<div class="panel p-5 text-red-700">${err.message}</div>`;
  }
}

async function boot() {
  if (!Auth.requireAuth("/admin")) return;
  const status = await Branding.load();
  if (status.needs_setup) {
    window.location.href = "/pages/setup.html";
    return;
  }
  applyBrandChrome();
  try {
    state.me = await GMApi.api("/auth/me");
    Auth.setSession(Auth.getToken(), state.me);
  } catch {
    Auth.logout();
    return;
  }

  if (state.me.must_change_password || state.me.user?.must_change_password) {
    window.location.href = "/pages/change-password.html";
    return;
  }

  if (state.me.perfil === "aluno") {
    window.location.href = Auth.homeFor(state.me);
    return;
  }

  document.getElementById("user-name").textContent = state.me.user.nome;
  document.getElementById("user-role").textContent = roleLabel[state.me.perfil] || state.me.perfil;
  document.getElementById("logout-btn").onclick = () => Auth.logout();
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  const closeSidebar = () => {
    sidebar.classList.remove("open");
    overlay?.classList.remove("show");
  };
  document.getElementById("menu-btn").onclick = () => {
    const open = sidebar.classList.toggle("open");
    overlay?.classList.toggle("show", open);
  };
  overlay?.addEventListener("click", closeSidebar);

  const fallback = state.me.perfil === "aluno" ? "perfil" : "inicio";
  const initial = (location.hash || `#${fallback}`).replace("#", "");
  await renderView(initial);
}

boot();
