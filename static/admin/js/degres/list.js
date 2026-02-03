(function () {
  "use strict";

  // Ici tu peux ajouter plus tard:
  // - ouverture modale delete (si ton modal system est global)
  // - recherche / filtre
  // Pour le moment : safe

  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-az-modal-open]");
    if (!btn) return;

    // Si tu as déjà un système global modal dans admin.js,
    // laisse ce fichier vide.
    // Sinon, tu peux l’implémenter ici.
  });
})();
