/* admin/js/dashboard/superadmin.js */
/* global Chart */

(() => {
  "use strict";

  // =========================
  // Helpers DOM
  // =========================
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const safeJSON = (x, fallback) => {
    try {
      if (x == null) return fallback;
      return x;
    } catch (e) {
      return fallback;
    }
  };

  // =========================
  // Date FR (si tu veux forcer un format côté client)
  // =========================
  const setCurrentDateFR = () => {
    const el = $("#currentDate");
    if (!el) return;
    // si le backend remplit déjà, on ne touche pas
    if ((el.textContent || "").trim().length > 0) return;

    const d = new Date();
    const months = [
      "janvier", "février", "mars", "avril", "mai", "juin",
      "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ];
    const dd = String(d.getDate()).padStart(2, "0");
    const mm = months[d.getMonth()];
    const yyyy = d.getFullYear();
    el.textContent = `${dd} ${mm} ${yyyy}`;
  };

  // =========================
  // Tabs (Paiements / Inscriptions / Impayés)
  // =========================
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
      Object.entries(panels).forEach(([k, p]) => {
        if (!p) return;
        p.classList.toggle("active", k === key);
      });
    };

    tabs.forEach((btn) => {
      btn.addEventListener("click", () => setActive(btn.dataset.tab));
    });
  };

  // =========================
  // Chart (Pilotage 12 mois / 6 mois)
  // =========================
  let chartInstance = null;

  const buildChartData = (period) => {
    const src = window.AZ_CHART || {};
    const labels = safeJSON(src.labels, []);
    const paiements = safeJSON(src.paiements, []);
    const inscriptions = safeJSON(src.inscriptions, []);

    const take = period === "6m" ? 6 : 12;

    // on prend les derniers X éléments
    const L = labels.slice(-take);
    const P = paiements.slice(-take);
    const I = inscriptions.slice(-take);

    return { L, P, I };
  };

  const renderChart = (period = "12m") => {
    const canvas = $("#monthlyChart");
    if (!canvas || typeof Chart === "undefined") return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { L, P, I } = buildChartData(period);

    // destroy si existe
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }

    chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: L,
        datasets: [
          {
            label: "Paiements (MAD)",
            data: P,
            tension: 0.35,
            pointRadius: 2,
            borderWidth: 2,
          },
          {
            label: "Inscriptions (nb)",
            data: I,
            tension: 0.35,
            pointRadius: 2,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: true },
          tooltip: { enabled: true },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              // pas obligatoire, mais garde lisible
              precision: 0,
            },
          },
          x: {
            ticks: { autoSkip: true, maxRotation: 0 },
          },
        },
      },
    });
  };

  const initChartControls = () => {
    const periodSel = $("#chartPeriod");
    if (periodSel) {
      periodSel.addEventListener("change", () => {
        renderChart(periodSel.value || "12m");
      });
    }

    const exportBtn = $("#exportChart");
    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        const canvas = $("#monthlyChart");
        if (!canvas) return;

        // export PNG
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

  // =========================
  // Actualiser (reload page)
  // =========================
  const initRefresh = () => {
    const btn = $("#refreshDashboard");
    if (!btn) return;

    btn.addEventListener("click", () => {
      // animation légère (si tu veux)
      btn.disabled = true;
      btn.classList.add("is-loading");

      // reload simple (le backend recalculera tout)
      window.location.reload();
    });
  };

  // =========================
  // Rappels (placeholder)
  // =========================
  const initReminders = () => {
    const btn = $("#sendReminders");
    if (!btn) return;

    btn.addEventListener("click", () => {
      // Ici tu pourras brancher un endpoint AJAX plus tard.
      // Pour l’instant : feedback simple.
      btn.disabled = true;
      btn.classList.add("is-loading");

      setTimeout(() => {
        btn.disabled = false;
        btn.classList.remove("is-loading");
        alert("✅ Rappels : action à brancher (endpoint) — prêt côté UI.");
      }, 400);
    });
  };

  // =========================
  // Boot
  // =========================
  const boot = () => {
    setCurrentDateFR();
    initTabs();
    initRefresh();
    initReminders();
    initChartControls();

    // rendu initial chart
    const periodSel = $("#chartPeriod");
    renderChart(periodSel ? (periodSel.value || "12m") : "12m");
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
