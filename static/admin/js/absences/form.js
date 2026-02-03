/* =========================================================
   AZ — Absences Form (FINAL)
   - TomSelect Eleve + Seance
   - AJAX: eleves par (annee + groupe)
   - AJAX: seances par (annee + groupe + date)
   ========================================================= */

(function () {
  const cfg = window.AZ_ABS_FORM || {};
  const $ = (id) => document.getElementById(id);

  const elAnnee = $("id_annee");
  const elGroupe = $("id_groupe");
  const elEleve = $("id_eleve");
  const elDate = $("id_date");
  const elSeance = $("id_seance");

  if (!elAnnee || !elGroupe || !elEleve || !elDate || !elSeance) {
    console.warn("[AZ_ABS_FORM] éléments manquants");
    return;
  }
  if (!cfg.urlEleves || !cfg.urlSeances) {
    console.warn("[AZ_ABS_FORM] urls manquants");
    return;
  }

  // -----------------------------
  // Helpers
  // -----------------------------
  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.error || "http_error");
    return data;
  }

  function setNativeOptions(selectEl, items, placeholder) {
    const current = selectEl.value;
    selectEl.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder;
    selectEl.appendChild(opt0);

    (items || []).forEach((it) => {
      const opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.label;
      selectEl.appendChild(opt);
    });

    if ([...selectEl.options].some((o) => o.value === current)) selectEl.value = current;
    else selectEl.value = "";
  }

  // -----------------------------
  // TomSelect (Eleve, Seance)
  // -----------------------------
  const tsEleve = new TomSelect(elEleve, {
    create: false,
    persist: false,
    maxItems: 1,
    valueField: "id",
    labelField: "label",
    searchField: ["label"],
    placeholder: "— Choisir un élève —",
    preload: false,
    load: async (query, callback) => {
      // IMPORTANT: on charge seulement quand annee + groupe existent
      const anneeId = elAnnee.value;
      const groupeId = elGroupe.value;
      if (!anneeId || !groupeId) return callback([]);

      try {
        const url =
          `${cfg.urlEleves}?annee_id=${encodeURIComponent(anneeId)}` +
          `&groupe_id=${encodeURIComponent(groupeId)}` +
          `&q=${encodeURIComponent(query || "")}`;
        const data = await fetchJSON(url);
        callback(data.results || []);
      } catch (e) {
        console.error(e);
        callback([]);
      }
    },
    onFocus: function () {
      // au focus, si annee+groupe ok, on force un load (pour afficher la liste direct)
      const anneeId = elAnnee.value;
      const groupeId = elGroupe.value;
      if (anneeId && groupeId) this.load("");
    },
  });

  const tsSeance = new TomSelect(elSeance, {
    create: false,
    persist: false,
    maxItems: 1,
    valueField: "id",
    labelField: "label",
    searchField: ["label"],
    placeholder: "— Séance (option) —",
    preload: false,
    load: async (query, callback) => {
      const anneeId = elAnnee.value;
      const groupeId = elGroupe.value;
      const dateStr = elDate.value;
      if (!anneeId || !groupeId || !dateStr) return callback([]);

      try {
        // Ton endpoint api_seances_par_groupe_date attend: annee_id, groupe_id, date
        const url =
          `${cfg.urlSeances}?annee_id=${encodeURIComponent(anneeId)}` +
          `&groupe_id=${encodeURIComponent(groupeId)}` +
          `&date=${encodeURIComponent(dateStr)}`;
        const data = await fetchJSON(url);
        callback(data.results || []);
      } catch (e) {
        console.error(e);
        callback([]);
      }
    },
    onFocus: function () {
      const anneeId = elAnnee.value;
      const groupeId = elGroupe.value;
      const dateStr = elDate.value;
      if (anneeId && groupeId && dateStr) this.load("");
    },
  });

  // -----------------------------
  // Reload functions
  // -----------------------------
  function resetEleve() {
    tsEleve.clear(true);
    tsEleve.clearOptions();
    tsEleve.refreshOptions(false);
  }

  function resetSeance() {
    tsSeance.clear(true);
    tsSeance.clearOptions();
    tsSeance.refreshOptions(false);
  }

  function reloadEleves() {
    resetEleve();
    // si annee+groupe ok => load vide pour afficher liste
    if (elAnnee.value && elGroupe.value) tsEleve.load("");
  }

  function reloadSeances() {
    resetSeance();
    if (elAnnee.value && elGroupe.value && elDate.value) tsSeance.load("");
  }

  // -----------------------------
  // Events
  // -----------------------------
  elAnnee.addEventListener("change", () => {
    reloadEleves();
    reloadSeances();
  });

  elGroupe.addEventListener("change", () => {
    reloadEleves();
    reloadSeances();
  });

  elDate.addEventListener("change", () => {
    reloadSeances();
  });

  // -----------------------------
  // Preselect (update mode)
  // -----------------------------
  function preselectIfAny() {
    // Groupe déjà géré par Django (select normal)
    // Eleve / Seance => on injecte l’option si valeur déjà existante
    if (cfg.selectedEleve) {
      tsEleve.addOption({ id: String(cfg.selectedEleve), label: "Élève sélectionné" });
      tsEleve.setValue(String(cfg.selectedEleve), true);
    }
    if (cfg.selectedSeance) {
      tsSeance.addOption({ id: String(cfg.selectedSeance), label: "Séance sélectionnée" });
      tsSeance.setValue(String(cfg.selectedSeance), true);
    }
  }

  // Init: si annee+groupe déjà choisis -> charger
  if (elAnnee.value && elGroupe.value) reloadEleves();
  if (elAnnee.value && elGroupe.value && elDate.value) reloadSeances();

  preselectIfAny();
})();
