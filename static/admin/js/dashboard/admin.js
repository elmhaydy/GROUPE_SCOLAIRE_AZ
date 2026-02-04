// admin/js/dashboard/admin.js
(function () {
  "use strict";

  let chart = null;

  const $ = (sel, root = document) => root.querySelector(sel);

  function safeParseJsonScript(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || "{}");
    } catch (e) {
      console.warn("[AZ] JSON script parse failed:", e);
      return null;
    }
  }

  function getChartData() {
    // ✅ 1) json_script (recommandé)
    const fromScript = safeParseJsonScript("monthly-chart-data");
    if (fromScript && (fromScript.labels || fromScript.paiements || fromScript.inscriptions)) {
      // support plusieurs formats
      return {
        labels: fromScript.labels || [],
        paiements: fromScript.paiements || [],
        inscriptions: fromScript.inscriptions || [],
      };
    }

    // ✅ 2) fallback window.AZ_CHART
    if (window.AZ_CHART) {
      return {
        labels: window.AZ_CHART.labels || [],
        paiements: window.AZ_CHART.paiements || [],
        inscriptions: window.AZ_CHART.inscriptions || [],
      };
    }

    return { labels: [], paiements: [], inscriptions: [] };
  }

  function sliceLast(arr, n) {
    const a = Array.isArray(arr) ? arr : [];
    return a.slice(Math.max(a.length - n, 0));
  }

  function formatMAD(v) {
    const num = Number(v || 0);
    // format simple (tu peux le remplacer par Intl si tu veux)
    return num.toLocaleString("fr-FR");
  }

  function buildChart(canvas, base, period) {
    const count = period === "6m" ? 6 : 12;

    const labels = sliceLast(base.labels, count);
    const paiements = sliceLast(base.paiements, count);
    const inscriptions = sliceLast(base.inscriptions, count);

    // destroy ancien
    if (chart) {
      chart.destroy();
      chart = null;
    }

    // si pas de données
    const hasAny =
      labels.length &&
      (paiements.some((x) => Number(x) !== 0) || inscriptions.some((x) => Number(x) !== 0));

    if (!hasAny) {
      // garde le canvas vide mais au moins visible
      return null;
    }

    chart = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Paiements (MAD)",
            data: paiements,
            tension: 0.35,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 2,
          },
          {
            label: "Inscriptions (nb)",
            data: inscriptions,
            tension: 0.35,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 2,
            yAxisID: "y2",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false, // ✅ avec notre height CSS
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            labels: { boxWidth: 10, boxHeight: 10 },
          },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                const label = ctx.dataset.label || "";
                const v = ctx.parsed.y;
                if (label.includes("MAD")) return `${label}: ${formatMAD(v)}`;
                return `${label}: ${v}`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (v) => formatMAD(v),
            },
          },
          y2: {
            beginAtZero: true,
            position: "right",
            grid: { drawOnChartArea: false },
          },
        },
      },
    });

    return chart;
  }

  function setTitle(period) {
    const h3 = $(".azad-card-head h3");
    if (!h3) return;
    const base = h3.textContent.replace(/\(\s*\d+\s*mois\s*\)/i, "").trim();
    const txt = period === "6m" ? "Pilotage (6 mois)" : "Pilotage (12 mois)";
    // si ton h3 contient déjà l'icône via HTML, on évite de casser : on modifie seulement le texte si possible
    // => on fait simple : on remplace juste la partie texte si elle existe
    if (h3.innerText) h3.innerText = txt;
  }

  function init() {
    const canvas = $("#monthlyChart");
    const periodSel = $("#chartPeriod");
    const exportBtn = $("#exportChart");

    if (!canvas) {
      console.warn("[AZ] #monthlyChart not found");
      return;
    }

    const baseData = getChartData();

    // default
    const defaultPeriod = periodSel ? (periodSel.value || "12m") : "12m";
    buildChart(canvas, baseData, defaultPeriod);
    setTitle(defaultPeriod);

    if (periodSel) {
      periodSel.addEventListener("change", () => {
        const p = periodSel.value || "12m";
        buildChart(canvas, baseData, p);
        setTitle(p);
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        if (!chart) return;
        const a = document.createElement("a");
        a.href = chart.toBase64Image("image/png", 1);
        a.download = "pilotage.png";
        a.click();
      });
    }
  }

  window.addEventListener("DOMContentLoaded", init);
})();
