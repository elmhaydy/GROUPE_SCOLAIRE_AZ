/* static/admin/js/impaye.js */
/* AZ — Impayés mensuels (Admin) */

(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);

  function debounce(fn, wait = 450) {
    let t = null;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function setSelectLoading(selectEl, on, text = "Chargement...") {
    if (!selectEl) return;
    selectEl.disabled = !!on;
    selectEl.classList.toggle("is-loading", !!on);
    if (on) selectEl.innerHTML = `<option value="">${escapeHtml(text)}</option>`;
  }

  function fillGroupes(selectEl, items, selectedValue = "") {
    if (!selectEl) return;
    const opts = [`<option value="">Tous</option>`];

    (items || []).forEach((g) => {
      const id = String(g.id);
      const label = escapeHtml(g.label ?? "");
      const sel = String(selectedValue) === id ? "selected" : "";
      opts.push(`<option value="${id}" ${sel}>${label}</option>`);
    });

    selectEl.innerHTML = opts.join("");
  }

  function buildParamsFromForm(formEl) {
    const params = {};
    const fd = new FormData(formEl);
    for (const [k, v] of fd.entries()) params[k] = String(v ?? "").trim();

    if (!params.type) params.type = "ALL";

    // Auto mois => supprimer "mois"
    if (!params.mois) delete params.mois;

    // Nettoyage URL
    if (!params.q) delete params.q;
    if (!params.niveau) delete params.niveau;
    if (!params.groupe) delete params.groupe;
    if (!params.periode) delete params.periode;

    return params;
  }

  function toQueryString(params) {
    const usp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v === null || v === undefined) return;
      const val = String(v).trim();
      if (!val) return;
      usp.set(k, val);
    });
    return usp.toString();
  }

  function navigate(params) {
    const base = window.location.pathname;
    const qs = toQueryString(params);
    window.location.href = qs ? `${base}?${qs}` : base;
  }

  // DOM
  const form = $(".az-filter-form");
  if (!form) return;

  const inputQ = $('input[name="q"]', form);
  const selectAnnee = $("#id_annee", form);
  const selectMois = $("#id_mois", form);
  const selectNiveau = $("#id_niveau", form);
  const selectGroupe = $("#id_groupe", form);

  // ⚠️ adapte selon ton urls.py
  const ENDPOINT_GROUPES = "/ajax/groupes/"; // ou "/core/ajax/groupes/"

  async function fetchGroupes({ anneeId, niveauId }) {
    const url = new URL(ENDPOINT_GROUPES, window.location.origin);
    if (anneeId) url.searchParams.set("annee", anneeId);
    if (niveauId) url.searchParams.set("niveau", niveauId);

    const res = await fetch(url.toString(), {
      method: "GET",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });

    if (!res.ok) throw new Error("Erreur AJAX groupes");
    return await res.json(); // {"results":[...]}
  }

  async function refreshGroupes({ keepSelected = true } = {}) {
    if (!selectGroupe) return;

    const anneeId = selectAnnee ? selectAnnee.value : "";
    const niveauId = selectNiveau ? selectNiveau.value : "";
    const selectedBefore = keepSelected ? selectGroupe.value : "";

    try {
      setSelectLoading(selectGroupe, true, "Chargement des groupes...");
      const data = await fetchGroupes({ anneeId, niveauId });
      const results = data.results || [];
      fillGroupes(selectGroupe, results, selectedBefore);
      setSelectLoading(selectGroupe, false);
      selectGroupe.disabled = false;
      selectGroupe.classList.remove("is-loading");
    } catch (err) {
      console.error(err);
      fillGroupes(selectGroupe, [], "");
      setSelectLoading(selectGroupe, false);
      selectGroupe.disabled = false;
      selectGroupe.classList.remove("is-loading");
    }
  }

  const smartSubmit = debounce(() => {
    const params = buildParamsFromForm(form);
    navigate(params);
  }, 450);

  if (inputQ) inputQ.addEventListener("input", () => smartSubmit());
  if (selectMois) selectMois.addEventListener("change", () => smartSubmit());
  if (selectGroupe) selectGroupe.addEventListener("change", () => smartSubmit());

  if (selectAnnee) {
    selectAnnee.addEventListener("change", async () => {
      await refreshGroupes({ keepSelected: false });
      smartSubmit();
    });
  }

  if (selectNiveau) {
    selectNiveau.addEventListener("change", async () => {
      await refreshGroupes({ keepSelected: false });
      smartSubmit();
    });
  }

  (async function init() {
    if (selectGroupe) await refreshGroupes({ keepSelected: true });
  })();
})();
