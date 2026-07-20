const AlunoPortal = {
  me: null,
  aluno: null,
  view: "boletim",
  tab: "s1",
};

function fmtDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("pt-BR");
}

function fmtNum(v) {
  if (v === null || v === undefined || v === "") return "—";
  return Number(v).toFixed(2);
}

function sitBadge(situacao, label) {
  const cls = situacao === "aprovado" ? "ok" : situacao === "recuperacao" ? "warn" : situacao === "reprovado" ? "bad" : "";
  return `<span class="badge-sit ${cls}">${label || situacao || "—"}</span>`;
}

function setActiveMenu() {
  document.querySelectorAll(".boletim-icon-btn[data-view]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === AlunoPortal.view);
  });
}

async function loadAluno() {
  if (!AlunoPortal.me?.aluno_id) return null;
  return GMApi.api(`/alunos/${AlunoPortal.me.aluno_id}`);
}

function renderInfoHeader(escola) {
  const a = AlunoPortal.aluno;
  const me = AlunoPortal.me;
  const turma = a?.turma;
  const serie = turma?.serie?.nome || "—";
  const turmaNome = turma?.nome || "—";
  const ano = turma?.ano_letivo || new Date().getFullYear();

  return `
    <div class="boletim-info-grid">
      <div class="boletim-card">
        <table>
          <tr><th>Matrícula</th><td>${a?.matricula || me.user.username}</td></tr>
          <tr><th>Aluno(a)</th><td>${(me.user.nome || "").toUpperCase()}</td></tr>
          <tr><th>Período Letivo</th><td>${ano}</td></tr>
          <tr><th>Escola</th><td>${(escola?.nome || "Escola").toUpperCase()}</td></tr>
          <tr><th>Curso</th><td>${serie.toUpperCase()}</td></tr>
          <tr><th>Turma</th><td>${turmaNome}</td></tr>
          <tr><th>Situação</th><td>${a?.user?.ativo === false ? "INATIVO" : "MATRICULADO"}</td></tr>
        </table>
      </div>
      <div class="boletim-card">
        <div class="criterio-title">Critério de Avaliação</div>
        <table>
          <tr><th></th><th>Máximo</th><th>Média</th></tr>
          <tr><th>1º Semestre</th><td>50.00</td><td>—</td></tr>
          <tr><th>2º Semestre</th><td>50.00</td><td>—</td></tr>
          <tr><th>Total (S1+S2)</th><td>100.00</td><td>60.00</td></tr>
        </table>
      </div>
    </div>`;
}

