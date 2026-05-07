// Staff panel JS

const STATUS_OPTIONS = ["active","assigned","work_in_progress","completed","paused","cancelled"];

function badge(v) {
  const map = {
    admin:"badge-admin", staff:"badge-staff", client:"badge-client",
    active:"badge-active", assigned:"badge-staff", work_in_progress:"badge-staff",
    completed:"badge-completed", pending:"badge-pending",
    failed:"badge-failed", in_progress:"badge-staff", paused:"badge-paused", cancelled:"badge-paused"
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
    `<span class="badge ${m.member_role==='staff'?'badge-staff':'badge-client'}">${m.name}</span>`
  ).join(" ");
}

function fmtDate(s) { return s ? new Date(s + "Z").toLocaleDateString() : "—"; }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }
function openModal(id)  { document.getElementById(id).classList.add("open"); }

let _currentProjectId = null;

async function loadStaffDashboard() {
  const projects = await API.get("/api/staff/projects").catch(() => []);
  document.getElementById("st-projects").textContent = projects.length;
  document.getElementById("st-pending").textContent = "—";

  const tbody = document.getElementById("projects-tbody");
  if (!projects.length) { tbody.innerHTML = '<tr><td colspan="5" class="text-muted">No projects assigned.</td></tr>'; return; }
  tbody.innerHTML = projects.map(p => `
    <tr>
      <td>${p.title}</td>
      <td>${p.client_name || "—"}</td>
      <td>${badge(p.status)}</td>
      <td>${fmtDate(p.created_at)}</td>
      <td><a href="/staff/projects" class="btn btn-secondary btn-sm">View</a></td>
    </tr>
  `).join("");
}

async function loadStaffProjects() {
  const projects = await API.get("/api/staff/projects").catch(() => []);
  const tbody = document.getElementById("projects-tbody");
  if (!projects.length) { tbody.innerHTML = '<tr><td colspan="5" class="text-muted">No projects.</td></tr>'; return; }
  tbody.innerHTML = projects.map(p => `
    <tr>
      <td>${p.title}</td>
      <td>${p.client_name || "—"}</td>
      <td class="members-cell">${memberBadges(p.members)}</td>
      <td>${statusSelect(p.id, p.status)}</td>
      <td><button class="btn btn-secondary btn-sm" onclick="loadRequests(${p.id}, '${p.title.replace(/'/g,"\\'")}')">Requests</button></td>
    </tr>
  `).join("");
}

async function updateProjectStatus(pid, status) {
  try {
    await API.patch(`/api/staff/projects/${pid}/status`, { status });
  } catch (err) {
    alert("Failed to update status: " + err.message);
    loadStaffProjects();
  }
}

async function loadRequests(projectId, title) {
  _currentProjectId = projectId;
  document.getElementById("req-project-title").textContent = title;
  document.getElementById("projects-view").classList.add("hidden");
  document.getElementById("requests-view").classList.remove("hidden");

  const requests = await API.get(`/api/staff/projects/${projectId}/requests`).catch(() => []);
  const tbody = document.getElementById("requests-tbody");
  if (!requests.length) { tbody.innerHTML = '<tr><td colspan="5" class="text-muted">No requests.</td></tr>'; return; }
  tbody.innerHTML = requests.map(r => `
    <tr>
      <td>#${r.id}</td>
      <td>${badge(r.type)}</td>
      <td class="text-muted" style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${r.prompt || "—"}</td>
      <td>${badge(r.status)}</td>
      <td><button class="btn btn-secondary btn-sm" onclick="openUpdateReq(${r.id}, '${r.status}', ${JSON.stringify(r.output_text || "").replace(/</g,"&lt;")})">Update</button></td>
    </tr>
  `).join("");
}

function showProjects() {
  document.getElementById("requests-view").classList.add("hidden");
  document.getElementById("projects-view").classList.remove("hidden");
}

function openUpdateReq(id, status, output) {
  const form = document.getElementById("update-req-form");
  form.querySelector('[name="id"]').value = id;
  form.querySelector('[name="status"]').value = status;
  form.querySelector('[name="output_text"]').value = output || "";
  openModal("update-req-modal");
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("update-req-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await API.patch(`/api/staff/requests/${fd.get("id")}`, {
        status: fd.get("status"),
        output_text: fd.get("output_text"),
      });
      closeModal("update-req-modal");
      if (_currentProjectId) loadRequests(_currentProjectId, document.getElementById("req-project-title").textContent);
    } catch (err) {
      alert(err.message);
    }
  });
});
