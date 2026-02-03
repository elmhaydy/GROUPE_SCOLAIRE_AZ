/* =========================================================
   AZ — PAIEMENTS JS (FINAL)
   - Search (montant, mode, ref, note, etc.)
   - Optional filters: nature, mode (si présents)
   - Sort via th[data-sort]
   - KPI "Affichés"
   - Empty state
   - Export CSV (visible rows)
   ========================================================= */

(function () {
  // Inputs / Buttons (certains peuvent ne pas exister => pas d'erreur)
  const qInput    = document.getElementById("paySearch");
  const clearBtn  = document.getElementById("payClear");
  const selNature = document.getElementById("payNature");
  const selMode   = document.getElementById("payMode");
  const exportBtn = document.getElementById("payExport");

  // Table
  const table = document.getElementById("payTable");
  const tbody = document.getElementById("payTbody") || (table ? table.querySelector("tbody") : null);
  const empty = document.getElementById("payEmpty");
  const kShown = document.getElementById("kpiShown");

  if (!table || !tbody || !kShown) return;

  let rows = Array.from(tbody.querySelectorAll(".pay-row"));

  function normalize(str) {
    return (str || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function setHidden(row, hidden) {
    row.style.display = hidden ? "none" : "";
  }

  function refreshShown() {
    const visible = rows.filter(r => r.style.display !== "none").length;
    kShown.textContent = String(visible);

    if (empty) {
      // Si on a des paiements mais 0 visible => afficher empty
      // Si pas de paiements du tout, ton template gère déjà l'empty.
      empty.style.display = (rows.length > 0 && visible === 0) ? "" : "none";
    }
  }

  function applyFilters() {
    const q = normalize(qInput ? qInput.value : "");
    const nat = selNature ? selNature.value : "";
    const mode = selMode ? selMode.value : "";

    rows.forEach(r => {
      const hay = normalize(r.getAttribute("data-haystack") || r.innerText);
      const rNat = r.getAttribute("data-nature") || "";
      const rMode = r.getAttribute("data-mode") || "";

      const matchQ = !q || hay.includes(q);
      const matchN = !nat || rNat === nat;
      const matchM = !mode || rMode === mode;

      setHidden(r, !(matchQ && matchN && matchM));
    });

    refreshShown();
  }

  // ======================
  // Sorting
  // ======================
  let sortKey = "date";
  let sortDir = "desc";

  function getSortVal(row, key) {
    if (key === "date") return row.getAttribute("data-date") || "";
    if (key === "nature") return row.getAttribute("data-nature") || "";
    if (key === "mode") return row.getAttribute("data-mode") || "";
    if (key === "montant") return parseFloat(row.getAttribute("data-montant") || "0");
    return "";
  }

  function sortRows(key) {
    // toggle direction
    if (sortKey === key) {
      sortDir = (sortDir === "asc") ? "desc" : "asc";
    } else {
      sortKey = key;
      // par défaut : date desc, autres asc
      sortDir = (key === "date") ? "desc" : "asc";
    }

    const factor = (sortDir === "asc") ? 1 : -1;

    rows.sort((a, b) => {
      const va = getSortVal(a, key);
      const vb = getSortVal(b, key);

      if (typeof va === "number" && typeof vb === "number") {
        return (va - vb) * factor;
      }
      // strings
      if (va < vb) return -1 * factor;
      if (va > vb) return  1 * factor;
      return 0;
    });

    // repaint DOM
    rows.forEach(r => tbody.appendChild(r));

    // réappliquer filtre après tri (garde l’état visible)
    applyFilters();
  }

  // Click headers
  table.querySelectorAll("thead th[data-sort]").forEach(th => {
    th.style.cursor = "pointer";
    th.addEventListener("click", () => sortRows(th.getAttribute("data-sort")));
  });

  // ======================
  // Export CSV (visible rows)
  // ======================
  function exportCSV() {
    const visibleRows = rows.filter(r => r.style.display !== "none");

    const header = ["Date", "Nature", "Mode", "Montant", "Reference"];
    const lines = [header.join(",")];

    const safe = (s) => `"${String(s ?? "").replace(/"/g, '""')}"`;

    visibleRows.forEach(r => {
      const date = r.getAttribute("data-date") || "";
      const nature = r.getAttribute("data-nature") || "";
      const mode = r.getAttribute("data-mode") || "";
      const montant = r.getAttribute("data-montant") || "";

      const tds = r.querySelectorAll("td");
      const ref = (tds[4]?.innerText || "").replace(/\s+/g, " ").trim();

      lines.push([safe(date), safe(nature), safe(mode), safe(montant), safe(ref)].join(","));
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `paiements_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  }

  // ======================
  // Events
  // ======================
  if (qInput) {
    qInput.addEventListener("input", applyFilters);
    qInput.addEventListener("change", applyFilters);
  }
  if (selNature) selNature.addEventListener("change", applyFilters);
  if (selMode) selMode.addEventListener("change", applyFilters);

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (qInput) qInput.value = "";
      if (selNature) selNature.value = "";
      if (selMode) selMode.value = "";
      applyFilters();
      if (qInput) qInput.focus();
    });
  }

  if (exportBtn) {
    exportBtn.addEventListener("click", exportCSV);
  }

  // Init
  applyFilters();
})();
