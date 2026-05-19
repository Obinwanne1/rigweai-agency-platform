(async () => {
  try {
    const user = await API.get("/api/auth/me");
    document.getElementById("nav-user-name").textContent = user.name;
    document.getElementById("nav-user-role").textContent = user.role;
    const avatarEl = document.getElementById("nav-user-avatar");
    if (avatarEl) avatarEl.textContent = user.name ? user.name.charAt(0).toUpperCase() : "?";

    const path = window.location.pathname;
    const a = (href) => `class="nav-link${path === href ? ' active' : ''}"`;

    const nav = document.getElementById("sidebar-nav");
    if (user.role === "admin") {
      nav.innerHTML = `
        <span class="nav-section">Admin</span>
        <a href="/admin/dashboard" ${a('/admin/dashboard')}><span class="icon">◼</span> Dashboard</a>
        <a href="/admin/users" ${a('/admin/users')}><span class="icon">👥</span> Users</a>
        <a href="/admin/projects" ${a('/admin/projects')}><span class="icon">📁</span> Projects</a>
        <span class="nav-section">Tools</span>
        <a href="/client/content-gen" ${a('/client/content-gen')}><span class="icon">✏️</span> Content Gen</a>
        <a href="/client/chat" ${a('/client/chat')}><span class="icon">💬</span> Chat</a>
        <a href="/client/file-processor" ${a('/client/file-processor')}><span class="icon">📄</span> File Processor</a>`;
    } else if (user.role === "staff") {
      nav.innerHTML = `
        <span class="nav-section">Staff</span>
        <a href="/staff/dashboard" ${a('/staff/dashboard')}><span class="icon">◼</span> Dashboard</a>
        <a href="/staff/projects" ${a('/staff/projects')}><span class="icon">📁</span> Projects</a>
        <span class="nav-section">Tools</span>
        <a href="/client/content-gen" ${a('/client/content-gen')}><span class="icon">✏️</span> Content Gen</a>
        <a href="/client/chat" ${a('/client/chat')}><span class="icon">💬</span> Chat</a>
        <a href="/client/file-processor" ${a('/client/file-processor')}><span class="icon">📄</span> File Processor</a>`;
    }
    // client role: leave template sidebar as-is
  } catch {}
})();
