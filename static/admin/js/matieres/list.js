(() => {
  const cfg = window.AZ_MAT || {};
  if (!cfg.autoSubmit) return;

  const degreEl = document.getElementById("id_degre");
  const niveauEl = document.getElementById("id_niveau");
  if (!degreEl || !niveauEl) return;

  function submitForm(el) {
    const form = el.closest("form");
    if (form) form.submit();
  }

  degreEl.addEventListener("change", () => submitForm(degreEl));
  niveauEl.addEventListener("change", () => submitForm(niveauEl));
})();
