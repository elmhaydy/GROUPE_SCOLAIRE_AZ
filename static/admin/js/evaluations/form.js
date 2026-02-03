/* static/admin/js/evaluations/form.js */
/* AZ — Cascade: Niveau -> (Groupes + Matières) ; Groupe -> Enseignants */

(function () {
  "use strict";

  const CFG = window.AZ_EVAL || {};
  const URL_GROUPES = CFG.URL_GROUPES || "";
  const URL_ENS = CFG.URL_ENS || "";
  const URL_MAT = CFG.URL_MAT || "";
  const ANNEE_ID = String(CFG.ANNEE_ID || "").trim();

  const $ = (sel, root = document) => root.querySelector(sel);

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function getJSON(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error("AJAX error");
    return await res.json();
  }

  function buildUrl(base, params) {
    const u = new URL(base, window.location.origin);
    Object.entries(params || {}).forEach(([k, v]) => {
      const val = String(v ?? "").trim();
      if (val) u.searchParams.set(k, val);
    });
    return u.toString();
  }

  // ✅ init TomSelect sans casser les <option> déjà présents
  function initTomKeepOptions(selectEl) {
    if (!selectEl) return null;
    if (selectEl.tomselect) return selectEl.tomselect;

    return new TomSelect(selectEl, {
      create: false,
      allowEmptyOption: true,
      plugins: ["clear_button"],
      valueField: "value",
      labelField: "text",
      searchField: ["text"],
      maxOptions: 400,
      closeAfterSelect: true,
      render: {
        option: (data) => `<div>${escapeHtml(data.text)}</div>`,
        item: (data) => `<div>${escapeHtml(data.text)}</div>`,
      },
    });
  }

  function tsLock(ts, placeholder) {
    if (!ts) return;
    ts.clear(true);
    ts.clearOptions();
    ts.addOption({ value: "", text: placeholder });
    ts.refreshOptions(false);
    ts.disable();
  }

  function tsFill(ts, items, placeholder, selectedValue = "") {
    if (!ts) return;

    ts.clearOptions();
    ts.addOption({ value: "", text: placeholder });

    (items || []).forEach((it) => {
      ts.addOption({
        value: String(it.id),
        text: String(it.label ?? it.nom ?? it.text ?? ""),
      });
    });

    ts.refreshOptions(false);
    ts.enable();

    if (selectedValue) ts.setValue(String(selectedValue), true);
    else ts.clear(true);
  }

  // DOM
  const niveauUI = $("#id_niveau_ui");
  const groupeEl = $("#id_groupe");
  const ensEl = $("#id_enseignant");
  const matEl = $("#id_matiere");

  if (!niveauUI || !groupeEl || !ensEl || !matEl) return;

  // ✅ Niveau: on garde ses options Django
  const tsNiveau = initTomKeepOptions(niveauUI);

  // ✅ Autres: on gère par AJAX
  const tsGroupe = initTomKeepOptions(groupeEl);
  const tsEns = initTomKeepOptions(ensEl);
  const tsMat = initTomKeepOptions(matEl);

  // Lock initial
  tsLock(tsGroupe, "— Sélectionner un groupe —");
  tsLock(tsEns, "— Sélectionner un enseignant —");
  tsLock(tsMat, "— Sélectionner une matière —");

  // Load groupes by niveau
  async function loadGroupesByNiveau() {
    const niveauId = String(tsNiveau.getValue() || "").trim();

    tsLock(tsGroupe, "Chargement des groupes...");
    tsLock(tsEns, "— Sélectionner un enseignant —");

    if (!niveauId) {
      tsLock(tsGroupe, "— Sélectionner un groupe —");
      return;
    }

    const url = buildUrl(URL_GROUPES, { annee: ANNEE_ID, niveau: niveauId });
    try {
      const data = await getJSON(url);
      tsFill(tsGroupe, data.results || [], "— Sélectionner un groupe —");
    } catch (e) {
      console.error("loadGroupesByNiveau", e);
      tsLock(tsGroupe, "Erreur chargement groupes");
    }
  }

  // Load matières by niveau (comme tu as demandé)
  async function loadMatieresByNiveau() {
    const niveauId = String(tsNiveau.getValue() || "").trim();

    tsLock(tsMat, "Chargement des matières...");
    if (!niveauId) {
      tsLock(tsMat, "— Sélectionner une matière —");
      return;
    }

    const url = buildUrl(URL_MAT, { niveau: niveauId });
    try {
      const data = await getJSON(url);
      tsFill(tsMat, data.results || [], "— Sélectionner une matière —");
    } catch (e) {
      console.error("loadMatieresByNiveau", e);
      tsLock(tsMat, "Erreur chargement matières");
    }
  }

  // Load enseignants by groupe
  async function loadEnseignantsByGroupe() {
    const groupeId = String(tsGroupe.getValue() || "").trim();

    tsLock(tsEns, "Chargement des enseignants...");
    if (!groupeId) {
      tsLock(tsEns, "— Sélectionner un enseignant —");
      return;
    }

    const url = buildUrl(URL_ENS, { annee: ANNEE_ID, groupe: groupeId });
    try {
      const data = await getJSON(url);
      tsFill(tsEns, data.results || [], "— Sélectionner un enseignant —");
    } catch (e) {
      console.error("loadEnseignantsByGroupe", e);
      tsLock(tsEns, "Erreur chargement enseignants");
    }
  }

  // EVENTS
  tsNiveau.on("change", async () => {
    // Niveau change => recharge groupes + matières
    await loadGroupesByNiveau();
    await loadMatieresByNiveau();
  });

  tsGroupe.on("change", async () => {
    // Groupe change => recharge enseignants
    await loadEnseignantsByGroupe();
  });

  // INIT si niveau déjà sélectionné (retour erreur form)
  (async function init() {
    const niveauInit = String(tsNiveau.getValue() || "").trim();
    if (niveauInit) {
      await loadGroupesByNiveau();
      await loadMatieresByNiveau();
    }
  })();
})();
