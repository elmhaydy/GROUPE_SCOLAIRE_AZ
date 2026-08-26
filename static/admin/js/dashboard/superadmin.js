/**
 * SUPER ADMIN EXECUTIVE DASHBOARD JS ENGINE
 * ApexCharts + Sparklines + Interactivity + Command Palette (Ctrl+K)
 */

document.addEventListener("DOMContentLoaded", () => {
  initApexChart();
  initSparklines();
  initTabs();
  initCommandPalette();
  initChartRangeSelector();

  // Re-render chart if theme changes
  const observer = new MutationObserver(() => {
    if (apexInstance) {
      apexInstance.destroy();
      initApexChart();
    }
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
});

/* --------------------------------------------------------------------------
   1. APEXCHARTS FINANCIAL GRAPH (THEME AWARE: LIGHT & DARK)
   -------------------------------------------------------------------------- */
let apexInstance = null;

function initApexChart() {
  const dataNode = document.getElementById("sa-chart-data");
  const apexContainer = document.getElementById("apexSaChart");
  const fallbackCanvas = document.getElementById("saChart");

  if (!dataNode) return;

  let payload = {};
  try {
    payload = JSON.parse(dataNode.textContent || "{}");
  } catch (e) {
    console.error("Erreur de parsing du payload du graphique :", e);
    return;
  }

  const labels = payload.labels || [];
  const recettes = payload.net || payload.recettes || [];
  const depenses = payload.depenses || [];
  const impayes = payload.impayes || [];

  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const labelColor = isLight ? "#475569" : "#94a3b8";
  const gridColor = isLight ? "#e2e8f0" : "rgba(255, 255, 255, 0.05)";
  const tooltipTheme = isLight ? "light" : "dark";

  if (typeof ApexCharts !== "undefined" && apexContainer) {
    apexContainer.innerHTML = "";
    const options = {
      series: [
        { name: "Net Recettes", data: recettes },
        { name: "Dépenses", data: depenses },
        { name: "Impayés", data: impayes }
      ],
      chart: {
        type: "area",
        height: 290,
        toolbar: { show: false },
        background: "transparent",
        fontFamily: "'Inter', sans-serif"
      },
      colors: [isLight ? "#059669" : "#10b981", isLight ? "#4f46e5" : "#6366f1", isLight ? "#d97706" : "#f59e0b"],
      stroke: { curve: "smooth", width: 3 },
      fill: {
        type: "gradient",
        gradient: {
          shadeIntensity: 1,
          opacityFrom: isLight ? 0.35 : 0.45,
          opacityTo: 0.05,
          stops: [0, 90, 100]
        }
      },
      dataLabels: { enabled: false },
      xaxis: {
        categories: labels,
        axisBorder: { show: false },
        axisTicks: { show: false },
        labels: { style: { colors: labelColor, fontSize: "12px", fontWeight: 600 } }
      },
      yaxis: {
        labels: {
          style: { colors: labelColor, fontSize: "12px", fontWeight: 600 },
          formatter: (val) => val.toLocaleString() + " MAD"
        }
      },
      grid: {
        borderColor: gridColor,
        strokeDashArray: 4
      },
      tooltip: {
        theme: tooltipTheme,
        y: { formatter: (val) => val.toLocaleString() + " MAD" }
      },
      legend: {
        labels: { colors: isLight ? "#0f172a" : "#cbd5e1" },
        position: "top",
        horizontalAlign: "right",
        fontWeight: 600
      }
    };

    apexInstance = new ApexCharts(apexContainer, options);
    apexInstance.render();
  } else if (typeof Chart !== "undefined" && fallbackCanvas) {
    fallbackCanvas.style.display = "block";
    new Chart(fallbackCanvas, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          { label: "Net Recettes", data: recettes, borderColor: isLight ? "#059669" : "#10b981", tension: 0.4 },
          { label: "Dépenses", data: depenses, borderColor: isLight ? "#4f46e5" : "#6366f1", tension: 0.4 },
          { label: "Impayés", data: impayes, borderColor: isLight ? "#d97706" : "#f59e0b", tension: 0.4 }
        ]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });
  }
}

