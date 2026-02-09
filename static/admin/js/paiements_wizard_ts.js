/* =========================================
   AZ • Paiements Wizard (FINAL)
   - ÉLÈVE toujours searchable (TomSelect) même si Niveau/Groupe vides
   - Niveau/Groupe = filtres OPTIONNELS (ne bloquent jamais l’élève)
   - Transport guard conservé
   - Panier fratrie/batch conservé
   ========================================= */

(function () {
  const $ = (id) => document.getElementById(id);
  const cfg = window.AZ_WIZ || {};

  // selects
  const niveauSelect = $("niveauSelect");
  const groupeSelect = $("groupeSelect");
  const eleveSelect = $("eleveSelect");
  const fratrieBox = $("fratrieBox");

  // fratrie cart (NEW UI)
  const fratrieCart = $("fratrieCart");
  const btnAddToFratrie = $("btnAddToFratrie");
  const btnClearFratrie = $("btnClearFratrie");
  const fratriePayload = $("fratriePayload"); // optional
  const batchPayload = $("batchPayload");     // required

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

  // TomSelect instance
  let eleveTS = null;

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

    // fratrie data
    fratrie: [],

    // ✅ panier fratrie (batch)
    cartEleves: new Map(), // eleve_id -> snapshot data
    currentEleveId: null,
    currentEleveLabel: "",
  };

  // ---------- utils ----------
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

  function safeParseJSON(raw, fallback) {
    try {
      const x = JSON.parse(raw);
      return x ?? fallback;
    } catch (e) {
      return fallback;
    }
  }

  function getSelectedEleveLabel() {
    // quand TomSelect charge via API, l’option existe côté TS, pas toujours côté <select>.
    // On garde un fallback sûr.
    const opt = eleveSelect?.options?.[eleveSelect.selectedIndex];
    return opt ? opt.textContent.trim() : (state.currentEleveLabel || "");
  }

  // =========================
  // TOMSELECT (ÉLÈVE) — toujours actif
  // =========================
  function initEleveTomSelect() {
    if (typeof TomSelect === "undefined") return;
    if (!eleveSelect) return;

    if (eleveTS) {
      try { eleveTS.destroy(); } catch (e) {}
      eleveTS = null;
    }

    // ✅ ne jamais désactiver l’élève
    eleveSelect.disabled = false;

    eleveTS = new TomSelect(eleveSelect, {
      create: false,
      allowEmptyOption: true,
      maxOptions: 80,
      placeholder: "Tape matricule / nom…",
      valueField: "value",
      labelField: "text",
      searchField: ["text"],
      dropdownParent: "body", // ✅ évite clipping
      preload: true,

      render: {
        no_results: () =>
          `<div class="no-results" style="padding:10px;color:#94a3b8;">Aucun élève</div>`,
        option: (data, escape) =>
          `<div class="option">${escape(data.text)}</div>`,
        item: (data, escape) =>
          `<div class="item">${escape(data.text)}</div>`,
      },

      load: async (query, callback) => {
        try {
          const q = (query || "").trim();
          const gid = (groupeSelect?.value || "").trim();

          // ✅ URL de recherche (priorité)
          const baseUrl = cfg.elevesSearchUrl || cfg.elevesUrl;
          if (!baseUrl) return callback([]);

          const params = new URLSearchParams();
          params.set("q", q);

          // ✅ filtre optionnel par groupe
          if (gid) {
            params.set("groupe_id", gid);
            params.set("groupe", gid);
          }

          const data = await fetchJSON(`${baseUrl}?${params.toString()}`);

          const items =
            data.results ||
            data.items ||
            data.eleves ||
            data.data ||
            (Array.isArray(data) ? data : []);

          const list = (Array.isArray(items) ? items : [])
            .map(x => {
              const id = String(x.id ?? x.pk ?? x.value ?? "");
              const label = String(
                x.label ??
                x.nom ??
                x.text ??
                x.name ??
                `${x.matricule || ""} ${x.prenom || ""} ${x.nom_famille || ""}`.trim()
              ).trim();
              return { value: id, text: label };
            })
            .filter(o => o.value && o.text);

          callback(list);
        } catch (e) {
          callback([]);
        }
      },

      onDropdownOpen: () => {
        try { eleveTS?.focus(); } catch (e) {}
      },

      onChange: (val) => {
        if (!val) return;
        const id = String(val);
        // snapshot label depuis TomSelect
        try {
          const opt = eleveTS?.options?.[id];
          if (opt?.text) state.currentEleveLabel = String(opt.text);
        } catch (e) {}

        eleveSelect.value = id;
        loadInscriptionAndAll(id);
      }
    });
  }

  // =========================
  // ✅ TRANSPORT GUARD
  // =========================
  function clearTransportSelection() {
    state.tr_selected = new Set();
    state.tr_prices = {};
    transportPayload.value = JSON.stringify({ selected_ids: [], prices: {} });
  }

  function applyTransportGuard() {
    const enabled = !!state.tr_enabled;

    if (btnTr) {
      btnTr.disabled = !enabled;
      btnTr.classList.toggle("is-disabled", !enabled);
      btnTr.title = enabled ? "" : "Transport désactivé pour cet élève";
    }

    if (!enabled && typeTransaction.value === "TRANSPORT") {
      setType("SCOLARITE");
    }

    if (packTrOn) {
      if (!enabled) {
        packTrOn.checked = false;
        packTrOn.disabled = true;
        clearTransportSelection();
      } else {
        packTrOn.disabled = false;
      }
    }

    if (!enabled && packTrBlock) {
      packTrBlock.style.display = "none";
    }
  }

  // =========================
  // TYPE SWITCH
  // =========================
  function setType(type) {
    if (type === "TRANSPORT" && !state.tr_enabled) {
      if (transportHint) transportHint.style.display = "";
      type = "SCOLARITE";
    }

    typeTransaction.value = type;

    btnSco?.classList.toggle("is-active", type === "SCOLARITE");
    btnIns?.classList.toggle("is-active", type === "INSCRIPTION");
    btnTr?.classList.toggle("is-active", type === "TRANSPORT");
    btnPack?.classList.toggle("is-active", type === "PACK");

    if (blocScolarite) blocScolarite.style.display = (type === "SCOLARITE") ? "" : "none";
    if (blocInscription) blocInscription.style.display = (type === "INSCRIPTION") ? "" : "none";
    if (blocTransport) blocTransport.style.display = (type === "TRANSPORT") ? "" : "none";
    if (blocPack) blocPack.style.display = (type === "PACK") ? "" : "none";

    recomputeAll();
  }

  btnSco?.addEventListener("click", () => setType("SCOLARITE"));
  btnIns?.addEventListener("click", () => setType("INSCRIPTION"));
  btnTr?.addEventListener("click", () => setType("TRANSPORT"));
  btnPack?.addEventListener("click", () => setType("PACK"));

  // =========================
  // RESET UI finance (sans toucher TomSelect élève)
  // =========================
  function resetFinanceUI({ keepCart = true } = {}) {
    const oldCart = new Map(state.cartEleves);

    state.inscription_id = null;
    state.max_inscription = "0.00";
    state.sco_echeances = [];
    state.sco_selected = new Set();
    state.sco_prices = {};
    state.tr_enabled = false;
    state.tr_tarif = "0.00";
    state.tr_echeances = [];
    state.tr_selected = new Set();
    state.tr_prices = {};
    state.fratrie = [];
    state.currentEleveId = null;
    // state.currentEleveLabel => on garde si besoin (pas grave)
    // mais on peut vider :
    state.currentEleveLabel = "";

    if (!keepCart) state.cartEleves = new Map();
    else state.cartEleves = oldCart;

    if (inscriptionId) inscriptionId.value = "";
    if (echeancesPayload) echeancesPayload.value = "";
    if (transportPayload) transportPayload.value = "";
    if (packPayload) packPayload.value = "";
    if (fratriePayload) fratriePayload.value = "";
    if (batchPayload) batchPayload.value = "";

    if (totalTxt) totalTxt.textContent = "0.00";

    if (moisTbody) moisTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;
    if (transportTbody) transportTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;
    if (packScoTbody) packScoTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;
    if (packTrTbody) packTrTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;

    if (transportHint) transportHint.style.display = "none";
    if (transportTableWrap) transportTableWrap.style.display = "none";

    if (packTrDisabled) packTrDisabled.style.display = "none";
    if (packTrTableWrap) packTrTableWrap.style.display = "none";

    if (fratrieBox) {
      fratrieBox.style.display = "none";
      fratrieBox.innerHTML = "";
    }

    if (maxInscriptionTxt) maxInscriptionTxt.textContent = "";
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
    updateCartUI();
  }

  // =========================
  // CART UI
  // =========================
  function updateCartUI() {
    if (!fratrieCart || !btnAddToFratrie || !btnClearFratrie) return;

    const items = Array.from(state.cartEleves.values());

    const canAdd =
      !!state.currentEleveId &&
      !!state.inscription_id &&
      !state.cartEleves.has(String(state.currentEleveId));

    btnAddToFratrie.disabled = !canAdd;

    if (!items.length) {
      fratrieCart.style.display = "none";
      fratrieCart.innerHTML = "";
      btnClearFratrie.style.display = "none";
    } else {
      fratrieCart.style.display = "";
      btnClearFratrie.style.display = "";

      fratrieCart.innerHTML = items.map(it => `
        <span class="az-chip is-active" style="cursor:default;">
          ${esc(it.label)}
          <button type="button" class="az-chip" data-remove="${esc(it.id)}" style="margin-left:8px;">✕</button>
        </span>
      `).join(" ");

      fratrieCart.querySelectorAll("button[data-remove]").forEach(b => {
        b.addEventListener("click", () => {
          const id = String(b.dataset.remove);
          state.cartEleves.delete(id);
          recomputeAll();
          updateCartUI();
        });
      });
    }

    if (fratriePayload) {
      fratriePayload.value = JSON.stringify({
        eleves: items.map(x => ({ eleve_id: x.id, inscription_id: x.inscription_id }))
      });
    }
  }

  btnAddToFratrie?.addEventListener("click", () => {
    if (!state.currentEleveId || !state.inscription_id) return;

    const id = String(state.currentEleveId);
    if (state.cartEleves.has(id)) return;

    const scoSnap = safeParseJSON(echeancesPayload?.value || "", { selected_ids: [], prices: {} });
    const trSnap  = safeParseJSON(transportPayload?.value || "", { selected_ids: [], prices: {} });
    const packSnap = safeParseJSON(packPayload?.value || "", {});

    state.cartEleves.set(id, {
      id,
      eleve_id: id,
      inscription_id: String(state.inscription_id),
      label: state.currentEleveLabel || `Élève #${id}`,

      type_transaction: String(typeTransaction?.value || "SCOLARITE"),
      echeances_payload: scoSnap,
      transport_payload: trSnap,
      pack_payload: packSnap,
      montant_inscription: (montantInscription?.value || "0.00"),
    });

    recomputeAll();
    updateCartUI();
  });

  btnClearFratrie?.addEventListener("click", () => {
    state.cartEleves = new Map();
    recomputeAll();
    updateCartUI();
  });

  // =========================
  // fratrie buttons
  // =========================
  function renderFratrieButtons() {
    const fr = Array.isArray(state.fratrie) ? state.fratrie : [];
    if (!fratrieBox) return;

    if (!fr.length) {
      fratrieBox.style.display = "none";
      fratrieBox.innerHTML = "";
      return;
    }

    fratrieBox.style.display = "";
    fratrieBox.innerHTML = `
      <div class="az-muted">Frères/Sœurs :</div>
      <div class="az-fratrie-list">
        ${fr.map(f => `
          <button type="button" class="az-chip" data-eid="${esc(f.id)}">
            ${esc(f.matricule)} — ${esc(f.nom)} ${esc(f.prenom)} ${f.groupe_label ? "• " + esc(f.groupe_label) : ""}
          </button>
        `).join("")}
      </div>
      <div class="az-muted" style="margin-top:8px;">
        Astuce: clique un frère/sœur puis “+ Ajouter…” pour le panier.
      </div>
    `;

    fratrieBox.querySelectorAll("button[data-eid]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const eid = String(btn.dataset.eid);

        // ✅ sélection dans TomSelect
        if (eleveTS) {
          try { eleveTS.setValue(eid, true); } catch (e) {}
          try {
            const opt = eleveTS?.options?.[eid];
            if (opt?.text) state.currentEleveLabel = String(opt.text);
          } catch (e) {}
        } else {
          eleveSelect.value = eid;
        }

        await loadInscriptionAndAll(eid);
      });
    });
  }

  // =========================
  // tables + payload
  // =========================
  function renderTableGeneric(tbody, echeances, selectedSet, pricesMap) {
    if (!tbody) return;

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

  function buildBatchPayloadIfNeeded() {
    if (!batchPayload) return;

    const items = Array.from(state.cartEleves.values());

    // batch seulement si 2+ élèves
    if (items.length < 2) {
      batchPayload.value = "";
      return;
    }

    batchPayload.value = JSON.stringify({
      type_transaction: String(typeTransaction?.value || "SCOLARITE"),
      items: items.map(it => ({
        inscription_id: it.inscription_id,
        type_transaction: it.type_transaction,
        echeances_payload: it.echeances_payload,
        transport_payload: it.transport_payload,
        pack_payload: it.pack_payload,
        montant_inscription: it.montant_inscription
      }))
    });
  }

  function recomputeAll() {
    if (echeancesPayload) echeancesPayload.value = JSON.stringify(buildPayload(state.sco_selected, state.sco_prices));
    if (transportPayload) transportPayload.value = JSON.stringify(buildPayload(state.tr_selected, state.tr_prices));

    const type = String(typeTransaction?.value || "SCOLARITE");
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

      if (packPayload) packPayload.value = JSON.stringify(pack);

      if (!trAllowed) clearTransportSelection();

      if (pack.ins_on) total += toNum(pack.ins_amount);
      if (pack.sco_on) total += sumSelected(state.sco_echeances, state.sco_selected, state.sco_prices);
      if (trAllowed && pack.tr_on) total += sumSelected(state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    if (totalTxt) totalTxt.textContent = total.toFixed(2);

    if (packInsBlock) packInsBlock.style.display = packInsOn?.checked ? "" : "none";
    if (packScoBlock) packScoBlock.style.display = packScoOn?.checked ? "" : "none";

    if (packTrBlock) {
      const showTr = !!packTrOn?.checked && !!state.tr_enabled;
      packTrBlock.style.display = showTr ? "" : "none";
    }

    applyTransportGuard();
    buildBatchPayloadIfNeeded();
  }

  packInsOn?.addEventListener("change", recomputeAll);
  packScoOn?.addEventListener("change", recomputeAll);
  packTrOn?.addEventListener("change", recomputeAll);
  packInsAmount?.addEventListener("input", recomputeAll);
  montantInscription?.addEventListener("input", recomputeAll);

  // =========================
  // load by niveau/groupe/eleve
  // =========================
  async function loadGroupes(niveauId) {
    if (!groupeSelect) return;

    groupeSelect.innerHTML = `<option value="">—</option>`;
    groupeSelect.disabled = true;

    // ✅ reset finance mais élève reste searchable
    resetFinanceUI({ keepCart: true });

    // ✅ pas de niveau => stop. (élève global OK)
    if (!niveauId) return;

    const data = await fetchJSON(`${cfg.groupesUrl}?niveau_id=${encodeURIComponent(niveauId)}`);
    const items = data.results || data.items || data.groupes || data.data || (Array.isArray(data) ? data : []);

    groupeSelect.innerHTML =
      `<option value="">— Choisir —</option>` +
      (items || []).map(x => `<option value="${x.id}">${esc(x.label || x.nom || x.text || x.name)}</option>`).join("");

    groupeSelect.disabled = false;
  }

  async function loadEleves(groupeId) {
    // ✅ reset finance mais élève reste searchable
    resetFinanceUI({ keepCart: true });

    // ✅ important: on ne disable jamais eleveSelect
    if (eleveSelect) eleveSelect.disabled = false;
    if (eleveTS) {
      try { eleveTS.enable(); } catch (e) {}
      try { eleveTS.clear(true); } catch (e) {}
    }

    // ✅ si pas de groupe => rien à précharger (recherche globale fonctionne)
    if (!groupeId) return;

    // (OPTIONNEL) préchargement des élèves du groupe dans TomSelect
    const url = `${cfg.elevesUrl}?groupe_id=${encodeURIComponent(groupeId)}&groupe=${encodeURIComponent(groupeId)}`;
    const data = await fetchJSON(url);

    const items =
      data.results ||
      data.items ||
      data.eleves ||
      data.data ||
      (Array.isArray(data) ? data : []);

    const finalItems = Array.isArray(items) ? items : [];

    if (eleveTS) {
      try {
        eleveTS.clearOptions();
        finalItems.forEach(x => {
          const id = String(x.id ?? x.pk ?? x.value ?? "");
          const label = String(
            x.label ??
            x.nom ??
            x.text ??
            x.name ??
            `${x.matricule || ""} ${x.prenom || ""} ${x.nom_famille || ""}`.trim()
          ).trim();
          if (id && label) eleveTS.addOption({ value: id, text: label });
        });
        eleveTS.refreshOptions(false);
        eleveTS.enable();
      } catch (e) {}
    }
  }

  async function loadInscriptionAndAll(eleveId) {
    resetFinanceUI({ keepCart: true });

    state.currentEleveId = String(eleveId);
    state.currentEleveLabel = state.currentEleveLabel || getSelectedEleveLabel();

    if (moisTbody) moisTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    if (transportTbody) transportTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    if (packScoTbody) packScoTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    if (packTrTbody) packTrTbody.innerHTML = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;

    const inscData = await fetchJSON(`${cfg.inscByEleveUrl}?eleve_id=${encodeURIComponent(eleveId)}`);
    state.inscription_id = inscData.inscription_id;
    if (inscriptionId) inscriptionId.value = state.inscription_id || "";

    state.fratrie = inscData.fratrie || [];
    renderFratrieButtons();
    updateCartUI();

    if (!state.inscription_id) {
      const msg = `<tr><td colspan="3" class="az-muted">Aucune inscription active pour cet élève.</td></tr>`;
      if (moisTbody) moisTbody.innerHTML = msg;
      if (transportTbody) transportTbody.innerHTML = msg;
      if (packScoTbody) packScoTbody.innerHTML = msg;
      if (packTrTbody) packTrTbody.innerHTML = msg;
      applyTransportGuard();
      recomputeAll();
      return;
    }

    const echData = await fetchJSON(`${cfg.echeancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.sco_echeances = echData.items || [];
    state.max_inscription = echData.tarifs?.reste_inscription || "0.00";

    const maxTxt = `Reste inscription: ${state.max_inscription} MAD`;
    if (maxInscriptionTxt) maxInscriptionTxt.textContent = maxTxt;
    if (packInsMax) packInsMax.textContent = maxTxt;

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

    const trData = await fetchJSON(`${cfg.transportEcheancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.tr_enabled = !!trData.enabled;
    state.tr_tarif = trData.tarif || "0.00";
    state.tr_echeances = trData.items || [];

    renderTableGeneric(moisTbody, state.sco_echeances, state.sco_selected, state.sco_prices);
    renderTableGeneric(packScoTbody, state.sco_echeances, state.sco_selected, state.sco_prices);

    if (!state.tr_enabled) {
      if (transportHint) transportHint.style.display = "";
      if (transportTableWrap) transportTableWrap.style.display = "none";

      if (packTrDisabled) packTrDisabled.style.display = "";
      if (packTrTableWrap) packTrTableWrap.style.display = "none";

      if (packTrOn) packTrOn.checked = false;
      clearTransportSelection();
    } else {
      if (transportHint) transportHint.style.display = "none";
      if (transportTableWrap) transportTableWrap.style.display = "";

      if (packTrDisabled) packTrDisabled.style.display = "none";
      if (packTrTableWrap) packTrTableWrap.style.display = "";

      renderTableGeneric(transportTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
      renderTableGeneric(packTrTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    applyTransportGuard();
    recomputeAll();
  }

  // events
  niveauSelect?.addEventListener("change", () => loadGroupes(niveauSelect.value));
  groupeSelect?.addEventListener("change", () => loadEleves(groupeSelect.value));

  // ✅ si quelqu’un change le <select> natif (au cas où)
  eleveSelect?.addEventListener("change", () => {
    const v = eleveSelect.value;
    if (v) loadInscriptionAndAll(v);
  });

  // init TomSelect
  initEleveTomSelect();

  // Prefill (optionnel)
  const p = window.__PREFILL__ || {};
  if (p.niveau_id && niveauSelect) {
    niveauSelect.value = p.niveau_id;
    loadGroupes(p.niveau_id).then(() => {
      if (p.groupe_id && groupeSelect) {
        groupeSelect.value = p.groupe_id;
        loadEleves(p.groupe_id).then(() => {
          if (p.eleve_id) {
            if (eleveTS) {
              try { eleveTS.setValue(String(p.eleve_id), true); } catch (e) {}
            } else if (eleveSelect) {
              eleveSelect.value = p.eleve_id;
            }
            loadInscriptionAndAll(p.eleve_id);
          }
        });
      }
    });
  }

  // default type
  setType("SCOLARITE");
})();
