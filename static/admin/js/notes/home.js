/* =========================================================
   AZ — Notes Home (Filters Ajax) — FINAL
   Chain:
     Niveau -> Groupes -> Enseignants -> Matières
   Endpoints:
     cfg.URL_GROUPES      ?annee=&niveau=
     cfg.URL_ENS          ?annee=&niveau=&groupe=
     cfg.URL_MAT          ?annee=&niveau=&groupe=&enseignant=
   ========================================================= */

(() => {
  "use strict";

  const cfg = window.AZ_NOTES_HOME || {};
  const form = document.getElementById("notesHomeFilter");
  if (!form) return;

  // Selects
  const $niveau = document.getElementById("f_niveau");
  const $groupe = document.getElementById("f_groupe");
  const $periode = document.getElementById("f_periode"); // pas ajax ici (année active)
  const $enseignant = document.getElementById("f_enseignant"); // ✅ doit exister dans ton HTML
  const $matiere = document.getElementById("f_matiere");

  // ✅ Année active (injecte-la dans window.AZ_NOTES_HOME.ANNEE_ID)
  const ANNEE_ID = String(cfg.ANNEE_ID || "").trim();

  // Tu peux activer si tu veux filtrer automatiquement au changement
  const AUTO_SUBMIT = false;

  // ---------------------------
  // Utils
  // ---------------------------
  const getVal = (el) => (el && el.value ? String(el.value).trim() : "");
  const isId = (v) => /^\d+$/.test(String(v || ""));
  const keyOf = (url, params) => url + "?" + new URLSearchParams(params).toString();

  const resetSelect = (el, placeholder) => {
    if (!el) return;
    el.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    el.appendChild(opt);
  };

  const setBusy = (el, busy, placeholder) => {
    if (!el) return;
    el.disabled = !!busy;
    el.dataset.loading = busy ? "1" : "0";
    if (busy && placeholder) {
      resetSelect(el, placeholder);
    }
  };

  const fillSelect = (el, items, placeholder, selectedValue) => {
    if (!el) return;
    const sel = String(selectedValue || "").trim();

    resetSelect(el, placeholder);

    for (const it of items || []) {
      const id = String(it.id ?? "").trim();
      const label = String(it.label ?? it.nom ?? it.text ?? `#${id}`);
      if (!id) continue;

      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = label;
      if (sel && id === sel) opt.selected = true;
      el.appendChild(opt);
    }
  };

  // ---------------------------
  // Fetch manager (abort + cache)
  // ---------------------------
  const cache = new Map();
  const controllers = new Map(); // name -> AbortController

  const fetchJSON = async (name, url, params) => {
    const u = new URL(url, window.location.origin);
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).trim() !== "") {
        u.searchParams.set(k, String(v).trim());
      }
    });

    const cacheKey = keyOf(u.pathname, Object.fromEntries(u.searchParams.entries()));
    if (cache.has(cacheKey)) return cache.get(cacheKey);

    // abort previous same-name request
    if (controllers.has(name)) {
      try { controllers.get(name).abort(); } catch (_) {}
    }
    const ac = new AbortController();
    controllers.set(name, ac);

    const res = await fetch(u.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      signal: ac.signal,
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    cache.set(cacheKey, data);
    return data;
  };

  const toItems = (data) => (Array.isArray(data) ? data : (data?.results || []));

  // ---------------------------
  // Loaders (CHAIN)
  // ---------------------------

  // 1) Niveau -> Groupes
  const loadGroupes = async () => {
    if (!cfg.URL_GROUPES || !$groupe) return;

    const niveau = getVal($niveau);

    // reset
    resetSelect($groupe, "— Tous —");
    if ($enseignant) resetSelect($enseignant, "— Tous —");
    if ($matiere) resetSelect($matiere, "— Toutes —");

    if (!isId(niveau)) return;

    setBusy($groupe, true, "Chargement...");
    try {
      const data = await fetchJSON("groupes", cfg.URL_GROUPES, {
        annee: ANNEE_ID,
        niveau,
      });

      const selected = $groupe.dataset.selected || $groupe.value || "";
      fillSelect($groupe, toItems(data), "— Tous —", selected);
      $groupe.dataset.selected = "";
    } catch (e) {
      console.warn("loadGroupes:", e);
      resetSelect($groupe, "— Tous —");
    } finally {
      setBusy($groupe, false);
    }
  };

  // 2) Groupe/Niveau -> Enseignants
  const loadEnseignants = async () => {
    if (!cfg.URL_ENS || !$enseignant) return;

    const niveau = getVal($niveau);
    const groupe = getVal($groupe);

    resetSelect($enseignant, "— Tous —");
    if ($matiere) resetSelect($matiere, "— Toutes —");

    // Si pas de niveau => stop
    if (!isId(niveau)) return;

    setBusy($enseignant, true, "Chargement...");
    try {
      const data = await fetchJSON("enseignants", cfg.URL_ENS, {
        annee: ANNEE_ID,
        niveau,
        groupe: isId(groupe) ? groupe : "",
      });

      const selected = $enseignant.dataset.selected || $enseignant.value || "";
      fillSelect($enseignant, toItems(data), "— Tous —", selected);
      $enseignant.dataset.selected = "";
    } catch (e) {
      console.warn("loadEnseignants:", e);
      resetSelect($enseignant, "— Tous —");
    } finally {
      setBusy($enseignant, false);
    }
  };

  // 3) (Niveau + Groupe + Enseignant) -> Matières
  const loadMatieres = async () => {
    if (!cfg.URL_MAT || !$matiere) return;

    const niveau = getVal($niveau);
    const groupe = getVal($groupe);
    const enseignant = $enseignant ? getVal($enseignant) : "";

    resetSelect($matiere, "— Toutes —");

    // Si pas de niveau => stop
    if (!isId(niveau)) return;

    // 👇 Important: tu voulais matières dépendantes de enseignant
    // => si enseignant pas choisi, on laisse vide (ou tu peux charger par niveau)
    if (!isId(enseignant)) return;

    setBusy($matiere, true, "Chargement...");
    try {
      const data = await fetchJSON("matieres", cfg.URL_MAT, {
        annee: ANNEE_ID,
        niveau,
        groupe: isId(groupe) ? groupe : "",
        enseignant,
      });

      const selected = $matiere.dataset.selected || $matiere.value || "";
      fillSelect($matiere, toItems(data), "— Toutes —", selected);
      $matiere.dataset.selected = "";
    } catch (e) {
      console.warn("loadMatieres:", e);
      resetSelect($matiere, "— Toutes —");
    } finally {
      setBusy($matiere, false);
    }
  };

  // ---------------------------
  // Chain runner
  // ---------------------------
  const runChainFromNiveau = async () => {
    await loadGroupes();
    await loadEnseignants();
    await loadMatieres();
  };

  const runChainFromGroupe = async () => {
    await loadEnseignants();
    await loadMatieres();
  };

  const runChainFromEnseignant = async () => {
    await loadMatieres();
  };

  // ---------------------------
  // Events
  // ---------------------------
  if ($niveau) {
    $niveau.addEventListener("change", async () => {
      // clear dependent selections
      if ($groupe) $groupe.dataset.selected = "";
      if ($enseignant) $enseignant.dataset.selected = "";
      if ($matiere) $matiere.dataset.selected = "";
      await runChainFromNiveau();
      if (AUTO_SUBMIT) form.submit();
    });
  }

  if ($groupe) {
    $groupe.addEventListener("change", async () => {
      if ($enseignant) $enseignant.dataset.selected = "";
      if ($matiere) $matiere.dataset.selected = "";
      await runChainFromGroupe();
      if (AUTO_SUBMIT) form.submit();
    });
  }

  if ($enseignant) {
    $enseignant.addEventListener("change", async () => {
      if ($matiere) $matiere.dataset.selected = "";
      await runChainFromEnseignant();
      if (AUTO_SUBMIT) form.submit();
    });
  }

  // Optionnel: auto-submit sur période/matière
  [$periode, $matiere].forEach((el) => {
    if (!el) return;
    el.addEventListener("change", () => {
      if (AUTO_SUBMIT) form.submit();
    });
  });

  // ---------------------------
  // Init (hydrate if selected)
  // ---------------------------
  (async () => {
    // si page chargée avec niveau déjà choisi -> on hydrate tout
    if (isId(getVal($niveau))) {
      await runChainFromNiveau();
    }
  })();
})();
