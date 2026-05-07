// Client panel JS

const STATUS_OPTIONS = ["active","assigned","work_in_progress","completed","paused","cancelled"];

function badge(v) {
  const map = {
    content:"badge-staff", chat:"badge-admin", file:"badge-client",
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
  if (!members || !members.length) return '<span class="text-muted">Unassigned</span>';
  const staff = members.filter(m => m.member_role === "staff");
  if (!staff.length) return '<span class="text-muted">Unassigned</span>';
  return staff.map(m => `<span class="badge badge-staff">${m.name}</span>`).join(" ");
}

function fmtDate(s) { return s ? new Date(s + "Z").toLocaleDateString() : "—"; }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }

async function loadClientDashboard() {
  const [projects, requests] = await Promise.all([
    API.get("/api/client/projects").catch(() => []),
    API.get("/api/client/requests").catch(() => []),
  ]);

  const ptbody = document.getElementById("projects-tbody");
  if (!projects.length) {
    ptbody.innerHTML = '<tr><td colspan="4" class="text-muted">No projects yet. Contact your account manager.</td></tr>';
  } else {
    ptbody.innerHTML = projects.map(p => `
      <tr>
        <td>${p.title}${p.description ? `<br><small class="text-muted">${p.description}</small>` : ""}</td>
        <td>${memberBadges(p.members)}</td>
        <td>${statusSelect(p.id, p.status)}</td>
        <td>${fmtDate(p.created_at)}</td>
      </tr>
    `).join("");
  }

  const rtbody = document.getElementById("requests-tbody");
  if (!requests.length) {
    rtbody.innerHTML = '<tr><td colspan="5" class="text-muted">No requests yet.</td></tr>';
  } else {
    rtbody.innerHTML = requests.map(r => `
      <tr>
        <td>${badge(r.type)}</td>
        <td class="text-muted" style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${r.prompt || "—"}</td>
        <td>${badge(r.status)}</td>
        <td>${fmtDate(r.created_at)}</td>
        <td>${r.output_text ? `<button class="btn btn-secondary btn-sm" onclick="showOutput(${JSON.stringify(r.output_text)})">View</button>` : "—"}</td>
      </tr>
    `).join("");
  }
}

async function updateProjectStatus(pid, status) {
  try {
    await API.patch(`/api/client/projects/${pid}/status`, { status });
  } catch (err) {
    alert("Failed to update status: " + err.message);
    loadClientDashboard();
  }
}

function showOutput(text) {
  document.getElementById("output-text").textContent = text;
  document.getElementById("output-modal").classList.add("open");
}

function copyOutput() {
  const text = document.getElementById("output-text").textContent;
  navigator.clipboard.writeText(text).then(() => alert("Copied!")).catch(() => {});
}
