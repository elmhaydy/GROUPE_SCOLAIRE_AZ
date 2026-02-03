/* =========================================================
   AZ — ABSENCES JS
   - Search + filters (type, justif)
   - Sort (date, type, justif)
   - KPI counters
   - Export CSV
   ========================================================= */

(function(){
  const qInput  = document.getElementById("absSearch");
  const clearBtn = document.getElementById("absClear");
  const selType = document.getElementById("absType");
  const selJust = document.getElementById("absJustif");
  const exportBtn = document.getElementById("absExport");

  const tbody = document.getElementById("absTbody");
  const empty = document.getElementById("absEmpty");

  const kTotal = document.getElementById("kpiTotal");
  const kAbs   = document.getElementById("kpiAbs");
  const kRet   = document.getElementById("kpiRet");
  const kNoJ   = document.getElementById("kpiNoJustif");

  const rows = Array.from(document.querySelectorAll(".abs-row"));
  const cards = Array.from(document.querySelectorAll(".abs-card"));

  function normalize(str){
    return (str || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function isVisible(el){
    return !el.classList.contains("abs-hidden");
  }

  function setHidden(el, hidden){
    el.classList.toggle("abs-hidden", hidden);
    el.style.display = hidden ? "none" : "";
  }

  function apply(){
    const q = normalize(qInput ? qInput.value : "");
    const t = selType ? selType.value : "";
    const j = selJust ? selJust.value : "";

    let visibleCount = 0;

    // Desktop rows
    rows.forEach(r => {
      const hay = normalize(r.getAttribute("data-haystack"));
      const type = r.getAttribute("data-type");
      const just = r.getAttribute("data-justif");

      const matchQ = !q || hay.includes(q);
      const matchT = !t || type === t;
      const matchJ = !j || just === j;

      const show = matchQ && matchT && matchJ;
      setHidden(r, !show);
      if (show) visibleCount++;
    });

    // Mobile cards
    cards.forEach(c => {
      const hay = normalize(c.getAttribute("data-haystack"));
      const type = c.getAttribute("data-type");
      const just = c.getAttribute("data-justif");

      const matchQ = !q || hay.includes(q);
      const matchT = !t || type === t;
      const matchJ = !j || just === j;

      setHidden(c, !(matchQ && matchT && matchJ));
    });

    // Empty state (desktop)
    if (empty && tbody){
      empty.style.display = visibleCount === 0 ? "" : "none";
    }

    // KPI
    refreshKPI();
  }

  function refreshKPI(){
    const visibleRows = rows.filter(r => r.style.display !== "none");
    const total = visibleRows.length;

    let abs = 0, ret = 0, noJust = 0;
    visibleRows.forEach(r => {
      const type = r.getAttribute("data-type");
      const just = r.getAttribute("data-justif");
      if (type === "ABS") abs++;
      if (type === "RET") ret++;
      if (just === "0") noJust++;
    });

    if (kTotal) kTotal.textContent = total;
    if (kAbs)   kAbs.textContent = abs;
    if (kRet)   kRet.textContent = ret;
    if (kNoJ)   kNoJ.textContent = noJust;
  }

  // Sorting
  let sortKey = "date";
  let sortDir = "desc";

  function sortRows(key){
    if (!tbody) return;

    if (sortKey === key){
      sortDir = (sortDir === "asc") ? "desc" : "asc";
    } else {
      sortKey = key;
      sortDir = (key === "date") ? "desc" : "asc";
    }

    const factor = sortDir === "asc" ? 1 : -1;

    const getVal = (r) => {
      if (key === "date") return r.getAttribute("data-date") || "";
      if (key === "type") return r.getAttribute("data-type") || "";
      if (key === "justif") return r.getAttribute("data-justif") || "";
      return "";
    };

    rows.sort((a,b) => {
      const va = getVal(a), vb = getVal(b);
      if (va < vb) return -1 * factor;
      if (va > vb) return  1 * factor;
      return 0;
    });

    // Re-append in new order
    rows.forEach(r => tbody.appendChild(r));
    apply();
  }

  document.querySelectorAll(".az-abs-table thead th[data-sort]").forEach(th => {
    th.addEventListener("click", () => sortRows(th.getAttribute("data-sort")));
  });

  // Export CSV (visible only)
  function exportCSV(){
    const visibleRows = rows.filter(r => r.style.display !== "none");
    const header = ["Date","Type","Seance","Justifie","Motif"];

    const lines = [header.join(",")];

    visibleRows.forEach(r => {
      const date = r.getAttribute("data-date") || "";
      const type = r.getAttribute("data-type") || "";
      const just = r.getAttribute("data-justif") === "1" ? "Oui" : "Non";

      const tds = r.querySelectorAll("td");
      const seance = (tds[2]?.innerText || "").replace(/\s+/g," ").trim();
      const motif  = (tds[4]?.innerText || "").replace(/\s+/g," ").trim();

      const safe = (s) => `"${String(s).replace(/"/g,'""')}"`;
      lines.push([safe(date), safe(type), safe(seance), safe(just), safe(motif)].join(","));
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `absences_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // Events
  if (qInput) qInput.addEventListener("input", apply);
  if (selType) selType.addEventListener("change", apply);
  if (selJust) selJust.addEventListener("change", apply);

  if (clearBtn){
    clearBtn.addEventListener("click", () => {
      if (qInput) qInput.value = "";
      if (selType) selType.value = "";
      if (selJust) selJust.value = "";
      apply();
      qInput && qInput.focus();
    });
  }

  if (exportBtn) exportBtn.addEventListener("click", exportCSV);

  // Init
  apply();
})();
