// Admin panel JS

const STATUS_OPTIONS = ["active","assigned","work_in_progress","completed","paused","cancelled"];

function badge(v) {
  const map = {
    admin:"badge-admin", staff:"badge-staff", client:"badge-client",
    active:"badge-active", inactive:"badge-paused",
    assigned:"badge-staff", work_in_progress:"badge-staff",
    completed:"badge-completed", pending:"badge-pending",
    failed:"badge-failed", paused:"badge-paused", cancelled:"badge-paused"
  };
  return `<span class="badge ${map[v]||''}">${v.replace(/_/g," ")}</span>`;
}

function statusSelect(pid, current) {
  const opts = STATUS_OPTIONS.map(s =>
    `<option value="${s}" ${s===current?"selected":""}>${s.replace(/_/g," ")}</option>`
  ).join("");
  return `<select class="form-select" style="font-size:0.8rem;padding:4px 8px;" onchange="updateProjectStatus(${pid},this.value)">${opts}</select>`;
}

function memberBadges(members) {
  if (!members || !members.length) return '<span class="text-muted">—</span>';
  return members.map(m =>
    `<span class="badge ${m.member_role==='staff'?'badge-staff':'badge-client'}" title="${m.email}">${m.name}</span>`
  ).join(" ");
}

function fmtDate(s) {
  if (!s) return "—";
  return new Date(s + "Z").toLocaleDateString();
}

function closeModal(id) { document.getElementById(id).classList.remove("open"); }
function openModal(id)  { document.getElementById(id).classList.add("open"); }

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

function openEditUser(id) {
  const u = _users.find(x => x.id === id);
  if (!u) return;
  const form = document.getElementById("edit-user-form");
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
let _allUsers = [];

async function loadProjects() {
  const [projects, users] = await Promise.all([
    API.get("/api/admin/projects").catch(() => []),
    API.get("/api/admin/users").catch(() => []),
  ]);
  _allUsers = users;

  const tbody = document.getElementById("projects-tbody");
  if (tbody) {
    if (!projects.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-muted">No projects.</td></tr>';
    } else {
      tbody.innerHTML = projects.map(p => `
        <tr>
          <td><strong>${p.title}</strong>${p.description ? `<br><small class="text-muted">${p.description}</small>` : ""}</td>
          <td>${p.client_name || "—"}</td>
          <td class="members-cell">${memberBadges(p.members)}</td>
          <td>${statusSelect(p.id, p.status)}</td>
          <td>${fmtDate(p.created_at)}</td>
          <td class="flex-gap">
            <button class="btn btn-secondary btn-sm" onclick="openMembersModal(${p.id})">Members</button>
            <button class="btn btn-danger btn-sm" onclick="deleteProject(${p.id})">Delete</button>
          </td>
        </tr>
      `).join("");
    }
  }

  // Populate create-modal selects
  const clientSel = document.getElementById("client-select");
  const staffSel  = document.getElementById("staff-select");
  if (clientSel) {
    const clients = users.filter(u => u.role === "client");
    clientSel.innerHTML = '<option value="">Select client…</option>' +
      clients.map(u => `<option value="${u.id}">${u.name}</option>`).join("");
  }
  if (staffSel) {
    const staff = users.filter(u => u.role === "staff" || u.role === "admin");
    staffSel.innerHTML = staff.map(u => `<option value="${u.id}">${u.name}</option>`).join("");
  }

  // Populate add-member select
  const addSel = document.getElementById("add-member-user");
  if (addSel) {
    addSel.innerHTML = '<option value="">Select user…</option>' +
      users.map(u => `<option value="${u.id}">${u.name} (${u.role})</option>`).join("");
  }
}

async function updateProjectStatus(pid, status) {
  try {
    await API.patch(`/api/admin/projects/${pid}`, { status });
  } catch (err) {
    alert("Failed to update status: " + err.message);
    loadProjects();
  }
}

function openCreateProject() {
  document.getElementById("create-project-form").reset();
  document.getElementById("create-project-error").style.display = "none";
  openModal("create-project-modal");
  loadProjects();
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

// ── Members Modal ──────────────────────────────────────────────────────
let _membersProjectId = null;

async function openMembersModal(pid) {
  _membersProjectId = pid;
  document.getElementById("members-project-id").value = pid;
  await refreshMembersList(pid);
  openModal("members-modal");
}

async function refreshMembersList(pid) {
  const projects = await API.get("/api/admin/projects").catch(() => []);
  const p = projects.find(x => x.id === pid);
  const members = p ? (p.members || []) : [];
  const el = document.getElementById("members-list");
  if (!members.length) {
    el.innerHTML = '<span class="text-muted">No members yet.</span>';
    return;
  }
  el.innerHTML = members.map(m => `
    <div class="flex-between" style="padding:6px 0; border-bottom:1px solid var(--border);">
      <span>${m.name} <span class="badge ${m.member_role==='staff'?'badge-staff':'badge-client'}">${m.member_role}</span></span>
      <button class="btn btn-danger btn-sm" onclick="removeMember(${pid},${m.id})">Remove</button>
    </div>
  `).join("");
}

async function addMember() {
  const uid  = parseInt(document.getElementById("add-member-user").value);
  const role = document.getElementById("add-member-role").value;
  if (!uid) return alert("Select a user first.");
  try {
    await API.post(`/api/admin/projects/${_membersProjectId}/members`, { user_id: uid, role });
    await refreshMembersList(_membersProjectId);
    loadProjects();
  } catch (err) {
    alert(err.message);
  }
}

async function removeMember(pid, uid) {
  try {
    await API.delete(`/api/admin/projects/${pid}/members/${uid}`);
    await refreshMembersList(pid);
    loadProjects();
  } catch (err) {
    alert(err.message);
  }
}

// ── Event listeners ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("create-user-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const errEl = document.getElementById("create-user-error");
    try {
      await API.post("/api/admin/users", Object.fromEntries(fd));
      closeModal("create-user-modal");
      loadUsers();
    } catch (err) {
      errEl.textContent = err.message;
      errEl.style.display = "block";
    }
  });

  document.getElementById("edit-user-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
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

  document.getElementById("create-project-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const staffSel = document.getElementById("staff-select");
    const selectedStaff = staffSel
      ? Array.from(staffSel.selectedOptions).map(o => ({ user_id: parseInt(o.value), role: "staff" }))
      : [];
    const body = {
      title: fd.get("title"),
      description: fd.get("description"),
      client_id: parseInt(fd.get("client_id")),
      member_ids: selectedStaff,
    };
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
});
