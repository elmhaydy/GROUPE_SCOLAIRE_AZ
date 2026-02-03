/* ==========================================================================
   dashboard_admin.js — AZ Admin Dashboard (AZ NEBULA)
   - Tabs (paiements / inscriptions / impayes)
   - Chart.js (12m / 6m) depuis json_script "monthly-chart-data"
   - Export PNG
   - Refresh UI + notifications
   - Rappels (UI demo)
   - Auto date (si besoin)
   ========================================================================== */

(() => {
  "use strict";

  // ---------- Helpers ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const getTheme = () => document.documentElement.getAttribute("data-theme") || "dark";
  const isDark = () => getTheme() === "dark";

  const textColor = () => (isDark() ? "#f1f5f9" : "#1e293b");
  const gridColor = () => (isDark() ? "rgba(255,255,255,.10)" : "rgba(0,0,0,.06)");
  const surfaceColor = () => (isDark() ? "#0f172a" : "#ffffff");

  const notify = (title, message, type = "info") => {
    if (window.azAdmin && typeof window.azAdmin.showNotification === "function") {
      window.azAdmin.showNotification(title, message, type);
      return;
    }
    // fallback
    console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
  };

  const fmtMoney = (n) => {
    const v = Number(n || 0);
    return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(v);
  };

  // ---------- Data parsing ----------
  function readMonthlyJson() {
    const el = $("#monthly-chart-data");
    if (!el) return null;

    try {
      // json_script => contenu textContent JSON
      return JSON.parse(el.textContent || "{}");
    } catch (e) {
      console.warn("monthly-chart-data JSON invalide", e);
      return null;
    }
  }

  /**
   * Normalise plusieurs formats possibles (tu peux adapter côté backend).
   * Formats acceptés:
   *  A) {labels:[...], payments:[...], unpaid:[...]}  (simple)
   *  B) {labels:[...], datasets:{paid:[...], unpaid:[...]}}
   *  C) [{label:"Jan", paid:123, unpaid:4}, ...]
   */
  function normalizeMonthlyData(raw) {
    if (!raw) return fallbackMonthly();

    // Format C: array of objects
    if (Array.isArray(raw)) {
      const labels = raw.map(x => x.label ?? x.month ?? "");
      const payments = raw.map(x => Number(x.paid ?? x.payments ?? x.encaisse ?? 0));
      const unpaid = raw.map(x => Number(x.unpaid ?? x.impayes ?? x.reste ?? 0));
      return { labels, payments, unpaid };
    }

    // Format A
    if (Array.isArray(raw.labels) && (raw.payments || raw.unpaid)) {
      return {
        labels: raw.labels,
        payments: (raw.payments || []).map(Number),
        unpaid: (raw.unpaid || []).map(Number),
      };
    }

    // Format B
    if (Array.isArray(raw.labels) && raw.datasets) {
      const paid = raw.datasets.paid || raw.datasets.payments || raw.datasets.encaisse || [];
      const unp = raw.datasets.unpaid || raw.datasets.impayes || raw.datasets.reste || [];
      return {
        labels: raw.labels,
        payments: paid.map(Number),
        unpaid: unp.map(Number),
      };
    }

    return fallbackMonthly();
  }

  function fallbackMonthly() {
    // fallback UI si backend vide
    const months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"];
    const now = new Date();
    const m = now.getMonth();
    const labels = months.slice(Math.max(0, m - 5), m + 1);
    return {
      labels,
      payments: [12000, 15000, 18000, 16000, 19000, 21000].slice(-labels.length),
      unpaid: [2000, 1500, 1200, 2500, 1800, 1000].slice(-labels.length),
    };
  }

  function slicePeriod(data, period) {
    const len = period === "6m" ? 6 : 12;
    const labels = (data.labels || []).slice(-len);
    const payments = (data.payments || []).slice(-len);
    const unpaid = (data.unpaid || []).slice(-len);
    return { labels, payments, unpaid };
  }

  // ---------- Tabs ----------
  function initTabs() {
    const tabs = $$(".azad-tab");
    const panels = $$(".azad-tabpanel");
    if (!tabs.length || !panels.length) return;

    tabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        const name = btn.dataset.tab;
        if (!name) return;

        tabs.forEach(t => t.classList.remove("active"));
        panels.forEach(p => p.classList.remove("active"));

        btn.classList.add("active");
        const panel = $(`#${name}Tab`);
        if (panel) panel.classList.add("active");
      });
    });
  }

  // ---------- Chart ----------
  let monthlyChart = null;
  let rawData = null;

  function createChart(ctx, data) {
    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Encaissements",
            data: data.payments,
            backgroundColor: "rgba(99,102,241,.85)",
            borderColor: "rgba(99,102,241,1)",
            borderRadius: 10,
            borderSkipped: false,
          },
          {
            label: "Impayés",
            data: data.unpaid,
            backgroundColor: "rgba(239,68,68,.80)",
            borderColor: "rgba(239,68,68,1)",
            borderRadius: 10,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: {
              usePointStyle: true,
              padding: 14,
              color: textColor(),
              font: { size: 12, weight: "600" },
            },
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const label = context.dataset?.label || "";
                const val = context.parsed?.y ?? context.raw ?? 0;
                return `${label}: ${fmtMoney(val)} MAD`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: gridColor(), drawBorder: false },
            ticks: { color: textColor(), font: { size: 11 } },
          },
          x: {
            grid: { display: false, drawBorder: false },
            ticks: { color: textColor(), font: { size: 11 } },
          },
        },
      },
    });
  }

  function buildOrUpdateChart(period = "12m") {
    const canvas = $("#monthlyChart");
    if (!canvas || typeof Chart === "undefined") return;

    const data = slicePeriod(rawData, period);

    if (!monthlyChart) {
      monthlyChart = createChart(canvas.getContext("2d"), data);
      return;
    }

    monthlyChart.data.labels = data.labels;
    monthlyChart.data.datasets[0].data = data.payments;
    monthlyChart.data.datasets[1].data = data.unpaid;

    // update theme colors too
    monthlyChart.options.plugins.legend.labels.color = textColor();
    monthlyChart.options.scales.y.grid.color = gridColor();
    monthlyChart.options.scales.y.ticks.color = textColor();
    monthlyChart.options.scales.x.ticks.color = textColor();

    monthlyChart.update();
  }

  function destroyChart() {
    if (monthlyChart) {
      monthlyChart.destroy();
      monthlyChart = null;
    }
  }

  // ---------- Actions ----------
  function initRefresh() {
    const btn = $("#refreshDashboard");
    if (!btn) return;

    btn.addEventListener("click", () => {
      btn.disabled = true;
      const old = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Actualisation...';

      // UI feedback (si tu veux => location.reload() )
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = old;
        notify("Dashboard", "Données rafraîchies.", "success");
      }, 900);
    });
  }

  function initExport() {
    const btn = $("#exportChart");
    if (!btn) return;

    btn.addEventListener("click", () => {
      if (!monthlyChart) {
        notify("Export", "Aucun graphique à exporter.", "warning");
        return;
      }

      const a = document.createElement("a");
      a.href = monthlyChart.toBase64Image("image/png", 1);
      a.download = `pilotage-admin-${new Date().toISOString().slice(0, 10)}.png`;
      a.click();

      notify("Export", "Graphique exporté (PNG).", "success");
    });
  }

  function initPeriodSelect() {
    const sel = $("#chartPeriod");
    if (!sel) return;

    sel.addEventListener("change", (e) => {
      const v = e.target.value || "12m";
      buildOrUpdateChart(v);
    });
  }

  function initReminders() {
    const btn = $("#sendReminders");
    if (!btn) return;

    btn.addEventListener("click", () => {
      btn.disabled = true;
      const old = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Envoi...';

      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = old;
        notify("Rappels", "Rappels envoyés (simulation).", "success");
      }, 1200);
    });
  }

  function initDate() {
    // si le backend affiche déjà la date, on touche pas. Sinon on calcule.
    const el = $("#currentDate");
    if (!el) return;
    if ((el.textContent || "").trim().length > 3) return;

    const options = { year: "numeric", month: "long", day: "numeric" };
    el.textContent = new Date().toLocaleDateString("fr-FR", options);
  }

  // ---------- Theme observer (rebuild chart colors) ----------
  function observeTheme() {
    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === "attributes" && m.attributeName === "data-theme") {
          // Rebuild chart to apply theme colors
          destroyChart();
          buildOrUpdateChart($("#chartPeriod")?.value || "12m");
        }
      }
    });

    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }

  // ---------- Init ----------
  document.addEventListener("DOMContentLoaded", () => {
    rawData = normalizeMonthlyData(readMonthlyJson());

    initTabs();
    initRefresh();
    initExport();
    initPeriodSelect();
    initReminders();
    initDate();

    // chart init
    buildOrUpdateChart($("#chartPeriod")?.value || "12m");

    observeTheme();
  });
})();
