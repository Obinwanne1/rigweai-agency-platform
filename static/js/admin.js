// Admin panel JS

function badge(role) {
  const map = { admin: "badge-admin", staff: "badge-staff", client: "badge-client",
                active: "badge-active", inactive: "badge-paused",
                completed: "badge-completed", pending: "badge-pending",
                failed: "badge-failed", paused: "badge-paused" };
  return `<span class="badge ${map[role] || ''}">${role}</span>`;
}

function fmtDate(s) {
  if (!s) return "—";
  return new Date(s + "Z").toLocaleDateString();
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

function openModal(id) {
  document.getElementById(id).classList.add("open");
}

// ── Dashboard ──────────────────────────────────────────────────────────
async function loadDashboard() {
  const [stats, requests] = await Promise.all([
    API.get("/api/admin/stats").catch(() => ({})),
    API.get("/api/admin/requests").catch(() => []),
  ]);

  document.getElementById("st-users").textContent = stats.users ?? "—";
  document.getElementById("st-clients").textContent = stats.clients ?? "—";
  document.getElementById("st-staff").textContent = stats.staff ?? "—";
  document.getElementById("st-projects").textContent = stats.projects ?? "—";
  document.getElementById("st-requests").textContent = stats.requests ?? "—";
  document.getElementById("st-pending").textContent = stats.pending_requests ?? "—";

  const tbody = document.getElementById("req-tbody");
  if (!requests.length) { tbody.innerHTML = '<tr><td colspan="5" class="text-muted">No requests yet.</td></tr>'; return; }
  tbody.innerHTML = requests.slice(0, 20).map(r => `
    <tr>
      <td>#${r.id}</td>
      <td>${r.client_name || "—"}</td>
      <td>${badge(r.type)}</td>
      <td>${badge(r.status)}</td>
      <td>${fmtDate(r.created_at)}</td>
    </tr>
  `).join("");
}

// ── Users ──────────────────────────────────────────────────────────────
let _users = [];

async function loadUsers() {
  const users = await API.get("/api/admin/users").catch(() => []);
  _users = users;
  const tbody = document.getElementById("users-tbody");
  if (!users.length) { tbody.innerHTML = '<tr><td colspan="6" class="text-muted">No users.</td></tr>'; return; }
  tbody.innerHTML = users.map(u => `
    <tr>
      <td>${u.name}</td>
      <td>${u.email}</td>
      <td>${badge(u.role)}</td>
      <td>${badge(u.is_active ? "active" : "inactive")}</td>
      <td>${fmtDate(u.created_at)}</td>
      <td class="flex-gap">
        <button class="btn btn-secondary btn-sm" onclick="openEditUser(${u.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})">Delete</button>
      </td>
    </tr>
  `).join("");
}

function openCreateUser() {
  document.getElementById("create-user-form").reset();
  document.getElementById("create-user-error").style.display = "none";
  openModal("create-user-modal");
}

document.addEventListener("DOMContentLoaded", () => {
  const createForm = document.getElementById("create-user-form");
  if (createForm) {
    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(createForm);
      const body = Object.fromEntries(fd);
      const errEl = document.getElementById("create-user-error");
      try {
        await API.post("/api/admin/users", body);
        closeModal("create-user-modal");
        loadUsers();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.style.display = "block";
      }
    });
  }

  const editForm = document.getElementById("edit-user-form");
  if (editForm) {
    editForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(editForm);
      const id = fd.get("id");
      const body = { name: fd.get("name"), role: fd.get("role"), is_active: fd.get("is_active") === "1" };
      if (fd.get("password")) body.password = fd.get("password");
      const errEl = document.getElementById("edit-user-error");
      try {
        await API.patch(`/api/admin/users/${id}`, body);
        closeModal("edit-user-modal");
        loadUsers();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.style.display = "block";
      }
    });
  }

  const createProjectForm = document.getElementById("create-project-form");
  if (createProjectForm) {
    createProjectForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(createProjectForm);
      const body = { title: fd.get("title"), description: fd.get("description"), client_id: parseInt(fd.get("client_id")), staff_id: fd.get("staff_id") ? parseInt(fd.get("staff_id")) : null };
      const errEl = document.getElementById("create-project-error");
      try {
        await API.post("/api/admin/projects", body);
        closeModal("create-project-modal");
        loadProjects();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.style.display = "block";
      }
    });
  }
});

function openEditUser(id) {
  const u = _users.find(x => x.id === id);
  if (!u) return;
  const form = document.getElementById("edit-user-form");
  form.id_field = id;
  form.querySelector('[name="id"]').value = id;
  form.querySelector('[name="name"]').value = u.name;
  form.querySelector('[name="role"]').value = u.role;
  form.querySelector('[name="is_active"]').value = u.is_active ? "1" : "0";
  form.querySelector('[name="password"]').value = "";
  document.getElementById("edit-user-error").style.display = "none";
  openModal("edit-user-modal");
}

async function deleteUser(id) {
  if (!confirm("Delete this user? This cannot be undone.")) return;
  try {
    await API.delete(`/api/admin/users/${id}`);
    loadUsers();
  } catch (err) {
    alert(err.message);
  }
}

// ── Projects ───────────────────────────────────────────────────────────
async function loadProjects() {
  const [projects, users] = await Promise.all([
    API.get("/api/admin/projects").catch(() => []),
    API.get("/api/admin/users").catch(() => []),
  ]);

  const tbody = document.getElementById("projects-tbody");
  if (tbody) {
    if (!projects.length) { tbody.innerHTML = '<tr><td colspan="6" class="text-muted">No projects.</td></tr>'; }
    else {
      tbody.innerHTML = projects.map(p => `
        <tr>
          <td>${p.title}</td>
          <td>${p.client_name || "—"}</td>
          <td>${p.staff_name || "Unassigned"}</td>
          <td>${badge(p.status)}</td>
          <td>${fmtDate(p.created_at)}</td>
          <td class="flex-gap">
            <button class="btn btn-danger btn-sm" onclick="deleteProject(${p.id})">Delete</button>
          </td>
        </tr>
      `).join("");
    }
  }

  // Populate selects
  const clientSel = document.getElementById("client-select");
  const staffSel = document.getElementById("staff-select");
  if (clientSel && staffSel) {
    const clients = users.filter(u => u.role === "client");
    const staff = users.filter(u => u.role === "staff" || u.role === "admin");
    clientSel.innerHTML = '<option value="">Select client…</option>' + clients.map(u => `<option value="${u.id}">${u.name}</option>`).join("");
    staffSel.innerHTML = '<option value="">Unassigned</option>' + staff.map(u => `<option value="${u.id}">${u.name}</option>`).join("");
  }
}

function openCreateProject() {
  document.getElementById("create-project-form").reset();
  document.getElementById("create-project-error").style.display = "none";
  openModal("create-project-modal");
  loadProjects(); // refresh selects
}

async function deleteProject(id) {
  if (!confirm("Delete this project?")) return;
  try {
    await API.delete(`/api/admin/projects/${id}`);
    loadProjects();
  } catch (err) {
    alert(err.message);
  }
}
