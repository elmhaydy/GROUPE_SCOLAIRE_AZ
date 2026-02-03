/* =========================================================
   AZ — Matières (FORM) — Tom Select init
   - auto sur tous les selects du formulaire
   ========================================================= */
(function(){
  const root = document.querySelector(".az-matiere-form");
  if (!root) return;

  const selects = root.querySelectorAll("select");
  selects.forEach((sel) => {
    // évite double init
    if (sel.dataset.ts === "1") return;
    sel.dataset.ts = "1";

    const isMultiple = sel.hasAttribute("multiple");

    new TomSelect(sel, {
      create: false,
      allowEmptyOption: true,
      plugins: isMultiple ? ["remove_button", "clear_button"] : ["clear_button"],
      maxOptions: 500,
      hideSelected: true,
      closeAfterSelect: !isMultiple,
      placeholder: sel.getAttribute("data-placeholder") || "Sélectionner…",
      render: {
        no_results: () => `<div class="no-results">Aucun résultat</div>`,
      },
    });
  });
})();
