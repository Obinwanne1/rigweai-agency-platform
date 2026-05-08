// Fetch wrapper — attaches JWT from memory (httpOnly cookie is primary auth), handles 401
const API = {
  _token: null,

  setToken(token) {
    this._token = token;
  },

  getToken() {
    return this._token;
  },

  _headers(extra = {}) {
    const h = { "Content-Type": "application/json", ...extra };
    const tok = this.getToken();
    if (tok) h["Authorization"] = `Bearer ${tok}`;
    return h;
  },

  async request(method, path, body = null) {
    const opts = { method, headers: this._headers(), credentials: "include" };
    if (body !== null) opts.body = JSON.stringify(body);
    const resp = await fetch(path, opts);
    if (resp.status === 401) {
      this.setToken(null);
      window.location.href = "/login";
      return;
    }
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw Object.assign(new Error(data.error || "Request failed"), { status: resp.status, data });
    return data;
  },

  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  put(path, body) { return this.request("PUT", path, body); },
  patch(path, body) { return this.request("PATCH", path, body); },
  delete(path) { return this.request("DELETE", path); },

  async upload(path, formData) {
    const headers = {};
    const tok = this.getToken();
    if (tok) headers["Authorization"] = `Bearer ${tok}`;
    const resp = await fetch(path, { method: "POST", headers, body: formData, credentials: "include" });
    if (resp.status === 401) { this.setToken(null); window.location.href = "/login"; return; }
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw Object.assign(new Error(data.error || "Upload failed"), { status: resp.status });
    return data;
  },
};
