/* =========================================================
   AZ — Niveaux (FORM) — admin/js/niveaux/form.js
   UX: focus, validation, anti double submit
   ========================================================= */

(function () {
  const form = document.querySelector(".az-niveau-form");
  if (!form) return;

  const degre = form.querySelector('select[name="degre"]');
  const nom = form.querySelector('input[name="nom"]');
  const ordre = form.querySelector('input[name="ordre"]');

  const errDegre = form.querySelector('[data-error-for="degre"]');
  const errNom = form.querySelector('[data-error-for="nom"]');
  const errOrdre = form.querySelector('[data-error-for="ordre"]');

  const saveBtn = document.getElementById("saveBtn");

  // Focus auto (si degre existe, sinon nom)
  if (degre) degre.focus();
  else if (nom) nom.focus();

  // Contraintes UI sur ordre
  if (ordre) {
    ordre.setAttribute("min", "1");
    ordre.setAttribute("step", "1");
    ordre.setAttribute("inputmode", "numeric");
  }

  function setError(input, zone, msg) {
    if (zone) zone.textContent = msg || "";
    if (!input) return;

    if (msg) {
      input.style.borderColor = "rgba(239,68,68,.55)";
      input.style.boxShadow = "0 0 0 4px rgba(239,68,68,.12)";
    } else {
      input.style.borderColor = "";
      input.style.boxShadow = "";
    }
  }

  function isEmptySelect(selectEl) {
    if (!selectEl) return false;
    const v = (selectEl.value || "").trim();
    return v === "" || v === "0" || v.toLowerCase() === "none";
  }

  function validate() {
    let ok = true;

    setError(degre, errDegre, "");
    setError(nom, errNom, "");
    setError(ordre, errOrdre, "");

    // Degré obligatoire (si select présent)
    if (degre && isEmptySelect(degre)) {
      ok = false;
      setError(degre, errDegre, "Le degré est obligatoire.");
    }

    const vNom = (nom?.value || "").trim();
    if (!vNom) {
      ok = false;
      setError(nom, errNom, "Le nom est obligatoire.");
    } else if (vNom.length < 2) {
      ok = false;
      setError(nom, errNom, "Le nom doit contenir au moins 2 caractères.");
    }

    const vOrdre = ordre?.value !== undefined ? Number(ordre.value) : NaN;
    if (Number.isNaN(vOrdre)) {
      ok = false;
      setError(ordre, errOrdre, "L’ordre est obligatoire.");
    } else if (vOrdre < 1) {
      ok = false;
      setError(ordre, errOrdre, "L’ordre doit être ≥ 1.");
    }

    return ok;
  }

  form.addEventListener("input", (e) => {
    const t = e.target;
    if (t === degre || t === nom || t === ordre) validate();
  });

  form.addEventListener("submit", (e) => {
    if (!validate()) {
      e.preventDefault();
      const firstBad = form.querySelector('select[style*="border-color"], input[style*="border-color"]');
      if (firstBad) firstBad.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.style.opacity = "0.85";
      saveBtn.innerHTML = "⏳ Enregistrement...";
    }
  });
})();
