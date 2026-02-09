/* static/admin/js/nav_nebula.js */
/* AZ — Nav dropdown persistence */

(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const STORAGE_NAV = "az-nav-open";

  function safeGet(key, fallback = null) {
    try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
  }
  function safeSet(key, value) {
    try { localStorage.setItem(key, value); } catch {}
  }

  function readState() {
    const raw = safeGet(STORAGE_NAV, "{}");
    try {
      const obj = JSON.parse(raw);
      return (obj && typeof obj === "object") ? obj : {};
    } catch { return {}; }
  }
  function writeState(state) {
    safeSet(STORAGE_NAV, JSON.stringify(state || {}));
  }

  function setOpen(dropEl, open) {
    const btn = $(".az-nav-drop-btn", dropEl);
    dropEl.setAttribute("data-open", open ? "true" : "false");
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const drops = $$(".az-nav-drop");
    const state = readState();

    drops.forEach((drop) => {
      const key = drop.getAttribute("data-drop") || "";
      const btn = $(".az-nav-drop-btn", drop);
      const hasActive = !!$(".az-nav-item.active", drop);

      const saved = (key && key in state) ? !!state[key] : null;
      const initialOpen = hasActive ? true : (saved === null ? (drop.getAttribute("data-open") !== "false") : saved);

      setOpen(drop, initialOpen);

      if (!btn) return;
      btn.addEventListener("click", () => {
        const now = drop.getAttribute("data-open") !== "true";
        setOpen(drop, now);
        if (key) {
          const next = readState();
          next[key] = now;
          writeState(next);
        }
      });
    });
  });
})();
