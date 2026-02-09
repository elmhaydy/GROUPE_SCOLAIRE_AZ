/* static/admin/js/dashboard/superadmin.js */
/* global Chart */

(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const toNumber = (x) => {
    const n = Number(x);
    return Number.isFinite(n) ? n : 0;
  };

  const formatMAD = (v) => {
    const n = toNumber(v);
    return n.toLocaleString("fr-FR", { maximumFractionDigits: 0 }) + " MAD";
  };

  const niceMax = (arr, minMax = 10) => {
    const max = Math.max(minMax, ...arr.map(toNumber));
    if (!Number.isFinite(max) || max <= 0) return minMax;
    const pow = Math.pow(10, String(Math.floor(max)).length - 1);
    return Math.ceil(max / pow) * pow;
  };

  // Date FR fallback (si backend vide)
  const setCurrentDateFR = () => {
    const el = $("#currentDate");
    if (!el) return;
    if ((el.textContent || "").trim().length > 0) return;

    const d = new Date();
    const months = [
      "janvier","février","mars","avril","mai","juin",
      "juillet","août","septembre","octobre","novembre","décembre"
    ];
    const dd = String(d.getDate()).padStart(2, "0");
    el.textContent = `${dd} ${months[d.getMonth()]} ${d.getFullYear()}`;
  };

  // Tabs activité récente
  const initTabs = () => {
    const tabs = $$(".azsa-tab");
    if (!tabs.length) return;

    const panels = {
      paiements: $("#paiementsTab"),
      inscriptions: $("#inscriptionsTab"),
      impayes: $("#impayesTab"),
    };

    const setActive = (key) => {
      tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === key));
      Object.entries(panels).forEach(([k, p]) => p && p.classList.toggle("active", k === key));
    };

    tabs.forEach((btn) => btn.addEventListener("click", (e) => {
      e.preventDefault();
      setActive(btn.dataset.tab);
    }));

    const current = tabs.find((b) => b.classList.contains("active"));
    setActive(current ? current.dataset.tab : "paiements");
  };

  // Refresh
  const initRefresh = () => {
    const btn = $("#refreshDashboard");
    if (!btn) return;
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      btn.disabled = true;
      btn.classList.add("is-loading");
      window.location.reload();
    });
  };

  // Chart pilotage (NET / DEPENSES / IMPAYES)
  let chartInstance = null;

  const getChartSource = () => {
    const src = window.AZ_CHART || {};
    return {
      labels: Array.isArray(src.labels) ? src.labels : [],
      net: (Array.isArray(src.net) ? src.net : []).map(toNumber),
      depenses: (Array.isArray(src.depenses) ? src.depenses : []).map(toNumber),
      impayes: (Array.isArray(src.impayes) ? src.impayes : []).map(toNumber),
    };
  };

  const slicePeriod = (take) => {
    const s = getChartSource();
    return {
      labels: s.labels.slice(-take),
      net: s.net.slice(-take),
      depenses: s.depenses.slice(-take),
      impayes: s.impayes.slice(-take),
    };
  };

  const renderChart = (period = "12m") => {
    const canvas = $("#monthlyChart");
    if (!canvas || typeof Chart === "undefined") return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const take = period === "6m" ? 6 : 12;
    const { labels, net, depenses, impayes } = slicePeriod(take);
    if (!labels.length) return;

    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }

    const yMax = niceMax([...net, ...depenses, ...impayes], 10);

    chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Net (MAD)", data: net, tension: 0.35, pointRadius: 2, borderWidth: 2 },
          { label: "Dépenses (MAD)", data: depenses, tension: 0.35, pointRadius: 2, borderWidth: 2 },
          { label: "Impayés (MAD)", data: impayes, tension: 0.35, pointRadius: 2, borderWidth: 2 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: true, position: "top", labels: { boxWidth: 26, boxHeight: 10 } },
          tooltip: {
            enabled: true,
            callbacks: { label: (c) => `${c.dataset.label}: ${formatMAD(c.parsed.y)}` },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: yMax,
            ticks: { callback: (v) => toNumber(v).toLocaleString("fr-FR") },
            grid: { drawBorder: false },
          },
          x: { ticks: { autoSkip: true, maxRotation: 0 }, grid: { drawBorder: false } },
        },
      },
    });
  };

  const initChartControls = () => {
    const periodSel = $("#chartPeriod");
    if (periodSel) periodSel.addEventListener("change", () => renderChart(periodSel.value || "12m"));

    const exportBtn = $("#exportChart");
    if (exportBtn) {
      exportBtn.addEventListener("click", (e) => {
        e.preventDefault();
        const canvas = $("#monthlyChart");
        if (!canvas) return;
        const url = canvas.toDataURL("image/png");
        const a = document.createElement("a");
        a.href = url;
        a.download = `pilotage_${new Date().toISOString().slice(0, 10)}.png`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      });
    }
  };

  const boot = () => {
    setCurrentDateFR();
    initTabs();
    initRefresh();
    initChartControls();

    const periodSel = $("#chartPeriod");
    renderChart(periodSel ? (periodSel.value || "12m") : "12m");
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
