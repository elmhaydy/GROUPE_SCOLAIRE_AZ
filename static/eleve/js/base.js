/* =========================================================
   AZ — Portail Élève (BASE JS) — FINAL CLEAN
   - Theme toggle (mobile + desktop) + localStorage
   - Sidebar drawer (mobile/tablet) + overlay + ESC
   - User dropdown (desktop) + click outside
   - Close alerts
   - Date/time
   - Badges (optionnel)
   - Password modal
   ========================================================= */

(function () {
  "use strict";

  const html = document.documentElement;

  // -----------------------------
  // THEME (Light par défaut)
  // -----------------------------
  const THEME_KEY = "AZ_ELEVE_THEME";

  function syncThemeIcons(theme) {
    const isDark = theme === "dark";
    document.querySelectorAll("#themeToggle i, #themeToggleDesk i").forEach((ico) => {
      if (!ico) return;
      ico.classList.remove("fa-moon", "fa-sun");
      ico.classList.add(isDark ? "fa-sun" : "fa-moon");
    });
  }

  function setTheme(theme) {
    html.setAttribute("data-theme", theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
    syncThemeIcons(theme);
  }

  function toggleTheme() {
    const current = html.getAttribute("data-theme") || "light";
    setTheme(current === "dark" ? "light" : "dark");
  }

  // init theme (✅ light par défaut si rien)
  (function initTheme() {
    let saved = null;
    try { saved = localStorage.getItem(THEME_KEY); } catch (e) {}

    const theme = (saved === "dark" || saved === "light") ? saved : "light";
    setTheme(theme);

    // si rien n'existe, on écrit light
    if (!saved) {
      try { localStorage.setItem(THEME_KEY, "light"); } catch (e) {}
    }
  })();

  const themeBtn = document.getElementById("themeToggle");
  const themeBtnDesk = document.getElementById("themeToggleDesk");
  if (themeBtn) themeBtn.addEventListener("click", toggleTheme);
  if (themeBtnDesk) themeBtnDesk.addEventListener("click", toggleTheme);

  // -----------------------------
  // DRAWER SIDEBAR
  // -----------------------------
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("azOverlay");
  const openBtn = document.getElementById("sidebarToggle");
  const closeBtn = document.getElementById("sidebarClose");
  const content = document.querySelector(".modern-content");

  function openSidebar() {
    if (!sidebar || !overlay) return;
    sidebar.classList.add("open");
    overlay.classList.add("show");
    document.body.classList.add("no-scroll");
    if (content) content.style.overflow = "hidden";
    if (openBtn) openBtn.setAttribute("aria-expanded", "true");
    overlay.setAttribute("aria-hidden", "false");
  }

  function closeSidebar() {
    if (!sidebar || !overlay) return;
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
    document.body.classList.remove("no-scroll");
    if (content) content.style.overflow = "";
    if (openBtn) openBtn.setAttribute("aria-expanded", "false");
    overlay.setAttribute("aria-hidden", "true");
  }

  if (openBtn) {
    openBtn.addEventListener("click", () => {
      sidebar && sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
    });
  }
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  if (overlay) overlay.addEventListener("click", closeSidebar);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeSidebar();
      closePwdModal(); // (si modal ouverte)
    }
  });

  // reset quand retour desktop
  function handleResize() {
    if (window.matchMedia("(min-width: 1025px)").matches) closeSidebar();
  }
  window.addEventListener("resize", handleResize);
  handleResize();

  // -----------------------------
  // USER DROPDOWN (desktop)
  // -----------------------------
  const menuWrapper = document.getElementById("userMenuWrapper");
  const menuToggle = document.getElementById("userMenuToggle");
  const menu = document.getElementById("userMenu");

  function closeMenu() {
    if (!menu) return;
    menu.classList.remove("open");
    if (menuToggle) menuToggle.setAttribute("aria-expanded", "false");
    menu.setAttribute("aria-hidden", "true");
  }

  function toggleMenu() {
    if (!menu) return;
    const open = menu.classList.toggle("open");
    if (menuToggle) menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
    menu.setAttribute("aria-hidden", open ? "false" : "true");
  }

  if (menuToggle) {
    menuToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleMenu();
    });
  }

  document.addEventListener("click", (e) => {
    if (!menuWrapper) return;
    if (!menuWrapper.contains(e.target)) closeMenu();
  });

  // -----------------------------
  // CLOSE ALERTS
  // -----------------------------
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".close-alert");
    if (!btn) return;
    const alert = btn.closest(".alert");
    if (!alert) return;

    alert.style.transition = "all .18s ease";
    alert.style.opacity = "0";
    alert.style.transform = "translateY(-6px)";
    setTimeout(() => alert.remove(), 180);
  });

  // -----------------------------
  // DATETIME
  // -----------------------------
  const dt = document.getElementById("currentDateTime");
  function pad(n) { return String(n).padStart(2, "0"); }

  function renderDT() {
    if (!dt) return;
    const span = dt.querySelector("span") || dt;
    const d = new Date();
    const days = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"];
    span.textContent =
      `${days[d.getDay()]} ${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} • ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  renderDT();
  setInterval(renderDT, 30000);

  // -----------------------------
  // BADGES (OPTIONNEL)
  // -----------------------------
  const badgeMap = {
    avis: 0,
    notes: 0,
    abs: 0,
    pdf: 0,
    edt: 0
  };

  Object.entries(badgeMap).forEach(([k, v]) => {
    const el = document.querySelector(`[data-badge="${k}"]`);
    if (!el) return;
    if (!v) {
      el.textContent = "—";
      el.style.opacity = ".65";
      return;
    }
    el.textContent = String(v);
    el.style.opacity = "1";
  });

  // -----------------------------
  // PASSWORD MODAL
  // -----------------------------
  const modal = document.getElementById("pwdModal");
  const openers = document.querySelectorAll("[data-open-password-modal]");
  const closers = modal ? modal.querySelectorAll("[data-modal-close]") : [];
  let lastFocus = null;

  function openPwdModal() {
    if (!modal) return;
    lastFocus = document.activeElement;
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("az-modal-open");

    setTimeout(() => {
      const first = modal.querySelector("input, button, [tabindex]:not([tabindex='-1'])");
      if (first) first.focus();
    }, 0);
  }

  function closePwdModal() {
    if (!modal) return;
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("az-modal-open");
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  openers.forEach((btn) => btn.addEventListener("click", openPwdModal));
  closers.forEach((btn) => btn.addEventListener("click", closePwdModal));

  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target.classList.contains("az-modal__backdrop")) closePwdModal();
    });
  }
})();
