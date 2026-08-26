/* Finance Dashboard — Chart.js v4 */
(function () {
  "use strict";

  const FONT = "'Inter', system-ui, sans-serif";
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const GRID_COLOR = isDark ? "rgba(255,255,255,.08)" : "rgba(0,0,0,.06)";
  const TEXT_COLOR = isDark ? "#94a3b8" : "#6b7280";
  const DU_BAR_BG = isDark ? "rgba(71,85,105,.5)" : "rgba(226,232,240,.5)";
  const DU_BAR_BORDER = isDark ? "#475569" : "#cbd5e1";

  function parseJson(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch { return null; }
  }

  function fmt(n) {
    return Number(n).toLocaleString("fr-FR", { maximumFractionDigits: 0 });
  }

  Chart.defaults.font.family = FONT;
  Chart.defaults.color = TEXT_COLOR;

  // ── 1. Encaissé par mois (bar groupé) ────────────────────────────────────
  (function buildEncaisse() {
    const data = parseJson("fd-encaisse-data");
    if (!data) return;
    const ctx = document.getElementById("chartEncaisse");
    if (!ctx) return;

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Dû total",
            data: data.sco_du.map((v, i) => v + (data.tr_du[i] || 0)),
            backgroundColor: DU_BAR_BG,
            borderColor: DU_BAR_BORDER,
            borderWidth: 1,
            borderRadius: 4,
            order: 3,
          },
          {
            label: "Scolarité encaissée",
            data: data.sco_paye,
            backgroundColor: "rgba(99,102,241,.75)",
            borderRadius: 4,
            order: 1,
          },
          {
            label: "Transport encaissé",
            data: data.tr_paye,
            backgroundColor: "rgba(16,185,129,.75)",
            borderRadius: 4,
            order: 2,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 12, padding: 16 } },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label} : ${fmt(ctx.parsed.y)} MAD`,
            },
          },
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            grid: { color: GRID_COLOR },
            ticks: { callback: (v) => fmt(v) + " MAD" },
          },
        },
      },
    });
  })();

  // ── 2. Prévisionnel (bar + line) ─────────────────────────────────────────
  (function buildPrev() {
    const data = parseJson("fd-prev-data");
    if (!data) return;
    const ctx = document.getElementById("chartPrevisionnel");
    if (!ctx) return;

    // Remplir la projection pour mois écoulés (null → valeur réelle)
    const projFull = data.projection.map((v, i) =>
      v !== null ? v : data.encaisse[i]
    );

    new Chart(ctx, {
      data: {
        labels: data.labels,
        datasets: [
          {
            type: "bar",
            label: "Attendu",
            data: data.attendu,
            backgroundColor: DU_BAR_BG,
            borderRadius: 4,
            order: 3,
          },
          {
            type: "bar",
            label: "Encaissé",
            data: data.encaisse,
            backgroundColor: "rgba(16,185,129,.75)",
            borderRadius: 4,
            order: 2,
          },
          {
            type: "line",
            label: "Projection",
            data: projFull,
            borderColor: "#6366f1",
            borderWidth: 2,
            borderDash: [4, 4],
            pointRadius: 4,
            pointBackgroundColor: "#6366f1",
            fill: false,
            tension: 0.3,
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 12, padding: 14 } },
          tooltip: {
            callbacks: {
              label: (c) => ` ${c.dataset.label} : ${fmt(c.parsed.y)} MAD`,
              afterBody: (items) => {
                const i = items[0]?.dataIndex ?? -1;
                if (i >= 0 && data.taux[i] != null) {
                  return [`Taux : ${data.taux[i]}%`];
                }
              },
            },
          },
          annotation: undefined,
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            grid: { color: GRID_COLOR },
            ticks: { callback: (v) => fmt(v) },
          },
        },
      },
    });
  })();

  // ── 3. Impayés par groupe (horizontal bar) ────────────────────────────────
  (function buildImpayes() {
    const data = parseJson("fd-impayes-data");
    if (!data || !data.labels.length) return;
    const ctx = document.getElementById("chartImpayes");
    if (!ctx) return;

    // Couleurs dégradées : rouge → orange selon rang
    const colors = data.labels.map((_, i) => {
      const ratio = i / Math.max(data.labels.length - 1, 1);
      const r = Math.round(239 - ratio * (239 - 251));
      const g = Math.round(68  + ratio * (115 - 68));
      const b = Math.round(68  + ratio * (22  - 68));
      return `rgba(${r},${g},${b},.8)`;
    });

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Reste dû",
            data: data.reste,
            backgroundColor: colors,
            borderRadius: 4,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (c) => ` ${fmt(c.parsed.x)} MAD — ${data.nb[c.dataIndex]} élève(s)`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: GRID_COLOR },
            ticks: { callback: (v) => fmt(v) },
          },
          y: { grid: { display: false } },
        },
      },
    });
  })();

  // ── 4. Transport (doughnut + sparkline) ───────────────────────────────────
  (function buildTransport() {
    const data = parseJson("fd-transport-data");
    if (!data) return;

    // Doughnut avec/sans transport
    const ctxD = document.getElementById("chartTransport");
    if (ctxD) {
      new Chart(ctxD, {
        type: "doughnut",
        data: {
          labels: ["Avec transport", "Sans transport"],
          datasets: [
            {
              data: [data.avec, data.sans],
              backgroundColor: ["#8b5cf6", "#e5e7eb"],
              borderWidth: 0,
              hoverOffset: 4,
            },
          ],
        },
        options: {
          cutout: "70%",
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (c) => ` ${c.label} : ${c.parsed} élève(s)`,
              },
            },
          },
        },
      });
    }

    // Sparkline transport par mois
    const ctxS = document.getElementById("chartTransportMois");
    if (ctxS) {
      const labels = ["Sep","Oct","Nov","Déc","Jan","Fév","Mar","Avr","Mai","Jun"];
      new Chart(ctxS, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Dû transport",
              data: data.du_mois,
              backgroundColor: "rgba(139,92,246,.25)",
              borderRadius: 3,
              order: 2,
            },
            {
              label: "Encaissé transport",
              data: data.paye_mois,
              backgroundColor: "rgba(139,92,246,.75)",
              borderRadius: 3,
              order: 1,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 10, padding: 12 } },
            tooltip: {
              callbacks: {
                label: (c) => ` ${c.dataset.label} : ${fmt(c.parsed.y)} MAD`,
              },
            },
          },
          scales: {
            x: { grid: { display: false } },
            y: {
              grid: { color: GRID_COLOR },
              ticks: { callback: (v) => fmt(v) },
            },
          },
        },
      });
    }
  })();
})();
