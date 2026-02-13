/* static/admin/js/sms/send.js */
/* AZ • SMS Send — Degré -> Niveau -> Groupe -> Élève + TomSelect Élève (FINAL) */

(function () {
  "use strict";

  const root = document.querySelector(".azsms");
  if (!root) return;

  // Django widgets
  const cibleType = document.getElementById("id_cible_type");
  const messageEl = document.getElementById("id_message");

  // Targets wrappers
  const wrapDegre = document.getElementById("wrap-degre");
  const wrapNiveau = document.getElementById("wrap-niveau");
  const wrapGroupe = document.getElementById("wrap-groupe");
  const wrapEleve = document.getElementById("wrap-eleve");

  // Selects
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
  const URL_ELEVES = window.AZ_SMS?.urlEleves || "";

  // TomSelect instance
  let tsEleve = null;

  function hideAllTargets() {
    if (wrapDegre) wrapDegre.style.display = "none";
    if (wrapNiveau) wrapNiveau.style.display = "none";
    if (wrapGroupe) wrapGroupe.style.display = "none";
    if (wrapEleve) wrapEleve.style.display = "none";
  }

  function resetNativeSelect(sel, placeholder = "— Choisir —") {
    if (!sel) return;
    sel.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    sel.appendChild(opt);
    sel.value = "";
  }

  function setDisabled(sel, on) {
    if (!sel) return;

    sel.disabled = !!on;

    // ✅ Sync TomSelect for eleve_select
    if (sel === eleveSelect && tsEleve) {
      if (on) tsEleve.lock();
      else tsEleve.unlock();
    }
  }

  async function fetchJSON(url) {
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} on ${url}\n${txt.slice(0, 300)}`);
    }
    return await res.json();
  }

  // -------------------------
  // TomSelect (Élève) — ALWAYS ON
  // -------------------------
  function initTomSelectEleve() {
    if (!window.TomSelect || !eleveSelect) return;
    if (tsEleve) return;

    // ✅ TomSelect bug: init sur <select disabled> => control non cliquable
    const wasDisabled = eleveSelect.disabled;
    eleveSelect.disabled = false;

    tsEleve = new TomSelect(eleveSelect, {
      create: false,
      allowEmptyOption: true,
      placeholder: "— Rechercher un élève —",
      closeAfterSelect: true,
      maxOptions: 2000,
      plugins: ["clear_button"],
    });

    // restore disabled state
    eleveSelect.disabled = wasDisabled;

    // ✅ sync UI état (si disabled => lock, sinon unlock)
    if (wasDisabled) tsEleve.lock();
    else tsEleve.unlock();
  }


  function tsEleveClear() {
    if (!tsEleve) {
      resetNativeSelect(eleveSelect);
      return;
    }
    tsEleve.clear(true);
    tsEleve.clearOptions();
    // garder l'option vide
    tsEleve.addOption({ value: "", text: "— Choisir —" });
    tsEleve.refreshOptions(false);
    tsEleve.setValue("", true);
  }

  function tsEleveSetOptions(items) {
    // items: [{id, label}]
    if (!eleveSelect) return;

    // si TomSelect pas dispo, fallback natif
    if (!tsEleve) {
      resetNativeSelect(eleveSelect);
      items.forEach((it) => {
        const o = document.createElement("option");
        o.value = it.id;
        o.textContent = it.label || ("Élève #" + it.id);
        eleveSelect.appendChild(o);
      });
      return;
    }

    tsEleve.clear(true);
    tsEleve.clearOptions();

    // option vide
    tsEleve.addOption({ value: "", text: "— Choisir —" });

    items.forEach((it) => {
      tsEleve.addOption({
        value: String(it.id),
        text: it.label || ("Élève #" + it.id),
      });
    });

    tsEleve.refreshOptions(false);
    tsEleve.setValue("", true);
  }

  // -------------------------
  // Loaders
  // -------------------------
  async function loadNiveaux(degreId) {
    resetNativeSelect(niveauSelect);
    resetNativeSelect(groupeSelect);

    setDisabled(niveauSelect, true);
    setDisabled(groupeSelect, true);
    setDisabled(eleveSelect, true);

    tsEleveClear();

    if (!degreId) return;

    const data = await fetchJSON(
      URL_NIVEAUX + "?degre_id=" + encodeURIComponent(degreId)
    );
    const items = data.results || data || [];

    items.forEach((it) => {
      const o = document.createElement("option");
      o.value = it.id;
      o.textContent = it.nom || it.label || ("Niveau #" + it.id);
      niveauSelect.appendChild(o);
    });

    setDisabled(niveauSelect, false);
  }

  async function loadGroupes(niveauId) {
    resetNativeSelect(groupeSelect);

    setDisabled(groupeSelect, true);
    setDisabled(eleveSelect, true);

    tsEleveClear();

    if (!niveauId) return;

    const data = await fetchJSON(
      URL_GROUPES + "?niveau_id=" + encodeURIComponent(niveauId)
    );
    const items = data.results || data || [];

    items.forEach((it) => {
      const o = document.createElement("option");
      o.value = it.id;
      o.textContent = it.nom || it.label || ("Groupe #" + it.id);
      groupeSelect.appendChild(o);
    });

    setDisabled(groupeSelect, false);
  }

  async function loadEleves(groupeId) {
    // dès qu’un groupe est choisi, on rend cliquable + on met un placeholder "Chargement"
    setDisabled(eleveSelect, false);

    // TomSelect UI: vider + placeholder
    if (tsEleve) {
      tsEleve.clear(true);
      tsEleve.clearOptions();
      tsEleve.addOption({ value: "", text: "Chargement..." });
      tsEleve.refreshOptions(false);
      tsEleve.setValue("", true);
    } else {
      resetNativeSelect(eleveSelect, "Chargement...");
    }

    if (!groupeId) {
      // si pas de groupe, on re-disable
      setDisabled(eleveSelect, true);
      if (tsEleve) tsEleveClear();
      else resetNativeSelect(eleveSelect);
      return;
    }

    const data = await fetchJSON(
      URL_ELEVES + "?groupe_id=" + encodeURIComponent(groupeId)
    );

    const items = data.results || [];
    tsEleveSetOptions(items);

    // si aucun élève => on laisse actif mais vide
    if (!items.length) {
      if (tsEleve) {
        tsEleve.clear(true);
        tsEleve.clearOptions();
        tsEleve.addOption({ value: "", text: "Aucun élève trouvé" });
        tsEleve.refreshOptions(false);
        tsEleve.setValue("", true);
      } else {
        resetNativeSelect(eleveSelect, "Aucun élève trouvé");
      }
    }
  }


  // -------------------------
  // UI rules
  // -------------------------
  function applyCiblageUI() {
    const t = (cibleType?.value || "").trim();
    hideAllTargets();

    // reset chain
    setDisabled(niveauSelect, true);
    setDisabled(groupeSelect, true);
    setDisabled(eleveSelect, true);

    resetNativeSelect(niveauSelect);
    resetNativeSelect(groupeSelect);
    tsEleveClear();

    if (t === "TOUS" || t === "") return;

    // Toujours Degré
    if (wrapDegre) wrapDegre.style.display = "";

    if (t === "DEGRE") return;

    if (wrapNiveau) wrapNiveau.style.display = "";

    if (t === "NIVEAU") return;

    if (wrapGroupe) wrapGroupe.style.display = "";

    if (t === "GROUPE") return;

    if (t === "ELEVE") {
      if (wrapEleve) wrapEleve.style.display = "";
    }
  }

  // SMS counter
  function updateSmsStats() {
    const text = messageEl?.value || "";
    const len = text.length;
    const parts = Math.max(1, Math.ceil(len / 160));

    if (smsCount) smsCount.textContent = String(len);
    if (smsParts) smsParts.textContent = String(parts);
    if (smsCount2) smsCount2.textContent = String(len);
    if (smsParts2) smsParts2.textContent = String(parts);

    if (smsPreview)
      smsPreview.textContent = text.trim()
        ? text
        : "Ton message apparaîtra ici…";
  }

  // -------------------------
  // Events
  // -------------------------
  if (cibleType) cibleType.addEventListener("change", applyCiblageUI);

  if (degreSelect) {
    degreSelect.addEventListener("change", async () => {
      try {
        await loadNiveaux(degreSelect.value);

        const t = (cibleType?.value || "").trim();
        if (t === "NIVEAU" || t === "GROUPE" || t === "ELEVE") {
          if (wrapNiveau) wrapNiveau.style.display = "";
          setDisabled(niveauSelect, false);
        }
      } catch (e) {
        console.error(e);
      }
    });
  }

  if (niveauSelect) {
    niveauSelect.addEventListener("change", async () => {
      try {
        await loadGroupes(niveauSelect.value);

        const t = (cibleType?.value || "").trim();
        if (t === "GROUPE" || t === "ELEVE") {
          if (wrapGroupe) wrapGroupe.style.display = "";
          setDisabled(groupeSelect, false);
        }
      } catch (e) {
        console.error(e);
      }
    });
  }

  if (groupeSelect) {
    groupeSelect.addEventListener("change", async () => {
      try {
        await loadEleves(groupeSelect.value);

        const t = (cibleType?.value || "").trim();
        if (t === "ELEVE") {
          if (wrapEleve) wrapEleve.style.display = "";
        }
      } catch (e) {
        console.error(e);
      }
    });
  }

  if (messageEl) messageEl.addEventListener("input", updateSmsStats);

  // -------------------------
  // INIT
  // -------------------------
  initTomSelectEleve();   // ✅ IMPORTANT: TomSelect toujours actif
  applyCiblageUI();
  updateSmsStats();
})();
