document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");
  const errEl = document.getElementById("login-error");
  const btnText = document.getElementById("btn-text");
  const btnSpinner = document.getElementById("btn-spinner");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errEl.style.display = "none";
    btnText.textContent = "Signing in…";
    btnSpinner.classList.remove("hidden");

    const email = form.email.value.trim();
    const password = form.password.value;

    try {
      const data = await API.post("/api/auth/login", { email, password });
      API.setToken(data.token);
      // Route by role
      const role = data.user.role;
      if (role === "admin") window.location.href = "/admin/dashboard";
      else if (role === "staff") window.location.href = "/staff/dashboard";
      else window.location.href = "/client/dashboard";
    } catch (err) {
      errEl.textContent = err.message || "Login failed";
      errEl.style.display = "block";
      btnText.textContent = "Sign In";
      btnSpinner.classList.add("hidden");
    }
  });
});

async function logout() {
  await API.post("/api/auth/logout", {}).catch(() => {});
  API.setToken(null);
  window.location.href = "/login";
}
