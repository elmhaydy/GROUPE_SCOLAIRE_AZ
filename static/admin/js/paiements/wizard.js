/* =========================================
   AZ • Paiements Wizard — PAYEUR: PARENT / AUTRE (FINAL + FRATRIE)
   - Mode Parent: TomSelect parent -> enfants
   - Mode Autre: TomSelect élève direct (TomSelect)
   - FRATRIE: fetch ajax_fratrie + click -> récup inscription_id -> charge échéances ✅
   - Panier sidebar + guard doublon
   - Transport guard + Inscription guard conservés
   ========================================= */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const cfg = window.AZ_WIZ || {};

  // payeur mode
  const btnModeParent = $("btnModeParent");
  const btnModeAutre = $("btnModeAutre");
  const payeurMode = $("payeurMode");
  const modeParentBox = $("modeParentBox");
  const modeAutreBox = $("modeAutreBox");
  const autreHint = $("autreHint");

  // selects
  const parentSelect = $("parentSelect");
  const eleveSelect = $("eleveSelect");             // enfants par parent
  const eleveDirectSelect = $("eleveDirectSelect"); // recherche élève direct (AUTRE)
  const eleveHint = $("eleveHint");

  // FRATRIE (AUTRE)
  const fratrieBox = $("fratrieBox");
  const fratrieList = $("fratrieList");

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

  // UI tables
  const moisTbody = $("moisTbody");
  const transportHint = $("transportHint");
  const transportTableWrap = $("transportTableWrap");
  const transportTbody = $("transportTbody");

  const montantInscription = $("montantInscription");
  const maxInscriptionTxt = $("maxInscriptionTxt");

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

  // cart (sidebar)
  const btnAddToCart = $("btnAddToCart");
  const btnClearCart = $("btnClearCart");
  const cartEmpty = $("cartEmpty");
  const cartList = $("cartList");
  const totalTxt = $("totalTxt");

  let parentTS = null;
  let eleveTS = null;

  const state = {
    payeur_mode: "PARENT", // PARENT | AUTRE
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
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      console.error("AJAX error", res.status, url, txt.slice(0, 250));
      throw new Error(`HTTP ${res.status}`);
    }
    return await res.json();
  }

  function safeParse(raw, fallback) {
    try { return JSON.parse(raw); } catch (e) { return fallback; }
  }

  // ---------- TYPE SWITCH ----------
  function setType(type) {
    if (type === "TRANSPORT" && !state.tr_enabled) type = "SCOLARITE";

    // inscription guard (si déjà payée)
    const reste = toNum(state.max_inscription || "0");
    if (type === "INSCRIPTION" && reste <= 0) type = "SCOLARITE";

    typeTransaction.value = type;

    btnSco?.classList.toggle("is-active", type === "SCOLARITE");
    btnIns?.classList.toggle("is-active", type === "INSCRIPTION");
    btnTr?.classList.toggle("is-active", type === "TRANSPORT");
    btnPack?.classList.toggle("is-active", type === "PACK");

    if (blocScolarite) blocScolarite.style.display = (type === "SCOLARITE") ? "" : "none";
    if (blocInscription) blocInscription.style.display = (type === "INSCRIPTION") ? "" : "none";
    if (blocTransport) blocTransport.style.display = (type === "TRANSPORT") ? "" : "none";
    if (blocPack) blocPack.style.display = (type === "PACK") ? "" : "none";

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
    if (transportPayload) transportPayload.value = JSON.stringify({ selected_ids: [], prices: {} });
  }

  function applyTransportGuard() {
    const enabled = !!state.tr_enabled;

    if (btnTr) {
      btnTr.disabled = !enabled;
      btnTr.classList.toggle("is-disabled", !enabled);
    }

    if (!enabled && typeTransaction?.value === "TRANSPORT") setType("SCOLARITE");

    // pack transport
    if (packTrOn && packTrDisabled && packTrTableWrap) {
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
  }

  // ---------- INSCRIPTION GUARD ----------
  function applyInscriptionGuard() {
    const reste = toNum(state.max_inscription || "0");
    const paid = (reste <= 0);

    if (btnIns) {
      btnIns.disabled = paid;
      btnIns.classList.toggle("is-disabled", paid);
      btnIns.title = paid ? "Inscription déjà payée" : "";
    }

    if (paid && typeTransaction?.value === "INSCRIPTION") setType("SCOLARITE");

    if (montantInscription) {
      montantInscription.disabled = paid;
      if (paid) montantInscription.value = "";
    }

    if (packInsOn) {
      if (paid) {
        packInsOn.checked = false;
        packInsOn.disabled = true;
        if (packInsBlock) packInsBlock.style.display = "none";
        if (packInsAmount) {
          packInsAmount.value = "";
          packInsAmount.disabled = true;
        }
      } else {
        packInsOn.disabled = false;
      }
    }
  }

  // ---------- FRATRIE ----------
  function hideFratrie() {
    if (fratrieBox) fratrieBox.style.display = "none";
    if (fratrieList) fratrieList.innerHTML = "";
  }

  async function fetchInscriptionIdForEleve(eleveId, matriculeMaybe) {
    // On doit récupérer inscription_id (année active) sinon pas d’échéances.
    // On utilise ajax_eleves_search (qui retourne id + inscription_id).
    const baseUrl = (cfg.elevesSearchUrl || "").trim();
    if (!baseUrl) return "";

    const params = new URLSearchParams();
    // meilleur filtre: matricule si dispo (rapide)
    if (matriculeMaybe) params.set("q", String(matriculeMaybe).trim());
    else params.set("q", String(eleveId).trim()); // fallback

    const data = await fetchJSON(`${baseUrl}?${params.toString()}`);
    const raw = data.items || data.results || [];
    const eid = String(eleveId);

    const found = (Array.isArray(raw) ? raw : []).find(x => String(x.id) === eid);
    if (found && found.inscription_id) return String(found.inscription_id);

    // fallback: si recherche n’a pas match, on prend le premier si unique
    if (raw.length === 1 && raw[0].inscription_id) return String(raw[0].inscription_id);

    return "";
  }

  async function loadFratrie(eleveId) {
    hideFratrie();

    if (state.payeur_mode !== "AUTRE") return;
    const baseUrl = (cfg.fratrieUrl || "").trim();
    if (!baseUrl) return;
    if (!eleveId) return;

    try {
      const data = await fetchJSON(`${baseUrl}?eleve=${encodeURIComponent(String(eleveId))}`);
      const items = (data && data.ok) ? (data.items || []) : [];
      if (!items.length) return;

      if (fratrieList) {
        fratrieList.innerHTML = items.map(it => {
          const id = String(it.id);
          const matricule = String(it.matricule || "");
          const label = `${matricule ? matricule + " — " : ""}${String(it.nom || "")} ${String(it.prenom || "")}`.trim();
          return `
            <button type="button"
                    class="az-chip"
                    data-fr="${esc(id)}"
                    data-mat="${esc(matricule)}"
                    data-label="${esc(label)}"
                    style="margin-right:8px;margin-bottom:8px;">
              🧒 ${esc(label)}
            </button>
          `;
        }).join("");

        fratrieList.querySelectorAll("button[data-fr]").forEach(btn => {
          btn.addEventListener("click", async () => {
            const sibId = String(btn.dataset.fr || "");
            const sibMat = String(btn.dataset.mat || "");
            const sibLabel = String(btn.dataset.label || "").trim();

            if (!sibId) return;

            // 1) Récup inscription_id du frère via ajax_eleves_search (année active)
            const inscId = await fetchInscriptionIdForEleve(sibId, sibMat);

            // 2) Sync TomSelect (optionnel mais propre)
            if (eleveTS) {
              try {
                if (!eleveTS.options[sibId]) eleveTS.addOption({ id: sibId, label: sibLabel, inscription_id: inscId });
                eleveTS.setValue(sibId, true);
              } catch (e) {}
            }

            // 3) Charger finance + échéances ✅
            await loadFinanceForEleve(sibId, sibLabel, inscId);
          });
        });
      }

      if (fratrieBox) fratrieBox.style.display = "";
    } catch (e) {
      console.error("fratrie load error", e);
      hideFratrie();
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

    if (inscriptionId) inscriptionId.value = "";
    if (echeancesPayload) echeancesPayload.value = "";
    if (transportPayload) transportPayload.value = "";
    if (packPayload) packPayload.value = "";

    const msg = `<tr><td colspan="3" class="az-muted">Choisis un élève…</td></tr>`;
    if (moisTbody) moisTbody.innerHTML = msg;
    if (transportTbody) transportTbody.innerHTML = msg;
    if (packScoTbody) packScoTbody.innerHTML = msg;
    if (packTrTbody) packTrTbody.innerHTML = msg;

    if (transportHint) transportHint.style.display = "none";
    if (transportTableWrap) transportTableWrap.style.display = "none";

    if (maxInscriptionTxt) maxInscriptionTxt.textContent = "";
    if (montantInscription) {
      montantInscription.value = "";
      montantInscription.disabled = true;
    }

    if (packInsAmount) {
      packInsAmount.value = "";
      packInsAmount.disabled = true;
    }
    if (packInsMax) packInsMax.textContent = "";

    hideFratrie();

    applyTransportGuard();
    applyInscriptionGuard();
    recompute();
  }

  // ---------- CART ----------
  function isCurrentInCart() {
    return !!state.currentEleveId && state.cart.has(String(state.currentEleveId));
  }

  function updateCartUI() {
    const items = Array.from(state.cart.values());

    if (btnClearCart) btnClearCart.style.display = items.length ? "" : "none";

    if (cartEmpty && cartList) {
      if (!items.length) {
        cartEmpty.style.display = "";
        cartList.style.display = "none";
        cartList.innerHTML = "";
      } else {
        cartEmpty.style.display = "none";
        cartList.style.display = "";
        cartList.innerHTML = items.map(it => `
          <div class="az-cart-item">
            <div class="az-cart-item-main">
              <div class="az-cart-item-name">${esc(it.label)}</div>
              <div class="az-cart-item-sub az-muted">${esc(it.sub || "")}</div>
            </div>
            <button type="button" class="az-cart-remove" data-rm="${esc(it.eleve_id)}" title="Retirer">✕</button>
          </div>
        `).join("");

        cartList.querySelectorAll("button[data-rm]").forEach(b => {
          b.addEventListener("click", () => {
            state.cart.delete(String(b.dataset.rm));
            updateCartUI();
            recompute();
          });
        });
      }
    }

    // batch si 2+
    if (batchPayload) {
      if (items.length >= 2) {
        batchPayload.value = JSON.stringify({
          type_transaction: String(typeTransaction?.value || "SCOLARITE"),
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

    // bouton add
    if (btnAddToCart) {
      const canAdd = !!state.currentEleveId && !!state.inscription_id && !isCurrentInCart();
      btnAddToCart.disabled = !canAdd;

      if (isCurrentInCart()) btnAddToCart.textContent = "✅ Déjà dans panier";
      else btnAddToCart.textContent = "+ Ajouter au panier";
    }
  }

  btnAddToCart?.addEventListener("click", () => {
    if (!state.currentEleveId || !state.inscription_id) return;
    const key = String(state.currentEleveId);
    if (state.cart.has(key)) return;

    const scoSnap = safeParse(echeancesPayload?.value || "", { selected_ids: [], prices: {} });
    const trSnap  = safeParse(transportPayload?.value || "", { selected_ids: [], prices: {} });
    const packSnap = safeParse(packPayload?.value || "", {});

    state.cart.set(key, {
      eleve_id: key,
      label: state.currentEleveLabel || `Élève #${key}`,
      sub: `Inscription #${String(state.inscription_id)}`,
      inscription_id: String(state.inscription_id),
      echeances_payload: scoSnap,
      transport_payload: trSnap,
      pack_payload: packSnap,
      montant_inscription: (montantInscription?.value || "0.00"),
    });

    updateCartUI();
    recompute();
  });

  btnClearCart?.addEventListener("click", () => {
    state.cart = new Map();
    updateCartUI();
    recompute();
  });

  // ---------- RECOMPUTE ----------
  function recompute() {
    if (echeancesPayload) echeancesPayload.value = JSON.stringify(buildPayload(state.sco_selected, state.sco_prices));
    if (transportPayload) transportPayload.value = JSON.stringify(buildPayload(state.tr_selected, state.tr_prices));

    applyTransportGuard();
    applyInscriptionGuard();

    const type = String(typeTransaction?.value || "SCOLARITE");
    let total = 0;

    if (type === "SCOLARITE") {
      total = sumSelected(state.sco_echeances, state.sco_selected, state.sco_prices);
    } else if (type === "TRANSPORT") {
      total = sumSelected(state.tr_echeances, state.tr_selected, state.tr_prices);
    } else if (type === "INSCRIPTION") {
      const reste = toNum(state.max_inscription || "0");
      total = (reste <= 0) ? 0 : toNum(montantInscription?.value || "0");
    } else if (type === "PACK") {
      const reste = toNum(state.max_inscription || "0");
      const insAllowed = (reste > 0);

      const pack = {
        ins_on: insAllowed ? !!packInsOn?.checked : false,
        sco_on: !!packScoOn?.checked,
        tr_on: state.tr_enabled ? !!packTrOn?.checked : false,
        ins_amount: insAllowed ? (packInsAmount?.value || "0.00") : "0.00",
        sco: buildPayload(state.sco_selected, state.sco_prices),
        tr: state.tr_enabled ? buildPayload(state.tr_selected, state.tr_prices) : { selected_ids: [], prices: {} },
      };
      if (packPayload) packPayload.value = JSON.stringify(pack);

      if (pack.ins_on) total += toNum(pack.ins_amount);
      if (pack.sco_on) total += sumSelected(state.sco_echeances, state.sco_selected, state.sco_prices);
      if (pack.tr_on && state.tr_enabled) total += sumSelected(state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    if (totalTxt) totalTxt.textContent = total.toFixed(2);

    if (packInsBlock) packInsBlock.style.display = packInsOn?.checked ? "" : "none";
    if (packScoBlock) packScoBlock.style.display = packScoOn?.checked ? "" : "none";
    if (packTrBlock) packTrBlock.style.display = (packTrOn?.checked && state.tr_enabled) ? "" : "none";

    updateCartUI();
  }

  packInsOn?.addEventListener("change", recompute);
  packScoOn?.addEventListener("change", recompute);
  packTrOn?.addEventListener("change", recompute);
  packInsAmount?.addEventListener("input", recompute);
  montantInscription?.addEventListener("input", recompute);

  // ---------- LOAD CHILD FINANCE ----------
  async function loadFinanceForEleve(eleveId, eleveLabel, inscId) {
    resetChildFinance();

    state.currentEleveId = String(eleveId);
    state.currentEleveLabel = String(eleveLabel || "");
    if (eleveHint) eleveHint.textContent = state.currentEleveLabel ? `Sélection: ${state.currentEleveLabel}` : "";

    const loading = `<tr><td colspan="3" class="az-muted">Chargement…</td></tr>`;
    if (moisTbody) moisTbody.innerHTML = loading;
    if (transportTbody) transportTbody.innerHTML = loading;
    if (packScoTbody) packScoTbody.innerHTML = loading;
    if (packTrTbody) packTrTbody.innerHTML = loading;

    state.inscription_id = (inscId || "").trim() || null;
    if (inscriptionId) inscriptionId.value = state.inscription_id || "";

    if (!state.inscription_id) {
      const msg = `<tr><td colspan="3" class="az-muted">Aucune inscription active pour cet élève.</td></tr>`;
      if (moisTbody) moisTbody.innerHTML = msg;
      if (transportTbody) transportTbody.innerHTML = msg;
      if (packScoTbody) packScoTbody.innerHTML = msg;
      if (packTrTbody) packTrTbody.innerHTML = msg;
      applyTransportGuard();
      applyInscriptionGuard();
      recompute();
      return;
    }

    // scolarité
    const echData = await fetchJSON(`${cfg.echeancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.sco_echeances = echData.items || [];
    state.max_inscription = echData.tarifs?.reste_inscription || "0.00";

    const maxTxt = `Reste inscription: ${state.max_inscription} MAD`;
    if (maxInscriptionTxt) maxInscriptionTxt.textContent = maxTxt;
    if (packInsMax) packInsMax.textContent = maxTxt;

    const maxN = toNum(state.max_inscription);
    if (montantInscription) {
      montantInscription.value = (maxN > 0 ? maxN.toFixed(2) : "");
      montantInscription.disabled = !(maxN > 0);
    }
    if (packInsAmount) {
      packInsAmount.value = (maxN > 0 ? maxN.toFixed(2) : "");
      packInsAmount.disabled = !(maxN > 0);
    }

    // transport
    const trData = await fetchJSON(`${cfg.transportEcheancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.tr_enabled = !!trData.enabled;
    state.tr_echeances = trData.items || [];

    renderTable(moisTbody, state.sco_echeances, state.sco_selected, state.sco_prices);
    renderTable(packScoTbody, state.sco_echeances, state.sco_selected, state.sco_prices);

    if (!state.tr_enabled) {
      if (transportHint) transportHint.style.display = "";
      if (transportTableWrap) transportTableWrap.style.display = "none";
      if (packTrDisabled) packTrDisabled.style.display = "";
      if (packTrTableWrap) packTrTableWrap.style.display = "none";
      if (packTrOn) packTrOn.checked = false;
      clearTransport();
    } else {
      if (transportHint) transportHint.style.display = "none";
      if (transportTableWrap) transportTableWrap.style.display = "";
      if (packTrDisabled) packTrDisabled.style.display = "none";
      if (packTrTableWrap) packTrTableWrap.style.display = "";
      renderTable(transportTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
      renderTable(packTrTbody, state.tr_echeances, state.tr_selected, state.tr_prices);
    }

    applyTransportGuard();
    applyInscriptionGuard();
    recompute();

    // ✅ FRATRIE seulement en AUTRE
    if (state.payeur_mode === "AUTRE") {
      loadFratrie(state.currentEleveId);
    } else {
      hideFratrie();
    }
  }

  // ---------- LOAD ENFANTS BY PARENT ----------
  async function loadEnfants(parentId) {
    if (!eleveSelect) return;

    eleveSelect.innerHTML = `<option value="">— Choisir —</option>`;
    eleveSelect.disabled = true;
    if (eleveHint) eleveHint.textContent = "";
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
    const inscId = opt ? (opt.getAttribute("data-insc") || "") : "";
    if (eid) loadFinanceForEleve(eid, label, inscId);
  });

  // ---------- TOMSELECT PARENT ----------
  function initParentTS() {
    if (typeof TomSelect === "undefined") return;
    if (!parentSelect) return;

    const baseUrl = (cfg.parentsSearchUrl || "").trim();
    if (!baseUrl) return;

    if (parentTS) { try { parentTS.destroy(); } catch (e) {} parentTS = null; }

    parentTS = new TomSelect(parentSelect, {
      create: false,
      allowEmptyOption: true,
      maxOptions: 50,
      placeholder: "Tape nom / téléphone…",
      valueField: "id",
      labelField: "label",
      searchField: ["label"],
      dropdownParent: "body",
      preload: true,

      render: {
        no_results: () => `<div class="no-results" style="padding:10px;color:#94a3b8;">Aucun parent</div>`,
        option: (data, escape) => `<div class="option">${escape(data.label)}</div>`,
        item: (data, escape) => `<div class="item">${escape(data.label)}</div>`,
      },

      load: async (query, callback) => {
        try {
          const params = new URLSearchParams();
          params.set("q", (query || "").trim());
          const data = await fetchJSON(`${baseUrl}?${params.toString()}`);
          const raw = data.items || data.results || [];
          const list = (Array.isArray(raw) ? raw : [])
            .map(x => ({ id: String(x.id ?? ""), label: String(x.label ?? "").trim() }))
            .filter(o => o.id && o.label);
          callback(list);
        } catch (e) { callback([]); }
      },

      onChange: (val) => {
        const pid = String(val || "");
        state.parent_id = pid || null;

        // nouveau parent => reset + panier vidé
        state.cart = new Map();
        updateCartUI();

        if (eleveSelect) {
          eleveSelect.value = "";
          eleveSelect.innerHTML = `<option value="">— Choisir —</option>`;
          eleveSelect.disabled = true;
        }

        resetChildFinance();
        loadEnfants(pid);
      }
    });
  }

  // ---------- TOMSELECT ELEVE DIRECT (AUTRE) ----------
  function initEleveTS() {
    if (typeof TomSelect === "undefined") return;
    if (!eleveDirectSelect) return;

    const baseUrl = (cfg.elevesSearchUrl || "").trim();
    if (!baseUrl) return;

    if (eleveTS) { try { eleveTS.destroy(); } catch (e) {} eleveTS = null; }

    eleveTS = new TomSelect(eleveDirectSelect, {
      create: false,
      allowEmptyOption: true,
      maxOptions: 50,
      placeholder: "Tape matricule / nom / prénom…",
      valueField: "id",
      labelField: "label",
      searchField: ["label"],
      dropdownParent: "body",
      preload: false,

      render: {
        no_results: () => `<div class="no-results" style="padding:10px;color:#94a3b8;">Aucun élève</div>`,
        option: (data, escape) => `<div class="option">${escape(data.label)}</div>`,
        item: (data, escape) => `<div class="item">${escape(data.label)}</div>`,
      },

      load: async (query, callback) => {
        try {
          const q = (query || "").trim();
          if (q.length < 1) return callback([]);
          const params = new URLSearchParams();
          params.set("q", q);

          const data = await fetchJSON(`${baseUrl}?${params.toString()}`);
          const raw = data.items || data.results || [];

          const list = (Array.isArray(raw) ? raw : [])
            .map(x => ({
              id: String(x.id ?? ""),
              label: String(x.label ?? "").trim(),
              inscription_id: String(x.inscription_id ?? ""),
            }))
            .filter(o => o.id && o.label);

          callback(list);
        } catch (e) {
          callback([]);
        }
      },

      onChange: (val) => {
        const id = String(val || "");
        if (!id) { resetChildFinance(); updateCartUI(); return; }

        const obj = eleveTS.options[id] || {};
        const label = String(obj.label || "");
        const inscId = String(obj.inscription_id || "");

        if (autreHint) autreHint.style.display = "";
        loadFinanceForEleve(id, label, inscId);
      }
    });
  }

  // ---------- PAYEUR MODE SWITCH ----------
  function setPayeurMode(mode) {
    state.payeur_mode = (mode === "AUTRE") ? "AUTRE" : "PARENT";
    if (payeurMode) payeurMode.value = state.payeur_mode;

    btnModeParent?.classList.toggle("is-active", state.payeur_mode === "PARENT");
    btnModeAutre?.classList.toggle("is-active", state.payeur_mode === "AUTRE");

    if (modeParentBox) modeParentBox.style.display = (state.payeur_mode === "PARENT") ? "" : "none";
    if (modeAutreBox) modeAutreBox.style.display = (state.payeur_mode === "AUTRE") ? "" : "none";
    if (autreHint) autreHint.style.display = "none";

    resetChildFinance();

    if (state.payeur_mode === "PARENT") {
      if (parentTS) parentTS.clear(true);
      if (eleveSelect) {
        eleveSelect.innerHTML = `<option value="">— Choisir un parent d’abord —</option>`;
        eleveSelect.disabled = true;
      }
      hideFratrie();
    } else {
      state.parent_id = null;
      if (parentTS) parentTS.clear(true);
      if (eleveSelect) {
        eleveSelect.innerHTML = `<option value="">— Mode élève direct —</option>`;
        eleveSelect.disabled = true;
      }
      if (eleveTS) eleveTS.clear(true);
      hideFratrie();
    }

    updateCartUI();
    recompute();
  }

  btnModeParent?.addEventListener("click", () => setPayeurMode("PARENT"));
  btnModeAutre?.addEventListener("click", () => setPayeurMode("AUTRE"));

  // init
  initParentTS();
  initEleveTS();
  setType("SCOLARITE");
  setPayeurMode("PARENT");
  updateCartUI();
})();
