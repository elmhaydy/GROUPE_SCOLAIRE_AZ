(function () {
  const form = document.getElementById("edtProfForm");
  const selAnnee = document.getElementById("id_annee");
  const selNiveau = document.getElementById("id_niveau");
  const selGroupe = document.getElementById("id_groupe");
  const selEns = document.getElementById("id_enseignant");

  if (!form || !selAnnee || !selNiveau || !selGroupe || !selEns) return;

  // ✅ auto-submit quand l’enseignant change (UX rapide)
  selEns.addEventListener("change", () => form.submit());

  // ✅ optionnel : submit aussi pour groupe
  selGroupe.addEventListener("change", () => form.submit());

  // ✅ année / niveau => submit (le backend recalcule listes, simple et fiable)
  selAnnee.addEventListener("change", () => {
    // reset cascade
    selNiveau.value = "";
    selGroupe.value = "";
    selEns.value = "";
    form.submit();
  });

  selNiveau.addEventListener("change", () => {
    selGroupe.value = "";
    selEns.value = "";
    form.submit();
  });
})();
