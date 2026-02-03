/* ==========================================================================
   AZ — Super Admin Dashboard (FINAL)
   - Tabs (activité)
   - Chart.js (12m / 6m) via json_script "monthly-chart-data"
   - Support formats:
       A) {labels, payments, unpaid}
       B) {labels, paid, impayes}
       C) {labels, paiements_k, inscriptions}  ✅ ton backend actuel
   - Refresh + Export PNG
   - Reminders (hook notif azAdmin)
   - Re-render chart on theme change (html[data-theme])
   ========================================================================== */

class AZSuperAdminDashboard {
  constructor() {
    this.charts = {};
    this.currentPeriod = "12m";
    this.chartData = this.readBackendChartData();
    this.init();
  }

  init() {
    this.updateDate();
    this.setupTabs();
    this.setupButtons();
    this.setupCharts();
    this.observeTheme();
  }

  /* -----------------------------
     BACKEND DATA (json_script)
     ----------------------------- */
  readBackendChartData() {
    const el = document.getElementById("monthly-chart-data");
    if (!el) return null;

    try {
      const raw = JSON.parse(el.textContent || "{}");
      const labels = raw.labels || raw.months || [];

      // 1) Formats "paid/unpaid"
      const payments =
        raw.payments ||
        raw.paid ||
        raw.encaisse ||
        (raw.datasets && (raw.datasets.payments || raw.datasets.paid)) ||
        null;

      const unpaid =
        raw.unpaid ||
        raw.impayes ||
        (raw.datasets && (raw.datasets.unpaid || raw.datasets.impayes)) ||
        null;

      // 2) ✅ Ton format actuel: paiements_k + inscriptions
      const paiements_k = Array.isArray(raw.paiements_k) ? raw.paiements_k : null;
      const inscriptions = Array.isArray(raw.inscriptions) ? raw.inscriptions : null;

      return {
        labels: Array.isArray(labels) ? labels : [],
        payments: Array.isArray(payments) ? payments : null,
        unpaid: Array.isArray(unpaid) ? unpaid : null,
        paiements_k,
        inscriptions,
        _raw: raw,
      };
    } catch (e) {
      console.warn("monthly-chart-data JSON invalide:", e);
      return null;
    }
  }

  getFallbackData(period = "12m") {
    const months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"];
    const now = new Date();
    const m = now.getMonth();
    const len = period === "6m" ? 6 : 12;

    const labels = [];
    for (let i = len - 1; i >= 0; i--) {
      labels.push(months[(m - i + 12) % 12]);
    }

    // fallback dummy (propre)
    const serieA = labels.map((_, i) => 8 + i * 1.2);     // "Paiements (k MAD)"
    const serieB = labels.map((_, i) => Math.max(1, 6 - i * 0.35)); // "Impayés (k MAD)"

    return {
      labels,
      a: serieA,
      b: serieB,
      aLabel: "Paiements (k MAD)",
      bLabel: "Impayés (k MAD)",
      money: true,
    };
  }

  sliceLast(arr, n) {
    if (!Array.isArray(arr)) return [];
    return arr.slice(Math.max(0, arr.length - n));
  }

  normalizeNumberArray(arr) {
    if (!Array.isArray(arr)) return [];
    return arr.map((v) => Number(v) || 0);
  }

  allZero(arr) {
    return (arr || []).every((v) => Number(v) === 0);
  }

