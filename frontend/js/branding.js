const Branding = {
  escola: null,

  async load() {
    try {
      const status = await GMApi.api("/escola/status", { auth: false });
      this.escola = status.escola;
      if (this.escola) this.apply(this.escola);
      return status;
    } catch {
      return { needs_setup: false, escola: null };
    }
  },

  apply(escola) {
    if (!escola) return;
    const root = document.documentElement;
    root.style.setProperty("--sea", escola.cor_primaria || "#0f6e7c");
    root.style.setProperty("--sea-deep", escola.cor_secundaria || "#0a4f59");
    root.style.setProperty("--btn", escola.cor_botoes || escola.cor_primaria || "#0f6e7c");
    root.style.setProperty("--menu", escola.cor_menu || "#0b1f2a");
    root.dataset.theme = escola.tema || "claro";
    if (escola.tema === "escuro") {
      root.style.setProperty("--ink", "#e8f2f4");
      root.style.setProperty("--line", "rgba(232, 242, 244, 0.14)");
      document.body?.classList.add("theme-dark");
    } else {
      root.style.setProperty("--ink", "#0b1f2a");
      root.style.setProperty("--line", "rgba(11, 31, 42, 0.12)");
      document.body?.classList.remove("theme-dark");
    }
    document.title = `${escola.nome} | Portal`;
  },

  logoHtml(size = "2.75rem") {
    const e = this.escola;
    if (e?.logo) {
      return `<img class="brand-logo" src="${e.logo}" alt="Logo" style="width:${size};height:${size};object-fit:contain;border-radius:0.7rem;background:#fff" />`;
    }
    const initials = (e?.nome || "G&M").split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase();
    return `<div class="brand-mark" style="width:${size};height:${size}">${initials}</div>`;
  },

  headerBrandHtml() {
    const e = this.escola || { nome: "Escola", slogan: "" };
    return `
      <div class="flex items-center gap-3 min-w-0">
        ${this.logoHtml("2.5rem")}
        <div class="min-w-0">
          <p class="font-display text-base md:text-lg leading-tight truncate">${e.nome}</p>
          <p class="text-xs text-[rgba(11,31,42,0.55)] truncate">${e.slogan || ""}</p>
        </div>
      </div>`;
  },

  printHeaderHtml() {
    const e = this.escola || {};
    const cnpj = e.mostrar_cnpj_impressao && e.cnpj ? `<p>CNPJ: ${e.cnpj}</p>` : "";
    return `
      <div class="print-brand">
        ${e.logo ? `<img src="${e.logo}" alt="Logo" />` : ""}
        <div>
          <h1>${e.nome || "Escola"}</h1>
          <p>${e.slogan || ""}</p>
          <p>${[e.endereco, e.cidade, e.estado, e.cep].filter(Boolean).join(" · ")}</p>
          <p>${[e.telefone, e.email].filter(Boolean).join(" · ")}</p>
          ${cnpj}
        </div>
      </div>`;
  },

  printFooterHtml() {
    const e = this.escola || {};
    return `<div class="print-footer">${e.rodape_impressao || e.nome || ""} · ${e.diretor ? "Dir.: " + e.diretor : ""}</div>`;
  },
};

window.Branding = Branding;
