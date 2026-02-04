(function () {
  const dangerBtn = document.querySelector(".az-btn-danger");
  if (dangerBtn) dangerBtn.focus();

  // Optionnel: confirmation navigateur (si tu veux sécurité extra)
  const form = document.querySelector("form[data-az-modal-form]");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    // commente ces 3 lignes si tu ne veux pas de confirm
    const ok = confirm("Confirmer la suppression ? Cette action est irréversible.");
    if (!ok) e.preventDefault();
  });
})();
