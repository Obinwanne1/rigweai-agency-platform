document.getElementById("new-pw").addEventListener("input", function() {
  const el = document.getElementById("pw-strength");
  const v = this.value;
  if (!v) { el.innerHTML = ""; return; }
  const s = scorePassword(v);
  const labels = ["", "Weak", "Weak", "Fair", "Good", "Strong"];
  const cls    = ["", "weak", "weak", "fair", "good", "strong"];
  el.innerHTML = `<span class="${cls[s]}">${labels[s]}</span>`;
});

if (new URLSearchParams(location.search).get("force") === "1") {
  document.getElementById("force-banner").classList.remove("hidden");
}

document.getElementById("change-pw-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const errEl = document.getElementById("pw-error");
  const successEl = document.getElementById("pw-success");
  const spinner = document.getElementById("pw-spinner");
  const btnText = document.getElementById("pw-btn-text");

  errEl.style.display = "none";
  successEl.style.display = "none";

  const newPw = form.new_password.value;
  const confirm = form.confirm_password.value;
  if (newPw !== confirm) {
    errEl.textContent = "New passwords do not match.";
    errEl.style.display = "block";
    return;
  }

  spinner.classList.remove("hidden");
  btnText.textContent = "Updating…";
  form.querySelector("button[type=submit]").disabled = true;

  try {
    await API.post("/api/auth/change-password", {
      current_password: form.current_password.value,
      new_password: newPw,
    });
    successEl.style.display = "block";
    form.reset();
    document.getElementById("pw-strength").innerHTML = "";
    document.getElementById("force-banner").classList.add("hidden");
    if (new URLSearchParams(location.search).get("force") === "1") {
      setTimeout(() => { window.location.href = "/dashboard"; }, 1500);
    }
  } catch (err) {
    errEl.textContent = err.message || "Failed to change password.";
    errEl.style.display = "block";
  } finally {
    spinner.classList.add("hidden");
    btnText.textContent = "Update Password";
    form.querySelector("button[type=submit]").disabled = false;
  }
});
