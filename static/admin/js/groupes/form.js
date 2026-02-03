/* admin/js/groupes/form.js
   AZ — Groupes (Form)
   - Anim "saving" sur le bouton
   - Validation front légère (obligatoires)
   - Affiche les erreurs sous chaque champ (data-error-for)
   NOTE: ne remplace pas la validation Django, juste UX.
*/
(function () {
  const form = document.querySelector(".az-groupe-form");
  if (!form) return;

  const saveBtn = document.getElementById("saveBtn");

  // Helpers
  const $fieldWrap = (el) => el?.closest(".az-field");
  const setError = (name, msg) => {
    const err = form.querySelector(`[data-error-for="${name}"]`);
    const input = form.querySelector(`[name="${CSS.escape(name)}"]`);
    const wrap = $fieldWrap(input);

    if (wrap) wrap.classList.toggle("is-invalid", !!msg);
    if (err) err.textContent = msg || "";
  };

  const clearAllErrors = () => {
    ["annee", "niveau", "nom", "capacite"].forEach((n) => setError(n, ""));
  };

  const getVal = (name) => {
    const el = form.querySelector(`[name="${CSS.escape(name)}"]`);
    return (el?.value || "").trim();
  };

  // 1) Live clear errors on input/change
  ["annee", "niveau", "nom", "capacite"].forEach((name) => {
    const el = form.querySelector(`[name="${CSS.escape(name)}"]`);
    if (!el) return;

    const evt = el.tagName === "SELECT" ? "change" : "input";
    el.addEventListener(evt, () => setError(name, ""));
  });

  // 2) Submit validation + animation
  form.addEventListener("submit", (e) => {
    clearAllErrors();

    const annee = getVal("annee");
    const niveau = getVal("niveau");
    const nom = getVal("nom");
    const capacite = getVal("capacite");

    let ok = true;

    if (!annee) { setError("annee", "Année obligatoire."); ok = false; }
    if (!niveau) { setError("niveau", "Niveau obligatoire."); ok = false; }
    if (!nom) { setError("nom", "Nom du groupe obligatoire."); ok = false; }

    // capacité: si renseignée => nombre >= 0
    if (capacite) {
      const n = Number(capacite);
      if (!Number.isFinite(n) || n < 0) {
        setError("capacite", "Capacité invalide (nombre ≥ 0).");
        ok = false;
      }
    }

    if (!ok) {
      e.preventDefault();
      // focus premier champ invalide
      const firstInvalid = form.querySelector(".az-field.is-invalid input, .az-field.is-invalid select, .az-field.is-invalid textarea");
      firstInvalid?.focus();
      return;
    }

    // animation saving
    if (saveBtn) {
      saveBtn.classList.add("is-loading");
      saveBtn.setAttribute("aria-busy", "true");
    }
  });

  // 3) Petit confort: Enter sur input nom => submit
  const nomInput = form.querySelector('[name="nom"]');
  if (nomInput) {
    nomInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        // laisser submit normal, mais évite saut de ligne si textarea
        if (nomInput.tagName !== "TEXTAREA") {
          // ok
        }
      }
    });
  }
})();
