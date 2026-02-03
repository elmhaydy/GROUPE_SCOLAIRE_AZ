(() => {
  "use strict";

  const cfg = window.AZ_AVIS || {};
  const URL_GROUPES = cfg.urlGroupes || "";
  const URL_ELEVES  = cfg.urlEleves  || "";

  const form = document.querySelector("form.azavis-grid");
  if (!form) return;

  // Fields (Django ids)
  const typeEl   = document.getElementById("id_cible_type");
  const titreEl  = document.getElementById("id_titre");
  const contEl   = document.getElementById("id_contenu");

  const degreEl  = document.getElementById("id_degre");
  const niveauEl = document.getElementById("id_niveau");
  const groupeEl = document.getElementById("id_groupe");
  const eleveEl  = document.getElementById("id_eleve");

  // UI blocks
  const blocks   = Array.from(form.querySelectorAll(".azavis-block"));
  const stepper  = document.getElementById("azAvisStepper");
  const steps    = stepper ? Array.from(stepper.querySelectorAll(".st")) : [];

  const cibles   = Array.from(form.querySelectorAll(".azavis-cible"));

  // Preview
  const chipEl   = document.getElementById("azPreviewChip");
  const pTitleEl = document.getElementById("azPreviewTitle");
  const pContEl  = document.getElementById("azPreviewContent");
  const pMetaEl  = document.getElementById("azPreviewMeta");

  // Group UI
  const groupLoader = document.getElementById("azGroupLoader");
  const groupMini   = document.getElementById("azGroupMini");

  // Eleve UI
  const eleveLoader = document.getElementById("azEleveLoader");

  // Summary
  const sumCible = document.getElementById("azSumCible");
  const sumTitre = document.getElementById("azSumTitre");

  if (!typeEl) return;

  // -------------------------
  // Helpers
  // -------------------------
  const getText = (sel) => {
    if (!sel) return "";
    const opt = sel.options[sel.selectedIndex];
    if (!opt) return "";
    return (opt.textContent || "").trim();
  };

  const setLoading = (loaderEl, on) => {
    if (!loaderEl) return;
    loaderEl.classList.toggle("is-on", !!on);
  };

  const setOptions = (selectEl, items, placeholder, keepValue) => {
    if (!selectEl) return;

    const prev = keepValue ?? selectEl.value;
    selectEl.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder;
    selectEl.appendChild(opt0);

    (items || []).forEach((it) => {
      const opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.label || it.nom || ("#" + it.id);
      selectEl.appendChild(opt);
    });

    // restore if possible
    const exists = Array.from(selectEl.options).some(o => o.value === String(prev));
    selectEl.value = exists ? String(prev) : "";
  };

  async function fetchJSON(url) {
    try {
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  // -------------------------
  // Stepper
  // -------------------------
  let currentStep = 1;

  function showStep(n) {
    currentStep = Math.max(1, Math.min(3, n));

    blocks.forEach(b => {
      const id = Number(b.getAttribute("data-block"));
      b.classList.toggle("is-hidden", id !== currentStep);
    });

    steps.forEach(s => {
      const st = Number(s.getAttribute("data-step"));
      s.classList.toggle("is-on", st === currentStep);
      s.classList.toggle("is-done", st < currentStep);
    });

    updatePreview();
    updateSummary();
  }

  function step1Valid() {
    // léger: laisser serveur valider, mais UX : titre + contenu non vides
    const t = (titreEl?.value || "").trim();
    const c = (contEl?.value || "").trim();
    return t.length > 0 && c.length > 0;
  }

  function step2Valid() {
    const type = (typeEl.value || "TOUS");
    if (type === "TOUS") return true;
    if (type === "DEGRE") return !!(degreEl && degreEl.value);
    if (type === "NIVEAU") return !!(niveauEl && niveauEl.value);
    if (type === "GROUPE") return !!(niveauEl && niveauEl.value) && !!(groupeEl && groupeEl.value);
    if (type === "ELEVE")  return !!(niveauEl && niveauEl.value) && !!(groupeEl && groupeEl.value) && !!(eleveEl && eleveEl.value);
    return true;
  }

  form.addEventListener("click", (e) => {
    const btnNext = e.target.closest("[data-next]");
    const btnPrev = e.target.closest("[data-prev]");

    if (btnNext) {
      if (currentStep === 1 && !step1Valid()) {
        // focus
        titreEl?.focus();
        return;
      }
      if (currentStep === 2 && !step2Valid()) {
        typeEl?.focus();
        return;
      }
      showStep(currentStep + 1);
    }

    if (btnPrev) {
      showStep(currentStep - 1);
    }
  });

  // -------------------------
  // Ciblage (show/hide) + reset
  // -------------------------
  function showCibleUI(type) {
    const t = type || "TOUS";

    cibles.forEach(box => {
      const allowed = (box.getAttribute("data-cible") || "").split(/\s+/).filter(Boolean);
      box.classList.toggle("is-on", allowed.includes(t));
    });

    // Reset intelligent des champs non utilisés (IMPORTANT pour éviter erreurs)
    if (t === "TOUS") {
      if (degreEl)  degreEl.value = "";
      if (niveauEl) niveauEl.value = "";
      if (groupeEl) groupeEl.value = "";
      if (eleveEl)  eleveEl.value = "";
    }

    if (t === "DEGRE") {
      if (niveauEl) niveauEl.value = "";
      if (groupeEl) groupeEl.value = "";
      if (eleveEl)  eleveEl.value = "";
    }

    if (t === "NIVEAU") {
      if (degreEl)  degreEl.value = "";
      if (groupeEl) groupeEl.value = "";
      if (eleveEl)  eleveEl.value = "";
    }

    if (t === "GROUPE") {
      if (degreEl)  degreEl.value = "";
      if (eleveEl)  eleveEl.value = "";
      // keep niveau + groupe
    }

    if (t === "ELEVE") {
      if (degreEl)  degreEl.value = "";
      // keep niveau + groupe + eleve
    }

    updatePreview();
    updateSummary();
  }

  // -------------------------
  // AJAX: Groupes (niveau -> groupes)
  // -------------------------
  async function loadGroupes({ keepSelected } = {}) {
    if (!URL_GROUPES || !groupeEl || !niveauEl) return;

    const niveau = niveauEl.value || "";
    if (!niveau) {
      setOptions(groupeEl, [], "— Sélectionner un groupe —", "");
      if (groupMini) groupMini.textContent = "—";
      updatePreview();
      return;
    }

    const url = URL_GROUPES + "?niveau=" + encodeURIComponent(niveau);

    groupeEl.disabled = true;
    setLoading(groupLoader, true);

    const data = await fetchJSON(url);
    const items = data ? (data.results || data.groupes || []) : [];

    setOptions(groupeEl, items, "— Sélectionner un groupe —", keepSelected);

    groupeEl.disabled = false;
    setLoading(groupLoader, false);

    if (groupMini) {
      const txt = getText(groupeEl);
      groupMini.textContent = txt && !txt.startsWith("—") ? txt : "—";
    }

    updatePreview();
    updateSummary();
  }

  // -------------------------
  // AJAX: Eleves (groupe -> eleves)
  // -------------------------
  async function loadEleves({ keepSelected } = {}) {
    if (!URL_ELEVES || !eleveEl || !groupeEl) return;

    const gid = groupeEl.value || "";
    if (!gid) {
      setOptions(eleveEl, [], "— Sélectionner un élève —", "");
      updatePreview();
      return;
    }

    const url = URL_ELEVES + "?groupe_id=" + encodeURIComponent(gid);

    eleveEl.disabled = true;
    setLoading(eleveLoader, true);

    const data = await fetchJSON(url);
    const items = data ? (data.results || data.eleves || []) : [];

    setOptions(eleveEl, items, "— Sélectionner un élève —", keepSelected);

    eleveEl.disabled = false;
    setLoading(eleveLoader, false);

    updatePreview();
    updateSummary();
  }

  // -------------------------
  // Preview + Summary
  // -------------------------
  function buildMeta(type) {
    const t = type || "TOUS";

    if (t === "TOUS") return "Tous";
    if (t === "DEGRE") return getText(degreEl) || "—";
    if (t === "NIVEAU") return getText(niveauEl) || "—";
    if (t === "GROUPE") {
      const n = getText(niveauEl);
      const g = getText(groupeEl);
      return [n, g].filter(Boolean).join(" • ") || "—";
    }
    if (t === "ELEVE") {
      const n = getText(niveauEl);
      const g = getText(groupeEl);
      const e = getText(eleveEl);
      return [n, g, e].filter(Boolean).join(" • ") || "—";
    }
    return "—";
  }

  function updatePreview() {
    const type = typeEl.value || "TOUS";
    const t = (titreEl?.value || "").trim() || "Titre de l’avis…";
    const c = (contEl?.value || "").trim() || "Contenu de l’avis…";

    if (chipEl) chipEl.textContent = type;
    if (pTitleEl) pTitleEl.textContent = t;
    if (pContEl) pContEl.textContent = c;

    if (pMetaEl) {
      const metaSpan = pMetaEl.querySelector("span");
      if (metaSpan) metaSpan.textContent = buildMeta(type);
    }

    if (groupMini) {
      const txt = getText(groupeEl);
      groupMini.textContent = txt && !txt.startsWith("—") ? txt : "—";
    }
  }

  function updateSummary() {
    if (!sumCible && !sumTitre) return;
    const type = typeEl.value || "TOUS";
    if (sumCible) sumCible.textContent = type + " • " + buildMeta(type);
    if (sumTitre) sumTitre.textContent = (titreEl?.value || "").trim() || "—";
  }

  // -------------------------
  // FIX SUBMIT: vider champs non utilisés (sans disabled)
  // -------------------------
  function enforceSubmitClean() {
    const type = typeEl.value || "TOUS";

    // Toujours enlever les valeurs "en trop" pour ne pas bloquer la validation Django
    if (type === "TOUS") {
      degreEl && (degreEl.value = "");
      niveauEl && (niveauEl.value = "");
      groupeEl && (groupeEl.value = "");
      eleveEl && (eleveEl.value = "");
    }

    if (type === "DEGRE") {
      niveauEl && (niveauEl.value = "");
      groupeEl && (groupeEl.value = "");
      eleveEl && (eleveEl.value = "");
    }

    if (type === "NIVEAU") {
      degreEl && (degreEl.value = "");
      groupeEl && (groupeEl.value = "");
      eleveEl && (eleveEl.value = "");
    }

    if (type === "GROUPE") {
      degreEl && (degreEl.value = "");
      eleveEl && (eleveEl.value = "");
      // niveau + groupe restent
    }

    if (type === "ELEVE") {
      degreEl && (degreEl.value = "");
      // niveau + groupe + eleve restent
    }
  }

  form.addEventListener("submit", (e) => {
    enforceSubmitClean();
    // option UX: bloquer si step2 invalide
    // (mais même si tu supprimes ça, Django valide côté serveur)
    if (!step1Valid()) {
      e.preventDefault();
      showStep(1);
      titreEl?.focus();
      return;
    }
    if (!step2Valid()) {
      e.preventDefault();
      showStep(2);
      typeEl?.focus();
      return;
    }
  });

  // -------------------------
  // Events
  // -------------------------
  typeEl.addEventListener("change", async () => {
    const t = typeEl.value || "TOUS";
    showCibleUI(t);

    // si GROUPE/ELEVE et niveau déjà choisi => charger groupes
    if ((t === "GROUPE" || t === "ELEVE") && niveauEl?.value) {
      const keep = groupeEl?.value || "";
      await loadGroupes({ keepSelected: keep });

      // si ELEVE et groupe déjà choisi => charger élèves
      if (t === "ELEVE" && groupeEl?.value) {
        const keepE = eleveEl?.value || "";
        await loadEleves({ keepSelected: keepE });
      }
    }
  });

  if (titreEl) titreEl.addEventListener("input", () => { updatePreview(); updateSummary(); });
  if (contEl)  contEl.addEventListener("input", () => { updatePreview(); updateSummary(); });

  if (degreEl) degreEl.addEventListener("change", () => { updatePreview(); updateSummary(); });

  if (niveauEl) {
    niveauEl.addEventListener("change", async () => {
      // quand niveau change: on doit recharger groupes (pour GROUPE/ELEVE)
      const t = typeEl.value || "TOUS";

      // si on est en ELEVE => reset groupe+eleve
      if (t === "ELEVE") {
        if (eleveEl) eleveEl.value = "";
      }
      if (groupeEl) groupeEl.value = "";

      if (t === "GROUPE" || t === "ELEVE") {
        await loadGroupes();
      }

      updatePreview();
      updateSummary();
    });
  }

  if (groupeEl) {
    groupeEl.addEventListener("change", async () => {
      const t = typeEl.value || "TOUS";
      if (t === "ELEVE") {
        if (eleveEl) eleveEl.value = "";
        await loadEleves();
      }
      updatePreview();
      updateSummary();
    });
  }

  if (eleveEl) {
    eleveEl.addEventListener("change", () => {
      updatePreview();
      updateSummary();
    });
  }

  // -------------------------
  // Init (edit + create)
  // -------------------------
  function init() {
    // Step 1 visible
    showStep(1);

    // show cible UI
    const t = typeEl.value || "TOUS";
    showCibleUI(t);

    // init preview
    updatePreview();
    updateSummary();

    // Edition: si niveau déjà set -> charger groupes et conserver la sélection
    if ((t === "GROUPE" || t === "ELEVE") && niveauEl?.value) {
      const keepG = groupeEl?.value || "";
      loadGroupes({ keepSelected: keepG }).then(() => {
        if (t === "ELEVE" && groupeEl?.value) {
          const keepE = eleveEl?.value || "";
          loadEleves({ keepSelected: keepE });
        }
      });
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
