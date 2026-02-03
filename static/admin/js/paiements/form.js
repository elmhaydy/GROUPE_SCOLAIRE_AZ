/* static/admin/js/paiements/form.js — AZ NEBULA — Paiements (FINAL v20) */
(function () {
  const $ = (s, r = document) => r.querySelector(s);

  const form = $("#payForm");
  const step2 = $("#step2");

  const stepPill1 = $("#stepPill1");
  const stepPill2 = $("#stepPill2");
  const stepHint = $("#stepHint");

  const niveau = $("#id_niveau_ui");
  const groupe = $("#id_groupe_ui");

  const inscSelect = $("#id_inscription");
  const inscInfo = $("#inscInfo");
  const inscInfoText = $("#inscInfoText");

  const monthsGrid = $("#monthsGrid");

  const totalDisplay = $("#totalDisplay");
  const pickedCount = $("#pickedCount");
  const pickedCount2 = $("#pickedCount2");
  const pickedList = $("#pickedList");
  const sideStatus = $("#sideStatus");

  const hiddenPayload = $("#id_echeances_payload");
  const hiddenTotal = $("#id_montant_total");
  const hiddenMontant = $("#id_montant");
  const submitBtn = $("#submitBtn");

  const btnSelectAllDue = $("#btnSelectAllDue");
  const btnClearAll = $("#btnClearAll");

  let ts = null;

  // state
  let currentInscId = null;
  let echeances = [];
  let selected = new Set(); // echeance_id (string)
  let prices = {};          // {id: "500.00"}

  function money(n) {
    const x = Number(n || 0);
    return (Math.round(x * 100) / 100).toFixed(2);
  }

  function setStatus(icon, text) {
    if (!sideStatus) return;
    sideStatus.innerHTML = `<i class="${icon}"></i><span>${text}</span>`;
  }

  function setStep(step) {
    if (step === 1) {
      step2.style.display = "none";
      stepPill1.classList.add("is-on");
      stepPill2.classList.remove("is-on");
      stepPill2.classList.add("is-off");

      stepHint.textContent = "Étape 1 : Choisis Niveau → Groupe → Élève.";

      submitBtn.style.display = "none";
      submitBtn.disabled = true;

      setStatus("fa-solid fa-circle-info", "Choisis un élève puis sélectionne les mois.");
      return;
    }

    step2.style.display = "block";
    stepPill1.classList.add("is-on");
    stepPill2.classList.remove("is-off");
    stepPill2.classList.add("is-on");

    stepHint.textContent = "Étape 2 : Sélectionne les mois, ajuste les montants, puis valide.";

    submitBtn.style.display = "inline-flex";
    // disabled via recompute()

    setStatus("fa-solid fa-wand-magic-sparkles", "Sélectionne des mois (au moins 1) pour activer la validation.");
  }

  async function fetchJSON(url) {
    const r = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  }

  function initTomSelect() {
    if (!inscSelect) return;

    ts = new TomSelect(inscSelect, {
      create: false,
      allowEmptyOption: true,
      placeholder: "— Choisir l’inscription (élève) —",
      persist: false,
      maxOptions: 1000,
      render: {
        option: function (data, escape) {
          return `<div class="az-ts-opt"><div class="az-ts-main">${escape(data.text)}</div></div>`;
        }
      }
    });

    ts.on("change", async (value) => {
      currentInscId = (value || "").toString().trim();
      if (!currentInscId) {
        resetAfterInsc();
        return;
      }
      await loadEcheances(currentInscId);
    });

    // si valeur existante (ex: re-render après erreur)
    const existing = (ts.getValue() || "").toString().trim();
    if (existing) {
      currentInscId = existing;
      loadEcheances(existing).catch(console.error);
    }
  }

  function resetAfterInsc() {
    currentInscId = null;
    echeances = [];
    selected.clear();
    prices = {};

    monthsGrid.innerHTML = "";
    updateSideList();
    updateKPI(0, 0);

    hiddenPayload.value = "";
    hiddenTotal.value = "0.00";
    hiddenMontant.value = "0.00";

    if (inscInfo) inscInfo.style.display = "none";
    setStep(1);
  }

  async function loadGroupes(niveauId) {
    groupe.innerHTML = `<option value="">— Choisir un groupe —</option>`;
    groupe.disabled = true;

    if (!niveauId) return;

    const url = `${window.AZ_PAY.groupesParNiveauUrl}?niveau_id=${encodeURIComponent(niveauId)}`;
    const data = await fetchJSON(url);

    (data.results || []).forEach((g) => {
      const opt = document.createElement("option");
      opt.value = g.id;
      opt.textContent = g.label;
      groupe.appendChild(opt);
    });

    groupe.disabled = false;
  }

  niveau?.addEventListener("change", async () => {
    try { await loadGroupes(niveau.value); } catch (e) { console.error(e); }
  });

  groupe?.addEventListener("change", () => {
    // BONUS UX: si tu veux “forcer” l’utilisateur à choisir élève après groupe,
    // tu peux reset ici. Sinon on ne casse rien.
    // resetAfterInsc();
  });

  function clamp(val, max) {
    const v = Number(val || 0);
    const m = Number(max || 0);
    if (v < 0) return 0;
    if (m > 0 && v > m) return m;
    return v;
  }

  async function loadEcheances(inscriptionId) {
    setStatus("fa-solid fa-rotate", "Chargement des échéances…");

    const url = `${window.AZ_PAY.echeancesUrl}?inscription=${encodeURIComponent(inscriptionId)}`;
    const data = await fetchJSON(url);

    echeances = data.items || [];
    selected.clear();
    prices = {};

    const tarifs = data.tarifs || {};
    if (inscInfoText) {
      inscInfoText.innerHTML = `
        Frais mensuel (réf) : <b>${money(tarifs.frais_scolarite_mensuel)}</b> MAD
        • Reste inscription : <b>${money(tarifs.reste_inscription)}</b> MAD
        ${tarifs.tarif_override ? ' • <b class="az-warn">Tarif override</b>' : ''}
      `;
    }
    if (inscInfo) inscInfo.style.display = "block";

    monthsGrid.innerHTML = "";

    echeances.forEach((e) => {
      const id = String(e.id);
      const reste = money(e.reste);
      const du = money(e.du);
      const paye = money(e.paye);

      prices[id] = reste; // default = reste

      const card = document.createElement("button");
      card.type = "button";
      card.className = "az-month-card";

      if (e.is_paye) card.classList.add("is-paid");
      else if (Number(reste) > 0 && Number(paye) === 0) card.classList.add("is-due");
      else if (Number(reste) > 0 && Number(paye) > 0) card.classList.add("is-partial");

      card.dataset.id = id;

      card.innerHTML = `
        <div class="m-top">
          <div class="m-name">${e.mois_nom || ("M" + e.mois_index)}</div>
          <div class="m-state">
            ${e.is_paye ? `<span class="az-badge az-badge-ok">PAYÉ</span>` : `<span class="az-badge az-badge-soft">RESTE</span>`}
          </div>
        </div>

        <div class="m-stats">
          <div class="m-stat"><span>DU</span><b>${du}</b></div>
          <div class="m-stat"><span>Payé</span><b>${paye}</b></div>
          <div class="m-stat"><span>Reste</span><b>${reste}</b></div>
        </div>

        <div class="m-edit">
          <div class="m-input">
            <label>Montant</label>
            <input
              class="az-month-price"
              inputmode="decimal"
              type="number"
              min="0"
              step="0.01"
              value="${reste}"
              ${e.is_paye ? "disabled" : ""}
            />
            <small class="m-max">${e.is_paye ? "Verrouillé" : "Max: " + reste}</small>
          </div>

          <div class="m-toggle">
            <span class="t-label">Sélection</span>
            <span class="t-pill ${e.is_paye ? "is-off" : "is-off"}"><b>OFF</b></span>
          </div>
        </div>
      `;

      // toggle selection (ignore clicks inside input)
      card.addEventListener("click", (ev) => {
        const target = ev.target;
        if (target && target.classList && target.classList.contains("az-month-price")) return;
        if (e.is_paye) return;

        if (selected.has(id)) selected.delete(id);
        else selected.add(id);

        syncMonthUI(card, id);
        recompute();
      });

      // price input
      const input = card.querySelector(".az-month-price");
      input?.addEventListener("input", () => {
        const clamped = clamp(input.value, e.reste);
        input.value = money(clamped);
        prices[id] = money(clamped);
        if (selected.has(id)) recompute();
        updateSideList(); // live
      });

      monthsGrid.appendChild(card);
    });

    setStep(2);
    recompute();
  }

  function syncMonthUI(card, id) {
    const pill = card.querySelector(".t-pill");
    if (!pill) return;

    if (selected.has(id)) {
      card.classList.add("is-selected");
      pill.classList.add("is-on");
      pill.classList.remove("is-off");
      pill.innerHTML = "<b>ON</b>";
    } else {
      card.classList.remove("is-selected");
      pill.classList.remove("is-on");
      pill.classList.add("is-off");
      pill.innerHTML = "<b>OFF</b>";
    }
  }

  function updateKPI(total, count) {
    if (totalDisplay) totalDisplay.textContent = money(total);
    if (pickedCount) pickedCount.textContent = String(count);
    if (pickedCount2) pickedCount2.textContent = String(count);
  }

  function updateSideList() {
    if (!pickedList) return;

    const ids = Array.from(selected);
    if (!ids.length) {
      pickedList.innerHTML = `<div class="az-empty">Aucun mois sélectionné.</div>`;
      return;
    }

    const map = {};
    (echeances || []).forEach((e) => (map[String(e.id)] = e));

    pickedList.innerHTML = ids
      .map((id) => {
        const e = map[id];
        const label = e?.mois_nom || "Mois";
        const val = money(prices[id] || 0);
        return `
          <div class="az-pick-row">
            <div class="p-left">
              <b>${label}</b>
              <span class="p-sub">ID #${id}</span>
            </div>
            <div class="p-right">
              <b>${val}</b><span>MAD</span>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function recompute() {
    let total = 0;
    selected.forEach((id) => { total += Number(prices[id] || 0); });

    updateKPI(total, selected.size);
    updateSideList();

    hiddenTotal.value = money(total);
    hiddenMontant.value = money(total);

    hiddenPayload.value = JSON.stringify({
      selected_ids: Array.from(selected),
      prices: prices
    });

    submitBtn.disabled = !(currentInscId && selected.size > 0 && total > 0);

    // micro feedback visuel
    stepPill2.style.borderColor =
      selected.size > 0 ? "rgba(114,9,183,.55)" : "var(--az-border)";
  }

  // Quick actions
  btnSelectAllDue?.addEventListener("click", () => {
    (echeances || []).forEach((e) => {
      const id = String(e.id);
      if (e.is_paye) return;
      const reste = Number(e.reste || 0);
      if (reste <= 0) return;
      selected.add(id);
      prices[id] = money(prices[id] ?? reste);
      const card = monthsGrid.querySelector(`.az-month-card[data-id="${id}"]`);
      if (card) syncMonthUI(card, id);
    });
    recompute();
  });

  btnClearAll?.addEventListener("click", () => {
    selected.clear();
    monthsGrid.querySelectorAll(".az-month-card.is-selected").forEach((c) => {
      c.classList.remove("is-selected");
      const pill = c.querySelector(".t-pill");
      if (pill) {
        pill.classList.remove("is-on");
        pill.classList.add("is-off");
        pill.innerHTML = "<b>OFF</b>";
      }
    });
    recompute();
  });

  // submit safety
  form?.addEventListener("submit", (e) => {
    if (!currentInscId || selected.size === 0) {
      e.preventDefault();
      stepHint.textContent = "⚠️ Sélectionne au moins un mois avant de valider.";
      setStatus("fa-solid fa-triangle-exclamation", "Sélectionne au moins un mois pour valider.");
      return;
    }

    submitBtn.classList.add("is-loading");
    submitBtn.disabled = true;
    setStatus("fa-solid fa-lock", "Validation en cours…");
  });

  // init
  initTomSelect();
  setStep(1);
})();
