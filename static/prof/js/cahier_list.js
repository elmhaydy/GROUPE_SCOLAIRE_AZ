(function () {
  const groupeEl = document.getElementById("id_groupe");
  const matiereEl = document.getElementById("id_matiere");
  const hintEl = document.getElementById("matiere_hint");

  if (!groupeEl || !matiereEl || !window.AZ_API?.matieres) return;

  function setHint(text) {
    if (!hintEl) return;
    hintEl.textContent = text || "";
  }

  function resetMatieres() {
    matiereEl.innerHTML = `<option value="">— Matière —</option>`;
  }

  async function loadMatieres(groupeId, keepSelectedId) {
    resetMatieres();

    if (!groupeId) {
      matiereEl.disabled = true;
      setHint("Choisis d’abord un groupe.");
      return;
    }

    matiereEl.disabled = true;
    setHint("Chargement des matières...");

    try {
      const url = `${window.AZ_API.matieres}?groupe=${encodeURIComponent(groupeId)}`;
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });

      if (!res.ok) {
        setHint("Impossible de charger les matières.");
        return;
      }

      const data = await res.json();
      const results = Array.isArray(data.results) ? data.results : [];

      for (const it of results) {
        const opt = document.createElement("option");
        opt.value = String(it.id);
        opt.textContent = it.label;
        if (keepSelectedId && String(it.id) === String(keepSelectedId)) {
          opt.selected = true;
        }
        matiereEl.appendChild(opt);
      }

      matiereEl.disabled = false;
      setHint(results.length ? "" : "Aucune matière pour ce groupe.");
    } catch (e) {
      setHint("Erreur réseau pendant le chargement.");
    } finally {
      if (groupeEl.value) matiereEl.disabled = false;
    }
  }

  // init (quand tu reviens sur la page avec des filtres déjà choisis)
  const initGroupe = window.AZ_SELECTED?.groupe || "";
  const initMatiere = window.AZ_SELECTED?.matiere || "";
  loadMatieres(initGroupe, initMatiere);

  // change groupe => reload matières + reset sélection
  groupeEl.addEventListener("change", () => {
    loadMatieres(groupeEl.value, "");
  });
})();
