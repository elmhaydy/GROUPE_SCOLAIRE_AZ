(() => {
  const anneeEl  = document.getElementById("id_annee");
  const niveauEl = document.getElementById("id_niveau");
  const groupeEl = document.getElementById("id_groupe");

  if (!anneeEl || !niveauEl || !groupeEl) return;

  const cfg = window.AZ_PARENT || {};
  const URL_NIVEAUX = cfg.urlNiveaux || "";
  const URL_GROUPES = cfg.urlGroupes || "";

  if (!URL_NIVEAUX || !URL_GROUPES) {
    console.warn("[AZ] URLs AJAX manquantes (AZ_PARENT).");
    return;
  }

  function setOptions(selectEl, items, placeholderText) {
    const current = selectEl.value;
    selectEl.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholderText;
    selectEl.appendChild(opt0);

    (items || []).forEach(it => {
      const opt = document.createElement("option");
      opt.value = String(it.id);
      opt.textContent = it.label;
      selectEl.appendChild(opt);
    });

    if ([...selectEl.options].some(o => o.value === current)) {
      selectEl.value = current;
    } else {
      selectEl.value = "";
    }
  }

  async function fetchJSON(url) {
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!res.ok) return {};
    return await res.json();
  }

  async function loadNiveaux() {
    const annee = anneeEl.value || "";
    const url = URL_NIVEAUX + "?annee=" + encodeURIComponent(annee);

    const data = await fetchJSON(url);
    setOptions(niveauEl, data.results || [], "Tous");

    await loadGroupes();
  }

  async function loadGroupes() {
    const annee  = anneeEl.value || "";
    const niveau = niveauEl.value || "";
    const url =
      URL_GROUPES +
      "?annee=" + encodeURIComponent(annee) +
      "&niveau=" + encodeURIComponent(niveau);

    const data = await fetchJSON(url);
    setOptions(groupeEl, data.results || [], "Tous");
  }

  anneeEl.addEventListener("change", async () => { await loadNiveaux(); });
  niveauEl.addEventListener("change", async () => { await loadGroupes(); });
})();
