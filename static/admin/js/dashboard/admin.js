// AZ Dashboard Admin v2
(function () {
  "use strict";

  let chart = null;

  const $ = (sel, root = document) => root.querySelector(sel);

  function loadChartData() {
    const script = document.getElementById("azd-chart-data");
    if (!script) return null;
    try {
      return JSON.parse(script.textContent || "{}");
    } catch (e) {
      console.warn("[AZ] chart JSON parse error:", e);
      return null;
    }
  }

  function sliceData(base, count) {
    const take = (arr) => Array.isArray(arr) ? arr.slice(Math.max(arr.length - count, 0)) : [];
    return {
      labels: take(base.labels || []),
      net: take(base.net || []),
      depenses: take(base.depenses || []),
      impayes: take(base.impayes || []),
    };
  }

  function gradient(ctx, color) {
    const g = ctx.createLinearGradient(0, 0, 0, 260);
    g.addColorStop(0, color.replace("1)", "0.28)"));
    g.addColorStop(1, color.replace("1)", "0.03)"));
    return g;
  }

  function buildChart(canvas, base, range) {
    if (!canvas || !base) return;

    const ctx = canvas.getContext("2d");
    const data = sliceData(base, range);

    if (chart) {
      chart.destroy();
      chart = null;
    }

    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Net",
            data: data.net,
            borderColor: "rgba(14,165,233,1)",
            backgroundColor: gradient(ctx, "rgba(14,165,233,1)"),
            tension: 0.35,
            fill: true,
            borderWidth: 2,
            pointRadius: 3,
          },
          {
            label: "D&eacute;penses",
            data: data.depenses,
            borderColor: "rgba(239,68,68,1)",
            backgroundColor: gradient(ctx, "rgba(239,68,68,1)"),
            tension: 0.35,
            fill: true,
            borderWidth: 2,
            pointRadius: 3,
          },
          {
            label: "Impay&eacute;s",
            data: data.impayes,
            borderColor: "rgba(249,115,22,1)",
            backgroundColor: gradient(ctx, "rgba(249,115,22,1)"),
            tension: 0.35,
            fill: true,
            borderWidth: 2,
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { boxWidth: 12, boxHeight: 12 } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.parsed.y || 0).toLocaleString("fr-FR")}`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: (v) => Number(v).toLocaleString("fr-FR") },
            grid: { color: "rgba(148,163,184,0.16)" },
          },
          x: {
            grid: { color: "rgba(148,163,184,0.10)" },
          },
        },
      },
    });
  }

  function init() {
    const canvas = $("#azdChart");
    const rangeSel = $("#azdChartRange");
    const exportBtn = $("#azdExportChart");
    const base = loadChartData();
    if (!canvas || !base) return;

    const defaultRange = Number(rangeSel?.value || 12);
    buildChart(canvas, base, defaultRange);

    if (rangeSel) {
      rangeSel.addEventListener("change", () => {
        const r = Number(rangeSel.value || 12);
        buildChart(canvas, base, r);
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        if (!chart) return;
        const a = document.createElement("a");
        a.href = chart.toBase64Image("image/png", 1);
        a.download = "dashboard-az.png";
        a.click();
      });
    }
  }

  window.addEventListener("DOMContentLoaded", init);
})();
