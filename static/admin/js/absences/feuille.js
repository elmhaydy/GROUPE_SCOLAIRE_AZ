/* =========================================================
   AZ — Feuille de présence (FINAL) — FIX SAVE
   - Envoie: PRESENT / ABSENT / RETARD
   - body: { seance_id, date, items }
   ========================================================= */

(function () {
  const cfg = window.PRESENCE_CONFIG || {};
  const $ = (id) => document.getElementById(id);

  const tbody = $("tbody");
  const seanceInfo = $("seance_info");
  const msgBox = $("msg");

  const cTotal = $("c_total")?.querySelector("b");
  const cPresent = $("c_present")?.querySelector("b");
  const cAbsent = $("c_absent")?.querySelector("b");
  const cRetard = $("c_retard")?.querySelector("b");

  const btnAllPresent = $("btn_all_present");
  const btnAllAbsent = $("btn_all_absent");
  const btnAllRetard = $("btn_all_retard");
  const btnSave = $("btn_save");
  const btnPrint = $("btn_print");
  const search = $("search");

  if (!cfg.apiUrl || !cfg.saveUrl || !cfg.seanceId || !cfg.dateStr) {
    console.error("PRESENCE_CONFIG manquant:", cfg);
    return;
  }

  function flash(text, type = "ok") {
    if (!msgBox) return;
    msgBox.innerHTML = `<div class="az-msg ${type}">${text}</div>`;
    setTimeout(() => { msgBox.innerHTML = ""; }, 2500);
  }

  function safe(v, def = "") {
    return (v === null || v === undefined) ? def : v;
  }

  function normalize(str) {
    return String(str || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "");
  }

  // ✅ Backend attend: PRESENT | ABSENT | RETARD
  function getSelectedStatus(id) {
    const checked = document.querySelector(`input[name="st_${id}"]:checked`);
    const v = checked ? checked.value : "P";

    if (v === "A") return "ABSENT";
    if (v === "R") return "RETARD";
    return "PRESENT";
  }

  function updateCounters() {
    const rows = tbody.querySelectorAll("tr[data-row]");
    let total = 0, p = 0, a = 0, r = 0;

    rows.forEach(tr => {
      if (tr.classList.contains("is-hidden")) return;
      total += 1;
      const id = tr.getAttribute("data-id");
      const st = getSelectedStatus(id);
      if (st === "PRESENT") p++;
      else if (st === "ABSENT") a++;
      else if (st === "RETARD") r++;
    });

    if (cTotal) cTotal.textContent = total;
    if (cPresent) cPresent.textContent = p;
    if (cAbsent) cAbsent.textContent = a;
    if (cRetard) cRetard.textContent = r;
  }

  function bindRowEvents() {
    tbody.addEventListener("change", (e) => {
      const t = e.target;
      if (t && t.matches('input[type="radio"].az-status-in')) {
        updateCounters();
      }
    });
  }

  function applySearch() {
    const q = normalize(search?.value || "");
    const rows = tbody.querySelectorAll("tr[data-row]");

    rows.forEach(tr => {
      const hay = tr.getAttribute("data-search") || "";
      const ok = q === "" || hay.includes(q);
      tr.classList.toggle("is-hidden", !ok);
    });

    updateCounters();
  }

  function render(data) {
    const seanceLabel = safe(data.seance_label, "");
    const dateLabel = safe(data.date, cfg.dateStr || "");

    if (seanceInfo) {
      seanceInfo.innerHTML = `
        <span><i class="fa-solid fa-calendar-days"></i> <b>${dateLabel}</b></span>
        ${seanceLabel ? `<span style="opacity:.7;">—</span><span>${seanceLabel}</span>` : ""}
      `;
    }

    const rows = data.eleves || [];
    if (!rows.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="3" class="az-loading-row">
            <span>Aucun élève trouvé pour ce groupe.</span>
          </td>
        </tr>
      `;
      updateCounters();
      return;
    }

    tbody.innerHTML = rows.map((x) => {
      const id = x.id;
      const matricule = safe(x.matricule, "—");
      const nom = safe(x.nom, "");
      const prenom = safe(x.prenom, "");
      const full = `${nom} ${prenom}`.trim() || "—";

      // API renvoie "P"|"A"|"R" (si c’est ton cas) -> OK
      const st = safe(x.statut, "P");
      const ckP = st === "P" ? "checked" : "";
      const ckA = st === "A" ? "checked" : "";
      const ckR = st === "R" ? "checked" : "";

      const searchBlob = normalize(`${matricule} ${nom} ${prenom}`);

      return `
        <tr class="az-tr" data-row="1" data-id="${id}" data-search="${searchBlob}">
          <td class="az-td"><strong>${matricule}</strong></td>

          <td class="az-td">
            <div class="az-row-e">
              <div><strong>${full}</strong></div>
              <div class="az-sub">${safe(x.groupe_label, "")}</div>
            </div>
          </td>

          <td class="az-td">
            <div class="az-status" data-id="${id}">
              <input class="az-status-in" type="radio" name="st_${id}" id="st_${id}_p" value="P" ${ckP}>
              <label class="az-status-btn is-present" for="st_${id}_p">
                <i class="fa-solid fa-check"></i><span>Présent</span>
              </label>

              <input class="az-status-in" type="radio" name="st_${id}" id="st_${id}_a" value="A" ${ckA}>
              <label class="az-status-btn is-absent" for="st_${id}_a">
                <i class="fa-solid fa-xmark"></i><span>Absent</span>
              </label>

              <input class="az-status-in" type="radio" name="st_${id}" id="st_${id}_r" value="R" ${ckR}>
              <label class="az-status-btn is-retard" for="st_${id}_r">
                <i class="fa-solid fa-clock"></i><span>Retard</span>
              </label>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    updateCounters();
  }

  async function load() {
    try {
      const url = `${cfg.apiUrl}?seance_id=${encodeURIComponent(cfg.seanceId)}&date=${encodeURIComponent(cfg.dateStr)}`;
      const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      const data = await res.json();
      render(data);
    } catch (e) {
      console.error(e);
      tbody.innerHTML = `<tr><td colspan="3" class="az-loading-row">Erreur de chargement.</td></tr>`;
    }
  }

  function setAll(value) {
    const rows = tbody.querySelectorAll("tr[data-row]:not(.is-hidden)");
    rows.forEach(tr => {
      const id = tr.getAttribute("data-id");
      const targetId = `st_${id}_${value.toLowerCase()}`;
      const radio = document.getElementById(targetId);
      if (radio) radio.checked = true;
    });
    updateCounters();
  }

  // ✅ SAVE FIX: envoie items (pas "items" undefined), et map statut backend
  async function save() {
    const rows = tbody.querySelectorAll("tr[data-row]");
    const items = Array.from(rows).map(tr => {
      const id = tr.getAttribute("data-id");
      return { eleve_id: Number(id), statut: getSelectedStatus(id) };
    });

    try {
      const res = await fetch(cfg.saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": cfg.csrfToken,
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({
          seance_id: Number(cfg.seanceId),
          date: cfg.dateStr,
          items: items
        })
      });

      const data = await res.json();
      if (!res.ok || data.ok === false) {
        flash(data.error || data.message || "Erreur lors de l’enregistrement.", "bad");
        return;
      }

      flash(`Feuille enregistrée ✅ (${data.saved || 0})`, "ok");
    } catch (e) {
      console.error(e);
      flash("Erreur réseau lors de l’enregistrement.", "bad");
    }
  }

  bindRowEvents();

  if (btnAllPresent) btnAllPresent.addEventListener("click", () => setAll("P"));
  if (btnAllAbsent) btnAllAbsent.addEventListener("click", () => setAll("A"));
  if (btnAllRetard) btnAllRetard.addEventListener("click", () => setAll("R"));

  if (btnSave) btnSave.addEventListener("click", save);
  if (btnPrint) btnPrint.addEventListener("click", () => window.print());
  if (search) search.addEventListener("input", applySearch);

  load();
})();
