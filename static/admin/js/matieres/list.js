/* static/admin/js/matieres/list.js */
/* AZ • Matières — List (FINAL) */

(function () {
  "use strict";

  const cfg = window.AZ_MAT || {};
  const form = document.querySelector(".az-filter-form");
  const degreSel = document.getElementById("id_degre");
  const niveauSel = document.getElementById("id_niveau");

  if (!form || !degreSel || !niveauSel) return;

  // Sauver toutes les options niveaux (sauf la 1ère "— Tous —")
  const allNiveauOptions = Array.from(niveauSel.querySelectorAll("option")).map((opt) => ({
    value: opt.value,
    text: opt.textContent || "",
    isAll: opt.value === "",
    // on récupère le libellé degré à partir du texte "DEGRE / Niveau"
    degreLabel: (opt.textContent || "").split("/")[0].trim(),
    el: opt,
  }));

  function rebuildNiveauOptions(filterDegreLabel) {
    const current = niveauSel.value;

    // vide
    niveauSel.innerHTML = "";

    // Always keep "— Tous —"
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = "— Tous —";
    niveauSel.appendChild(optAll);

    // Remettre options filtrées
    const filtered = allNiveauOptions.filter((o) => {
      if (o.isAll) return false;
      if (!filterDegreLabel) return true; // pas de filtre => tous niveaux
      return o.degreLabel === filterDegreLabel;
    });

    for (const o of filtered) {
      const opt = document.createElement("option");
      opt.value = o.value;
      opt.textContent = o.text;
      niveauSel.appendChild(opt);
    }

    // Restaure sélection si possible
    const exists = Array.from(niveauSel.options).some((x) => x.value === current);
    niveauSel.value = exists ? current : "";
  }

  function autoSubmitIfEnabled() {
    if (cfg.autoSubmit) form.submit();
  }

  // Init filter (si un degré est déjà selected côté server)
  document.addEventListener("DOMContentLoaded", function () {
    const degreLabel = (degreSel.options[degreSel.selectedIndex]?.textContent || "").trim();
    const hasDegre = !!degreSel.value;

    rebuildNiveauOptions(hasDegre ? degreLabel : "");
  });

  // Change degré => refiltre niveaux + reset niveau + submit (optionnel)
  degreSel.addEventListener("change", function () {
    const degreLabel = (degreSel.options[degreSel.selectedIndex]?.textContent || "").trim();
    const hasDegre = !!degreSel.value;

    rebuildNiveauOptions(hasDegre ? degreLabel : "");
    // reset niveau selection when degre changes
    niveauSel.value = "";

    autoSubmitIfEnabled();
  });

  // Change niveau => submit (optionnel)
  niveauSel.addEventListener("change", function () {
    autoSubmitIfEnabled();
  });
})();
