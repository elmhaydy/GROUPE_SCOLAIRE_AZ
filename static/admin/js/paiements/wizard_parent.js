/* =========================================
   AZ • Paiements Wizard — MODE PARENT (FINAL)
   - Parent searchable (TomSelect)
   - Enfants chargés par parent
   - Paiement multi-enfants => batch_payload (un seul reçu)
   - Transport guard OK
   ========================================= */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const cfg = window.AZ_WIZ || {};

  // selects
  const parentSelect = $("parentSelect");
  const eleveSelect = $("eleveSelect");
  const eleveHint = $("eleveHint");

  // switch
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
  const batchPayload = $("batchPayload");

  // UI
  const moisTbody = $("moisTbody");
  const transportHint = $("transportHint");
  const transportTableWrap = $("transportTableWrap");
  const transportTbody = $("transportTbody");

  const montantInscription = $("montantInscription");
  const maxInscriptionTxt = $("maxInscriptionTxt");
  const totalTxt = $("totalTxt");

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

  // cart
  const cartBox = $("cartBox");
  const btnAddToCart = $("btnAddToCart");
  const btnClearCart = $("btnClearCart");

  let parentTS = null;

  const state = {
    parent_id: null,
    currentEleveId: null,
    currentEleveLabel: "",
    inscription_id: null,

    // scolarité
    sco_echeances: [],
    sco_selected: new Set(),
    sco_prices: {},

    // transport
    tr_enabled: false,
    tr_echeances: [],
    tr_selected: new Set(),
    tr_prices: {},

    max_inscription: "0.00",

    // panier multi-enfants
    cart: new Map(), // eleve_id -> snapshot
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

  function safeParse(raw, fallback) {
    try { return JSON.parse(raw); } catch (e) { return fallback; }
  }

  // ---------- TYPE SWITCH ----------
  function setType(type) {
    if (type === "TRANSPORT" && !state.tr_enabled) {
      type = "SCOLARITE";
    }
    typeTransaction.value = type;

    btnSco?.classList.toggle("is-active", type === "SCOLARITE");
    btnIns?.classList.toggle("is-active", type === "INSCRIPTION");
    btnTr?.classList.toggle("is-active", type === "TRANSPORT");
    btnPack?.classList.toggle("is-active", type === "PACK");

    blocScolarite.style.display = (type === "SCOLARITE") ? "" : "none";
    blocInscription.style.display = (type === "INSCRIPTION") ? "" : "none";
    blocTransport.style.display = (type === "TRANSPORT") ? "" : "none";
    blocPack.style.display = (type === "PACK") ? "" : "none";

    recompute();
  }

  btnSco?.addEventListener("click", () => setType("SCOLARITE"));
  btnIns?.addEventListener("click", () => setType("INSCRIPTION"));
  btnTr?.addEventListener("click", () => setType("TRANSPORT"));
  btnPack?.addEventListener("click", () => setType("PACK"));

  // ---------- RENDER TABLE ----------
  function renderTable(tbody, echeances, selectedSet, pricesMap) {
    if (!tbody) return;

    if (!echeances.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="az-muted">Aucune échéance.</td></tr>`;
      return;
    }

    tbody.innerHTML = echeances.map(e => {
      const id = String(e.id);
      const isPaid = !!e.is_paye || e.statut === "PAYE";
      const du = (e.du ?? "0.00");
      const checked = isPaid ? "checked" : (selectedSet.has(id) ? "checked" : "");
      const disabled = isPaid ? "disabled" : "";
      const val = pricesMap[id] ?? du;

      return `
        <tr class="${isPaid ? "is-paid" : ""}">
          <td><input type="checkbox" data-id="${esc(id)}" ${checked} ${disabled}></td>
          <td>${esc(e.mois_nom)}</td>
          <td>
            ${isPaid
              ? `<strong>${esc(du)} MAD</strong>`
              : `<input class="az-input az-input-mini" type="number" step="0.01" min="0" data-price="${esc(id)}" value="${esc(val)}">`
            }
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll('input[type="checkbox"][data-id]').forEach(chk => {
      chk.addEventListener("change", () => {
        if (chk.disabled) return;
        const id = String(chk.dataset.id);
        if (chk.checked) selectedSet.add(id);
        else selectedSet.delete(id);
        recompute();
      });
    });

    tbody.querySelectorAll('input[type="number"][data-price]').forEach(inp => {
      inp.addEventListener("input", () => {
        const id = String(inp.dataset.price);
        pricesMap[id] = inp.value;

        selectedSet.add(id);
        const chk = tbody.querySelector(`input[type="checkbox"][data-id="${CSS.escape(id)}"]`);
        if (chk && !chk.checked) chk.checked = true;

        recompute();
      });
    });
  }

  function buildPayload(selectedSet, pricesMap) {
    return {
      selected_ids: Array.from(selectedSet).map(x => parseInt(x, 10)).filter(n => !Number.isNaN(n)),
      prices: pricesMap
    };
  }

  function sumSelected(echeances, selectedSet, pricesMap) {
    const map = {};
    echeances.forEach(e => { map[String(e.id)] = e; });

    let total = 0;
    selectedSet.forEach(id => {
      const e = map[id];
      if (!e) return;
      if (e.is_paye || e.statut === "PAYE") return;
      total += toNum(pricesMap[id] ?? e.du ?? "0");
    });
    return total;
  }

  // ---------- TRANSPORT GUARD ----------
  function clearTransport() {
    state.tr_selected = new Set();
    state.tr_prices = {};
    transportPayload.value = JSON.stringify({ selected_ids: [], prices: {} });
  }

  function applyTransportGuard() {
    const enabled = !!state.tr_enabled;

    btnTr.disabled = !enabled;
    btnTr.classList.toggle("is-disabled", !enabled);

    if (!enabled && typeTransaction.value === "TRANSPORT") {
      setType("SCOLARITE");
    }

    // pack transport
    if (!enabled) {
      packTrOn.checked = false;
      packTrOn.disabled = true;
      packTrDisabled.style.display = "";
      packTrTableWrap.style.display = "none";
      clearTransport();
    } else {
      packTrOn.disabled = false;
      packTrDisabled.style.display = "none";
    }
  }

  // ---------- RESET CURRENT CHILD FINANCE ----------
  function resetChildFinance() {
    state.currentEleveId = null;
    state.currentEleveLabel = "";
    state.inscription_id = null;

    state.sco_echeances = [];
    state.sco_selected = new Set();
    state.sco_prices = {};

    state.tr_enabled = false;
    state.tr_echeances = [];
    state.tr_selected = new Set();
    state.tr_prices = {};

    state.max_inscription = "0.00";

    inscriptionId.value = "";
    echeancesPayload.value = "";
    transportPayload.value = "";
    packPayload.value = "";

    moisTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un enfant…</td></tr>`;
    transportTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un enfant…</td></tr>`;
    packScoTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un enfant…</td></tr>`;
    packTrTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un enfant…</td></tr>`;

    transportHint.style.display = "none";
    transportTableWrap.style.display = "none";

    maxInscriptionTxt.textContent = "";
    montantInscription.value = "";
    montantInscription.disabled = true;

    packInsAmount.value = "";
    packInsAmount.disabled = true;
    packInsMax.textContent = "";

    btnAddToCart.disabled = true;
    recompute();
  }

  // ---------- CART UI ----------
  function updateCartUI() {
    const items = Array.from(state.cart.values());

    if (!items.length) {
      cartBox.style.display = "none";
      cartBox.innerHTML = "";
      btnClearCart.style.display = "none";
    } else {
      cartBox.style.display = "";
      btnClearCart.style.display = "";
      cartBox.innerHTML = items.map(it => `
        <span class="az-chip is-active" style="cursor:default;">
          ${esc(it.label)}
          <button type="button" class="az-chip" data-rm="${esc(it.eleve_id)}" style="margin-left:8px;">✕</button>
        </span>
      `).join(" ");

      cartBox.querySelectorAll("button[data-rm]").forEach(b => {
        b.addEventListener("click", () => {
          state.cart.delete(String(b.dataset.rm));
          recompute();
          updateCartUI();
        });
      });
    }

    // batch si 2+
    if (items.length >= 2) {
      batchPayload.value = JSON.stringify({
        type_transaction: String(typeTransaction.value || "SCOLARITE"),
        items: items.map(it => ({
          inscription_id: it.inscription_id,
          echeances_payload: it.echeances_payload,
          transport_payload: it.transport_payload,
          pack_payload: it.pack_payload,
          montant_inscription: it.montant_inscription
        }))
      });
    } else {
      batchPayload.value = "";
    }
  }

  btnAddToCart?.addEventListener("click", () => {
    if (!state.currentEleveId || !state.inscription_id) return;
    const key = String(state.currentEleveId);
    if (state.cart.has(key)) return;

    const scoSnap = safeParse(echeancesPayload.value || "", { selected_ids: [], prices: {} });
    const trSnap  = safeParse(transportPayload.value || "", { selected_ids: [], prices: {} });
    const packSnap = safeParse(packPayload.value || "", {});

    state.cart.set(key, {
      eleve_id: key,
      label: state.currentEleveLabel || `Élève #${key}`,
      inscription_id: String(state.inscription_id),
      echeances_payload: scoSnap,
      transport_payload: trSnap,
      pack_payload: packSnap,
      montant_inscription: (montantInscription.value || "0.00"),
    });

    updateCartUI();
  });

  btnClearCart?.addEventListener("click", () => {
    state.cart = new Map();
    updateCartUI();
    recompute();
  });

  // ---------- RECOMPUTE ----------
  function recompute() {
    echeancesPayload.value = JSON.stringify(buildPayload(state.sco_selected, state.sco_prices));
    transportPayload.value = JSON.stringify(buildPayload(state.tr_selected, state.tr_prices));

    const type = String(typeTransaction.value || "SCOLARITE");
    let total = 0;

    if (type === "SCOLARITE") {
      total = sumSelected(state.sco_echeances, state.sco_selected, state.sco_prices);
    } else if (type === "TRANSPORT") {
      total = sumSelected(state.tr_echeances, state.tr_selected, state.tr_prices);
    } else if (type === "INSCRIPTION") {
      total = toNum(montantInscription.value || "0");
    } else if (type === "PACK") {
      const pack = {
        ins_on: !!packInsOn.checked,
        sco_on: !!packScoOn.checked,
        tr_on: state.tr_enabled ? !!packTrOn.checked : false,
        ins_amount: packInsAmount.value || "0.00",
        sco: buildPayload(state.sco_selected, state.sco_prices),
        tr: state.tr_enabled ? buildPayload(state.tr_selected, state.tr_prices) : { selected_ids: [], prices: {} },
      };
      packPayload.value = JSON.stringify(pack);

      if (pack.ins_on) total += toNum(pack.ins_amount);
      if (pack.sco_on) total += sumSelected(state.sco_echeances, state.sco_selected, state.sco_prices);
      if (pack.tr_on && state.tr_enabled) total += sumSelected(state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    totalTxt.textContent = total.toFixed(2);

    packInsBlock.style.display = packInsOn.checked ? "" : "none";
    packScoBlock.style.display = packScoOn.checked ? "" : "none";
    packTrBlock.style.display = (packTrOn.checked && state.tr_enabled) ? "" : "none";

    // enable add to cart
    const canAdd = !!state.currentEleveId && !!state.inscription_id && !state.cart.has(String(state.currentEleveId));
    btnAddToCart.disabled = !canAdd;

    updateCartUI();
  }

  packInsOn?.addEventListener("change", recompute);
  packScoOn?.addEventListener("change", recompute);
  packTrOn?.addEventListener("change", recompute);
  packInsAmount?.addEventListener("input", recompute);
  montantInscription?.addEventListener("input", recompute);

  // ---------- LOAD CHILD FINANCE ----------
  async function loadFinanceForEleve(eleveId, eleveLabel) {
    resetChildFinance();

    state.currentEleveId = String(eleveId);
    state.currentEleveLabel = String(eleveLabel || "");
    eleveHint.textContent = state.currentEleveLabel ? `Sélection: ${state.currentEleveLabel}` : "";

    moisTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    transportTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    packScoTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    packTrTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;

    // 👉 on utilise ton endpoint existant (inscription-by-eleve) ? NON ici on a direct inscription via enfantsByParent
    // Donc on va récupérer inscription_id depuis l’option data-insc.
    const opt = eleveSelect.options[eleveSelect.selectedIndex];
    const inscId = opt ? opt.getAttribute("data-insc") : "";
    state.inscription_id = inscId || null;
    inscriptionId.value = state.inscription_id || "";

    if (!state.inscription_id) {
      const msg = `<tr><td colspan="3" class="az-muted">Aucune inscription active pour cet élève.</td></tr>`;
      moisTbody.innerHTML = msg;
      transportTbody.innerHTML = msg;
      packScoTbody.innerHTML = msg;
      packTrTbody.innerHTML = msg;
      applyTransportGuard();
      recompute();
      return;
    }

    // echeances scolarité
    const echData = await fetchJSON(`${cfg.echeancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.sco_echeances = echData.items || [];
    state.max_inscription = echData.tarifs?.reste_inscription || "0.00";

    const maxTxt = `Reste inscription: ${state.max_inscription} MAD`;
    maxInscriptionTxt.textContent = maxTxt;
    packInsMax.textContent = maxTxt;

    const maxN = toNum(state.max_inscription);
    montantInscription.value = (maxN > 0 ? maxN.toFixed(2) : "");
    montantInscription.disabled = !(maxN > 0);

    packInsAmount.value = (maxN > 0 ? maxN.toFixed(2) : "");
    packInsAmount.disabled = !(maxN > 0);

    // transport
    const trData = await fetchJSON(`${cfg.transportEcheancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.tr_enabled = !!trData.enabled;
    state.tr_echeances = trData.items || [];

    renderTable(moisTbody, state.sco_echeances, state.sco_selected, state.sco_prices);
    renderTable(packScoTbody, state.sco_echeances, state.sco_selected, state.sco_prices);

    if (!state.tr_enabled) {
      transportHint.style.display = "";
      transportTableWrap.style.display = "none";
      packTrDisabled.style.display = "";
      packTrTableWrap.style.display = "none";
      packTrOn.checked = false;
      clearTransport();
    } else {
      transportHint.style.display = "none";
      transportTableWrap.style.display = "";
      packTrDisabled.style.display = "none";
      packTrTableWrap.style.display = "";
      renderTable(transportTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
      renderTable(packTrTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    applyTransportGuard();
    recompute();
  }

  // ---------- LOAD ENFANTS BY PARENT ----------
  async function loadEnfants(parentId) {
    eleveSelect.innerHTML = `<option value="">— Choisir —</option>`;
    eleveSelect.disabled = true;
    eleveHint.textContent = "";
    resetChildFinance();

    if (!parentId) return;

    const data = await fetchJSON(`${cfg.enfantsByParentUrl}?parent_id=${encodeURIComponent(parentId)}`);
    const items = data.items || data.results || [];

    if (!items.length) {
      eleveSelect.innerHTML = `<option value="">— Aucun enfant —</option>`;
      eleveSelect.disabled = true;
      return;
    }

    eleveSelect.innerHTML =
      `<option value="">— Choisir —</option>` +
      items.map(it => `
        <option value="${esc(it.eleve_id)}" data-insc="${esc(it.inscription_id || "")}">
          ${esc(it.label)}
        </option>
      `).join("");

    eleveSelect.disabled = false;
  }

  eleveSelect?.addEventListener("change", () => {
    const opt = eleveSelect.options[eleveSelect.selectedIndex];
    const eid = eleveSelect.value;
    const label = opt ? opt.textContent.trim() : "";
    if (eid) loadFinanceForEleve(eid, label);
  });

  // ---------- TOMSELECT PARENT ----------
  function initParentTS() {
    if (typeof TomSelect === "undefined") return;
    if (!parentSelect) return;

    parentTS = new TomSelect(parentSelect, {
      create: false,
      allowEmptyOption: true,
      maxOptions: 50,
      placeholder: "Tape nom / CIN / téléphone…",
      valueField: "value",
      labelField: "text",
      searchField: ["text"],
      dropdownParent: "body",
      preload: true,

      render: {
        no_results: () => `<div class="no-results" style="padding:10px;color:#94a3b8;">Aucun parent</div>`,
        option: (data, escape) => `<div class="option">${escape(data.text)}</div>`,
        item: (data, escape) => `<div class="item">${escape(data.text)}</div>`,
      },

      load: async (query, callback) => {
        try {
          const q = (query || "").trim();
          const baseUrl = cfg.parentsSearchUrl;
          if (!baseUrl) return callback([]);
          const params = new URLSearchParams();
          params.set("q", q);
          const data = await fetchJSON(`${baseUrl}?${params.toString()}`);
          const items = data.items || data.results || [];
          callback(items.map(x => ({ value: String(x.id), text: String(x.label) })));
        } catch (e) {
          callback([]);
        }
      },

      onChange: (val) => {
        const pid = String(val || "");
        state.parent_id = pid || null;
        state.cart = new Map(); // nouveau parent => reset panier
        updateCartUI();
        loadEnfants(pid);
      }
    });
  }

  // init
  initParentTS();
  setType("SCOLARITE");
})();
