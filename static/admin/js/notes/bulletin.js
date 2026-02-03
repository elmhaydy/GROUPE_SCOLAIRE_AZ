(function () {
  const q = document.getElementById("azbulSearch");
  const clear = document.getElementById("azbulClear");
  const table = document.getElementById("azbulTable");
  const empty = document.getElementById("azbulEmpty");

  // auto-submit quand on change les selects (optionnel)
  const annee = document.getElementById("azbulAnnee");
  const periode = document.getElementById("azbulPeriode");
  if (annee && periode) {
    annee.addEventListener("change", () => annee.form && annee.form.submit());
    periode.addEventListener("change", () => periode.form && periode.form.submit());
  }

  // progress bars
  if (table) {
    table.querySelectorAll(".fill").forEach((el) => {
      const v = parseFloat(el.getAttribute("data-val") || "0");
      const pct = Math.max(0, Math.min(100, (v / 20) * 100));
      el.style.width = pct + "%";
    });
  }

  // toggle details
  if (table) {
    table.querySelectorAll(".toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-target");
        const row = document.getElementById(id);
        if (!row) return;

        const open = row.style.display === "table-row";
        row.style.display = open ? "none" : "table-row";
        btn.classList.toggle("open", !open);
      });
    });
  }

  // search filter
  function applyFilter() {
    if (!table || !q) return;
    const term = (q.value || "").trim().toLowerCase();

    let visibleCount = 0;
    const rows = table.querySelectorAll("tbody tr.row");
    rows.forEach((r) => {
      const mat = (r.getAttribute("data-matiere") || "").toLowerCase();
      const show = !term || mat.includes(term);

      r.style.display = show ? "" : "none";

      // detail row is right after
      const detail = r.nextElementSibling;
      if (detail && detail.classList.contains("detail")) {
        // si on cache la matière => on cache aussi détail
        if (!show) detail.style.display = "none";
      }

      if (show) visibleCount++;
    });

    if (empty) empty.style.display = visibleCount ? "none" : "block";
  }

  if (q) q.addEventListener("input", applyFilter);
  if (clear && q) {
    clear.addEventListener("click", () => {
      q.value = "";
      applyFilter();
      q.focus();
    });
  }

  applyFilter();
})();
