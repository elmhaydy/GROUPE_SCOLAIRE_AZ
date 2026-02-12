/* static/admin/js/matieres/form.js */
/* AZ • Matières — Form (FINAL) */

(function () {
  "use strict";

  function initTomSelect(id, placeholder) {
    const el = document.getElementById(id);
    if (!el || el.tomselect) return null;

    return new TomSelect(el, {
      plugins: ["remove_button"],
      maxOptions: 5000,
      hideSelected: true,
      closeAfterSelect: false,
      persist: false,
      create: false,
      placeholder: placeholder || "Rechercher...",
      render: {
        no_results: function () {
          return `<div class="no-results">Aucun résultat</div>`;
        },
      },
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    // Multi-select Niveaux + Enseignants
    initTomSelect("id_niveaux", "Rechercher un niveau…");
    
  });
})();
