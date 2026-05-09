(async () => {
  try {
    const user = await API.get("/api/auth/me");
    if (user.role === "admin") window.location.replace("/admin/dashboard");
    else if (user.role === "staff") window.location.replace("/staff/dashboard");
    else window.location.replace("/client/dashboard");
  } catch {
    window.location.replace("/login");
  }
})();
