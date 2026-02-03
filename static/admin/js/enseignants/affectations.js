/* admin/js/enseignants/affectations.js
   FINAL (GROUP-ONLY)
   - Charge groupes selon l'année
   - Préserve selectedGroupe une seule fois (après POST)
*/

(() => {
  const anneeEl  = document.getElementById("id_annee_aff");
  const groupeEl = document.getElementById("id_groupe_aff");
  if (!anneeEl || !groupeEl) return;

  const cfg = window.AZ_AFF || {};
  const URL_GROUPES  = (cfg.urlGroupesParAnnee || "").toString();

  let selectedGroupe = (cfg.selectedGroupe || "").toString();

  if (!URL_GROUPES) {
    console.warn("[AZ] urlGroupesParAnnee manquante dans window.AZ_AFF.");
    return;
  }

  async function fetchJSON(url) {
    try {
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!res.ok) return { results: [] };
      return await res.json();
    } catch (e) {
      console.warn("[AZ] fetch failed:", e);
      return { results: [] };
    }
  }

  function setOptions(select, items, placeholder, wanted = "") {
    const current = select.value;
    select.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder || "— Choisir —";
    select.appendChild(opt0);

    (items || []).forEach(it => {
      const o = document.createElement("option");
      o.value = String(it.id);
      o.textContent = it.label;
      select.appendChild(o);
    });

    const w = (wanted || current || "").toString();
    if (w && [...select.options].some(o => o.value === w)) select.value = w;
    else select.value = "";
  }

  async function loadGroupes() {
    const anneeId = (anneeEl.value || "").toString();
    setOptions(groupeEl, [], "Chargement...");

    if (!anneeId) {
      setOptions(groupeEl, [], "— Choisir —");
      return;
    }

    const data = await fetchJSON(URL_GROUPES + "?annee_id=" + encodeURIComponent(anneeId));
    const results = data.results || [];

    setOptions(
      groupeEl,
      results,
      results.length ? "— Choisir —" : "Aucun groupe pour cette année",
      selectedGroupe
    );

    // consommer une seule fois (important après POST)
    selectedGroupe = "";
  }

  anneeEl.addEventListener("change", loadGroupes);
  loadGroupes();
})();
