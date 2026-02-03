/* =========================================================
   AZ — Evaluations List (list.js) — MODERNE MAX
   Cascade: Niveau => Groupes => Enseignants => Matières
   Dépendances: window.AZ_EVAL = { URL_GROUPES, URL_ENS, URL_MAT }
   ========================================================= */

(() => {
  const cfg = window.AZ_EVAL || {};
  const form = document.getElementById("evalFilterForm");
  if (!form) return;

  const $annee = document.getElementById("f_annee");
  const $niveau = document.getElementById("f_niveau");
  const $groupe = document.getElementById("f_groupe");
  const $enseignant = document.getElementById("f_enseignant");
  const $matiere = document.getElementById("f_matiere");

  // --- petits helpers ---
  const val = (el) => (el && el.value ? el.value.trim() : "");

  const esc = (s) => String(s ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");

  const setSelect = (el, items, placeholder, keepValue = true) => {
    if (!el) return;
    const current = keepValue ? String(el.value || "") : "";
    let html = `<option value="">${esc(placeholder)}</option>`;

    for (const it of (items || [])) {
      const id = String(it.id ?? "");
      const label = String(it.label ?? it.nom ?? it.text ?? "");
      const selected = (id && id === current) ? "selected" : "";
      html += `<option value="${esc(id)}" ${selected}>${esc(label)}</option>`;
    }

    el.innerHTML = html;

    // si current n’existe plus => reset
    if (keepValue && current && ![...el.options].some(o => o.value === current)) {
      el.value = "";
    }
  };

  const setLoading = (el, placeholder = "Chargement...") => {
    if (!el) return;
    el.disabled = true;
    el.innerHTML = `<option value="">${esc(placeholder)}</option>`;
  };

  const setEmpty = (el, placeholder) => {
    if (!el) return;
    el.disabled = false;
    el.innerHTML = `<option value="">${esc(placeholder)}</option>`;
  };

  // --- fetch moderne + cache + abort ---
  const cache = new Map();       // key -> results[]
  const aborters = new Map();    // key -> AbortController

  const buildURL = (url, params = {}) => {
    const u = new URL(url, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).trim() !== "") {
        u.searchParams.set(k, v);
      }
    });
    return u.toString();
  };

  const fetchResults = async (key, url, params) => {
    if (!url) return [];

    const full = buildURL(url, params);

    // cache
    if (cache.has(full)) return cache.get(full);

    // abort previous same key
    if (aborters.has(key)) aborters.get(key).abort();
    const controller = new AbortController();
    aborters.set(key, controller);

    const res = await fetch(full, {
      method: "GET",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      signal: controller.signal,
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    const results = Array.isArray(data) ? data : (data.results || []);
    cache.set(full, results);
    return results;
  };

  // --- loaders cascade ---
  const loadGroupes = async ({ keep = true } = {}) => {
    if (!$groupe || !cfg.URL_GROUPES) return;
    const annee = val($annee);
    const niveau = val($niveau);

    setLoading($groupe, "Chargement groupes...");
    try {
      const items = await fetchResults("groupes", cfg.URL_GROUPES, { annee, niveau });
      setSelect($groupe, items, "Tous", keep);
      $groupe.disabled = false;
    } catch {
      setEmpty($groupe, "Tous");
    }
  };

  const loadEnseignants = async ({ keep = true } = {}) => {
    if (!$enseignant || !cfg.URL_ENS) return;

    const annee = val($annee);
    const niveau = val($niveau);
    const groupe = val($groupe);

    // si pas de groupe choisi, on laisse "Tous"
    if (!groupe) {
      setEmpty($enseignant, "Tous");
      return;
    }

    setLoading($enseignant, "Chargement enseignants...");
    try {
      const items = await fetchResults("enseignants", cfg.URL_ENS, { annee, niveau, groupe });
      setSelect($enseignant, items, "Tous", keep);
      $enseignant.disabled = false;
    } catch {
      setEmpty($enseignant, "Tous");
    }
  };

  const loadMatieres = async ({ keep = true } = {}) => {
    if (!$matiere || !cfg.URL_MAT) return;

    const annee = val($annee);
    const niveau = val($niveau);
    const groupe = val($groupe);
    const enseignant = val($enseignant);

    // ✅ logique AZ: matières dépend de (groupe + enseignant)
    if (!groupe) {
      setEmpty($matiere, "Toutes");
      return;
    }

    setLoading($matiere, "Chargement matières...");
    try {
      const items = await fetchResults("matieres", cfg.URL_MAT, {
        annee,
        niveau,
        groupe,
        enseignant, // <= IMPORTANT (car ta view maintenant le gère)
      });

      setSelect($matiere, items, "Toutes", keep);
      $matiere.disabled = false;
    } catch {
      setEmpty($matiere, "Toutes");
    }
  };

  // --- reset descendants ---
  const resetEnseignants = () => setEmpty($enseignant, "Tous");
  const resetMatieres = () => setEmpty($matiere, "Toutes");

  // --- events cascade ---
  if ($niveau) {
    $niveau.addEventListener("change", async () => {
      // niveau change -> reset groupe/enseignant/matiere
      resetEnseignants();
      resetMatieres();

      await loadGroupes({ keep: false });
      await loadEnseignants({ keep: false }); // dépend du groupe (vide => Tous)
      await loadMatieres({ keep: false });
    });
  }

  if ($groupe) {
    $groupe.addEventListener("change", async () => {
      // groupe change -> reset enseignant/matiere
      resetEnseignants();
      resetMatieres();

      await loadEnseignants({ keep: false }); // enseignant dépend du groupe
      await loadMatieres({ keep: false });    // matiere dépend du groupe (et enseignant si choisi)
    });
  }

  if ($enseignant) {
    $enseignant.addEventListener("change", async () => {
      // enseignant change -> recharge matières
      await loadMatieres({ keep: false });
    });
  }

  // (optionnel) si année change => on peut recascader pareil
  if ($annee) {
    $annee.addEventListener("change", async () => {
      resetEnseignants();
      resetMatieres();

      await loadGroupes({ keep: false });
      await loadEnseignants({ keep: false });
      await loadMatieres({ keep: false });
    });
  }

  // --- hydration au chargement ---
  (async () => {
    // si ton serveur pré-remplit déjà, keep=true garde la sélection
    await loadGroupes({ keep: true });
    await loadEnseignants({ keep: true });
    await loadMatieres({ keep: true });
  })();

})();
