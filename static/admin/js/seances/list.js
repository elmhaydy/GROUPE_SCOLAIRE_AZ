/* admin/js/seances/list.js
   AZ — Séances list — filters (simple)
*/

(() => {
  const anneeEl = document.getElementById("id_annee");
  const niveauEl = document.getElementById("id_niveau");
  const groupeEl = document.getElementById("id_groupe");
  const enseignantEl = document.getElementById("id_enseignant");

  if (!anneeEl || !niveauEl || !groupeEl || !enseignantEl) return;

  const cfg = window.AZ_SEANCES || {};
  const URL_NIVEAUX = cfg.urlNiveaux || "";
  const URL_GROUPES = cfg.urlGroupes || "";
  const URL_ENSEIGNANTS = cfg.urlEnseignants || "";

  if (!URL_NIVEAUX || !URL_GROUPES || !URL_ENSEIGNANTS) {
    console.warn("[AZ] URLs AJAX manquantes (AZ_SEANCES).");
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

    // restore if still exists
    if ([...selectEl.options].some(o => o.value === current)) {
      selectEl.value = current;
    } else {
      selectEl.value = "";
    }
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
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
    const annee = anneeEl.value || "";
    const niveau = niveauEl.value || "";
    const url =
      URL_GROUPES +
      "?annee=" + encodeURIComponent(annee) +
      "&niveau=" + encodeURIComponent(niveau);

    const data = await fetchJSON(url);
    setOptions(groupeEl, data.results || [], "Tous");

    await loadEnseignants();
  }

  async function loadEnseignants() {
    const annee = anneeEl.value || "";
    const groupe = groupeEl.value || "";
    const url =
      URL_ENSEIGNANTS +
      "?annee=" + encodeURIComponent(annee) +
      "&groupe=" + encodeURIComponent(groupe);

    const data = await fetchJSON(url);
    setOptions(enseignantEl, data.results || [], "Tous");
  }

  anneeEl.addEventListener("change", () => { loadNiveaux(); });
  niveauEl.addEventListener("change", () => { loadGroupes(); });
  groupeEl.addEventListener("change", () => { loadEnseignants(); });

  // init: si année est déjà set -> cascade
  loadNiveaux();
})();
