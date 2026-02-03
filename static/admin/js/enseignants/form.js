(() => {
  const form = document.querySelector(".az-ens-form");
  const saveBtn = document.getElementById("saveBtn");
  if (!form) return;

  function fieldWrapByName(name){
    const input = form.querySelector(`[name="${name}"]`);
    if (!input) return null;
    return input.closest(".az-field");
  }

  function setError(name, msg){
    const wrap = fieldWrapByName(name);
    const box = form.querySelector(`.az-error[data-error-for="${name}"]`);
    if (wrap) wrap.classList.add("is-invalid");
    if (box){
      box.textContent = msg || "";
      box.style.display = msg ? "block" : "none";
    }
  }

  function clearError(name){
    const wrap = fieldWrapByName(name);
    const box = form.querySelector(`.az-error[data-error-for="${name}"]`);
    if (wrap) wrap.classList.remove("is-invalid");
    if (box){
      box.textContent = "";
      box.style.display = "none";
    }
  }

  function isValidEmail(v){
    // simple + safe
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  // Clear errors on input
  ["nom","prenom","telephone","email","specialite"].forEach(n => {
    const el = form.querySelector(`[name="${n}"]`);
    if (!el) return;
    el.addEventListener("input", () => clearError(n));
    el.addEventListener("change", () => clearError(n));
  });

  form.addEventListener("submit", (e) => {
    // front validation légère
    let ok = true;

    const nom = (form.querySelector('[name="nom"]')?.value || "").trim();
    const prenom = (form.querySelector('[name="prenom"]')?.value || "").trim();
    const email = (form.querySelector('[name="email"]')?.value || "").trim();

    // reset
    ["nom","prenom","email"].forEach(clearError);

    if (!nom){
      ok = false;
      setError("nom", "Le nom est obligatoire.");
    }
    if (!prenom){
      ok = false;
      setError("prenom", "Le prénom est obligatoire.");
    }
    if (email && !isValidEmail(email)){
      ok = false;
      setError("email", "Email invalide (ex: prof@ecole.ma).");
    }

    if (!ok){
      e.preventDefault();
      return;
    }

    // UX submit
    if (saveBtn){
      saveBtn.disabled = true;
      saveBtn.style.opacity = "0.85";
    }
  });
})();
