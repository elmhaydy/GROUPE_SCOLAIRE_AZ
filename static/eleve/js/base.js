/* =========================================================
   AZ — Portail Élève (BASE JS)
   - Sidebar drawer (mobile/tablet) + block scroll content
   - Overlay click closes + ESC
   - Theme toggle (mobile + desktop) with localStorage
   - User dropdown (desktop)
   - Close alerts
   - Date/time
   ========================================================= */

(function () {
  const html = document.documentElement;

  // -----------------------------
  // THEME (persist)
  // -----------------------------
  const THEME_KEY = "AZ_ELEVE_THEME";

  function setTheme(theme) {
    html.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);

    const isDark = theme === "dark";
    document.querySelectorAll("#themeToggle i, #themeToggleDesk i").forEach((ico) => {
      if (!ico) return;
      ico.classList.remove("fa-moon", "fa-sun");
      ico.classList.add(isDark ? "fa-sun" : "fa-moon");
    });
  }

  function toggleTheme() {
    const current = html.getAttribute("data-theme") || "light";
    setTheme(current === "dark" ? "light" : "dark");
  }

  // init theme
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") setTheme(saved);

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

  if (openBtn) openBtn.addEventListener("click", () => {
    sidebar && sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
  });

  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  if (overlay) overlay.addEventListener("click", closeSidebar);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSidebar();
  });

  // When back to desktop, ensure sidebar is not stuck open
  function handleResize() {
    if (window.matchMedia("(min-width: 1025px)").matches) {
      closeSidebar();
    }
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
  function pad(n){ return String(n).padStart(2,"0"); }

  function renderDT() {
    if (!dt) return;
    const span = dt.querySelector("span") || dt;
    const d = new Date();
    const days = ["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"];
    span.textContent =
      `${days[d.getDay()]} ${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} • ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  renderDT();
  setInterval(renderDT, 30000);
})();

(function(){
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("azOverlay");       // ton overlay
  const openBtn = document.getElementById("sidebarToggle");   // ton bouton menu (mobile)
  const closeBtn = document.getElementById("sidebarClose");   // bouton X dans sidebar

  function openSidebar(){
    if (!sidebar || !overlay) return;
    sidebar.classList.add("open");
    overlay.classList.add("show");
    document.body.classList.add("no-scroll");
  }
  function closeSidebar(){
    if (!sidebar || !overlay) return;
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
    document.body.classList.remove("no-scroll");
  }

  if (openBtn) openBtn.addEventListener("click", openSidebar);
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  if (overlay) overlay.addEventListener("click", closeSidebar);
  document.addEventListener("keydown", (e)=>{ if(e.key==="Escape") closeSidebar(); });

  // ✅ reset quand on revient desktop
  window.addEventListener("resize", ()=>{
    if (window.matchMedia("(min-width: 1025px)").matches) closeSidebar();
  });

  /* =======================================================
     BADGES (OPTIONNEL)
     - Tu peux alimenter ça via Django (data-*)
     - Ici c'est juste un exemple (0/—)
     ======================================================= */
  const badgeMap = {
    avis: 0,   // ex: nb avis non lus
    notes: 0,  // ex: nouvelles notes
    abs: 0     // ex: absences ce mois
  };

  Object.entries(badgeMap).forEach(([k,v])=>{
    const el = document.querySelector(`[data-badge="${k}"]`);
    if (!el) return;
    if (!v){
      el.textContent = "—";
      el.style.opacity = ".65";
      return;
    }
    el.textContent = String(v);
    el.style.opacity = "1";
  });
})();
/* =========================================================
   AZ — Password Modal
   - open/close (click outside, ESC)
   - lock scroll
   ========================================================= */
(function(){
  const modal = document.getElementById("pwdModal");
  if(!modal) return;

  const openers = document.querySelectorAll("[data-open-password-modal]");
  const closers = modal.querySelectorAll("[data-modal-close]");
  let lastFocus = null;

  function openModal(){
    lastFocus = document.activeElement;
    modal.classList.add("show");
    modal.setAttribute("aria-hidden","false");
    document.body.classList.add("az-modal-open");

    // focus first input
    setTimeout(() => {
      const first = modal.querySelector("input, button, [tabindex]:not([tabindex='-1'])");
      if(first) first.focus();
    }, 0);
  }

  function closeModal(){
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden","true");
    document.body.classList.remove("az-modal-open");
    if(lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  openers.forEach(btn => btn.addEventListener("click", openModal));
  closers.forEach(btn => btn.addEventListener("click", closeModal));

  // click backdrop closes
  modal.addEventListener("click", (e) => {
    if(e.target.classList.contains("az-modal__backdrop")) closeModal();
  });

  // ESC closes
  document.addEventListener("keydown", (e) => {
    if(!modal.classList.contains("show")) return;
    if(e.key === "Escape") closeModal();
  });
})();
