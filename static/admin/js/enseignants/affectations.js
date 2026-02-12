/* admin/js/enseignants/affectations.js — FINAL
   - Groupe dépend de Année
   - Matière dépend de Groupe
   - Ciblage SAFE par name$ (évite ids dupliqués)
   - Supporte it.label OU it.nom
   - Restaure selectedGroupe/selectedMatiere une seule fois
*/

(() => {
  "use strict";
  if (window.__AZ_AFF__) return;
  window.__AZ_AFF__ = true;

  const form = document.querySelector(".az-aff-form");
  if (!form) return;

  // ✅ SAFE: name$=...
  const anneeEl  = form.querySelector('select[name$="annee"]');
  const groupeEl = form.querySelector('select[name$="groupe"]');
  const matEl    = form.querySelector('select[name$="matiere_fk"]');

  if (!anneeEl || !groupeEl || !matEl) return;

  const cfg = window.AZ_AFF || {};
  const URL_GROUPES  = String(cfg.urlGroupesParAnnee || "");
  const URL_MATIERES = String(cfg.urlMatieresParGroupe || "");

  let selectedGroupe  = String(cfg.selectedGroupe || "");
  let selectedMatiere = String(cfg.selectedMatiere || "");

  if (!URL_GROUPES || !URL_MATIERES) {
    console.warn("[AZ_AFF] URLs manquantes", { URL_GROUPES, URL_MATIERES });
    return;
  }

  async function fetchJSON(url) {
    try {
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) return { results: [] };
      return await res.json();
    } catch (e) {
      console.warn("[AZ_AFF] fetchJSON failed:", e);
      return { results: [] };
    }
  }

  function itemLabel(it) {
    // Supporte plusieurs formats possibles côté API
    return String(it?.label ?? it?.nom ?? it?.name ?? "");
  }

  function setOptions(select, items, placeholder, wanted = "") {
    const current = select.value;
    select.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder || "— Choisir —";
    select.appendChild(opt0);

    (items || []).forEach((it) => {
      const o = document.createElement("option");
      o.value = String(it.id);
      o.textContent = itemLabel(it) || `#${it.id}`;
      select.appendChild(o);
    });

    const w = String(wanted || current || "");
    if (w && [...select.options].some((o) => o.value === w)) select.value = w;
    else select.value = "";
  }

  function lockMatieres(text = "— Choisir un groupe —") {
    setOptions(matEl, [], text);
    matEl.disabled = true;
  }

  async function loadGroupes() {
    const anneeId = String(anneeEl.value || "");

    // reset
    setOptions(groupeEl, [], "Chargement...");
    lockMatieres("— Choisir un groupe —");

    if (!anneeId) {
      setOptions(groupeEl, [], "— Choisir —");
      return;
    }

    const data = await fetchJSON(URL_GROUPES + "?annee_id=" + encodeURIComponent(anneeId));
    const results = Array.isArray(data.results) ? data.results : [];

    setOptions(
      groupeEl,
      results,
      results.length ? "— Choisir —" : "Aucun groupe",
      selectedGroupe
    );

    // consommer 1 fois
    selectedGroupe = "";

    // si un groupe est sélectionné => charge matières
    await loadMatieres();
  }

  async function loadMatieres() {
    const gid = String(groupeEl.value || "");

    setOptions(matEl, [], "Chargement...");
    matEl.disabled = true;

    if (!gid) {
      lockMatieres("— Choisir un groupe —");
      return;
    }

    const data = await fetchJSON(URL_MATIERES + "?groupe_id=" + encodeURIComponent(gid));
    const results = Array.isArray(data.results) ? data.results : [];

    setOptions(
      matEl,
      results,
      results.length ? "— Sélectionner une matière —" : "Aucune matière",
      selectedMatiere
    );

    matEl.disabled = results.length === 0;

    // consommer 1 fois
    selectedMatiere = "";
  }

  anneeEl.addEventListener("change", loadGroupes);
  groupeEl.addEventListener("change", loadMatieres);

  // init
  loadGroupes();
})();
