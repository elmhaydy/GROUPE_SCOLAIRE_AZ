(function () {
  const root = document.querySelector(".azsms");
  if (!root) return;

  // Django widgets
  const cibleType = document.getElementById("id_cible_type");
  const messageEl = document.getElementById("id_message");

  // Targets
  const wrapDegre = document.getElementById("wrap-degre");
  const wrapNiveau = document.getElementById("wrap-niveau");
  const wrapGroupe = document.getElementById("wrap-groupe");
  const wrapEleve = document.getElementById("wrap-eleve");

  const degreSelect = document.getElementById("degre_select");
  const niveauSelect = document.getElementById("niveau_select");
  const groupeSelect = document.getElementById("groupe_select");
  const eleveSelect = document.getElementById("eleve_select");

  // Counters + preview
  const smsCount = document.getElementById("smsCount");
  const smsParts = document.getElementById("smsParts");
  const smsCount2 = document.getElementById("smsCount2");
  const smsParts2 = document.getElementById("smsParts2");
  const smsPreview = document.getElementById("smsPreview");

  // Endpoints
  const URL_NIVEAUX = window.AZ_SMS?.urlNiveaux || "";
  const URL_GROUPES = window.AZ_SMS?.urlGroupes || "";
  const URL_ELEVES  = window.AZ_SMS?.urlEleves || "";

  function hideAllTargets() {
    if (wrapDegre) wrapDegre.style.display = "none";
    if (wrapNiveau) wrapNiveau.style.display = "none";
    if (wrapGroupe) wrapGroupe.style.display = "none";
    if (wrapEleve) wrapEleve.style.display = "none";
  }

  function resetSelect(sel, placeholder = "— Choisir —") {
    if (!sel) return;
    sel.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    sel.appendChild(opt);
    sel.value = "";
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    return await res.json();
  }

  async function loadNiveaux(degreId) {
    resetSelect(niveauSelect);
    resetSelect(groupeSelect);
    resetSelect(eleveSelect);

    niveauSelect.disabled = true;
    groupeSelect.disabled = true;
    eleveSelect.disabled = true;

    if (!degreId) return;

    const data = await fetchJSON(URL_NIVEAUX + "?degre_id=" + encodeURIComponent(degreId));
    const items = data.results || data || [];

    items.forEach(it => {
      const o = document.createElement("option");
      o.value = it.id;
      o.textContent = it.nom || it.label || ("Niveau #" + it.id);
      niveauSelect.appendChild(o);
    });

    niveauSelect.disabled = false;
  }

  async function loadGroupes(niveauId) {
    resetSelect(groupeSelect);
    resetSelect(eleveSelect);

    groupeSelect.disabled = true;
    eleveSelect.disabled = true;

    if (!niveauId) return;

    const data = await fetchJSON(URL_GROUPES + "?niveau_id=" + encodeURIComponent(niveauId));
    const items = data.results || data || [];

    items.forEach(it => {
      const o = document.createElement("option");
      o.value = it.id;
      o.textContent = it.nom || it.label || ("Groupe #" + it.id);
      groupeSelect.appendChild(o);
    });

    groupeSelect.disabled = false;
  }

  async function loadEleves(groupeId) {
    resetSelect(eleveSelect);
    eleveSelect.disabled = true;

    if (!groupeId) return;

    const data = await fetchJSON(URL_ELEVES + "?groupe_id=" + encodeURIComponent(groupeId));
    const items = data.results || [];

    items.forEach(it => {
      const o = document.createElement("option");
      o.value = it.id;
      o.textContent = it.label || (it.nom ? it.nom : ("Élève #" + it.id));
      eleveSelect.appendChild(o);
    });

    eleveSelect.disabled = false;
  }

  function applyCiblageUI() {
    const t = (cibleType?.value || "").trim();
    hideAllTargets();

    // disable chain by default
    if (niveauSelect) niveauSelect.disabled = true;
    if (groupeSelect) groupeSelect.disabled = true;
    if (eleveSelect) eleveSelect.disabled = true;

    // clear downstream to avoid sending garbage
    resetSelect(niveauSelect);
    resetSelect(groupeSelect);
    resetSelect(eleveSelect);

    if (t === "TOUS" || t === "") return;

    // Always show degre to start chain (your rule)
    if (wrapDegre) wrapDegre.style.display = "";

    if (t === "DEGRE") return;

    if (t === "NIVEAU") {
      if (wrapNiveau) wrapNiveau.style.display = "";
      // enable niveau only after degre selected
      return;
    }

    if (t === "GROUPE") {
      if (wrapNiveau) wrapNiveau.style.display = "";
      if (wrapGroupe) wrapGroupe.style.display = "";
      return;
    }

    if (t === "ELEVE") {
      if (wrapNiveau) wrapNiveau.style.display = "";
      if (wrapGroupe) wrapGroupe.style.display = "";
      if (wrapEleve) wrapEleve.style.display = "";
      return;
    }
  }

  // SMS counter (simple GSM-like)
  function updateSmsStats() {
    const text = (messageEl?.value || "");
    const len = text.length;
    const parts = Math.max(1, Math.ceil(len / 160));

    if (smsCount) smsCount.textContent = String(len);
    if (smsParts) smsParts.textContent = String(parts);
    if (smsCount2) smsCount2.textContent = String(len);
    if (smsParts2) smsParts2.textContent = String(parts);

    if (smsPreview) smsPreview.textContent = text.trim() ? text : "Ton message apparaîtra ici…";
  }

  // Events
  if (cibleType) cibleType.addEventListener("change", applyCiblageUI);

  if (degreSelect) {
    degreSelect.addEventListener("change", async () => {
      await loadNiveaux(degreSelect.value);
      // show needed
      const t = (cibleType?.value || "").trim();
      if (t === "NIVEAU" || t === "GROUPE" || t === "ELEVE") {
        if (wrapNiveau) wrapNiveau.style.display = "";
        if (niveauSelect) niveauSelect.disabled = false;
      }
    });
  }

  if (niveauSelect) {
    niveauSelect.addEventListener("change", async () => {
      await loadGroupes(niveauSelect.value);
      const t = (cibleType?.value || "").trim();
      if (t === "GROUPE" || t === "ELEVE") {
        if (wrapGroupe) wrapGroupe.style.display = "";
        if (groupeSelect) groupeSelect.disabled = false;
      }
    });
  }

  if (groupeSelect) {
    groupeSelect.addEventListener("change", async () => {
      await loadEleves(groupeSelect.value);
      const t = (cibleType?.value || "").trim();
      if (t === "ELEVE") {
        if (wrapEleve) wrapEleve.style.display = "";
      }
    });
  }

  if (messageEl) messageEl.addEventListener("input", updateSmsStats);

  // Init
  applyCiblageUI();
  updateSmsStats();
})();
