(() => {
  const cfg = window.AZ_ABS_PRATIQUE || {};

  const anneeId = String(cfg.anneeId || "").trim();
  const URL_GROUPES = String(cfg.urlGroupes || "").trim();
  const URL_SEANCES = String(cfg.urlSeances || "").trim();
  const URL_FEUILLE = String(cfg.urlFeuilleBase || "").trim();

  const elN = document.getElementById("id_niveau");
  const elG = document.getElementById("id_groupe");
  const elD = document.getElementById("id_date");
  const btn = document.getElementById("btn_load");
  const box = document.getElementById("seances_box");
  const hint = document.getElementById("hint");

  if (!elN || !elG || !elD || !btn || !box || !hint) return;

  function setHint(text, type = "info") {
    hint.textContent = text;
    hint.dataset.type = type;
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

    // restore if still valid
    if ([...selectEl.options].some(o => o.value === current)) selectEl.value = current;
    else selectEl.value = "";
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!res.ok) return null;
    try { return await res.json(); } catch { return null; }
  }

  function renderSeances(list, dateStr) {
    box.innerHTML = "";

    if (!list || !list.length) {
      box.innerHTML = `<div class="az-seances-empty">Aucune séance pour cette date.</div>`;
      setHint("Aucune séance trouvée pour ce jour.", "warn");
      return;
    }

    setHint("Clique sur une séance pour ouvrir la feuille de présence.", "ok");

    list.forEach(s => {
      const a = document.createElement("a");
      a.className = "az-seance-item";
      a.href = `${URL_FEUILLE}?seance_id=${encodeURIComponent(s.id)}&date=${encodeURIComponent(dateStr)}`;

      a.innerHTML = `
        <div class="meta">
          <div class="title">${escapeHTML(s.label || "Séance")}</div>
          ${s.sub ? `<div class="sub">${escapeHTML(s.sub)}</div>` : `<div class="sub">Feuille de présence</div>`}
        </div>
        <div class="go">➡️</div>
      `;

      box.appendChild(a);
    });
  }

  function escapeHTML(str) {
    return String(str).replace(/[&<>"']/g, m => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[m]));
  }

  async function loadGroupes() {
    if (!anneeId || !URL_GROUPES) return;

    const niveauId = elN.value || "";
    const url = `${URL_GROUPES}?annee=${encodeURIComponent(anneeId)}&niveau=${encodeURIComponent(niveauId)}`;

    elG.disabled = true;
    const data = await fetchJSON(url);
    setOptions(elG, (data && data.results) || [], "— Choisir —");
    elG.disabled = false;
  }

  async function loadSeances() {
    const groupeId = elG.value || "";
    const dateStr = elD.value || "";

    if (!anneeId || !groupeId || !dateStr) {
      setHint("⚠️ Choisis un groupe + une date.", "warn");
      box.innerHTML = "";
      return;
    }

    setHint("Chargement...", "loading");
    box.innerHTML = "";

    const url = `${URL_SEANCES}?annee_id=${encodeURIComponent(anneeId)}&groupe_id=${encodeURIComponent(groupeId)}&date=${encodeURIComponent(dateStr)}`;
    const data = await fetchJSON(url);
    renderSeances((data && data.results) || [], dateStr);
  }

  // Events
  elN.addEventListener("change", async () => {
    await loadGroupes();
    // reset séances after changing niveau
    box.innerHTML = "";
    setHint("Sélectionne un groupe puis clique “Afficher”.");
  });

  btn.addEventListener("click", loadSeances);

  // Auto-load: si déjà groupe+date dans le contexte
  (async () => {
    await loadGroupes();
    if (elG.value && elD.value) {
      await loadSeances();
    }
  })();
})();
