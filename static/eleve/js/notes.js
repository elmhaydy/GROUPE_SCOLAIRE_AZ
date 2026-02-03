/* =========================================================
   AZ — Notes JS
   - Build filters (period/subject/type) from DOM
   - Search + filter
   - Compute stats (avg/best/count)
   - Progress bars + badge grade
   - Export CSV (client side)
   ========================================================= */

(function(){
  const q = (sel, root=document) => root.querySelector(sel);
  const qa = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  const rows = qa(".notes-row");
  const cards = qa(".note-card");

  const input = q("#notesSearch");
  const clear = q("#notesClear");
  const selPeriod = q("#notesPeriod");
  const selSubject = q("#notesSubject");
  const selType = q("#notesType");
  const empty = q("#notesEmpty");

  const statAvg = q("#statAvg");
  const statBest = q("#statBest");
  const statCount = q("#statCount");

  const exportBtn = q("#notesExportCsv");

  function normalize(str){
    return (str || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function num(v){
    const n = parseFloat(String(v).replace(",", "."));
    return Number.isFinite(n) ? n : null;
  }

  function gradeFromPercent(p){
    if (p == null) return { label:"—", cls:"" };
    if (p >= 85) return { label:"Très bien", cls:"g-a" };
    if (p >= 70) return { label:"Bien", cls:"g-b" };
    if (p >= 50) return { label:"Passable", cls:"g-c" };
    return { label:"À revoir", cls:"g-d" };
  }

  function applyGradeUI(el, note, max){
    const pct = (max > 0) ? (note / max) * 100 : null;
    const g = gradeFromPercent(pct);
    const badge = el.querySelector(".badge-grade");
    const fill = el.querySelector(".score-fill");

    if (badge){
      badge.textContent = g.label;
      badge.classList.remove("g-a","g-b","g-c","g-d");
      if (g.cls) badge.classList.add(g.cls);
    }
    if (fill){
      fill.style.width = pct == null ? "0%" : `${Math.max(0, Math.min(100, pct)).toFixed(0)}%`;
    }
  }

  // Add grade colors (small inject)
  function injectGradeStyles(){
    const css = `
      .badge-grade.g-a{ border-color: rgba(34,197,94,.35); background: rgba(34,197,94,.12); color:#166534; }
      .badge-grade.g-b{ border-color: rgba(59,130,246,.35); background: rgba(59,130,246,.12); color:#1d4ed8; }
      .badge-grade.g-c{ border-color: rgba(245,158,11,.35); background: rgba(245,158,11,.14); color:#92400e; }
      .badge-grade.g-d{ border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.12); color:#b91c1c; }
    `;
    const style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  }
  injectGradeStyles();

  // Build filter options from rows (desktop)
  function buildOptions(selectEl, values){
    if (!selectEl) return;
    const cur = selectEl.value || "";
    const base = selectEl.querySelector("option[value='']");
    selectEl.innerHTML = "";
    if (base) selectEl.appendChild(base);
    values.sort((a,b)=>a.localeCompare(b, "fr"));
    values.forEach(v=>{
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      selectEl.appendChild(opt);
    });
    selectEl.value = cur;
  }

  function init(){
    // progress + grade on load
    rows.forEach(r=>{
      const note = num(r.dataset.note);
      const max = num(r.dataset.max);
      if (note != null && max != null) applyGradeUI(r, note, max);
    });
    cards.forEach(c=>{
      const note = num(c.dataset.note);
      const max = num(c.dataset.max);
      if (note != null && max != null) applyGradeUI(c, note, max);
    });

    // build filters
    const periods = new Set();
    const subjects = new Set();

    rows.forEach(r=>{
      if (r.dataset.periode) periods.add(r.dataset.periode);
      if (r.dataset.matiere) subjects.add(r.dataset.matiere);
    });

    buildOptions(selPeriod, Array.from(periods));
    buildOptions(selSubject, Array.from(subjects));

    refresh();
  }

  function matchesItem(dataset, qText, period, subject, type){
    const hay = normalize(
      `${dataset.date || ""} ${dataset.matiere || ""} ${dataset.titre || ""} ${dataset.periode || ""} ${dataset.type || ""}`
    );

    const okQ = !qText || hay.includes(qText);
    const okP = !period || (dataset.periode === period);
    const okS = !subject || (dataset.matiere === subject);
    const okT = !type || normalize(dataset.type) === normalize(type);

    return okQ && okP && okS && okT;
  }

  function refresh(){
    const qText = normalize(input?.value || "");
    const period = selPeriod?.value || "";
    const subject = selSubject?.value || "";
    const type = selType?.value || "";

    let visibleCount = 0;
    let sumPct = 0;
    let pctCount = 0;
    let bestPct = null;

    // Desktop rows
    rows.forEach(r=>{
      const ok = matchesItem(r.dataset, qText, period, subject, type);
      r.style.display = ok ? "" : "none";

      if (ok){
        visibleCount++;
        const note = num(r.dataset.note);
        const max = num(r.dataset.max);
        if (note != null && max != null && max > 0){
          const pct = (note/max)*100;
          sumPct += pct;
          pctCount++;
          bestPct = (bestPct == null) ? pct : Math.max(bestPct, pct);
        }
      }
    });

    // Mobile cards
    cards.forEach(c=>{
      const ok = matchesItem(c.dataset, qText, period, subject, type);
      c.style.display = ok ? "" : "none";
    });

    // Stats
    if (statCount) statCount.textContent = String(visibleCount);
    if (pctCount > 0){
      const avg = sumPct / pctCount;
      if (statAvg) statAvg.textContent = `${avg.toFixed(1)}%`;
      if (statBest) statBest.textContent = `${bestPct.toFixed(1)}%`;
    }else{
      if (statAvg) statAvg.textContent = "—";
      if (statBest) statBest.textContent = "—";
    }

    // Empty state
    if (empty){
      empty.style.display = (visibleCount === 0) ? "block" : "none";
    }
  }

  // Events
  if (input) input.addEventListener("input", refresh);
  if (selPeriod) selPeriod.addEventListener("change", refresh);
  if (selSubject) selSubject.addEventListener("change", refresh);
  if (selType) selType.addEventListener("change", refresh);

  if (clear){
    clear.addEventListener("click", ()=>{
      if (input) input.value = "";
      if (selPeriod) selPeriod.value = "";
      if (selSubject) selSubject.value = "";
      if (selType) selType.value = "";
      refresh();
      input?.focus();
    });
  }

  // CSV Export
  function toCsvRow(arr){
    return arr.map(v=>{
      const s = String(v ?? "");
      const escaped = s.replace(/"/g,'""');
      return `"${escaped}"`;
    }).join(",");
  }

  function exportCSV(){
    // export visible rows
    const visible = rows.filter(r => r.style.display !== "none");
    if (!visible.length) return;

    const header = ["Date","Matière","Évaluation","Période","Type","Note","Max"];
    const lines = [toCsvRow(header)];

    visible.forEach(r=>{
      lines.push(toCsvRow([
        r.dataset.date,
        r.dataset.matiere,
        r.dataset.titre,
        r.dataset.periode,
        r.dataset.type,
        r.dataset.note,
        r.dataset.max
      ]));
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "notes.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  }

  if (exportBtn) exportBtn.addEventListener("click", exportCSV);

  init();
})();
