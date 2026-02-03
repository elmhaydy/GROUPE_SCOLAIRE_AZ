(function () {
  const groupe = document.getElementById("id_groupe");
  const matiere = document.getElementById("id_matiere");
  const periode = document.getElementById("id_periode");

  const helpM = document.getElementById("matiereHelp");
  const helpP = document.getElementById("periodeHelp");

  // accepte AZ_EVAL ou AZ_CAHIER (pour compat)
  const cfg = window.AZ_EVAL || window.AZ_CAHIER || {};
  const URL_MATIERES = cfg.URL_MATIERES || "";
  const URL_PERIODES = cfg.URL_PERIODES || ""; // optionnel si tu veux

  if (!groupe) return;

  function setHelp(el, txt) {
    if (el) el.textContent = txt || "";
  }

  function resetSelect(select, placeholder) {
    if (!select) return "";
    const current = select.value || "";
    select.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder;
    select.appendChild(opt0);
    select.disabled = true;
    select.style.opacity = "0.75";
    return current;
  }

  function enableSelect(select) {
    if (!select) return;
    select.disabled = false;
    select.style.opacity = "1";
  }

  function fillSelect(select, list, previousValue) {
    if (!select) return 0;

    let added = 0;
    list.forEach((it) => {
      const id = it.id ?? it.value ?? it.pk;
      const label = it.label ?? it.nom ?? it.name ?? it.text;
      if (id == null || !label) return;

      const opt = document.createElement("option");
      opt.value = String(id);
      opt.textContent = String(label);
      select.appendChild(opt);
      added++;
    });

    if (added) {
      enableSelect(select);

      // restore previous value if still present
      if (previousValue && Array.from(select.options).some(o => o.value === String(previousValue))) {
        select.value = String(previousValue);
      }
    }
    return added;
  }

  async function fetchJSON(url, params) {
    const u = new URL(url, window.location.origin);
    Object.entries(params || {}).forEach(([k, v]) => u.searchParams.set(k, v));

    const res = await fetch(u.toString(), {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return await res.json();
  }

  async function loadMatieres(gid) {
    if (!matiere) return;

    const prev = resetSelect(matiere, "— Choisir une matière —");

    if (!gid) {
      setHelp(helpM, "Choisis un groupe d’abord.");
      return;
    }

    if (!URL_MATIERES) {
      setHelp(helpM, "URL matières manquante.");
      return;
    }

    setHelp(helpM, "Chargement des matières…");

    try {
      const json = await fetchJSON(URL_MATIERES, { groupe_id: gid });
      const list = Array.isArray(json) ? json : (json.results || []);

      const added = fillSelect(matiere, list, prev);
      if (added) setHelp(helpM, "Matières chargées.");
      else setHelp(helpM, "Aucune matière trouvée (vérifie tes affectations).");
    } catch (e) {
      setHelp(helpM, "Erreur réseau/API.");
    }
  }

  async function loadPeriodes(gid) {
    if (!periode) return;

    const prev = resetSelect(periode, "— Choisir une période —");

    if (!gid) {
      setHelp(helpP, "Choisis un groupe d’abord.");
      return;
    }

    // si tu n'as pas d'API periodes, on laisse désactivé
    if (!URL_PERIODES) {
      setHelp(helpP, "Choisis un groupe (périodes non configurées).");
      return;
    }

    setHelp(helpP, "Chargement des périodes…");

    try {
      const json = await fetchJSON(URL_PERIODES, { groupe_id: gid });
      const list = Array.isArray(json) ? json : (json.results || []);

      const added = fillSelect(periode, list, prev);
      if (added) setHelp(helpP, "Périodes chargées.");
      else setHelp(helpP, "Aucune période trouvée.");
    } catch (e) {
      setHelp(helpP, "Erreur réseau/API.");
    }
  }

  async function onGroupeChange() {
    const gid = groupe.value || "";
    await Promise.all([
      loadMatieres(gid),
      loadPeriodes(gid),
    ]);
  }

  // init
  if (matiere) resetSelect(matiere, "— Choisir un groupe d’abord —");
  if (periode) resetSelect(periode, "— Choisir un groupe d’abord —");

  groupe.addEventListener("change", onGroupeChange);

  // si déjà sélectionné (POST error / back navigation)
  if (groupe.value) onGroupeChange();
})();
