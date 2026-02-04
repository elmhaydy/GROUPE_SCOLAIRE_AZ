/* =========================================================
   AZ • STAFF DASHBOARD JS
   File: static/admin/js/dashboard/staff.js
========================================================= */

(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function animateCounter(el, opts = {}) {
    // anime uniquement si contenu numérique
    const text = (el.textContent || "").trim().replace(/\s/g, "");
    if (!text) return;

    // Ex: "12" / "12.600,00" / "12600,00" / "12600"
    const raw = text.replace(/[^\d,.-]/g, "");
    if (!raw || !/[0-9]/.test(raw)) return;

    // tente parse en float (FR -> .)
    const num = parseFloat(raw.replace(/\./g, "").replace(",", "."));
    if (!Number.isFinite(num)) return;

    const duration = opts.duration ?? 650;
    const start = performance.now();
    const from = 0;
    const to = num;

    // format final : si entier => 0 décimales, sinon 2
    const hasDecimals = Math.abs(to - Math.round(to)) > 0.001;
    const format = (v) => {
      const val = hasDecimals ? v.toFixed(2) : Math.round(v).toString();
      // format FR simple (espace milliers + virgule)
      const parts = val.split(".");
      const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
      return parts.length > 1 ? `${intPart},${parts[1]}` : intPart;
    };

    // garde suffix/prefix autour du nombre (ex: " MAD", "%")
    const prefix = (el.dataset.prefix || "");
    const suffix = (el.dataset.suffix || "");
    // si on détecte MAD dans le parent proche, laisse le template gérer (on anime juste le nombre)
    const original = el.innerHTML;

    // si l'élément contient déjà du HTML (span unité), on ne touche pas
    if (/<span/i.test(original)) return;

    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      // easing
      const eased = 1 - Math.pow(1 - t, 3);
      const cur = from + (to - from) * eased;
      el.textContent = `${prefix}${format(cur)}${suffix}`;
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = `${prefix}${format(to)}${suffix}`;
    }

    requestAnimationFrame(tick);
  }

  function addLoadingOnClick(btn) {
    if (!btn) return;
    btn.addEventListener("click", () => {
      btn.classList.add("is-loading");
      btn.setAttribute("aria-busy", "true");
      // si c'est un <a>, on laisse naviguer tout de suite (donc pas de setTimeout)
      if (btn.tagName === "BUTTON") {
        // petite sécurité UX si le bouton ne fait rien
        setTimeout(() => {
          btn.classList.remove("is-loading");
          btn.removeAttribute("aria-busy");
        }, 1200);
      }
    });
  }

  function init() {
    // 1) animation des valeurs KPI (si texte pur)
    $$(".azad-kpi-val").forEach((el) => animateCounter(el, { duration: 700 }));

    // 2) animation des valeurs présences
    $$(".azad-pres-val").forEach((el) => animateCounter(el, { duration: 650 }));

    // 3) loading state sur boutons
    $$(".azad-btn").forEach(addLoadingOnClick);

    // 4) raccourci clavier : R = reload
    document.addEventListener("keydown", (e) => {
      if (e.key && (e.key.toLowerCase() === "r") && (e.ctrlKey || e.metaKey)) return; // laisse CTRL+R normal
      if (e.key && e.key.toLowerCase() === "r" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        // évite si focus input
        const t = (document.activeElement && document.activeElement.tagName) || "";
        if (["INPUT", "TEXTAREA", "SELECT"].includes(t)) return;
        window.location.reload();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
// admin/js/dashboard/staff.js
(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // Micro-anim: entrance
  window.addEventListener("DOMContentLoaded", () => {
    const cards = $$(".azad-card, .azad-kpi");
    cards.forEach((el, i) => {
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
      el.style.transition = "opacity .25s ease, transform .25s ease";
      setTimeout(() => {
        el.style.opacity = "1";
        el.style.transform = "translateY(0)";
      }, 40 + i * 40);
    });

    const note = $("#staffNote");
    if (note) {
      setTimeout(() => {
        note.style.transition = "opacity .25s ease, transform .25s ease";
        note.style.opacity = "0";
        note.style.transform = "translateY(4px)";
      }, 6000);
    }
  });
})();
