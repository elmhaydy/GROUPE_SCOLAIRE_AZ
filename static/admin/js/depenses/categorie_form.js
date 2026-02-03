// static/admin/js/depenses/categorie_form.js
(() => {
  // Auto-focus sur le champ nom
  const nom = document.querySelector('input[name="nom"]');
  if (nom) nom.focus();

  // Empêcher double submit (spams)
  const form = document.querySelector(".az-catf-form");
  if (!form) return;

  form.addEventListener("submit", () => {
    const btn = form.querySelector('button[type="submit"]');
    if (!btn) return;
    btn.disabled = true;
    btn.classList.add("az-btn-disabled");
  });
})();
