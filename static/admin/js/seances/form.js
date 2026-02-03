/* =========================================================
   AZ — Seances Form (FINAL)
   - Groupe dépend de l'année (api_groupes_par_annee)
   - Enseignant dépend de (année + groupe) (api_enseignants)
   - Tom Select sur annee/groupe/enseignant
   - Mode update: conserve la sélection
   ========================================================= */

(function () {
  const anneeEl  = document.getElementById("id_annee");
  const groupeEl = document.getElementById("id_groupe");
  const ensEl    = document.getElementById("id_enseignant");

  if (!anneeEl || !groupeEl || !ensEl) return;

  const cfg = window.AZ_SEANCE || {};
  const apiGroupes = cfg.apiGroupes || "";
  const apiEnseignants = cfg.apiEnseignants || "";

  const selectedGroupeValue = (document.getElementById("selected_groupe_value")?.textContent || "").trim();
  const selectedEnsValue    = (document.getElementById("selected_enseignant_value")?.textContent || "").trim();

  // =========================
  // Tom Select init
  // =========================
  function makeTom(selectEl, placeholderText){
    if (!selectEl) return null;
    if (selectEl.tomselect) return selectEl.tomselect;

    return new TomSelect(selectEl, {
      create: false,
      allowEmptyOption: true,
      placeholder: placeholderText,
      maxOptions: 5000,
      searchField: ["text"],
      render: {
        no_results: function(){
          return '<div class="no-results">Aucun résultat</div>';
        }
      }
    });
  }

  const tomAnnee  = makeTom(anneeEl,  "Choisir une année…");
  const tomGroupe = makeTom(groupeEl, "Choisir un groupe…");
  const tomEns    = makeTom(ensEl,    "Choisir un enseignant…");

  // =========================
  // Helpers Tom refresh
  // =========================
  function setNativeOptions(selectEl, firstLabel, items, keepValue){
    selectEl.innerHTML = "";
    const first = document.createElement("option");
    first.value = "";
    first.textContent = firstLabel;
    selectEl.appendChild(first);

    (items || []).forEach(it => {
      const opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.label;
      if (keepValue && String(keepValue) === String(it.id)) opt.selected = true;
      selectEl.appendChild(opt);
    });
  }

  function syncTom(tom, items, keepValue){
    if (!tom) return;
    tom.clear(true);
    tom.clearOptions();

    if (items && items.length){
      tom.addOptions(items.map(x => ({ value: String(x.id), text: x.label })));
      tom.refreshOptions(false);
      if (keepValue) tom.setValue(String(keepValue), true);
    } else {
      tom.refreshOptions(false);
    }
  }

  // =========================
  // Load Groupes by Année
  // =========================
  async function loadGroupes(keepSelected){
    if (!apiGroupes){
      // fallback: ne casse pas
      return;
    }

    const anneeId = anneeEl.value;
    // reset groupes
    setNativeOptions(groupeEl, "— Choisir un groupe —", [], "");
    if (tomGroupe){
      tomGroupe.clear(true);
      tomGroupe.clearOptions();
      tomGroupe.sync();
    }

    // reset enseignants aussi
    setNativeOptions(ensEl, "— Choisir année + groupe —", [], "");
    if (tomEns){
      tomEns.clear(true);
      tomEns.clearOptions();
      tomEns.sync();
    }

    if (!anneeId) return;

    try{
      // API: /core/api/groupes/?annee_id=XX (ton url name: api_groupes_par_annee)
      const url = `${apiGroupes}?annee_id=${encodeURIComponent(anneeId)}`;
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });

      if (!res.ok){
        console.error("API groupes HTTP:", res.status, await res.text());
        return;
      }

      const data = await res.json();
      const rows = (data && data.results) ? data.results : [];

      // rows attendu: [{id, label}]
      const keep = keepSelected ? (selectedGroupeValue || groupeEl.value || "") : "";

      setNativeOptions(groupeEl, "— Choisir un groupe —", rows, keep);
      syncTom(tomGroupe, rows, keep);

      // si on a un groupe => charger enseignants
      if (keep) {
        groupeEl.value = String(keep);
        if (tomGroupe) tomGroupe.setValue(String(keep), true);
        await loadEnseignants(true);
      }

    }catch(e){
      console.error("Erreur fetch groupes:", e);
    }
  }

  // =========================
  // Load Enseignants by (Année + Groupe)
  // =========================
  async function loadEnseignants(keepSelected){
    if (!apiEnseignants){
      return;
    }

    const anneeId = anneeEl.value;
    const groupeId = groupeEl.value;

    if (!anneeId || !groupeId){
      setNativeOptions(ensEl, "— Choisir année + groupe —", [], "");
      syncTom(tomEns, [], "");
      return;
    }

    // loading label
    setNativeOptions(ensEl, "Chargement...", [], "");
    syncTom(tomEns, [], "");

    try{
      const url = `${apiEnseignants}?annee_id=${encodeURIComponent(anneeId)}&groupe_id=${encodeURIComponent(groupeId)}`;
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });

      if (!res.ok){
        console.error("API enseignants HTTP:", res.status, await res.text());
        setNativeOptions(ensEl, "Erreur chargement enseignants", [], "");
        syncTom(tomEns, [], "");
        return;
      }

      const data = await res.json();
      const rows = (data && data.results) ? data.results : [];

      if (!rows.length){
        setNativeOptions(ensEl, "Aucun enseignant affecté à ce groupe", [], "");
        syncTom(tomEns, [], "");
        return;
      }

      const currentChosen = (tomEns && tomEns.getValue()) || ensEl.value || "";
      const keep = keepSelected ? (selectedEnsValue || currentChosen || "") : "";

      setNativeOptions(ensEl, "— Choisir un enseignant —", rows, keep);
      syncTom(tomEns, rows, keep);

    }catch(e){
      console.error("Erreur fetch enseignants:", e);
      setNativeOptions(ensEl, "Erreur chargement enseignants", [], "");
      syncTom(tomEns, [], "");
    }
  }

  // =========================
  // Events
  // =========================
  anneeEl.addEventListener("change", function(){
    // quand année change => reload groupes (et reset enseignant)
    loadGroupes(false);
  });

  groupeEl.addEventListener("change", function(){
    loadEnseignants(false);
  });

  // =========================
  // Init (important update)
  // =========================
  document.addEventListener("DOMContentLoaded", function(){
    // 1) charger groupes selon année + reselect si update
    loadGroupes(true);
    // 2) si pas d'API groupes, on peut au moins charger enseignants
    // (au cas où ton form groupe est déjà filtré server-side)
    if (!apiGroupes) loadEnseignants(true);
  });

})();
