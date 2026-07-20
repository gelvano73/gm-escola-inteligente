const Auth = {
  tokenKey: "gm_token",
  userKey: "gm_user",

  getToken() {
    return localStorage.getItem(this.tokenKey);
  },

  getUser() {
    const raw = localStorage.getItem(this.userKey);
    return raw ? JSON.parse(raw) : null;
  },

  setSession(token, me) {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem(this.userKey, JSON.stringify(me));
  },

  clear() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  },

  loginPathFor(perfil) {
    if (perfil === "admin" || perfil === "professor") return "/admin";
    return "/";
  },

  requireAuth(loginPath) {
    if (!this.getToken()) {
      window.location.href = loginPath || "/";
      return false;
    }
    return true;
  },

  async login(usuario, password) {
    const tokenData = await GMApi.api("/auth/login-json", {
      method: "POST",
      body: { usuario, password },
      auth: false,
    });
    const me = await fetch(`${GMApi.API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    }).then(async (r) => {
      if (!r.ok) throw new Error("Não foi possível carregar o perfil");
      return r.json();
    });
    this.setSession(tokenData.access_token, me);
    return me;
  },

  logout() {
    const me = this.getUser();
    const path = this.loginPathFor(me?.perfil);
    this.clear();
    window.location.href = path;
  },

  homeFor(me) {
    if (me?.must_change_password || me?.user?.must_change_password) {
      return "/pages/change-password.html";
    }
    if (me?.perfil === "aluno") return "/pages/aluno.html";
    return "/pages/dashboard.html";
  },
};

window.Auth = Auth;
