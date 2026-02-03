/* =========================================================
   AZ — EDT JS (FIX)
   - Filter (search)
   - Highlight current time slot ONLY for TODAY column
   ========================================================= */

(function(){
  const searchInput = document.getElementById("edtSearch");
  const clearBtn = document.getElementById("edtClear");

  // -------------------------
  // FILTER
  // -------------------------
  function normalize(str){
    return (str || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function applyFilter(qRaw){
    const q = normalize(qRaw);

    document.querySelectorAll(".edt-grid .edt-cell").forEach(cell => {
      const evt = cell.querySelector(".edt-event");
      const empty = cell.querySelector(".edt-empty");
      if (!evt) return;

      const hay = normalize(evt.getAttribute("data-haystack") || evt.textContent);
      const match = !q || hay.includes(q);

      evt.classList.toggle("edt-hidden", !match);
      if (empty) empty.classList.toggle("edt-hidden", match);
    });

    document.querySelectorAll(".edt-mobile .edt-m-card").forEach(card => {
      const hay = normalize(card.getAttribute("data-haystack") || card.textContent);
      const match = !q || hay.includes(q);
      card.classList.toggle("edt-hidden", !match);
    });
  }

  if (searchInput){
    searchInput.addEventListener("input", (e) => applyFilter(e.target.value));
  }
  if (clearBtn){
    clearBtn.addEventListener("click", () => {
      if (!searchInput) return;
      searchInput.value = "";
      applyFilter("");
      searchInput.focus();
    });
  }

  // -------------------------
  // HIGHLIGHT "NOW" ONLY TODAY
  // -------------------------
  function parseRange(text){
    const t = (text || "").replace(/\s/g,"");
    const parts = t.split("–").length === 2 ? t.split("–") : t.split("-");
    if (parts.length !== 2) return null;

    const [a,b] = parts;

    const toMin = (hhmm) => {
      const [hh,mm] = hhmm.split(":").map(n => parseInt(n,10));
      if (Number.isNaN(hh) || Number.isNaN(mm)) return null;
      return hh*60 + mm;
    };

    const start = toMin(a);
    const end = toMin(b);
    if (start == null || end == null) return null;
    return { start, end };
  }

  // Trouver l’index de colonne correspondant à AUJOURD’HUI
  function getTodayColIndex(){
    const ths = Array.from(document.querySelectorAll(".edt-grid thead th"));
    if (ths.length < 2) return null;

    // th[0] = Heure, donc on prend les jours à partir de 1
    const dayHeaders = ths.slice(1).map(th => normalize(th.textContent));

    const today = new Date();
    const frDays = ["dimanche","lundi","mardi","mercredi","jeudi","vendredi","samedi"];
    const todayName = frDays[today.getDay()];

    // match exact ou commence par (si tu as "Mer" ou "Mercredi")
    let idx = dayHeaders.findIndex(h => h === todayName || h.startsWith(todayName));
    if (idx === -1) {
      // fallback: match sur les 3 premières lettres
      const short = todayName.slice(0,3);
      idx = dayHeaders.findIndex(h => h.startsWith(short));
    }
    return idx === -1 ? null : idx; // idx = 0..N-1 (dans edt-cell)
  }

  function markNow(){
    const now = new Date();
    const nowMin = now.getHours()*60 + now.getMinutes();
    const todayColIndex = getTodayColIndex(); // 0..N-1 dans .edt-cell

    // reset desktop
    document.querySelectorAll(".edt-hour-cell.is-now, .edt-cell.is-now").forEach(el => {
      el.classList.remove("is-now");
    });

    // reset mobile
    document.querySelectorAll(".edt-m-card.is-now").forEach(el => {
      el.classList.remove("is-now");
    });

    // Desktop
    document.querySelectorAll(".edt-hour-cell .edt-time").forEach(timeEl => {
      const range = parseRange(timeEl.textContent);
      if (!range) return;

      const isNow = nowMin >= range.start && nowMin < range.end;
      const hourCell = timeEl.closest(".edt-hour-cell");
      if (hourCell) hourCell.classList.toggle("is-now", isNow);

      if (!isNow) return;

      const row = hourCell.closest("tr");
      if (!row) return;

      // ✅ IMPORTANT: on highlight UNIQUEMENT la colonne du jour actuel
      if (todayColIndex == null) return;
      const cells = row.querySelectorAll(".edt-cell");
      const todayCell = cells[todayColIndex];
      if (!todayCell) return;

      const evt = todayCell.querySelector(".edt-event");
      if (evt && !evt.classList.contains("edt-hidden")){
        todayCell.classList.add("is-now");
      }
    });

    // Mobile: uniquement la section du jour actuel
    const frDays = ["dimanche","lundi","mardi","mercredi","jeudi","vendredi","samedi"];
    const todayName = normalize(frDays[new Date().getDay()]);

    document.querySelectorAll(".edt-day").forEach(dayBlock => {
      const title = dayBlock.querySelector(".edt-day-title");
      if (!title) return;

      const label = normalize(title.textContent);
      const isToday = label === todayName || label.startsWith(todayName) || label.startsWith(todayName.slice(0,3));
      if (!isToday) return;

      dayBlock.querySelectorAll(".edt-m-card").forEach(card => {
        const t = card.querySelector(".edt-m-time");
        if (!t) return;

        const range = parseRange(t.textContent);
        if (!range) return;

        const isNow = nowMin >= range.start && nowMin < range.end;
        card.classList.toggle("is-now", isNow);
      });
    });
  }

  markNow();
  setInterval(markNow, 30000);
})();