function renderGradesTable(boletim, tab) {
  if (!boletim.length) {
    return `<div class="boletim-empty">Nenhuma nota lançada até o momento.</div>`;
  }

  if (tab === "final") {
    return `
      <div class="boletim-table-wrap">
        <table class="boletim-grades">
          <thead>
            <tr>
              <th>Componente Curricular</th>
              <th>1º Semestre</th>
              <th>2º Semestre</th>
              <th>Total (S1+S2)</th>
              <th>Situação</th>
            </tr>
          </thead>
          <tbody>
            ${boletim
              .map(
                (b) => `<tr>
                <td class="disc">${(b.disciplina_nome || "").toUpperCase()}</td>
                <td>${fmtNum(b.semestre1)}</td>
                <td>${fmtNum(b.semestre2)}</td>
                <td class="nota-final">${fmtNum(b.media_final)}</td>
                <td>${sitBadge(b.situacao, b.situacao_label)}</td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>`;
  }

  const key = tab === "s2" ? "detalhe_semestre2" : "detalhe_semestre1";
  const totalKey = tab === "s2" ? "semestre2" : "semestre1";
  const titulo = tab === "s2" ? "2º Semestre" : "1º Semestre";

  return `
    <div class="boletim-table-wrap">
      <table class="boletim-grades">
        <thead>
          <tr>
            <th rowspan="2">Componente Curricular</th>
            <th colspan="5">${titulo}</th>
            <th rowspan="2">Faltas</th>
            <th rowspan="2">Notas</th>
          </tr>
          <tr>
            <th>P1</th><th>P2</th><th>Trab.</th><th>Part.</th><th>Total</th>
          </tr>
        </thead>
        <tbody>
          ${boletim
            .map((b) => {
              const d = b[key] || {};
              return `<tr>
                <td class="disc">${(b.disciplina_nome || "").toUpperCase()}</td>
                <td>${fmtNum(d.prova1)}</td>
                <td>${fmtNum(d.prova2)}</td>
                <td>${fmtNum(d.trabalho)}</td>
                <td>${fmtNum(d.participacao)}</td>
                <td class="nota-final">${fmtNum(d.total ?? b[totalKey])}</td>
                <td>0</td>
                <td class="nota-final">${fmtNum(d.total ?? b[totalKey])}</td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>`;
}

async function viewBoletim() {
  const root = document.getElementById("aluno-content");
  const [boletim, escola] = await Promise.all([
    GMApi.api("/notas/boletim"),
    Branding.load().then(() => Branding.escola),
  ]);

  root.innerHTML = `
    ${renderInfoHeader(escola)}
    <h2 class="boletim-section-title">Notas Escolares</h2>
    <div class="boletim-tabs">
      <button type="button" class="boletim-tab ${AlunoPortal.tab === "s1" ? "active" : ""}" data-tab="s1">1º Semestre</button>
      <button type="button" class="boletim-tab ${AlunoPortal.tab === "s2" ? "active" : ""}" data-tab="s2">2º Semestre</button>
      <button type="button" class="boletim-tab ${AlunoPortal.tab === "final" ? "active" : ""}" data-tab="final">Resultado Final</button>
    </div>
    <div id="grades-panel">${renderGradesTable(boletim, AlunoPortal.tab)}</div>
    <p class="boletim-scroll-hint">Deslize a tabela para o lado para ver todas as colunas.</p>
    <p style="margin-top:0.75rem;font-size:0.82rem;color:#667">
      Composição do semestre: Prova 1 (15) + Prova 2 (15) + Trabalho (10) + Participação (10) = 50.
      Pontuação final = S1 + S2 (máx. 100). Aprovado ≥ 60 · Recuperação 30–59 · Reprovado &lt; 30.
      Ex.: 25 + 35 = 60 → Aprovado.
    </p>`;

  root.querySelectorAll(".boletim-tab").forEach((btn) => {
    btn.onclick = () => {
      AlunoPortal.tab = btn.dataset.tab;
      document.getElementById("grades-panel").innerHTML = renderGradesTable(boletim, AlunoPortal.tab);
      root.querySelectorAll(".boletim-tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === AlunoPortal.tab));
    };
  });
}

async function viewEventos() {
  const root = document.getElementById("aluno-content");
  const eventos = await GMApi.api("/eventos");
  root.innerHTML = `
    <h2 class="boletim-section-title">Eventos</h2>
    ${
      eventos.length
        ? `<div class="boletim-list">${eventos
            .map(
              (e) => `<article class="boletim-list-item">
              <h3>${e.titulo}</h3>
              <p><strong>Tipo:</strong> ${e.tipo} · <strong>Data:</strong> ${fmtDate(e.data_evento)} ${e.horario || ""}</p>
              <p><strong>Local:</strong> ${e.local || "A definir"}</p>
              <p>${e.descricao || ""}</p>
            </article>`
            )
            .join("")}</div>`
        : `<div class="boletim-empty">Nenhum evento cadastrado.</div>`
    }`;
}

async function viewOcorrencias() {
  const root = document.getElementById("aluno-content");
  const ocorrencias = await GMApi.api("/ocorrencias");
  root.innerHTML = `
    <h2 class="boletim-section-title">Ocorrências</h2>
    ${
      ocorrencias.length
        ? `<div class="boletim-list">${ocorrencias
            .map(
              (o) => `<article class="boletim-list-item">
              <h3>${o.tipo} · ${o.gravidade}</h3>
              <p><strong>Data:</strong> ${fmtDate(o.data_ocorrencia)}</p>
              <p>${o.descricao}</p>
            </article>`
            )
            .join("")}</div>`
        : `<div class="boletim-empty">Nenhuma ocorrência registrada.</div>`
    }`;
}

async function viewNoticias() {
  const root = document.getElementById("aluno-content");
  const noticias = await GMApi.api("/noticias");
  root.innerHTML = `
    <h2 class="boletim-section-title">Notícias</h2>
    ${
      noticias.length
        ? `<div class="boletim-list">${noticias
            .map(
              (n) => `<article class="boletim-list-item">
              <h3>${n.titulo}</h3>
              <p><strong>Categoria:</strong> ${n.categoria}</p>
              <p>${n.resumo || n.conteudo || ""}</p>
            </article>`
            )
            .join("")}</div>`
        : `<div class="boletim-empty">Nenhuma notícia publicada.</div>`
    }`;
}

function renderServicoPage({ titulo, resumo, passos, docs, prazo }) {
  const a = AlunoPortal.aluno;
  const me = AlunoPortal.me;
  return `
    <h2 class="boletim-section-title">${titulo}</h2>
    <div class="boletim-card" style="padding:1rem;margin-bottom:1rem">
      <p style="margin:0 0 0.75rem;color:#445">${resumo}</p>
      <table>
        <tr><th>Aluno(a)</th><td>${(me.user.nome || "").toUpperCase()}</td></tr>
        <tr><th>Matrícula</th><td>${a?.matricula || me.user.username}</td></tr>
        <tr><th>Turma</th><td>${a?.turma ? `${a.turma.serie?.nome || ""} ${a.turma.nome}` : "—"}</td></tr>
        <tr><th>Prazo / período</th><td>${prazo}</td></tr>
      </table>
    </div>
    <div class="boletim-list">
      <article class="boletim-list-item">
        <h3>Como solicitar</h3>
        <ol class="boletim-steps">${passos.map((p) => `<li>${p}</li>`).join("")}</ol>
      </article>
      <article class="boletim-list-item">
        <h3>Documentos necessários</h3>
        <ul class="boletim-steps">${docs.map((d) => `<li>${d}</li>`).join("")}</ul>
      </article>
      <article class="boletim-list-item">
        <h3>Status da solicitação</h3>
        <p>Nenhuma solicitação registrada neste período. Procure a secretaria ou registre o pedido presencialmente.</p>
        <p class="boletim-servico-note">Em breve será possível enviar o pedido online por este portal.</p>
      </article>
    </div>`;
}

async function viewTransferencias() {
  document.getElementById("aluno-content").innerHTML = renderServicoPage({
    titulo: "Transferências",
    resumo: "Solicite transferência escolar (entrada ou saída) junto à secretaria. O histórico e a documentação serão conferidos antes da liberação.",
    prazo: "Durante o ano letivo, conforme calendário da secretaria",
    passos: [
      "Preencha o requerimento de transferência na secretaria.",
      "Entregue a documentação listada abaixo.",
      "Aguarde a análise e a emissão da guia de transferência.",
    ],
    docs: [
      "Documento de identidade do aluno e do responsável",
      "Comprovante de residência",
      "Histórico escolar / declaração de transferência da escola de origem (quando aplicável)",
    ],
  });
}

async function viewAvaliacaoEspecial() {
  document.getElementById("aluno-content").innerHTML = renderServicoPage({
    titulo: "Avaliação Especial",
    resumo: "Avaliação aplicada em situações específicas (atestado médico, ausência justificada em prova oficial ou determinação pedagógica).",
    prazo: "Até 5 dias úteis após o retorno às aulas ou conforme calendário da coordenação",
    passos: [
      "Informe a coordenação pedagógica sobre o motivo da solicitação.",
      "Anexe atestado ou justificativa oficial.",
      "Aguarde a definição de data, disciplina e conteúdo da avaliação.",
    ],
    docs: [
      "Atestado médico ou justificativa oficial",
      "Requerimento assinado pelo responsável (quando menor de idade)",
    ],
  });
}

async function viewSegundaChamada() {
  document.getElementById("aluno-content").innerHTML = renderServicoPage({
    titulo: "Segunda Chamada",
    resumo: "Segunda oportunidade de realização de prova para alunos que faltaram à avaliação na data oficial, mediante justificativa aceita.",
    prazo: "Pedido em até 48 horas após a prova original (ou no retorno com atestado)",
    passos: [
      "Solicite a segunda chamada na secretaria ou coordenação.",
      "Apresente a justificativa da ausência.",
      "Compareça na data e horário divulgados para a reaplicação.",
    ],
    docs: [
      "Atestado ou comprovante da ausência",
      "Formulário de segunda chamada",
    ],
  });
}

async function viewRenovacaoMatricula() {
  document.getElementById("aluno-content").innerHTML = renderServicoPage({
    titulo: "Renovação de Matrícula",
    resumo: "Confirme a continuidade do aluno na escola para o próximo período letivo e atualize dados cadastrais do responsável.",
    prazo: "Conforme calendário oficial de rematrícula divulgado pela escola",
    passos: [
      "Verifique o período de renovação nas notícias/comunicados.",
      "Atualize telefone, e-mail e endereço do responsável.",
      "Confirme a renovação na secretaria e retire o comprovante.",
    ],
    docs: [
      "Documento do responsável",
      "Comprovante de residência atualizado",
      "Comprovante de quitação (quando exigido pela escola)",
    ],
  });
}

const views = {
  boletim: viewBoletim,
  eventos: viewEventos,
  ocorrencias: viewOcorrencias,
  noticias: viewNoticias,
  transferencias: viewTransferencias,
  "avaliacao-especial": viewAvaliacaoEspecial,
  "segunda-chamada": viewSegundaChamada,
  "renovacao-matricula": viewRenovacaoMatricula,
};

async function renderView(viewId) {
  AlunoPortal.view = views[viewId] ? viewId : "boletim";
  location.hash = AlunoPortal.view;
  setActiveMenu();
  const root = document.getElementById("aluno-content");
  root.innerHTML = `<p class="boletim-loading">Carregando...</p>`;
  try {
    await views[AlunoPortal.view]();
  } catch (err) {
    root.innerHTML = `<div class="boletim-empty" style="color:#b42318">${err.message}</div>`;
  }
}

async function boot() {
  if (!Auth.requireAuth("/")) return;

  const status = await Branding.load();
  if (status.needs_setup) {
    window.location.href = "/pages/setup.html";
    return;
  }

  try {
    AlunoPortal.me = await GMApi.api("/auth/me");
    Auth.setSession(Auth.getToken(), AlunoPortal.me);
  } catch {
    Auth.logout();
    return;
  }

  if (AlunoPortal.me.perfil !== "aluno") {
    window.location.href = Auth.homeFor(AlunoPortal.me);
    return;
  }

  if (AlunoPortal.me.must_change_password || AlunoPortal.me.user?.must_change_password) {
    window.location.href = "/pages/change-password.html";
    return;
  }

  document.getElementById("escola-nome").textContent = Branding.escola?.nome || "Escola";
  document.title = `Notas Escolares | ${Branding.escola?.nome || "Escola"}`;

  AlunoPortal.aluno = await loadAluno();

  document.querySelectorAll(".boletim-icon-btn[data-view]").forEach((btn) => {
    btn.onclick = () => {
      renderView(btn.dataset.view);
      closeMobileMenu();
    };
  });
  document.getElementById("btn-sair").onclick = () => Auth.logout();

  const menuToggle = document.getElementById("menu-toggle");
  const menu = document.getElementById("aluno-menu");
  function closeMobileMenu() {
    if (!menu || !menuToggle) return;
    if (window.matchMedia("(max-width: 1023px)").matches) {
      menu.classList.remove("is-open");
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.textContent = "Menu";
    }
  }
  menuToggle?.addEventListener("click", () => {
    const open = menu.classList.toggle("is-open");
    menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
    menuToggle.textContent = open ? "Fechar" : "Menu";
  });

  const initial = (location.hash || "#boletim").replace("#", "");
  await renderView(initial);
  initWaAssistente();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatWaText(text) {
  return escapeHtml(text)
    .replace(/\*([^*]+)\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function appendWaBubble(who, text, extraClass = "") {
  const box = document.getElementById("wa-messages");
  if (!box) return null;
  const div = document.createElement("div");
  div.className = `wa-bubble ${who} ${extraClass}`.trim();
  div.innerHTML = formatWaText(text);
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

async function sendWaMessage(message) {
  const text = (message || "").trim();
  if (!text) return;
  const input = document.getElementById("wa-input");
  if (input) input.value = "";
  appendWaBubble("you", text);
  const typing = appendWaBubble("bot", "Digitando...", "typing");
  try {
    const res = await GMApi.api("/whatsapp/aluno-chat", {
      method: "POST",
      body: { message: text },
    });
    typing?.remove();
    appendWaBubble("bot", res.reply || "Sem resposta.");
  } catch (err) {
    typing?.remove();
    appendWaBubble("bot", "Não foi possível responder agora: " + err.message);
  }
}

function initWaAssistente() {
  const fab = document.getElementById("wa-fab");
  const panel = document.getElementById("wa-panel");
  const closeBtn = document.getElementById("wa-close");
  const form = document.getElementById("wa-form");
  const messages = document.getElementById("wa-messages");
  if (!fab || !panel || !form || !messages) return;

  const openPanel = () => {
    panel.classList.remove("hidden");
    panel.setAttribute("aria-hidden", "false");
    if (!messages.dataset.ready) {
      const nome = AlunoPortal.me?.user?.nome?.split(" ")[0] || "aluno";
      appendWaBubble(
        "bot",
        `Olá, ${nome}! Sou o Assistente Escolar via WhatsApp.\nPergunte sobre notas, ocorrências, eventos ou peça ajuda para estudar.`
      );
      messages.dataset.ready = "1";
    }
    document.getElementById("wa-input")?.focus();
  };

  const closePanel = () => {
    panel.classList.add("hidden");
    panel.setAttribute("aria-hidden", "true");
  };

  fab.onclick = () => {
    if (panel.classList.contains("hidden")) openPanel();
    else closePanel();
  };
  closeBtn.onclick = closePanel;

  form.onsubmit = async (e) => {
    e.preventDefault();
    await sendWaMessage(document.getElementById("wa-input").value);
  };

  document.querySelectorAll("[data-wa-q]").forEach((btn) => {
    btn.onclick = () => sendWaMessage(btn.dataset.waQ);
  });
}

boot();