/* --------------------------------------------------------------------------
   2. KPI SPARKLINES
   -------------------------------------------------------------------------- */
function initSparklines() {
  if (typeof ApexCharts === "undefined") return;

  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const spark1Node = document.getElementById("sparkline-revenue");
  const spark2Node = document.getElementById("sparkline-impayes");

  if (spark1Node) {
    spark1Node.innerHTML = "";
    new ApexCharts(spark1Node, {
      series: [{ data: [12, 18, 14, 22, 28, 35, 42] }],
      chart: { type: "area", height: 40, sparkline: { enabled: true } },
      colors: [isLight ? "#059669" : "#10b981"],
      stroke: { curve: "smooth", width: 2 },
      fill: { opacity: 0.25 },
      tooltip: { enabled: false }
    }).render();
  }

  if (spark2Node) {
    spark2Node.innerHTML = "";
    new ApexCharts(spark2Node, {
      series: [{ data: [30, 25, 22, 18, 15, 12, 8] }],
      chart: { type: "area", height: 40, sparkline: { enabled: true } },
      colors: [isLight ? "#d97706" : "#f59e0b"],
      stroke: { curve: "smooth", width: 2 },
      fill: { opacity: 0.25 },
      tooltip: { enabled: false }
    }).render();
  }
}

/* --------------------------------------------------------------------------
   3. TABS SWITCHER
   -------------------------------------------------------------------------- */
function initTabs() {
  const tabBtns = document.querySelectorAll(".sa-tab-btn");
  const tabPanels = document.querySelectorAll(".sa-tab-panel");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");

      tabBtns.forEach((b) => b.classList.remove("active"));
      tabPanels.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPanel = document.getElementById(`tab-${targetTab}`);
      if (targetPanel) targetPanel.classList.add("active");
    });
  });
}

/* --------------------------------------------------------------------------
   4. COMMAND PALETTE (CTRL + K)
   -------------------------------------------------------------------------- */
function initCommandPalette() {
  const cmdkBtn = document.getElementById("saCmdk");
  const cmdkModal = document.getElementById("saCmdkModal");
  const cmdkInput = document.getElementById("saCmdkInput");
  const cmdkResults = document.getElementById("saCmdkResults");

  if (!cmdkModal || !cmdkInput) return;

  function openCmdk() {
    cmdkModal.classList.add("open");
    cmdkInput.focus();
    cmdkInput.value = "";
    filterItems("");
  }

  function closeCmdk() {
    cmdkModal.classList.remove("open");
  }

  if (cmdkBtn) {
    cmdkBtn.addEventListener("click", openCmdk);
  }

  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (cmdkModal.classList.contains("open")) {
        closeCmdk();
      } else {
        openCmdk();
      }
    } else if (e.key === "Escape" && cmdkModal.classList.contains("open")) {
      closeCmdk();
    }
  });

  cmdkModal.addEventListener("click", (e) => {
    if (e.target === cmdkModal) closeCmdk();
  });

  function filterItems(query) {
    const items = cmdkResults.querySelectorAll(".cmdk-item");
    const q = query.toLowerCase().trim();

    items.forEach((item) => {
      const text = item.textContent.toLowerCase();
      if (!q || text.includes(q)) {
        item.style.display = "flex";
      } else {
        item.style.display = "none";
      }
    });
  }

  cmdkInput.addEventListener("input", (e) => {
    filterItems(e.target.value);
  });
}

/* --------------------------------------------------------------------------
   5. CHART RANGE SELECTOR
   -------------------------------------------------------------------------- */
function initChartRangeSelector() {
  const rangeSelect = document.getElementById("saChartRange");
  if (!rangeSelect) return;

  rangeSelect.addEventListener("change", (e) => {
    const range = e.target.value;
    const url = new URL(window.location.href);
    url.searchParams.set("range", range);
    window.location.href = url.toString();
  });
}
