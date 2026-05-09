document.getElementById("fp-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("fp-error");
  const spinner = document.getElementById("fp-spinner");
  const btnText = document.getElementById("fp-btn-text");
  errEl.style.display = "none";

  spinner.classList.remove("hidden");
  btnText.textContent = "Sending…";
  e.target.querySelector("button").disabled = true;

  try {
    const res = await API.post("/api/auth/forgot-password", {
      email: document.getElementById("fp-email").value.trim(),
    });

    document.getElementById("fp-form-wrap").classList.add("hidden");

    if (res.message === "no_email") {
      const adminEl = document.getElementById("fp-admin-contact");
      adminEl.textContent = res.admin || "your administrator";
      document.getElementById("fp-no-email").classList.remove("hidden");
    } else {
      document.getElementById("fp-sent").classList.remove("hidden");
    }
  } catch (err) {
    errEl.textContent = err.message || "Something went wrong. Try again.";
    errEl.style.display = "block";
    spinner.classList.add("hidden");
    btnText.textContent = "Send Reset Link";
    e.target.querySelector("button").disabled = false;
  }
});
