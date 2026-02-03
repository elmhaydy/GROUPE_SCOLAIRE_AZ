(() => {
  const anneeEl   = document.getElementById("id_annee");
  const niveauEl  = document.getElementById("id_niveau");
  const groupeEl  = document.getElementById("id_groupe");
  const periodeEl = document.getElementById("id_periode");
  if (!anneeEl || !niveauEl || !groupeEl || !periodeEl) return;

  const cfg = window.AZ_ABS || {};
  const URL_NIVEAUX  = cfg.urlNiveaux  || "";
  const URL_GROUPES  = cfg.urlGroupes  || "";
  const URL_PERIODES = cfg.urlPeriodes || "";
  if (!URL_NIVEAUX || !URL_GROUPES || !URL_PERIODES) return;

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

    if ([...selectEl.options].some(o => o.value === current)) selectEl.value = current;
    else selectEl.value = "";
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!res.ok) return {};
    return await res.json();
  }

  async function loadNiveaux() {
    const annee = anneeEl.value || "";
    const data = await fetchJSON(URL_NIVEAUX + "?annee=" + encodeURIComponent(annee));
    setOptions(niveauEl, data.results || [], "— Tous —");
  }

  async function loadGroupes() {
    const annee  = anneeEl.value || "";
    const niveau = niveauEl.value || "";
    const data = await fetchJSON(
      URL_GROUPES + "?annee=" + encodeURIComponent(annee) + "&niveau=" + encodeURIComponent(niveau)
    );
    setOptions(groupeEl, data.results || [], "— Tous —");
  }

  async function loadPeriodes() {
    const annee = anneeEl.value || "";
    const data = await fetchJSON(URL_PERIODES + "?annee=" + encodeURIComponent(annee));
    setOptions(periodeEl, data.results || [], "— Toutes —");
  }

  anneeEl.addEventListener("change", async () => {
    await loadNiveaux();
    await loadGroupes();
    await loadPeriodes();
  });

  niveauEl.addEventListener("change", async () => {
    await loadGroupes();
  });
})();
