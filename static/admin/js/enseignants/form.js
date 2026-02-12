/* static/admin/js/enseignants/form.js — FINAL (AZ) */
(() => {
  "use strict";
  if (window.__AZ_ENS_FORM__) return;
  window.__AZ_ENS_FORM__ = true;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // =========================================================
  // Photo preview
  // =========================================================
  const photoInput = $("#id_photo");
  const photoImg = $("#photoPreview");
  if (photoInput && photoImg) {
    photoInput.addEventListener("change", function () {
      const f = this.files && this.files[0];
      if (!f) return;
      photoImg.src = URL.createObjectURL(f);
      photoImg.style.display = "block";
    });
  }

  // =========================================================
  // API matières
  // =========================================================
  const apiUrlEl = $("#apiMatieresUrl");
  const API_URL = apiUrlEl ? String(apiUrlEl.value || "") : "";

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function setOptions(selectEl, items, placeholder, keepValue = "") {
    if (!selectEl) return;

    const cur = String(keepValue || selectEl.value || "");
    const opts = [];

    opts.push(`<option value="">${escapeHtml(placeholder || "— Choisir —")}</option>`);
    (items || []).forEach((it) => {
      opts.push(`<option value="${escapeHtml(it.id)}">${escapeHtml(it.label)}</option>`);
    });

    selectEl.innerHTML = opts.join("");

    if (cur && [...selectEl.options].some((o) => o.value === cur)) {
      selectEl.value = cur;
    } else {
      selectEl.value = "";
    }
  }

  function setLoading(selectEl, text = "Chargement...") {
    if (!selectEl) return;
    selectEl.disabled = true;
    selectEl.innerHTML = `<option value="">${escapeHtml(text)}</option>`;
  }

  function setEmptyDisabled(selectEl, text = "— Choisir un groupe —") {
    if (!selectEl) return;
    selectEl.disabled = true;
    selectEl.innerHTML = `<option value="">${escapeHtml(text)}</option>`;
  }

  async function fetchMatieres(groupeId) {
    if (!API_URL) return [];
    try {
      const url = new URL(API_URL, window.location.origin);
      url.searchParams.set("groupe_id", String(groupeId));

      const resp = await fetch(url.toString(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!resp.ok) return [];
      const data = await resp.json();
      return Array.isArray(data.results) ? data.results : [];
    } catch (e) {
      return [];
    }
  }

  function getRowElements(row) {
    const groupeSel = $('select[id$="-groupe"]', row);
    const matiereSel = $('select[id$="-matiere_fk"]', row);
    return { groupeSel, matiereSel };
  }

  async function refreshRowMatieres(row) {
    const { groupeSel, matiereSel } = getRowElements(row);
    if (!groupeSel || !matiereSel) return;

    const groupeId = String(groupeSel.value || "").trim();
    const current = String(matiereSel.value || "").trim();

    if (!groupeId) {
      setEmptyDisabled(matiereSel, "— Choisir un groupe —");
      return;
    }

    setLoading(matiereSel, "Chargement...");
    const items = await fetchMatieres(groupeId);

    if (!items.length) {
      setEmptyDisabled(matiereSel, "Aucune matière disponible");
      return;
    }

    // ⚠️ IMPORTANT: on évite de laisser disabled => sinon Django ne reçoit pas la valeur
    matiereSel.disabled = false;
    setOptions(matiereSel, items, "— Sélectionner une matière —", current);
  }

  function bindRow(row) {
    if (!row || row.__azBound) return;
    row.__azBound = true;

    const { groupeSel, matiereSel } = getRowElements(row);
    if (!groupeSel || !matiereSel) return;

    // init
    refreshRowMatieres(row);

    // change groupe => reload matières
    groupeSel.addEventListener("change", () => {
      setLoading(matiereSel, "Chargement...");
      refreshRowMatieres(row);
    });
  }

  function bindAllRows() {
    $$("#affRows .aff-row").forEach(bindRow);
  }

  // =========================================================
  // Add row (formset empty_form)
  // =========================================================
  const btnAdd = $("#btnAddAff");
  const rowsWrap = $("#affRows");
  const totalFormsEl = $("#id_aff-TOTAL_FORMS");
  const tpl = $("#affRowTpl");

  function addRow() {
    if (!rowsWrap || !totalFormsEl || !tpl) return;

    const index = parseInt(String(totalFormsEl.value || "0"), 10);
    const html = tpl.innerHTML.replaceAll("__prefix__", String(index));
    rowsWrap.insertAdjacentHTML("beforeend", html);
    totalFormsEl.value = String(index + 1);

    const newRow = $$("#affRows .aff-row").at(-1);
    if (newRow) bindRow(newRow);
  }

  if (btnAdd) btnAdd.addEventListener("click", addRow);

  // =========================================================
  // ✅ FIX CRITIQUE: au submit, ne jamais laisser un select disabled
  // (sinon Django ne reçoit pas la valeur => matiere_fk devient NULL => crash unique sans_matiere)
  // =========================================================
  const form = $(".az-ens-form");
  if (form) {
    form.addEventListener("submit", () => {
      // matières
      $$('#affRows select[id$="-matiere_fk"]').forEach((sel) => {
        if (sel.value) sel.disabled = false;
      });

      // groupe / année (au cas où)
      $$('#affRows select[id$="-groupe"], #affRows select[id$="-annee"]').forEach((sel) => {
        if (sel.value) sel.disabled = false;
      });
    });
  }

  // init
  bindAllRows();
})();
