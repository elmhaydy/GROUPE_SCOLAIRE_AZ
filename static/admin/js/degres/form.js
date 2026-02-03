/* =========================================================
   AZ NEBULA — Degrés (form.js) — Validation & UX
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".az-degre-form");
  if (!form) return;

  const nom = form.querySelector('input[name="nom"], textarea[name="nom"]');
  const ordre = form.querySelector('input[name="ordre"]');
  const errNom = form.querySelector('[data-error-for="nom"]');
  const errOrdre = form.querySelector('[data-error-for="ordre"]');
  const saveBtn = document.getElementById("saveBtn");

  // Focus auto
  if (nom) nom.focus();

  function setErr(el, msg) {
    if (!el) return;
    el.textContent = msg || "";
  }

  function normalizeNom(v) {
    return (v || "").trim();
  }

  function normalizeOrdre(v) {
    return (v || "").trim().replace(",", ".");
  }

  function validateNom() {
    const v = normalizeNom(nom?.value);
    setErr(errNom, "");

    if (!v) {
      setErr(errNom, "Le nom est obligatoire.");
      return false;
    }
    if (v.length < 2) {
      setErr(errNom, "Le nom est trop court.");
      return false;
    }
    return true;
  }

  function validateOrdre() {
    const v = normalizeOrdre(ordre?.value);
    setErr(errOrdre, "");

    if (!v) {
      setErr(errOrdre, "L’ordre est obligatoire.");
      return false;
    }

    const n = Number(v);
    // ordre doit être un entier positif
    if (Number.isNaN(n) || !Number.isFinite(n)) {
      setErr(errOrdre, "L’ordre doit être un nombre valide.");
      return false;
    }
    if (n <= 0) {
      setErr(errOrdre, "L’ordre doit être supérieur à 0.");
      return false;
    }
    if (!Number.isInteger(n)) {
      setErr(errOrdre, "L’ordre doit être un nombre entier (ex: 1, 2, 3...).");
      return false;
    }

    ordre.value = String(n);
    return true;
  }

  function validateAll() {
    const ok1 = nom ? validateNom() : true;
    const ok2 = ordre ? validateOrdre() : true;
    return ok1 && ok2;
  }

  // Live validate
  if (nom) nom.addEventListener("input", validateNom);
  if (ordre) ordre.addEventListener("input", validateOrdre);

  form.addEventListener("submit", (e) => {
    if (!validateAll()) {
      e.preventDefault();
      // Focus premier champ en erreur
      if (errNom?.textContent && nom) nom.focus();
      else if (errOrdre?.textContent && ordre) ordre.focus();
      return;
    }

    // UX: disable bouton
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.style.opacity = "0.85";
      saveBtn.innerHTML = "⏳ Enregistrement...";
    }
  });
});
