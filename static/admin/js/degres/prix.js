/* =========================================================
   AZ — Prix Degré (FORM) — Validation & UX
   - cible: form.az-form
   - input: name="frais_inscription"
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form.az-form");
  if (!form) return;

  const input = form.querySelector('input[name="frais_inscription"]');
  if (!input) return;

  // Crée une zone d'erreur si elle n'existe pas (sans changer ton thème)
  let err = form.querySelector('[data-error-for="frais_inscription"]');
  if (!err) {
    err = document.createElement("div");
    err.setAttribute("data-error-for", "frais_inscription");
    err.style.marginTop = "8px";
    err.style.fontWeight = "800";
    err.style.color = "var(--az-danger, #ef4444)";
    input.insertAdjacentElement("afterend", err);
  }

  const submitBtn = form.querySelector('button[type="submit"]');

  input.focus();

  function normalizeValue(v) {
    return (v || "").trim().replace(",", ".");
  }

  function validate() {
    const v = normalizeValue(input.value);
    err.textContent = "";

    if (!v) {
      err.textContent = "Le montant est obligatoire.";
      return false;
    }

    const n = Number(v);
    if (Number.isNaN(n) || n <= 0) {
      err.textContent = "Le montant doit être un nombre supérieur à 0.";
      return false;
    }

    // format 2 décimales
    input.value = n.toFixed(2);
    return true;
  }

  input.addEventListener("input", () => {
    // validation live sans forcer le format tant que l'utilisateur tape
    const v = normalizeValue(input.value);
    err.textContent = "";
    if (v && (Number.isNaN(Number(v)) || Number(v) <= 0)) {
      err.textContent = "Montant invalide.";
    }
  });

  form.addEventListener("submit", (e) => {
    if (!validate()) {
      e.preventDefault();
      input.focus();
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.style.opacity = "0.85";
      submitBtn.innerHTML = "⏳ Enregistrement...";
    }
  });
});
