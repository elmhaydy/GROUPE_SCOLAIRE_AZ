document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector(".az-prix-form");
  if (!form) return;

  const insc = form.querySelector('input[name="frais_inscription"]');
  const mens = form.querySelector('input[name="frais_scolarite_mensuel"]');
  const saveBtn = document.getElementById("saveBtn");

  function norm(el){
    const v = (el.value || "").trim().replace(",", ".");
    if (!v) return null;
    const n = Number(v);
    if (Number.isNaN(n) || n < 0) return NaN;
    return n;
  }

  function validateOne(el, label){
    const n = norm(el);
    if (n === null) { el.value = "0.00"; return true; } // vide => 0
    if (Number.isNaN(n)) {
      el.focus();
      alert(`Montant invalide pour "${label}". Exemple: 1500 ou 1500.00`);
      return false;
    }
    el.value = n.toFixed(2);
    return true;
  }

  if (insc) insc.focus();

  form.addEventListener("submit", function (e) {
    if (insc && !validateOne(insc, "Frais d'inscription")) { e.preventDefault(); return; }
    if (mens && !validateOne(mens, "Frais scolarité mensuel")) { e.preventDefault(); return; }

    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.style.opacity = "0.85";
      saveBtn.innerHTML = "⏳ Enregistrement...";
    }
  });
});