  getDataByPeriod(period) {
    const n = period === "6m" ? 6 : 12;

    // ✅ si backend existe, on choisit la meilleure combo dispo
    if (this.chartData && this.chartData.labels && this.chartData.labels.length) {
      const labels = this.sliceLast(this.chartData.labels, n);

      // Cas 1: payments + unpaid (MAD)
      if (Array.isArray(this.chartData.payments) && Array.isArray(this.chartData.unpaid)) {
        return {
          labels,
          a: this.sliceLast(this.normalizeNumberArray(this.chartData.payments), n),
          b: this.sliceLast(this.normalizeNumberArray(this.chartData.unpaid), n),
          aLabel: "Paiements",
          bLabel: "Impayés",
          money: true,
        };
      }

      // Cas 2: paiements_k + inscriptions (ton backend)
      if (Array.isArray(this.chartData.paiements_k) && Array.isArray(this.chartData.inscriptions)) {
        return {
          labels,
          a: this.sliceLast(this.normalizeNumberArray(this.chartData.paiements_k), n),
          b: this.sliceLast(this.normalizeNumberArray(this.chartData.inscriptions), n),
          aLabel: "Paiements (k MAD)",
          bLabel: "Inscriptions",
          money: false, // a est en "k", b est un compteur
        };
      }

      // Cas 3: paiements_k + impayes_k (si tu l’ajoutes plus tard)
      if (Array.isArray(this.chartData.paiements_k) && Array.isArray(this.chartData.unpaid)) {
        return {
          labels,
          a: this.sliceLast(this.normalizeNumberArray(this.chartData.paiements_k), n),
          b: this.sliceLast(this.normalizeNumberArray(this.chartData.unpaid), n),
          aLabel: "Paiements (k MAD)",
          bLabel: "Impayés",
          money: false,
        };
      }
    }

    // fallback
    return this.getFallbackData(period);
  }

