/* =========================================================
   AZ — Inscriptions form.js
   - Charge les groupes selon l'année (API)
   - Restore groupe sélectionné en mode edit
   ========================================================= */

(function () {
  function qs(id){ return document.getElementById(id); }

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector(".az-insc-form");
    if (!form) return;

    const annee = qs("id_annee");
    const groupe = qs("id_groupe");
    if (!annee || !groupe) return;

    const apiUrl = form.getAttribute("data-api-url");
    const selectedEl = qs("selected_groupe_value");
    const selectedValue = selectedEl ? (selectedEl.textContent || "").trim() : "";

    function resetGroupes() {
      groupe.innerHTML = "";
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = "— Choisir un groupe —";
      groupe.appendChild(opt0);
    }

    async function loadGroupes(keepSelected) {
      const anneeId = annee.value;
      resetGroupes();
      if (!anneeId) return;

      try {
        const res = await fetch(`${apiUrl}?annee_id=${encodeURIComponent(anneeId)}`);
        if (!res.ok) throw new Error("API error: " + res.status);

        const data = await res.json();
        const items = data.results || [];

        items.forEach(item => {
          const opt = document.createElement("option");
          opt.value = item.id;
          opt.textContent = item.label;

          if (keepSelected && selectedValue && String(item.id) === String(selectedValue)) {
            opt.selected = true;
          }

          groupe.appendChild(opt);
        });

      } catch (e) {
        console.error("Erreur chargement groupes:", e);
      }
    }

    // 1) au chargement (utile en mode edit)
    loadGroupes(true);

    // 2) au changement d'année
    annee.addEventListener("change", () => loadGroupes(false));
  });
})();
