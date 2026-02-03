/* prof/js/cahier_form.js
   FINAL SAFE
   - charge les matières selon le groupe choisi
   - respecte l’année active
   - respecte EnseignantGroupe (matiere_fk)
*/

(() => {
  const groupeEl  = document.getElementById("id_groupe");
  const matiereEl = document.getElementById("id_matiere");
  const statusEl  = document.getElementById("azpStatus");

  if (!groupeEl || !matiereEl) return;

  const cfg = window.AZ_CAHIER || {};
  const URL_GROUPES  = (cfg.URL_GROUPES || "").toString();
  const URL_MATIERES = (cfg.URL_MATIERES || "").toString();

  if (!URL_MATIERES) {
    console.warn("[AZ] URL_MATIERES manquante.");
    return;
  }

  // valeur initiale (cas update ou POST invalide)
  let initialMatiere = matiereEl.value || "";

  function setStatus(msg = "", type = "") {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = "azp-inline-status " + (type || "");
  }

  function resetMatieres(label = "Choisis un groupe d’abord.") {
    matiereEl.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = label;
    matiereEl.appendChild(opt);
    matiereEl.value = "";
  }

  async function fetchJSON(url) {
    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });
      if (!res.ok) return { results: [] };
      return await res.json();
    } catch (e) {
      console.warn("[AZ] fetch failed:", e);
      return { results: [] };
    }
  }

  async function loadMatieres() {
    const gid = (groupeEl.value || "").toString();

    resetMatieres("Chargement des matières…");
    setStatus("");

    if (!gid) {
      resetMatieres("Choisis un groupe d’abord.");
      return;
    }

    const data = await fetchJSON(
      URL_MATIERES + "?groupe_id=" + encodeURIComponent(gid)
    );

    const results = data.results || [];

    matiereEl.innerHTML = "";

    if (!results.length) {
      resetMatieres("Aucune matière pour ce groupe.");
      setStatus(
        "⚠️ Aucune matière affectée à ce groupe pour toi (année active).",
        "warn"
      );
      return;
    }

    // option vide
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "— Choisir —";
    matiereEl.appendChild(opt0);

    results.forEach(m => {
      const o = document.createElement("option");
      o.value = String(m.id);
      o.textContent = m.label;
      matiereEl.appendChild(o);
    });

    // restore valeur si possible (update / erreur POST)
    if (
      initialMatiere &&
      [...matiereEl.options].some(o => o.value === initialMatiere)
    ) {
      matiereEl.value = initialMatiere;
    } else {
      matiereEl.value = "";
    }

    // consommée une seule fois
    initialMatiere = "";
  }

  // events
  groupeEl.addEventListener("change", () => {
    initialMatiere = "";
    loadMatieres();
  });

  // init (cas update)
  if (groupeEl.value) {
    loadMatieres();
  } else {
    resetMatieres();
  }
})();
