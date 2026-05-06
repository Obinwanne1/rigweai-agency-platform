// ── Content Generator ──────────────────────────────────────────────────
async function generate() {
  const prompt = document.getElementById("prompt").value.trim();
  const context = document.getElementById("context").value.trim();
  const errEl = document.getElementById("gen-error");
  const output = document.getElementById("output");
  const btn = document.getElementById("gen-btn");
  const spinner = document.getElementById("gen-spinner");
  const btnText = document.getElementById("gen-btn-text");

  if (!prompt) { errEl.textContent = "Please enter a prompt."; errEl.style.display = "block"; return; }
  errEl.style.display = "none";
  btn.disabled = true;
  spinner.classList.remove("hidden");
  btnText.textContent = "Generating…";
  output.textContent = "Working on it…";

  try {
    const data = await API.post("/api/ai/generate", { prompt, context });
    output.textContent = data.output;
    document.getElementById("copy-btn").style.display = "inline-flex";
  } catch (err) {
    errEl.textContent = err.message || "Generation failed.";
    errEl.style.display = "block";
    output.textContent = "Generation failed. Please try again.";
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
    btnText.textContent = "Generate Content";
  }
}

function copyOutput() {
  const text = document.getElementById("output").textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("copy-btn");
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = "Copy"; }, 2000);
  });
}

// ── Chat ──────────────────────────────────────────────────────────────
let _conversationId = null;

async function loadChatPage() {
  const convs = await API.get("/api/client/conversations").catch(() => []);
  renderConvList(convs);
}

function renderConvList(convs) {
  const el = document.getElementById("conv-list");
  if (!el) return;
  if (!convs.length) { el.innerHTML = '<div class="text-muted">No previous chats.</div>'; return; }
  el.innerHTML = convs.map(c => `
    <button class="btn btn-secondary btn-sm" style="text-align:left; justify-content:flex-start;" onclick="loadConversation(${c.id})">
      ${c.title || "Conversation " + c.id}
      <span class="text-muted" style="margin-left:auto; font-size:0.75rem;">${new Date(c.updated_at + "Z").toLocaleDateString()}</span>
    </button>
  `).join("");
}

async function loadConversation(id) {
  // just set ID; history is server-side
  _conversationId = id;
  const msgs = document.getElementById("chat-messages");
  msgs.innerHTML = '<div class="chat-msg assistant">Conversation loaded. Continue chatting below.</div>';
}

function newConversation() {
  _conversationId = null;
  document.getElementById("chat-messages").innerHTML =
    '<div class="chat-msg assistant">Hello! I\'m the RigweAI assistant. How can I help you today?</div>';
  document.getElementById("chat-input").focus();
}

function chatKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

async function sendMessage() {
  const input = document.getElementById("chat-input");
  const msg = input.value.trim();
  if (!msg) return;

  const msgs = document.getElementById("chat-messages");
  const errEl = document.getElementById("chat-error");
  errEl.style.display = "none";

  appendMsg(msgs, "user", msg);
  input.value = "";

  const btn = document.getElementById("chat-send");
  const spinner = document.getElementById("chat-spinner");
  const btnText = document.getElementById("chat-btn-text");
  btn.disabled = true;
  spinner.classList.remove("hidden");
  btnText.textContent = "…";

  const typing = appendMsg(msgs, "assistant", "Thinking…");

  try {
    const data = await API.post("/api/ai/chat", { message: msg, conversation_id: _conversationId });
    _conversationId = data.conversation_id;
    typing.textContent = data.reply;
    // refresh conv list
    const convs = await API.get("/api/client/conversations").catch(() => []);
    renderConvList(convs);
  } catch (err) {
    typing.remove();
    errEl.textContent = err.message || "Chat failed.";
    errEl.style.display = "block";
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
    btnText.textContent = "Send";
  }
}

function appendMsg(container, role, text) {
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

// ── File Processor ─────────────────────────────────────────────────────
let _selectedFile = null;

function initFileProcessor() {
  const dropZone = document.getElementById("drop-zone");
  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) setFile(file);
  });
}

function fileSelected(input) {
  if (input.files[0]) setFile(input.files[0]);
}

function setFile(file) {
  _selectedFile = file;
  const info = document.getElementById("file-info");
  info.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  info.style.display = "block";
  document.getElementById("process-btn").disabled = false;
}

async function processFile() {
  if (!_selectedFile) return;
  const instruction = document.getElementById("instruction").value.trim();
  const errEl = document.getElementById("file-error");
  const output = document.getElementById("file-output");
  const btn = document.getElementById("process-btn");
  const spinner = document.getElementById("process-spinner");
  const btnText = document.getElementById("process-btn-text");

  errEl.style.display = "none";
  btn.disabled = true;
  spinner.classList.remove("hidden");
  btnText.textContent = "Processing…";
  output.textContent = "Analyzing your file…";

  const fd = new FormData();
  fd.append("file", _selectedFile);
  fd.append("instruction", instruction);

  try {
    const data = await API.upload("/api/ai/process-file", fd);
    output.textContent = data.output;
    document.getElementById("copy-file-btn").style.display = "inline-flex";
  } catch (err) {
    errEl.textContent = err.message || "Processing failed.";
    errEl.style.display = "block";
    output.textContent = "Processing failed. Please try again.";
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
    btnText.textContent = "Process File";
  }
}

function copyFileOutput() {
  const text = document.getElementById("file-output").textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("copy-file-btn");
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = "Copy"; }, 2000);
  });
}
