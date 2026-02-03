/* ==========================================================================
   AZ — Staff / Direction Dashboard (staff.js)
   - Date (optionnel)
   - Auto-scroll léger sur la liste paiements (si longue)
   - Mini refresh UX (reload)
   - Raccourcis clavier (optionnel)
   - Compatible dark/light (pas de Chart.js)
   ========================================================================== */

(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function notify(title, message, type = "info") {
    // Hook AZ (si tu l’as dans admin.js)
    if (window.azAdmin && typeof window.azAdmin.showNotification === "function") {
      window.azAdmin.showNotification(title, message, type);
      return;
    }
    console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
  }

  function formatDateFR(d = new Date()) {
    try {
      return d.toLocaleDateString("fr-FR", { year: "numeric", month: "long", day: "numeric" });
    } catch {
      return "";
    }
  }

  function initDate() {
    // Dans ton template staff tu n’as PAS d'id="currentDate"
    // mais si tu veux l’ajouter plus tard, ce code le gère.
    const el = $("#currentDate");
    if (!el) return;
    const txt = (el.textContent || "").trim();
    if (txt.length) return; // Django a déjà rendu la date
    el.textContent = formatDateFR();
  }

  function addQuickRefreshButton() {
    // Option: si tu veux un bouton refresh, tu peux l’ajouter dans HTML plus tard.
    // Si tu as un bouton id="refreshDashboard", il sera géré ici.
    const btn = $("#refreshDashboard");
    if (!btn) return;

    btn.addEventListener("click", () => {
      btn.disabled = true;
      const normal = btn.innerHTML;
      btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Actualisation...`;

      // refresh simple : reload page
      setTimeout(() => {
        window.location.reload();
      }, 350);
    });
  }

  function autoScrollPayments() {
    // Si la liste est longue, on fait un scroll doux automatique (style “ticker”)
    // Cherche la 2e carte "Derniers paiements" via .azad-card contenant .azad-list
    const lists = $$(".azad-card .azad-list");
    if (!lists.length) return;

    // On choisit la liste la plus “longue” (paiements)
    const list = lists.sort((a, b) => b.scrollHeight - a.scrollHeight)[0];

    // si pas de overflow, on ne fait rien
    if (list.scrollHeight <= list.clientHeight + 5) return;

    // On applique des styles inline safe (au cas où le CSS ne le fait pas)
    list.style.overflow = "auto";
    list.style.scrollBehavior = "smooth";

    let dir = 1; // 1 vers bas, -1 vers haut
    let rafId = null;
    let paused = false;

    const step = () => {
      if (paused) {
        rafId = requestAnimationFrame(step);
        return;
      }

      const max = list.scrollHeight - list.clientHeight;
      const next = Math.max(0, Math.min(max, list.scrollTop + dir * 0.35));

      list.scrollTop = next;

      // rebond
      if (next >= max - 1) dir = -1;
      if (next <= 1) dir = 1;

      rafId = requestAnimationFrame(step);
    };

    // pause au hover
    list.addEventListener("mouseenter", () => (paused = true));
    list.addEventListener("mouseleave", () => (paused = false));
    list.addEventListener("touchstart", () => (paused = true), { passive: true });
    list.addEventListener("touchend", () => (paused = false), { passive: true });

    // démarrer
    rafId = requestAnimationFrame(step);

    // cleanup si besoin (page unload)
    window.addEventListener("beforeunload", () => {
      if (rafId) cancelAnimationFrame(rafId);
    });
  }

  function keyboardShortcuts() {
    // Optionnel : R = reload, P = paiements, A = absences
    document.addEventListener("keydown", (e) => {
      // ignore si user écrit dans input/textarea
      const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : "";
      if (tag === "input" || tag === "textarea" || e.target.isContentEditable) return;

      if (e.key.toLowerCase() === "r") {
        notify("Dashboard", "Actualisation…", "info");
        window.location.reload();
      }
    });
  }

  function init() {
    initDate();
    addQuickRefreshButton();
    autoScrollPayments();
    keyboardShortcuts();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
