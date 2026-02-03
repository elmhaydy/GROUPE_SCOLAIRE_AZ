(function () {
  const q = document.getElementById("q");
  const groupe = document.getElementById("groupe");
  const sort = document.getElementById("sort");
  const count = document.getElementById("count");

  const table = document.getElementById("evTable");
  if (!table) return;

  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr.ev-row"));
  const cardsWrap = document.getElementById("evCards");

  // =========================
  // Helpers
  // =========================
  const norm = (s) => (s || "").toString().trim().toLowerCase();

  function rowText(r) {
    const mat = norm(r.dataset.matiere);
    const per = norm(r.dataset.periode);
    const grp = norm(r.dataset.groupeTxt);
    return `${mat} ${per} ${grp}`.trim();
  }

  function getRowDate(r) {
    // YYYY-MM-DD
    return r.dataset.date || "";
  }

  function getRowGroupeTxt(r) {
    return (r.dataset.groupeTxt || "").toString();
  }

  function getRowMatiereTxt(r) {
    return (r.dataset.matiere || "").toString();
  }

  function isRowVisible(r) {
    return r.style.display !== "none";
  }

  function setCount(nVisible, nTotal) {
    if (!count) return;
    count.textContent = nTotal ? `• ${nVisible}/${nTotal}` : "";
  }

  // =========================
  // Click row -> open href
  // =========================
  function bindRowClick(r) {
    r.addEventListener("click", (e) => {
      // si clic sur bouton/lien -> laisser
      const a = e.target.closest("a");
      if (a) return;

      const href = r.dataset.href;
      if (href) window.location.href = href;
    });
  }

  rows.forEach(bindRowClick);

  // =========================
  // Filtering + Sorting
  // =========================
  function apply() {
    const qq = norm(q?.value);
    const gid = (groupe?.value || "").toString();
    const srt = (sort?.value || "date_desc").toString();

    // 1) filter
    let visible = 0;
    rows.forEach((r) => {
      const okGroup = !gid || (r.dataset.groupe === gid);
      const okQuery = !qq || rowText(r).includes(qq);
      const show = okGroup && okQuery;
      r.style.display = show ? "" : "none";
      if (show) visible++;
    });

    // 2) sort visible rows only
    const visibleRows = rows.filter(isRowVisible);

    visibleRows.sort((a, b) => {
      if (srt === "date_asc") return getRowDate(a).localeCompare(getRowDate(b));
      if (srt === "date_desc") return getRowDate(b).localeCompare(getRowDate(a));
      if (srt === "groupe_asc") return getRowGroupeTxt(a).localeCompare(getRowGroupeTxt(b), "fr");
      if (srt === "matiere_asc") return getRowMatiereTxt(a).localeCompare(getRowMatiereTxt(b), "fr");
      return 0;
    });

    // re-append in order (only visible ones, hidden stay in place but hidden)
    visibleRows.forEach((r) => tbody.appendChild(r));

    // 3) update cards for mobile
    renderCards(visibleRows);

    // 4) count
    setCount(visible, rows.length);
  }

  // =========================
  // Mobile cards renderer
  // =========================
  function renderCards(list) {
    if (!cardsWrap) return;

    cardsWrap.innerHTML = "";
    cardsWrap.hidden = list.length === 0;

    list.forEach((r) => {
      const href = r.dataset.href || "#";

      // Extract from cells (safe)
      const tds = r.querySelectorAll("td");
      const dateTxt = (tds[0]?.querySelector(".cell-main")?.textContent || "").trim();
      const idTxt = (tds[0]?.querySelector(".cell-sub")?.textContent || "").trim();

      const matTxt = (tds[1]?.querySelector(".cell-main")?.textContent || "").trim();
      const matCode = (tds[1]?.querySelector(".cell-sub")?.textContent || "").trim();

      const perTxt = (tds[2]?.textContent || "").trim();
      const grpMain = (tds[3]?.querySelector(".cell-main")?.textContent || "").trim();
      const grpSub = (tds[3]?.querySelector(".cell-sub")?.textContent || "").trim();

      const noteMax = (tds[4]?.textContent || "").trim();

      const card = document.createElement("div");
      card.className = "ev-card";
      card.tabIndex = 0;

      card.innerHTML = `
        <div class="ev-card-top">
          <div>
            <div class="ev-card-title">${matTxt}</div>
            <div class="muted" style="margin-top:2px">${matCode ? matCode + " • " : ""}${dateTxt} ${idTxt ? "• " + idTxt : ""}</div>
          </div>
          <div class="pill">${noteMax}</div>
        </div>

        <div class="ev-card-meta">
          <span class="badge">${perTxt}</span>
          <span>${grpMain}</span>
          <span class="muted">• ${grpSub}</span>
        </div>

        <div class="ev-card-actions">
          <a class="azp-btn sm" href="${href}">
            <i class="fa-solid fa-pen-to-square"></i>
            <span>Saisir</span>
          </a>
        </div>
      `;

      // click card -> open
      card.addEventListener("click", (e) => {
        const a = e.target.closest("a");
        if (a) return;
        if (href && href !== "#") window.location.href = href;
      });

      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (href && href !== "#") window.location.href = href;
        }
      });

      cardsWrap.appendChild(card);
    });
  }

  // =========================
  // Events
  // =========================
  let t = null;
  function debounceApply() {
    clearTimeout(t);
    t = setTimeout(apply, 80);
  }

  q?.addEventListener("input", debounceApply);
  groupe?.addEventListener("change", apply);
  sort?.addEventListener("change", apply);

  // init
  apply();
})();
