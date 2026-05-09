document.getElementById("rp-new").addEventListener("input", function () {
  const el = document.getElementById("rp-strength");
  const v = this.value;
  if (!v) { el.innerHTML = ""; return; }
  const s = scorePassword(v);
  const labels = ["", "Weak", "Weak", "Fair", "Good", "Strong"];
  const cls    = ["", "weak", "weak", "fair", "good", "strong"];
  el.innerHTML = `<span class="${cls[s]}">${labels[s]}</span>`;
});

const token = new URLSearchParams(location.search).get("token");
if (!token) {
  document.getElementById("rp-form-wrap").classList.add("hidden");
  document.getElementById("rp-invalid").classList.remove("hidden");
}

document.getElementById("rp-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("rp-error");
  const spinner = document.getElementById("rp-spinner");
  const btnText = document.getElementById("rp-btn-text");
  errEl.style.display = "none";

  const newPw = document.getElementById("rp-new").value;
  const conf  = document.getElementById("rp-conf").value;
  if (newPw !== conf) {
    errEl.textContent = "Passwords do not match.";
    errEl.style.display = "block";
    return;
  }

  spinner.classList.remove("hidden");
  btnText.textContent = "Saving…";
  e.target.querySelector("button").disabled = true;

  try {
    await fetch("/api/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPw }),
    }).then(async r => {
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Reset failed");
      return d;
    });

    document.getElementById("rp-form-wrap").classList.add("hidden");
    document.getElementById("rp-success").classList.remove("hidden");
    setTimeout(() => { window.location.href = "/login"; }, 2000);
  } catch (err) {
    if (err.message.includes("Invalid") || err.message.includes("expired")) {
      document.getElementById("rp-form-wrap").classList.add("hidden");
      document.getElementById("rp-invalid").classList.remove("hidden");
    } else {
      errEl.textContent = err.message || "Failed to reset password.";
      errEl.style.display = "block";
    }
    spinner.classList.add("hidden");
    btnText.textContent = "Set New Password";
    e.target.querySelector("button").disabled = false;
  }
});
