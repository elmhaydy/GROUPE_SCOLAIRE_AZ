/* =========================================================
   AZ — Parents form.js (FINAL + TOM)
   - Ajout ligne formset (template empty_form) ✅
   - TOTAL_FORMS auto (prefix dynamique) ✅
   - TomSelect sur select élève (lignes existantes + nouvelles) ✅
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  const addBtn = document.getElementById("addRowBtn");
  const rows = document.getElementById("rows");
  const tpl = document.getElementById("emptyFormTpl");

  // TOTAL_FORMS : on le trouve quel que soit le prefix
  const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');

  if (!addBtn || !rows || !tpl || !totalForms) {
    console.error("[AZ Parents] Elements manquants:", { addBtn, rows, tpl, totalForms });
    return;
  }

  // prefix dynamique ex: "parenteleve_set"
  const prefix = totalForms.name.replace("-TOTAL_FORMS", "");

  // --- TOM SELECT helpers ---
  function initTomOnSelect(selectEl) {
    if (!selectEl) return;
    if (typeof TomSelect === "undefined") return;

    // éviter double init
    if (selectEl.tomselect) return;

    new TomSelect(selectEl, {
      create: false,
      maxItems: 1,
      allowEmptyOption: true,
      placeholder: "Choisir un élève…",
      searchField: ["text"],
      closeAfterSelect: true,
    });
  }

  function initTomOnAllRows() {
    rows.querySelectorAll('select[name$="-eleve"]').forEach((sel) => {
      initTomOnSelect(sel);
    });
  }

  // init tom sur lignes déjà affichées
  initTomOnAllRows();

  function getTemplateHTML() {
    // template.content (normal)
    if (tpl.content && tpl.content.firstElementChild) {
      const wrap = document.createElement("div");
      wrap.appendChild(tpl.content.cloneNode(true));
      return wrap.innerHTML;
    }
    // fallback innerHTML
    return tpl.innerHTML;
  }

  function addRow() {
    const index = parseInt(totalForms.value || "0", 10);

    // clone template
    let html = getTemplateHTML();

    // remplacer __prefix__ par l'index
    html = html.replaceAll("__prefix__", String(index));

    const temp = document.createElement("div");
    temp.innerHTML = html.trim();

    const newRow = temp.firstElementChild;
    if (!newRow) {
      console.error("[AZ Parents] Template vide / invalide");
      return;
    }

    // reset champs
    newRow.querySelectorAll("input, select, textarea").forEach((el) => {
      if (el.tagName === "SELECT") el.selectedIndex = 0;
      else if (el.type === "checkbox") el.checked = false;
      else if (el.type !== "hidden") el.value = "";
    });

    // append
    rows.appendChild(newRow);

    // incrément total
    totalForms.value = index + 1;

    // init tom sur le nouveau select élève
    const eleveSelect = newRow.querySelector(`select[name="${prefix}-${index}-eleve"]`);
    initTomOnSelect(eleveSelect);
  }

  addBtn.addEventListener("click", (e) => {
    e.preventDefault();
    addRow();
  });
});
