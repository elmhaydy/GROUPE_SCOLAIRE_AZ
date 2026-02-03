(function () {
  const $ = (id) => document.getElementById(id);
  const cfg = window.AZ_WIZ || {};

  // selects
  const niveauSelect = $("niveauSelect");
  const groupeSelect = $("groupeSelect");
  const eleveSelect = $("eleveSelect");
  const fratrieBox = $("fratrieBox");

  // switch buttons
  const btnSco = $("btnSco");
  const btnIns = $("btnIns");
  const btnTr = $("btnTr");
  const btnPack = $("btnPack");
  const typeTransaction = $("typeTransaction");

  // sections
  const blocScolarite = $("blocScolarite");
  const blocInscription = $("blocInscription");
  const blocTransport = $("blocTransport");
  const blocPack = $("blocPack");

  // hidden
  const inscriptionId = $("inscriptionId");
  const echeancesPayload = $("echeancesPayload");
  const transportPayload = $("transportPayload");
  const packPayload = $("packPayload");

  // scolarité ui
  const moisTbody = $("moisTbody");

  // transport ui
  const transportHint = $("transportHint");
  const transportTableWrap = $("transportTableWrap");
  const transportTbody = $("transportTbody");

  // inscription ui
  const montantInscription = $("montantInscription");
  const maxInscriptionTxt = $("maxInscriptionTxt");

  // total
  const totalTxt = $("totalTxt");

  // pack ui
  const packInsOn = $("packInsOn");
  const packScoOn = $("packScoOn");
  const packTrOn = $("packTrOn");

  const packInsBlock = $("packInsBlock");
  const packScoBlock = $("packScoBlock");
  const packTrBlock = $("packTrBlock");

  const packInsAmount = $("packInsAmount");
  const packInsMax = $("packInsMax");

  const packScoTbody = $("packScoTbody");
  const packTrTbody = $("packTrTbody");
  const packTrDisabled = $("packTrDisabled");
  const packTrTableWrap = $("packTrTableWrap");

  // ===== state =====
  let state = {
    inscription_id: null,
    max_inscription: "0.00",

    // scolarité
    sco_echeances: [],
    sco_selected: new Set(),
    sco_prices: {},

    // transport
    tr_enabled: false,
    tr_tarif: "0.00",
    tr_echeances: [],
    tr_selected: new Set(),
    tr_prices: {},
  };

  function esc(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function toNum(v) {
    return parseFloat(String(v ?? "0").replace(",", ".")) || 0;
  }

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    return await res.json();
  }

  // =========================
  // ✅ TRANSPORT GUARD (NEW)
  // =========================
  function clearTransportSelection() {
    state.tr_selected = new Set();
    state.tr_prices = {};
    transportPayload.value = JSON.stringify({ selected_ids: [], prices: {} });
  }

  function applyTransportGuard() {
    const enabled = !!state.tr_enabled;

    // bouton TRANSPORT
    if (btnTr) {
      btnTr.disabled = !enabled;
      btnTr.classList.toggle("is-disabled", !enabled);
      btnTr.title = enabled ? "" : "Transport désactivé pour cet élève";
    }

    // si on est déjà sur TRANSPORT -> retour scolarité
    if (!enabled && typeTransaction.value === "TRANSPORT") {
      setType("SCOLARITE");
    }

    // pack transport checkbox
    if (packTrOn) {
      if (!enabled) {
        packTrOn.checked = false;
        packTrOn.disabled = true;
        clearTransportSelection();
      } else {
        packTrOn.disabled = false;
      }
    }

    // bloc pack transport
    if (!enabled && packTrBlock) {
      packTrBlock.style.display = "none";
    }
  }

  // =========================
  // TYPE SWITCH
  // =========================
  function setType(type) {
    // ✅ empêcher TRANSPORT si désactivé
    if (type === "TRANSPORT" && !state.tr_enabled) {
      if (transportHint) transportHint.style.display = "";
      type = "SCOLARITE";
    }

    typeTransaction.value = type;

    btnSco.classList.toggle("is-active", type === "SCOLARITE");
    btnIns.classList.toggle("is-active", type === "INSCRIPTION");
    btnTr.classList.toggle("is-active", type === "TRANSPORT");
    btnPack.classList.toggle("is-active", type === "PACK");

    blocScolarite.style.display = (type === "SCOLARITE") ? "" : "none";
    blocInscription.style.display = (type === "INSCRIPTION") ? "" : "none";
    blocTransport.style.display = (type === "TRANSPORT") ? "" : "none";
    blocPack.style.display = (type === "PACK") ? "" : "none";

    recomputeAll();
  }

  btnSco.addEventListener("click", () => setType("SCOLARITE"));
  btnIns.addEventListener("click", () => setType("INSCRIPTION"));
  btnTr.addEventListener("click", () => setType("TRANSPORT"));
  btnPack.addEventListener("click", () => setType("PACK"));

  function resetFinanceUI() {
    state = {
      inscription_id: null,
      max_inscription: "0.00",
      sco_echeances: [],
      sco_selected: new Set(),
      sco_prices: {},
      tr_enabled: false,
      tr_tarif: "0.00",
      tr_echeances: [],
      tr_selected: new Set(),
      tr_prices: {},
    };

    inscriptionId.value = "";
    echeancesPayload.value = "";
    transportPayload.value = "";
    packPayload.value = "";

    totalTxt.textContent = "0.00";

    moisTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;
    transportTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;
    packScoTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;
    packTrTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;

    transportHint.style.display = "none";
    transportTableWrap.style.display = "none";

    packTrDisabled.style.display = "none";
    packTrTableWrap.style.display = "none";

    fratrieBox.style.display = "none";
    fratrieBox.innerHTML = "";

    maxInscriptionTxt.textContent = "";
    if (montantInscription) {
      montantInscription.value = "";
      montantInscription.max = "";
      montantInscription.disabled = true;
    }

    if (packInsAmount) {
      packInsAmount.value = "";
      packInsAmount.max = "";
      packInsAmount.disabled = true;
    }
    if (packInsMax) packInsMax.textContent = "";

    applyTransportGuard();
  }

  async function loadGroupes(niveauId) {
    groupeSelect.innerHTML = `<option value="">—</option>`;
    groupeSelect.disabled = true;

    eleveSelect.innerHTML = `<option value="">—</option>`;
    eleveSelect.disabled = true;

    resetFinanceUI();
    if (!niveauId) return;

    const data = await fetchJSON(`${cfg.groupesUrl}?niveau_id=${encodeURIComponent(niveauId)}`);
    const items = data.results || [];

    groupeSelect.innerHTML =
      `<option value="">— Choisir —</option>` +
      items.map(x => `<option value="${x.id}">${esc(x.label)}</option>`).join("");

    groupeSelect.disabled = false;
  }

  async function loadEleves(groupeId) {
    eleveSelect.innerHTML = `<option value="">—</option>`;
    eleveSelect.disabled = true;

    resetFinanceUI();
    if (!groupeId) return;

    const data = await fetchJSON(`${cfg.elevesUrl}?groupe_id=${encodeURIComponent(groupeId)}`);
    const items = data.results || [];

    eleveSelect.innerHTML =
      `<option value="">— Choisir —</option>` +
      items.map(x => `<option value="${x.id}">${esc(x.label)}</option>`).join("");

    eleveSelect.disabled = false;
  }

  function renderTableGeneric(tbody, echeances, selectedSet, pricesMap) {
    if (!echeances.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="az-muted">Aucune échéance.</td></tr>`;
      return;
    }

    tbody.innerHTML = echeances.map(e => {
      const id = String(e.id);
      const isPaid = !!e.is_paye;
      const du = (e.du ?? "0.00");

      const checked = isPaid ? "checked" : (selectedSet.has(id) ? "checked" : "");
      const disabledChk = isPaid ? "disabled" : "";

      const val = pricesMap[id] ?? du;

      return `
        <tr class="${isPaid ? "is-paid" : ""}">
          <td><input type="checkbox" data-eid="${id}" ${checked} ${disabledChk}></td>
          <td>${esc(e.mois_nom)}</td>
          <td>
            ${isPaid
              ? `<strong>${esc(du)} MAD</strong>`
              : `<input class="az-input az-input-mini" type="number" step="0.01" min="0" data-price="${id}" value="${esc(val)}">`
            }
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll("input[type=checkbox][data-eid]").forEach(chk => {
      chk.addEventListener("change", () => {
        if (chk.disabled) return;
        const id = String(chk.dataset.eid);
        if (chk.checked) selectedSet.add(id);
        else selectedSet.delete(id);
        recomputeAll();
      });
    });

    tbody.querySelectorAll("input[type=number][data-price]").forEach(inp => {
      inp.addEventListener("input", () => {
        const id = String(inp.dataset.price);
        pricesMap[id] = inp.value;

        // auto-check
        selectedSet.add(id);
        const chk = tbody.querySelector(`input[type=checkbox][data-eid="${CSS.escape(id)}"]`);
        if (chk && !chk.checked) chk.checked = true;

        recomputeAll();
      });
    });
  }

  function buildPayload(selectedSet, pricesMap) {
    return {
      selected_ids: Array.from(selectedSet)
        .map(x => parseInt(x, 10))
        .filter(n => !Number.isNaN(n)),
      prices: pricesMap
    };
  }

  function sumSelected(echeances, selectedSet, pricesMap) {
    const map = {};
    echeances.forEach(e => { map[String(e.id)] = e; });

    let total = 0.0;
    selectedSet.forEach(id => {
      const e = map[id];
      if (!e) return;
      if (e.is_paye) return;

      const base = (pricesMap[id] ?? e.du ?? "0");
      total += toNum(base);
    });
    return total;
  }

  function recomputeAll() {
    // payloads
    echeancesPayload.value = JSON.stringify(buildPayload(state.sco_selected, state.sco_prices));
    transportPayload.value = JSON.stringify(buildPayload(state.tr_selected, state.tr_prices));

    const type = typeTransaction.value;
    let total = 0.0;

    if (type === "SCOLARITE") {
      total = sumSelected(state.sco_echeances, state.sco_selected, state.sco_prices);
    } else if (type === "TRANSPORT") {
      total = sumSelected(state.tr_echeances, state.tr_selected, state.tr_prices);
    } else if (type === "INSCRIPTION") {
      total = toNum(montantInscription?.value || "0");
    } else if (type === "PACK") {
      const trAllowed = !!state.tr_enabled;

      const pack = {
        ins_on: !!packInsOn?.checked,
        sco_on: !!packScoOn?.checked,
        tr_on: trAllowed ? !!packTrOn?.checked : false,
        ins_amount: packInsAmount?.value || "0.00",
        sco: buildPayload(state.sco_selected, state.sco_prices),
        tr: trAllowed ? buildPayload(state.tr_selected, state.tr_prices) : { selected_ids: [], prices: {} },
      };

      packPayload.value = JSON.stringify(pack);

      if (!trAllowed) {
        clearTransportSelection();
      }

      if (pack.ins_on) total += toNum(pack.ins_amount);
      if (pack.sco_on) total += sumSelected(state.sco_echeances, state.sco_selected, state.sco_prices);
      if (trAllowed && pack.tr_on) total += sumSelected(state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    totalTxt.textContent = total.toFixed(2);

    // pack blocks
    if (packInsBlock) packInsBlock.style.display = packInsOn?.checked ? "" : "none";
    if (packScoBlock) packScoBlock.style.display = packScoOn?.checked ? "" : "none";

    // pack transport block dépend du transport enabled
    if (packTrBlock) {
      const showTr = !!packTrOn?.checked && !!state.tr_enabled;
      packTrBlock.style.display = showTr ? "" : "none";
    }

    applyTransportGuard();
  }

  packInsOn?.addEventListener("change", recomputeAll);
  packScoOn?.addEventListener("change", recomputeAll);
  packTrOn?.addEventListener("change", recomputeAll);
  packInsAmount?.addEventListener("input", recomputeAll);
  montantInscription?.addEventListener("input", recomputeAll);

  async function loadInscriptionAndAll(eleveId) {
    resetFinanceUI();

    moisTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    transportTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    packScoTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    packTrTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;

    const inscData = await fetchJSON(`${cfg.inscByEleveUrl}?eleve_id=${encodeURIComponent(eleveId)}`);
    state.inscription_id = inscData.inscription_id;
    inscriptionId.value = state.inscription_id || "";

    // fratrie
    const fratrie = inscData.fratrie || [];
    if (fratrie.length) {
      fratrieBox.style.display = "";
      fratrieBox.innerHTML = `
        <div class="az-muted">Frères/Sœurs :</div>
        <div class="az-fratrie-list">
          ${fratrie.map(f => `
            <button type="button" class="az-chip" data-eid="${esc(f.id)}">
              ${esc(f.matricule)} — ${esc(f.nom)} ${esc(f.prenom)} ${f.groupe_label ? "• " + esc(f.groupe_label) : ""}
            </button>
          `).join("")}
        </div>
      `;
      fratrieBox.querySelectorAll("button[data-eid]").forEach(btn => {
        btn.addEventListener("click", async () => {
          eleveSelect.value = btn.dataset.eid;
          await loadInscriptionAndAll(btn.dataset.eid);
        });
      });
    }

    if (!state.inscription_id) {
      const msg = `<tr><td colspan="3" class="az-muted">Aucune inscription active pour cet élève.</td></tr>`;
      moisTbody.innerHTML = msg;
      transportTbody.innerHTML = msg;
      packScoTbody.innerHTML = msg;
      packTrTbody.innerHTML = msg;
      applyTransportGuard();
      return;
    }

    // scolarité + reste inscription
    const echData = await fetchJSON(`${cfg.echeancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.sco_echeances = echData.items || [];
    state.max_inscription = echData.tarifs?.reste_inscription || "0.00";

    const maxTxt = `Reste inscription: ${state.max_inscription} MAD`;
    maxInscriptionTxt.textContent = maxTxt;
    if (packInsMax) packInsMax.textContent = maxTxt;

    // ✅ INSCRIPTION input: default = reste, max = reste
    const maxN = toNum(state.max_inscription);
    if (montantInscription) {
      montantInscription.value = (maxN > 0 ? maxN.toFixed(2) : "");
      montantInscription.max = (maxN > 0 ? maxN.toFixed(2) : "0");
      montantInscription.disabled = !(maxN > 0);
    }
    if (packInsAmount) {
      packInsAmount.value = (maxN > 0 ? maxN.toFixed(2) : "");
      packInsAmount.max = (maxN > 0 ? maxN.toFixed(2) : "0");
      packInsAmount.disabled = !(maxN > 0);
    }

    // transport
    const trData = await fetchJSON(`${cfg.transportEcheancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.tr_enabled = !!trData.enabled;
    state.tr_tarif = trData.tarif || "0.00";
    state.tr_echeances = trData.items || [];

    // render scolarité (wizard + pack)
    renderTableGeneric(moisTbody, state.sco_echeances, state.sco_selected, state.sco_prices);
    renderTableGeneric(packScoTbody, state.sco_echeances, state.sco_selected, state.sco_prices);

    // transport display
    if (!state.tr_enabled) {
      transportHint.style.display = "";
      transportTableWrap.style.display = "none";

      packTrDisabled.style.display = "";
      packTrTableWrap.style.display = "none";

      // ✅ force off
      if (packTrOn) packTrOn.checked = false;
      clearTransportSelection();
    } else {
      transportHint.style.display = "none";
      transportTableWrap.style.display = "";

      packTrDisabled.style.display = "none";
      packTrTableWrap.style.display = "";

      renderTableGeneric(transportTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
      renderTableGeneric(packTrTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    applyTransportGuard();
    recomputeAll();
  }

  // events
  niveauSelect.addEventListener("change", () => loadGroupes(niveauSelect.value));
  groupeSelect.addEventListener("change", () => loadEleves(groupeSelect.value));
  eleveSelect.addEventListener("change", () => loadInscriptionAndAll(eleveSelect.value));

  // Prefill
  const p = window.__PREFILL__ || {};
  if (p.niveau_id) {
    niveauSelect.value = p.niveau_id;
    loadGroupes(p.niveau_id).then(() => {
      if (p.groupe_id) {
        groupeSelect.value = p.groupe_id;
        loadEleves(p.groupe_id).then(() => {
          if (p.eleve_id) {
            eleveSelect.value = p.eleve_id;
            loadInscriptionAndAll(p.eleve_id);
          }
        });
      }
    });
  }

  // default
  setType("SCOLARITE");
})();
