/* =========================================
   AZ • Paiements Wizard — FINAL + Transport Toggle/Price ✅
   - NO AUTO SAVE defaults
   - Defaults uniquement via bouton
   - Transport: Activer/Désactiver + Tarif mensuel dans wizard
   - POST cfg.setTransportUrl {inscription_id, enabled, tarif_mensuel}
   - IMPORTANT: nécessite IDs uniques dans HTML:
       trEnableToggle, trTarifMensuel, btnApplyTransport, trApplyMsg (UNE SEULE FOIS)
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
  const eleveSelect = $("eleveSelect");
  const eleveDirectSelect = $("eleveDirectSelect");
  const eleveHint = $("eleveHint");

  // fratrie
  const fratrieBox = $("fratrieBox");
  const fratrieList = $("fratrieList");

  // type switch
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

  // pack
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
  const btnAddToCart = $("btnAddToCart");
  const btnClearCart = $("btnClearCart");
  const cartEmpty = $("cartEmpty");
  const cartList = $("cartList");
  const totalTxt = $("totalTxt");
  const totalTxtHero = $("totalTxtHero");

  // meta
  const eleveMetaCard = $("eleveMetaCard");
  const metaNom = $("metaNom");
  const metaMat = $("metaMat");
  const metaNiveau = $("metaNiveau");
  const metaGroupe = $("metaGroupe");
  const metaAnnee = $("metaAnnee");

  // bulk
  const bulkPriceSco = $("bulkPriceSco");
  const bulkPriceTr = $("bulkPriceTr");
  const bulkPriceScoPack = $("bulkPriceScoPack");
  const bulkPriceTrPack = $("bulkPriceTrPack");

  // defaults (manual only)
  const saveScoDefault = $("saveScoDefault");
  const saveTrDefault = $("saveTrDefault");
  const btnSaveScoDefault = $("btnSaveScoDefault");
  const btnSaveTrDefault = $("btnSaveTrDefault");
  const saveScoMsg = $("saveScoMsg");
  const saveTrMsg = $("saveTrMsg");

  // justificatifs
  const modeSel = $("mode");
  const justifType = $("justificatifType");
  const justifHint = $("justifHint");

  // ✅ Transport activation UI (NEW)
  const trEnableToggle = $("trEnableToggle");
  const trTarifMensuel = $("trTarifMensuel");
  const btnApplyTransport = $("btnApplyTransport");
  const trApplyMsg = $("trApplyMsg");

  let parentTS = null;
  let eleveTS = null;

  const state = {
    payeur_mode: "PARENT",
    parent_id: null,

    currentEleveId: null,
    currentEleveLabel: "",
    inscription_id: null,

    sco_echeances: [],
    sco_selected: new Set(),
    sco_prices: {},

    tr_enabled: false,
    tr_echeances: [],
    tr_selected: new Set(),
    tr_prices: {},

    max_inscription: "0.00",

    cart: new Map(),
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
  function safeParse(raw, fallback) {
    try { return JSON.parse(raw); } catch { return fallback; }
  }

  // CSRF
  function getCSRFToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input && input.value) return input.value;
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  async function fetchJSON(url) {
    const res = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (!ct.includes("application/json")) throw new Error("Réponse non-JSON (login/403 possible)");
    return await res.json();
  }

  async function postJSON(url, bodyObj) {
    const res = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(bodyObj || {}),
    });

    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!ct.includes("application/json")) throw new Error("Réponse non-JSON (login/403 possible)");
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  // ---------- Justifs UI ----------
  function updateJustifUI() {
    if (!modeSel || !justifHint) return;
    const m = String(modeSel.value || "").toUpperCase();
    if (m === "CHEQUE") {
      if (justifType) justifType.value = "CHEQUE";
      justifHint.textContent = "Recommandé: scan du chèque.";
    } else if (m === "VIREMENT") {
      if (justifType) justifType.value = "VIREMENT";
      justifHint.textContent = "Recommandé: reçu / preuve de virement.";
    } else {
      justifHint.textContent = "Optionnel. Recommandé pour chèque / virement.";
    }
  }
  modeSel?.addEventListener("change", updateJustifUI);

  // ---------- Meta ----------
  function showEleveMeta(meta) {
    if (!eleveMetaCard) return;
    if (!meta || !meta.ok) {
      eleveMetaCard.style.display = "none";
      return;
    }
    const e = meta.eleve || {};
    const n = meta.niveau || {};
    const g = meta.groupe || {};
    const a = meta.annee || {};

    if (metaNom) metaNom.textContent = `${e.nom || ""} ${e.prenom || ""}`.trim() || "—";
    if (metaMat) metaMat.textContent = e.matricule ? `Matricule: ${e.matricule}` : "";
    if (metaNiveau) metaNiveau.textContent = `Niveau: ${n.label || "—"}`;
    if (metaGroupe) metaGroupe.textContent = `Groupe: ${g.label || "—"}`;
    if (metaAnnee) metaAnnee.textContent = a.label ? `Année: ${a.label}` : "Année: —";

    eleveMetaCard.style.display = "";
  }
  async function loadEleveMetaByInscription(inscId) {
    if (!cfg.eleveMetaUrl || !inscId) return showEleveMeta(null);
    try {
      const data = await fetchJSON(`${cfg.eleveMetaUrl}?inscription=${encodeURIComponent(String(inscId))}`);
      showEleveMeta(data);
    } catch { showEleveMeta(null); }
  }

  // ---------- TYPE SWITCH ----------
  function setType(type) {
    // ✅ on laisse ouvrir Transport même si OFF (pour pouvoir l’activer)
    const reste = toNum(state.max_inscription || "0");
    if (type === "INSCRIPTION" && reste <= 0) type = "SCOLARITE";

    if (typeTransaction) typeTransaction.value = type;

    btnSco?.classList.toggle("is-active", type === "SCOLARITE");
    btnIns?.classList.toggle("is-active", type === "INSCRIPTION");
    btnTr?.classList.toggle("is-active", type === "TRANSPORT");
    btnPack?.classList.toggle("is-active", type === "PACK");

    if (blocScolarite) blocScolarite.style.display = (type === "SCOLARITE") ? "" : "none";
    if (blocInscription) blocInscription.style.display = (type === "INSCRIPTION") ? "" : "none";
    if (blocTransport) blocTransport.style.display = (type === "TRANSPORT") ? "" : "none";
    if (blocPack) blocPack.style.display = (type === "PACK") ? "" : "none";

    if (type === "TRANSPORT") applyTransportGuard();

    recompute();
  }
  btnSco?.addEventListener("click", () => setType("SCOLARITE"));
  btnIns?.addEventListener("click", () => setType("INSCRIPTION"));
  btnTr?.addEventListener("click", () => setType("TRANSPORT"));
  btnPack?.addEventListener("click", () => setType("PACK"));

  // ---------- TABLE ----------
  function renderTable(tbody, echeances, selectedSet, pricesMap) {
    if (!tbody) return;

    if (!echeances.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="azw-empty">Aucune échéance.</td></tr>`;
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
              : `<input class="azw-input azw-input--sm" type="number" step="0.01" min="0" data-price="${esc(id)}" value="${esc(val)}">`
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

  // ---------- BULK APPLY (remplissage فقط) ----------
  function fillVisibleInputs(containerEl, value) {
    if (!containerEl) return;
    const v = String(value ?? "").trim();
    if (v === "") return;

    const inputs = containerEl.querySelectorAll('input[type="number"][data-price]');
    inputs.forEach(inp => {
      if (inp.disabled) return;
      inp.value = v;

      const id = String(inp.dataset.price || "");
      const tb = inp.closest("tbody");
      if (!id || !tb) return;

      if (tb === moisTbody || tb === packScoTbody) {
        state.sco_prices[id] = v;
      } else if (tb === transportTbody || tb === packTrTbody) {
        state.tr_prices[id] = v;
      }
    });

    recompute();
  }

  // ---------- DEFAULTS (MANUAL ONLY) ----------
  function refreshSaveButtons() {
    const hasInsc = !!state.inscription_id;

    if (btnSaveScoDefault) {
      btnSaveScoDefault.disabled = !(
        hasInsc &&
        !!saveScoDefault?.checked &&
        String(bulkPriceSco?.value || "").trim() !== ""
      );
    }
    if (btnSaveTrDefault) {
      btnSaveTrDefault.disabled = !(
        hasInsc &&
        !!saveTrDefault?.checked &&
        String(bulkPriceTr?.value || "").trim() !== ""
      );
    }
  }

  async function saveDefault(kind) {
    if (!state.inscription_id) return;

    if (kind === "SCO") {
      if (!cfg.defaultScoUrl) return;
      const amount = String(bulkPriceSco?.value || "").trim();
      if (!amount) return;

      if (saveScoMsg) saveScoMsg.textContent = "Enregistrement...";
      await postJSON(cfg.defaultScoUrl, {
        inscription_id: state.inscription_id,
        amount,
        apply: true,
      });
      if (saveScoMsg) saveScoMsg.textContent = "✅ Défaut scolarité enregistré + échéances mises à jour.";
    } else {
      if (!cfg.defaultTrUrl) return;
      const amount = String(bulkPriceTr?.value || "").trim();
      if (!amount) return;

      if (saveTrMsg) saveTrMsg.textContent = "Enregistrement...";
      await postJSON(cfg.defaultTrUrl, {
        inscription_id: state.inscription_id,
        amount,
        apply: true,
      });
      if (saveTrMsg) saveTrMsg.textContent = "✅ Défaut transport enregistré + échéances mises à jour.";
    }

    await loadFinanceForEleve(state.currentEleveId, state.currentEleveLabel, String(state.inscription_id));
  }

  btnSaveScoDefault?.addEventListener("click", async () => {
    try { await saveDefault("SCO"); }
    catch (e) { if (saveScoMsg) saveScoMsg.textContent = `❌ ${e.message || e}`; }
  });
  btnSaveTrDefault?.addEventListener("click", async () => {
    try { await saveDefault("TR"); }
    catch (e) { if (saveTrMsg) saveTrMsg.textContent = `❌ ${e.message || e}`; }
  });

  saveScoDefault?.addEventListener("change", refreshSaveButtons);
  saveTrDefault?.addEventListener("change", refreshSaveButtons);
  bulkPriceSco?.addEventListener("input", refreshSaveButtons);
  bulkPriceTr?.addEventListener("input", refreshSaveButtons);

  // ✅ montant rapide => remplissage فقط (PAS de save)
  bulkPriceSco?.addEventListener("input", () => fillVisibleInputs(blocScolarite, bulkPriceSco.value));
  bulkPriceTr?.addEventListener("input", () => fillVisibleInputs(blocTransport, bulkPriceTr.value));

  // ✅ pack bulk => remplissage فقط (PAS de save)
  bulkPriceScoPack?.addEventListener("input", () => {
    fillVisibleInputs(packScoBlock, bulkPriceScoPack.value);
    if (bulkPriceSco) bulkPriceSco.value = bulkPriceScoPack.value;
    refreshSaveButtons();
  });
  bulkPriceTrPack?.addEventListener("input", () => {
    fillVisibleInputs(packTrBlock, bulkPriceTrPack.value);
    if (bulkPriceTr) bulkPriceTr.value = bulkPriceTrPack.value;
    refreshSaveButtons();
  });

  // ---------- TRANSPORT: ACTIVER + TARIF (AJAX) ----------
  function refreshTransportApplyBtn() {
    if (!btnApplyTransport) return;

    const hasInsc = !!state.inscription_id;
    const enabled = !!trEnableToggle?.checked;
    const tarif = toNum(trTarifMensuel?.value || "0");

    const okTarif = !enabled || tarif > 0;
    btnApplyTransport.disabled = !(hasInsc && okTarif);
  }

  trEnableToggle?.addEventListener("change", () => {
    refreshTransportApplyBtn();
    if (trEnableToggle?.checked) trTarifMensuel?.focus();
  });
  trTarifMensuel?.addEventListener("input", refreshTransportApplyBtn);

  async function applyTransportConfig() {
    if (!cfg.setTransportUrl) throw new Error("setTransportUrl manquant dans AZ_WIZ.");
    if (!state.inscription_id) throw new Error("Aucune inscription sélectionnée.");

    const enabled = !!trEnableToggle?.checked;
    const tarifN = toNum(trTarifMensuel?.value || "0");
    if (enabled && tarifN <= 0) throw new Error("Tarif mensuel obligatoire (> 0) quand transport est activé.");

    const payload = {
      inscription_id: state.inscription_id,
      enabled,
      tarif_mensuel: enabled ? String(tarifN.toFixed(2)) : "0.00",
    };

    if (trApplyMsg) trApplyMsg.textContent = "Enregistrement...";
    if (btnApplyTransport) btnApplyTransport.disabled = true;

    await postJSON(cfg.setTransportUrl, payload);

    if (trApplyMsg) trApplyMsg.textContent = "✅ Transport mis à jour.";
    await loadFinanceForEleve(state.currentEleveId, state.currentEleveLabel, String(state.inscription_id));
  }

  btnApplyTransport?.addEventListener("click", async () => {
    try { await applyTransportConfig(); }
    catch (e) { if (trApplyMsg) trApplyMsg.textContent = `❌ ${e.message || e}`; }
    finally { refreshTransportApplyBtn(); }
  });

  // ---------- TRANSPORT GUARD ----------
  function clearTransport() {
    state.tr_selected = new Set();
    state.tr_prices = {};
    if (transportPayload) transportPayload.value = JSON.stringify({ selected_ids: [], prices: {} });
  }

  function applyTransportGuard() {
    const enabled = !!state.tr_enabled;

    // ✅ bouton transport jamais disabled (sinon impossible d’activer)
    if (btnTr) {
      btnTr.disabled = false;
      btnTr.classList.toggle("is-disabled", !enabled);
    }

    // affichage table/hint selon enabled
    if (!enabled) {
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
    }

    // pack transport toggle
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
    const baseUrl = (cfg.elevesSearchUrl || "").trim();
    if (!baseUrl) return "";

    const params = new URLSearchParams();
    params.set("q", matriculeMaybe ? String(matriculeMaybe).trim() : String(eleveId).trim());

    const data = await fetchJSON(`${baseUrl}?${params.toString()}`);
    const raw = data.items || data.results || [];
    const eid = String(eleveId);

    const found = (Array.isArray(raw) ? raw : []).find(x => String(x.id) === eid);
    if (found && found.inscription_id) return String(found.inscription_id);
    if (raw.length === 1 && raw[0].inscription_id) return String(raw[0].inscription_id);
    return "";
  }

  async function loadFratrie(eleveId) {
    hideFratrie();
    if (state.payeur_mode !== "AUTRE") return;

    const baseUrl = (cfg.fratrieUrl || "").trim();
    if (!baseUrl || !eleveId) return;

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
            <button type="button" class="azw-chip" data-fr="${esc(id)}" data-mat="${esc(matricule)}" data-label="${esc(label)}">
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

            const inscId = await fetchInscriptionIdForEleve(sibId, sibMat);

            if (eleveTS) {
              try {
                if (!eleveTS.options[sibId]) eleveTS.addOption({ id: sibId, label: sibLabel, inscription_id: inscId });
                eleveTS.setValue(sibId, true);
              } catch {}
            }

            await loadFinanceForEleve(sibId, sibLabel, inscId);
          });
        });
      }

      if (fratrieBox) fratrieBox.style.display = "";
    } catch {
      hideFratrie();
    }
  }

  // ---------- RESET ----------
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

    if (bulkPriceSco) bulkPriceSco.value = "";
    if (bulkPriceTr) bulkPriceTr.value = "";
    if (bulkPriceScoPack) bulkPriceScoPack.value = "";
    if (bulkPriceTrPack) bulkPriceTrPack.value = "";

    if (saveScoDefault) saveScoDefault.checked = false;
    if (saveTrDefault) saveTrDefault.checked = false;
    if (saveScoMsg) saveScoMsg.textContent = "";
    if (saveTrMsg) saveTrMsg.textContent = "";

    // reset transport activation UI
    if (trEnableToggle) trEnableToggle.checked = false;
    if (trTarifMensuel) trTarifMensuel.value = "";
    if (trApplyMsg) trApplyMsg.textContent = "";
    refreshTransportApplyBtn();

    const msg = `<tr><td colspan="3" class="azw-empty">Choisis un élève…</td></tr>`;
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
    showEleveMeta(null);

    applyTransportGuard();
    applyInscriptionGuard();
    refreshSaveButtons();
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
          <div class="azw-cart-item">
            <div class="azw-cart-item-main">
              <div class="azw-cart-item-name">${esc(it.label)}</div>
              <div class="azw-cart-item-sub azw-muted">${esc(it.sub || "")}</div>
            </div>
            <button type="button" class="azw-cart-remove" data-rm="${esc(it.eleve_id)}" title="Retirer">✕</button>
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
      } else batchPayload.value = "";
    }

    if (btnAddToCart) {
      const canAdd = !!state.currentEleveId && !!state.inscription_id && !isCurrentInCart();
      btnAddToCart.disabled = !canAdd;
      btnAddToCart.textContent = isCurrentInCart() ? "✅ Déjà dans panier" : "+ Ajouter au panier";
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
    refreshSaveButtons();
    refreshTransportApplyBtn();

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

    const t = total.toFixed(2);
    if (totalTxt) totalTxt.textContent = t;
    if (totalTxtHero) totalTxtHero.textContent = t;

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

  // ---------- LOAD FINANCE ----------
  async function loadFinanceForEleve(eleveId, eleveLabel, inscId) {
    resetChildFinance();

    state.currentEleveId = String(eleveId);
    state.currentEleveLabel = String(eleveLabel || "");
    if (eleveHint) eleveHint.textContent = state.currentEleveLabel ? `Sélection: ${state.currentEleveLabel}` : "";

    const loading = `<tr><td colspan="3" class="azw-empty">Chargement…</td></tr>`;
    if (moisTbody) moisTbody.innerHTML = loading;
    if (transportTbody) transportTbody.innerHTML = loading;
    if (packScoTbody) packScoTbody.innerHTML = loading;
    if (packTrTbody) packTrTbody.innerHTML = loading;

    state.inscription_id = (inscId || "").trim() || null;
    if (inscriptionId) inscriptionId.value = state.inscription_id || "";
    if (state.inscription_id) loadEleveMetaByInscription(state.inscription_id);

    if (!state.inscription_id) {
      const msg = `<tr><td colspan="3" class="azw-empty">Aucune inscription active pour cet élève.</td></tr>`;
      if (moisTbody) moisTbody.innerHTML = msg;
      if (transportTbody) transportTbody.innerHTML = msg;
      if (packScoTbody) packScoTbody.innerHTML = msg;
      if (packTrTbody) packTrTbody.innerHTML = msg;
      showEleveMeta(null);
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

    // pré-remplissage UI seulement (pas save)
    const scoDef = String(echData.tarifs?.sco_default_mensuel ?? "").trim();
    if (bulkPriceSco && scoDef !== "") {
      bulkPriceSco.value = scoDef;
      if (bulkPriceScoPack) bulkPriceScoPack.value = scoDef;
      fillVisibleInputs(blocScolarite, scoDef);
      fillVisibleInputs(packScoBlock, scoDef);
    }

    // transport (fetch)
    const trData = await fetchJSON(`${cfg.transportEcheancesUrl}?inscription=${encodeURIComponent(state.inscription_id)}`);
    state.tr_enabled = !!trData.enabled;
    state.tr_echeances = trData.items || [];

    // sync UI toggle + tarif
    if (trEnableToggle) trEnableToggle.checked = !!state.tr_enabled;

    const trTarif = String(trData.tarif_mensuel ?? "").trim();
    if (trTarifMensuel) trTarifMensuel.value = (trTarif && trTarif !== "0.00") ? trTarif : "";
    if (trApplyMsg) trApplyMsg.textContent = "";
    refreshTransportApplyBtn();

    const trDef = String(trData.tr_default_mensuel ?? "").trim();
    const trFallback = String(trData.tarif_mensuel ?? "").trim();

    // bulk UI (existant)
    if (bulkPriceTr) {
      if (trDef !== "") bulkPriceTr.value = trDef;
      else if (trFallback !== "" && trFallback !== "0.00") bulkPriceTr.value = trFallback;
    }
    if (bulkPriceTrPack && bulkPriceTr) bulkPriceTrPack.value = bulkPriceTr.value;

    // render sco tables
    renderTable(moisTbody, state.sco_echeances, state.sco_selected, state.sco_prices);
    renderTable(packScoTbody, state.sco_echeances, state.sco_selected, state.sco_prices);

    // transport UI tables
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

      const useTr = (trDef || trFallback || "").trim();
      if (useTr !== "") {
        fillVisibleInputs(blocTransport, useTr);
        fillVisibleInputs(packTrBlock, useTr);
      }
    }

    applyTransportGuard();
    applyInscriptionGuard();
    refreshSaveButtons();
    recompute();

    if (state.payeur_mode === "AUTRE") loadFratrie(state.currentEleveId);
    else hideFratrie();
  }

  // enfants by parent
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

  // TomSelect parent
  function initParentTS() {
    if (typeof TomSelect === "undefined" || !parentSelect) return;
    const baseUrl = (cfg.parentsSearchUrl || "").trim();
    if (!baseUrl) return;

    if (parentTS) { try { parentTS.destroy(); } catch {} parentTS = null; }

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
        } catch { callback([]); }
      },
      onChange: (val) => {
        const pid = String(val || "");
        state.parent_id = pid || null;

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

  // TomSelect eleve direct
  function initEleveTS() {
    if (typeof TomSelect === "undefined" || !eleveDirectSelect) return;
    const baseUrl = (cfg.elevesSearchUrl || "").trim();
    if (!baseUrl) return;

    if (eleveTS) { try { eleveTS.destroy(); } catch {} eleveTS = null; }

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
        } catch { callback([]); }
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

  // payeur mode
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
  updateJustifUI();
})();