  /* -----------------------------
     UI
     ----------------------------- */
  updateDate() {
    const el = document.getElementById("currentDate");
    if (!el) return;
    if ((el.textContent || "").trim().length > 0) return;

    el.textContent = new Date().toLocaleDateString("fr-FR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  notify(title, message, type = "info") {
    if (window.azAdmin && typeof window.azAdmin.showNotification === "function") {
      window.azAdmin.showNotification(title, message, type);
      return;
    }
    console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
  }

  setBtnLoading(btn, isLoading, loadingHTML, normalHTML) {
    if (!btn) return;
    btn.disabled = !!isLoading;
    btn.dataset._normal = btn.dataset._normal || normalHTML || btn.innerHTML;
    btn.innerHTML = isLoading ? loadingHTML : btn.dataset._normal;
  }

  /* -----------------------------
     TABS
     ----------------------------- */
  setupTabs() {
    const tabs = document.querySelectorAll(".azsa-tab");
    const panels = document.querySelectorAll(".azsa-tabpanel");
    if (!tabs.length || !panels.length) return;

    tabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        const name = btn.dataset.tab;

        tabs.forEach((b) => b.classList.remove("active"));
        panels.forEach((p) => p.classList.remove("active"));

        btn.classList.add("active");
        const panel = document.getElementById(`${name}Tab`);
        if (panel) panel.classList.add("active");
      });
    });
  }

  /* -----------------------------
     BUTTONS
     ----------------------------- */
  setupButtons() {
    const refreshBtn = document.getElementById("refreshDashboard");
    if (refreshBtn) refreshBtn.addEventListener("click", () => this.refresh());

    const exportBtn = document.getElementById("exportChart");
    if (exportBtn) exportBtn.addEventListener("click", () => this.exportChart());

    const periodSel = document.getElementById("chartPeriod");
    if (periodSel) {
      periodSel.addEventListener("change", (e) => {
        this.currentPeriod = e.target.value || "12m";
        this.updateChartPeriod();
      });
    }

    const remindersBtn = document.getElementById("sendReminders");
    if (remindersBtn) remindersBtn.addEventListener("click", () => this.sendReminders());
  }

  refresh() {
    const btn = document.getElementById("refreshDashboard");
    const normal = btn ? btn.innerHTML : "";

    this.setBtnLoading(btn, true, `<i class="fa-solid fa-spinner fa-spin"></i> Actualisation...`, normal);

    setTimeout(() => {
      this.setBtnLoading(btn, false);
      // re-read backend data (si tu recharges par AJAX plus tard)
      this.chartData = this.readBackendChartData();
      this.updateChartPeriod();
      this.notify("Super Admin", "Dashboard actualisé.", "success");
    }, 650);
  }

  sendReminders() {
    const btn = document.getElementById("sendReminders");
    const normal = btn ? btn.innerHTML : "";

    this.setBtnLoading(btn, true, `<i class="fa-solid fa-spinner fa-spin"></i> Envoi...`, normal);

    setTimeout(() => {
      this.setBtnLoading(btn, false);
      this.notify("Relances", "Rappels envoyés (simulation).", "success");
    }, 900);
  }

  /* -----------------------------
     CHARTS
     ----------------------------- */
  setupCharts() {
    const canvas = document.getElementById("monthlyChart");
    if (!canvas || typeof Chart === "undefined") return;

    if (this.charts.monthly) {
      this.charts.monthly.destroy();
      this.charts.monthly = null;
    }

    const ctx = canvas.getContext("2d");
    const d = this.getDataByPeriod(this.currentPeriod);

    this.charts.monthly = new Chart(ctx, {
      type: "bar",
      data: {
        labels: d.labels,
        datasets: [
          {
            label: d.aLabel,
            data: d.a,
            backgroundColor: "rgba(99, 102, 241, 0.85)",
            borderColor: "rgba(99, 102, 241, 1)",
            borderRadius: 10,
            borderSkipped: false,
          },
          {
            label: d.bLabel,
            data: d.b,
            backgroundColor: "rgba(245, 158, 11, 0.85)",
            borderColor: "rgba(245, 158, 11, 1)",
            borderRadius: 10,
            borderSkipped: false,
          },
        ],
      },
      options: this.getChartOptions(d),
    });
  }

  getChartOptions(d) {
    const text = this.getTextColor();
    const grid = this.getGridColor();

    // ✅ évite l’axe 0→1 quand tout est à 0
    const hasAny = !(this.allZero(d.a) && this.allZero(d.b));

    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            usePointStyle: true,
            padding: 14,
            font: { size: 12, weight: "600" },
            color: text,
          },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const label = ctx.dataset.label || "";
              const val = ctx.parsed.y ?? 0;

              // si c’est le format money=true => afficher MAD
              if (d.money) return `${label}: ${this.formatMoney(val)} MAD`;

              // sinon affichage simple (k MAD / compteur)
              return `${label}: ${this.formatSimple(val)}`;
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          suggestedMax: hasAny ? undefined : 10,
          grid: { color: grid, drawBorder: false },
          ticks: { color: text, font: { size: 11 } },
        },
        x: {
          grid: { display: false, drawBorder: false },
          ticks: { color: text, font: { size: 11 } },
        },
      },
    };
  }

  updateChartPeriod() {
    if (!this.charts.monthly) {
      this.setupCharts();
      return;
    }

    const d = this.getDataByPeriod(this.currentPeriod);
    this.charts.monthly.data.labels = d.labels;
    this.charts.monthly.data.datasets[0].label = d.aLabel;
    this.charts.monthly.data.datasets[0].data = d.a;
    this.charts.monthly.data.datasets[1].label = d.bLabel;
    this.charts.monthly.data.datasets[1].data = d.b;
    this.charts.monthly.options = this.getChartOptions(d);
    this.charts.monthly.update();
  }

  exportChart() {
    const chart = this.charts.monthly;
    if (!chart) return;

    const link = document.createElement("a");
    link.href = chart.toBase64Image();
    link.download = `superadmin-pilotage-${new Date().toISOString().slice(0, 10)}.png`;
    link.click();

    this.notify("Export", "Graphique exporté.", "success");
  }

  /* -----------------------------
     THEME
     ----------------------------- */
  observeTheme() {
    const obs = new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === "attributes" && m.attributeName === "data-theme") {
          this.onThemeChange();
          break;
        }
      }
    });

    obs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
  }

  onThemeChange() {
    this.setupCharts();
  }

  getTheme() {
    return document.documentElement.getAttribute("data-theme") || "dark";
  }

  getTextColor() {
    return this.getTheme() === "dark" ? "#e5e7eb" : "#0f172a";
  }

  getGridColor() {
    return this.getTheme() === "dark" ? "rgba(255,255,255,0.10)" : "rgba(2,6,23,0.08)";
  }

  formatMoney(v) {
    try {
      return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(v) || 0);
    } catch {
      return String(v);
    }
  }

  formatSimple(v) {
    // ex: 12.3 => "12,3"
    try {
      return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(Number(v) || 0);
    } catch {
      return String(v);
    }
  }
}

/* -----------------------------
   Boot
   ----------------------------- */
document.addEventListener("DOMContentLoaded", () => {
  window.azSuperAdminDash = new AZSuperAdminDashboard();
});
