/* =========================================================
   AZ — Bulletin JS
   - auto submit select periode
   - search matière
   - toggle details (desktop + mobile)
   - progress bars (/20)
   - print
   ========================================================= */

(function(){
  const q = (s, r=document) => r.querySelector(s);
  const qa = (s, r=document) => Array.from(r.querySelectorAll(s));

  const sel = q("#bulPeriode");
  const printBtn = q("#bulPrint");

  const search = q("#bulSearch");
  const clear = q("#bulClear");
  const empty = q("#bulEmpty");

  // 1) changement période => submit
  if (sel){
    sel.addEventListener("change", () => {
      sel.form?.submit();
    });
  }

  // 2) print/pdf
  if (printBtn){
    printBtn.addEventListener("click", () => window.print());
  }

  // 3) progress bars
  qa(".fill").forEach(el=>{
    const val = parseFloat(el.getAttribute("data-val") || "0");
    const pct = Math.max(0, Math.min(100, (val/20)*100));
    el.style.width = pct.toFixed(0) + "%";
  });

  // 4) toggle details
  function toggleById(id, btn){
    const target = q("#"+id);
    if (!target) return;

    const open = target.classList.toggle("open");
    if (btn){
      btn.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  qa(".bul-toggle").forEach(btn=>{
    const id = btn.getAttribute("data-target");
    if (!id) return;
    btn.setAttribute("aria-expanded", "false");
    btn.addEventListener("click", () => toggleById(id, btn));
  });

  // 5) search matière
  function normalize(str){
    return (str || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function applyFilter(qText){
    const nq = normalize(qText);

    // desktop rows
    const rows = qa(".bul-row");
    let visible = 0;

    rows.forEach(r=>{
      const mat = normalize(r.getAttribute("data-matiere") || r.textContent);
      const ok = !nq || mat.includes(nq);

      r.style.display = ok ? "" : "none";

      // fermer détail si hidden
      const btn = r.querySelector(".bul-toggle");
      const detId = btn?.getAttribute("data-target");
      const det = detId ? q("#"+detId) : null;
      if (!ok && det){
        det.classList.remove("open");
        btn?.classList.remove("open");
      }

      if (ok) visible++;
    });

    // mobile cards
    const cards = qa(".m-card");
    cards.forEach(c=>{
      const mat = normalize(c.getAttribute("data-matiere") || c.textContent);
      const ok = !nq || mat.includes(nq);
      c.style.display = ok ? "" : "none";

      // fermer détail si hidden
      if (!ok){
        const detBtn = c.querySelector(".bul-toggle");
        const detId = detBtn?.getAttribute("data-target");
        const det = detId ? q("#"+detId) : null;
        det?.classList.remove("open");
        detBtn?.classList.remove("open");
      }
    });

    if (empty){
      empty.style.display = (visible === 0 && rows.length > 0) ? "block" : "none";
    }
  }

  if (search){
    search.addEventListener("input", (e)=> applyFilter(e.target.value));
  }
  if (clear){
    clear.addEventListener("click", ()=>{
      if (search) search.value = "";
      applyFilter("");
      search?.focus();
    });
  }
})();
