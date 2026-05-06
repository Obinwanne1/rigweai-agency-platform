function badge(v) {
  const map = { content:"badge-staff",chat:"badge-admin",file:"badge-client",
    completed:"badge-completed",pending:"badge-pending",failed:"badge-failed",in_progress:"badge-staff" };
  return `<span class="badge ${map[v]||''}">${v.replace("_"," ")}</span>`;
}

function fmtDate(s) { return s ? new Date(s + "Z").toLocaleDateString() : "—"; }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }

async function loadClientDashboard() {
  const [projects, requests] = await Promise.all([
    API.get("/api/client/projects").catch(() => []),
    API.get("/api/client/requests").catch(() => []),
  ]);

  const ptbody = document.getElementById("projects-tbody");
  if (!projects.length) ptbody.innerHTML = '<tr><td colspan="4" class="text-muted">No projects yet. Contact your account manager.</td></tr>';
  else ptbody.innerHTML = projects.map(p => `
    <tr>
      <td>${p.title}</td>
      <td>${p.staff_name || "Unassigned"}</td>
      <td><span class="badge badge-${p.status === 'active' ? 'active' : 'paused'}">${p.status}</span></td>
      <td>${fmtDate(p.created_at)}</td>
    </tr>
  `).join("");

  const rtbody = document.getElementById("requests-tbody");
  if (!requests.length) rtbody.innerHTML = '<tr><td colspan="5" class="text-muted">No requests yet.</td></tr>';
  else rtbody.innerHTML = requests.map(r => `
    <tr>
      <td>${badge(r.type)}</td>
      <td class="text-muted" style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${r.prompt || "—"}</td>
      <td>${badge(r.status)}</td>
      <td>${fmtDate(r.created_at)}</td>
      <td>${r.output_text ? `<button class="btn btn-secondary btn-sm" onclick="showOutput(${JSON.stringify(r.output_text)})">View</button>` : "—"}</td>
    </tr>
  `).join("");
}

function showOutput(text) {
  document.getElementById("output-text").textContent = text;
  document.getElementById("output-modal").classList.add("open");
}

function copyOutput() {
  const text = document.getElementById("output-text").textContent;
  navigator.clipboard.writeText(text).then(() => alert("Copied!")).catch(() => {});
}
