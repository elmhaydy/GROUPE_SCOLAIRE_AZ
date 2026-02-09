/* =========================================================
   AZ • admin.js — FINAL
   Sidebar: Desktop Collapse + Mobile Drawer
   Theme: localStorage "az-theme"
   Collapsed: localStorage "az-sidebar-collapsed" ("1"/"0")
   ========================================================= */

(function () {
  "use strict";

  class AZAdmin {
    constructor() {
      this.STORAGE_THEME = "az-theme";
      this.STORAGE_SIDEBAR_COLLAPSED = "az-sidebar-collapsed";

      this.theme = this.getTheme();
      this.isMobile = window.innerWidth <= 768;

      this.init();
    }

    /* =========================
       INIT
       ========================= */
    init() {
      // appliquer thème dès le départ
      document.documentElement.setAttribute("data-theme", this.theme);

      this.setupThemeToggle();
      this.setupSidebarToggle(); // ✅ FINAL
      this.setupUserMenu();
      this.setupAlertClosing();
      this.setupResponsive();
      this.setupEventListeners();

      this.applySidebarTooltips();
    }

    /* =========================
       THEME
       ========================= */
    getTheme() {
      try {
        const saved = localStorage.getItem(this.STORAGE_THEME);
        return (saved === "light" || saved === "dark") ? saved : "dark";
      } catch (e) {
        return "dark";
      }
    }

    saveTheme(theme) {
      try {
        localStorage.setItem(this.STORAGE_THEME, theme);
      } catch (e) {
        console.warn("localStorage non disponible");
      }
    }

    toggleTheme() {
      this.theme = (this.theme === "dark") ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", this.theme);
      this.saveTheme(this.theme);
      this.updateThemeIcon();
    }

    updateThemeIcon() {
      const themeIconDropdown = document.getElementById("azThemeIconDropdown");
      const themeLabelDropdown = document.getElementById("azThemeLabelDropdown");

      const isDark = this.theme === "dark";
      if (themeIconDropdown) themeIconDropdown.className = isDark ? "fas fa-sun" : "fas fa-moon";
      if (themeLabelDropdown) themeLabelDropdown.textContent = isDark ? "Mode clair" : "Mode sombre";
    }

    setupThemeToggle() {
      const themeDropdownBtn = document.getElementById("azThemeToggleDropdown");

      if (themeDropdownBtn) {
        themeDropdownBtn.addEventListener("click", () => {
          this.toggleTheme();
          this.closeUserMenu();
        });
      }

      this.updateThemeIcon();
    }

    /* =========================
       SIDEBAR (DESKTOP COLLAPSE + MOBILE DRAWER)
       ========================= */
    _isMobileNow() {
      return window.innerWidth <= 768;
    }

    _readCollapsed() {
      try {
        return localStorage.getItem(this.STORAGE_SIDEBAR_COLLAPSED) === "1";
      } catch (e) {
        return false;
      }
    }

    _saveCollapsed(val) {
      try {
        localStorage.setItem(this.STORAGE_SIDEBAR_COLLAPSED, val ? "1" : "0");
      } catch (e) {}
    }

    applyCollapsedFromStorage() {
      const sidebar = document.getElementById("sidebar");
      if (!sidebar) return;

      // mobile => pas de collapsed (drawer only)
      if (this._isMobileNow()) {
        sidebar.classList.remove("is-collapsed");
        return;
      }

      sidebar.classList.toggle("is-collapsed", this._readCollapsed());
    }

    toggleCollapsedDesktop() {
      const sidebar = document.getElementById("sidebar");
      if (!sidebar) return;

      const next = !sidebar.classList.contains("is-collapsed");
      sidebar.classList.toggle("is-collapsed", next);
      this._saveCollapsed(next);
      this.applySidebarTooltips();
    }

    openMobileSidebar() {
      const sidebar = document.getElementById("sidebar");
      const overlay = document.getElementById("azOverlay");
      if (!sidebar) return;

      sidebar.classList.add("active");
      if (overlay) overlay.classList.add("active");
    }

    closeMobileSidebar() {
      const sidebar = document.getElementById("sidebar");
      const overlay = document.getElementById("azOverlay");
      if (!sidebar) return;

      sidebar.classList.remove("active");
      if (overlay) overlay.classList.remove("active");
    }

    setupSidebarToggle() {
      const sidebarToggle = document.getElementById("sidebarToggle");
      const sidebar = document.getElementById("sidebar");
      const overlay = document.getElementById("azOverlay");

      if (!sidebar) return;

      // click hamburger:
      // - mobile => open/close drawer
      // - desktop => collapse/expand
      if (sidebarToggle) {
        sidebarToggle.addEventListener("click", () => {
          if (this._isMobileNow()) {
            sidebar.classList.contains("active") ? this.closeMobileSidebar() : this.openMobileSidebar();
          } else {
            this.toggleCollapsedDesktop();
          }
        });
      }

      // overlay click => close drawer (mobile)
      if (overlay) {
        overlay.addEventListener("click", () => this.closeMobileSidebar());
      }

      // click sur liens => close drawer (mobile)
      document.querySelectorAll(".az-nav-item").forEach((a) => {
        a.addEventListener("click", () => {
          if (this._isMobileNow()) this.closeMobileSidebar();
        });
      });

      // appliquer collapsed au chargement
      this.applyCollapsedFromStorage();
    }

    // tooltips en collapsed
    applySidebarTooltips() {
      document.querySelectorAll(".az-nav-item").forEach((a) => {
        const span = a.querySelector("span");
        const label = span ? (span.textContent || "").trim() : "";
        if (label) a.setAttribute("data-tooltip", label);
      });
    }

    /* =========================
       USER MENU
       ========================= */
    setupUserMenu() {
      const userMenuToggle = document.getElementById("userMenuToggle");
      const userMenu = document.getElementById("userMenu");
      if (!userMenuToggle || !userMenu) return;

      userMenuToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        userMenu.classList.toggle("active");
        userMenuToggle.classList.toggle("active");
      });

      document.addEventListener("click", (e) => {
        if (!userMenuToggle.contains(e.target) && !userMenu.contains(e.target)) {
          this.closeUserMenu();
        }
      });

      userMenu.querySelectorAll(".az-user-menu-item").forEach((item) => {
        item.addEventListener("click", () => this.closeUserMenu());
      });
    }

    closeUserMenu() {
      const userMenuToggle = document.getElementById("userMenuToggle");
      const userMenu = document.getElementById("userMenu");
      if (!userMenuToggle || !userMenu) return;

      userMenu.classList.remove("active");
      userMenuToggle.classList.remove("active");
    }

    /* =========================
       ALERTS
       ========================= */
    setupAlertClosing() {
      const alerts = document.querySelectorAll(".az-alert");

      alerts.forEach((alert) => {
        const closeBtn = alert.querySelector(".az-alert-close");

        const removeAlert = () => {
          alert.style.animation = "az-slide-out 0.3s ease-out forwards";
          setTimeout(() => alert.remove(), 300);
        };

        if (closeBtn) closeBtn.addEventListener("click", removeAlert);

        setTimeout(() => {
          if (alert && alert.parentNode) removeAlert();
        }, 5000);
      });
    }

    /* =========================
       RESPONSIVE
       ========================= */
    setupResponsive() {
      window.addEventListener("resize", () => {
        const wasMobile = this.isMobile;
        this.isMobile = window.innerWidth <= 768;

        // mobile -> desktop : fermer drawer
        if (wasMobile && !this.isMobile) {
          this.closeMobileSidebar();
        }

        // appliquer collapsed state sur desktop
        this.applyCollapsedFromStorage();
      });
    }

    /* =========================
       EVENTS
       ========================= */
    setupEventListeners() {
      const notificationBtn = document.querySelector(".az-notification-btn");
      if (notificationBtn) {
        notificationBtn.addEventListener("click", () => {
          this.showNotification("Notifications", "Aucune nouvelle notification");
        });
      }

      this.setupActionButtons();
    }

    setupActionButtons() {
      document.querySelectorAll("[data-action]").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const action = btn.dataset.action;
          this.handleAction(action, e);
        });
      });
    }

    handleAction(action, event) {
      switch (action) {
        case "delete":
          this.confirmDelete(event.target);
          break;
        case "edit":
          this.editItem(event.target);
          break;
        case "view":
          this.viewItem(event.target);
          break;
        default:
          console.log("Action non reconnue:", action);
      }
    }

    showNotification(title, message, type = "info") {
      const icon = this.getIconForType(type);

      const alert = document.createElement("div");
      alert.className = `az-alert az-alert-${type}`;
      alert.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
        <button class="az-alert-close" type="button">&times;</button>
      `;

      const messagesContainer =
        document.querySelector(".az-messages") || document.querySelector(".az-content");

      if (!messagesContainer) return;

      messagesContainer.insertBefore(alert, messagesContainer.firstChild);

      const closeBtn = alert.querySelector(".az-alert-close");
      const removeAlert = () => {
        alert.style.animation = "az-slide-out 0.3s ease-out forwards";
        setTimeout(() => alert.remove(), 300);
      };

      if (closeBtn) closeBtn.addEventListener("click", removeAlert);

      setTimeout(() => {
        if (alert && alert.parentNode) removeAlert();
      }, 5000);
    }

    getIconForType(type) {
      const icons = {
        success: "check-circle",
        error: "exclamation-circle",
        warning: "exclamation-triangle",
        info: "info-circle",
      };
      return icons[type] || "info-circle";
    }

    confirmDelete() {
      if (confirm("Êtes-vous sûr de vouloir supprimer cet élément ?")) {
        this.showNotification("Suppression", "Élément supprimé avec succès", "success");
      }
    }

    editItem() {
      this.showNotification("Édition", "Ouverture du formulaire d'édition...", "info");
    }

    viewItem() {
      this.showNotification("Affichage", "Ouverture des détails...", "info");
    }
  }

  /* =========================
     DOM READY
     ========================= */
  document.addEventListener("DOMContentLoaded", () => {
    window.azAdmin = new AZAdmin();

    // animation sortie alert (si pas en CSS)
    const style = document.createElement("style");
    style.textContent = `
      @keyframes az-slide-out {
        to { opacity: 0; transform: translateY(-10px); }
      }
    `;
    document.head.appendChild(style);
  });

  /* =========================
     UTILITAIRES GLOBAUX (optionnels)
     ========================= */
  window.AZUtils = window.AZUtils || {
    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        if (window.azAdmin) window.azAdmin.showNotification("Copie", "Copié ✅", "success");
      });
    },
  };

  window.AZApi = window.AZApi || {
    async get(url) {
      const r = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      return await r.json();
    },
  };

  window.AZForm = window.AZForm || {};
  window.AZModal = window.AZModal || {};
  window.AZTable = window.AZTable || {};
})();
