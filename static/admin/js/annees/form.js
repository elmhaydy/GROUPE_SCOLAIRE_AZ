/* =========================================================
   AZ — Année scolaire (FORM) — annee_form.js
   - Auto-format Nom: "2025/2026"
   - Validation: date_fin >= date_debut
   - Toasts (sans dépendances)
   ========================================================= */

(function () {
  "use strict";

  // ---------- Helpers ----------
  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function pad2(n) {
    n = String(n || "");
    return n.length === 1 ? "0" + n : n;
  }

  function isLightTheme() {
    return document.documentElement.getAttribute("data-theme") === "light";
  }

  // ---------- Toast ----------
  function ensureToastRoot() {
    let root = $("#azToastRoot");
    if (root) return root;

    root = document.createElement("div");
    root.id = "azToastRoot";
    root.style.position = "fixed";
    root.style.right = "18px";
    root.style.bottom = "18px";
    root.style.display = "grid";
    root.style.gap = "10px";
    root.style.zIndex = "9999";
    document.body.appendChild(root);
    return root;
  }

  function toast(type, title, message) {
    const root = ensureToastRoot();

    const el = document.createElement("div");
    el.className = "az-toast";
    el.setAttribute("role", "status");

    const light = isLightTheme();

    const bg = light ? "rgba(255,255,255,.95)" : "rgba(15,23,42,.92)";
    const border = light ? "rgba(15,23,42,.10)" : "rgba(148,163,184,.22)";
    const text = light ? "#0f172a" : "#e5e7eb";

    let accent = "#6366f1";
    let icon = "info-circle";
    if (type === "success") { accent = "#22c55e"; icon = "check-circle"; }
    if (type === "error") { accent = "#ef4444"; icon = "exclamation-circle"; }
    if (type === "warning") { accent = "#f59e0b"; icon = "triangle-exclamation"; }

    el.style.background = bg;
    el.style.border = "1px solid " + border;
    el.style.borderLeft = "4px solid " + accent;
    el.style.color = text;
    el.style.borderRadius = "14px";
    el.style.padding = "12px 12px";
    el.style.minWidth = "280px";
    el.style.maxWidth = "360px";
    el.style.boxShadow = "0 14px 35px rgba(0,0,0,.20)";
    el.style.display = "grid";
    el.style.gridTemplateColumns = "22px 1fr 22px";
    el.style.columnGap = "10px";
    el.style.alignItems = "start";
    el.style.transform = "translateY(8px)";
    el.style.opacity = "0";
    el.style.transition = "all .18s ease";

    el.innerHTML = `
      <div style="margin-top:2px;color:${accent}">
        <i class="fas fa-${icon}"></i>
      </div>
      <div>
        <div style="font-weight:700;font-size:13px;line-height:1.2;margin-bottom:3px;">${escapeHtml(title || "")}</div>
        <div style="font-size:12px;opacity:.9;line-height:1.35;">${escapeHtml(message || "")}</div>
      </div>
      <button type="button" aria-label="Fermer"
        style="all:unset;cursor:pointer;opacity:.75;display:flex;justify-content:center;">
        <i class="fas fa-xmark"></i>
      </button>
    `;

    const closeBtn = el.querySelector("button");
    closeBtn.addEventListener("click", () => removeToast(el));

    root.appendChild(el);

    // animate in
    requestAnimationFrame(() => {
      el.style.transform = "translateY(0)";
      el.style.opacity = "1";
    });

    // auto close
    const t = setTimeout(() => removeToast(el), 3600);
    el._azTimer = t;

    return el;
  }

  function removeToast(el) {
    if (!el) return;
    try { clearTimeout(el._azTimer); } catch (e) {}
    el.style.transform = "translateY(8px)";
    el.style.opacity = "0";
    setTimeout(() => {
      if (el && el.parentNode) el.parentNode.removeChild(el);
    }, 180);
  }

  function escapeHtml(str) {
    return String(str || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // ---------- Format Nom "YYYY/YYYY" ----------
  function formatSchoolYear(raw) {
    // garde seulement chiffres
    const digits = String(raw || "").replace(/\D/g, "").slice(0, 8); // max 8 chiffres
    if (digits.length <= 4) return digits; // ex: "2025"
    const a = digits.slice(0, 4);
    const b = digits.slice(4, 8);
    return b.length ? `${a}/${b}` : a;
  }

  function guessYearFromDates(dateDebutValue) {
    // dateDebutValue: "YYYY-MM-DD"
    if (!dateDebutValue) return null;
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateDebutValue);
    if (!m) return null;
    const y = Number(m[1]);
    return y ? `${y}/${y + 1}` : null;
  }

  // ---------- Validation Dates ----------
  function parseISODate(v) {
    // "YYYY-MM-DD" -> Date (local)
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v || ""));
    if (!m) return null;
    const y = Number(m[1]);
    const mo = Number(m[2]) - 1;
    const d = Number(m[3]);
    const dt = new Date(y, mo, d);
    return isNaN(dt.getTime()) ? null : dt;
  }

  function setFieldError(input, message) {
    if (!input) return;
    input.classList.add("az-field-invalid");
    input.setAttribute("aria-invalid", "true");

    // zone message
    let msg = input.parentElement ? input.parentElement.querySelector(".az-field-error-js") : null;
    if (!msg) {
      msg = document.createElement("div");
      msg.className = "az-field-error-js";
      msg.style.fontSize = "12px";
      msg.style.color = "#fca5a5";
      msg.style.marginTop = "6px";
      if (input.parentElement) input.parentElement.appendChild(msg);
    }
    msg.textContent = message || "Champ invalide.";
  }

  function clearFieldError(input) {
    if (!input) return;
    input.classList.remove("az-field-invalid");
    input.removeAttribute("aria-invalid");

    const msg = input.parentElement ? input.parentElement.querySelector(".az-field-error-js") : null;
    if (msg) msg.remove();
  }

  function validateDates(dateDebutEl, dateFinEl) {
    clearFieldError(dateDebutEl);
    clearFieldError(dateFinEl);

    const d1 = parseISODate(dateDebutEl ? dateDebutEl.value : "");
    const d2 = parseISODate(dateFinEl ? dateFinEl.value : "");

    // si un seul champ rempli, on laisse
    if (!d1 || !d2) return true;

    if (d2.getTime() < d1.getTime()) {
      setFieldError(dateFinEl, "La date de fin doit être supérieure ou égale à la date de début.");
      return false;
    }
    return true;
  }

  // ---------- Init ----------
  function init() {
    const form = $("form.az-form") || $("form"); // fallback
    if (!form) return;

    // Django ids typiques: id_nom, id_date_debut, id_date_fin, id_is_active
    const nomEl = $("#id_nom", form);
    const dateDebutEl = $("#id_date_debut", form);
    const dateFinEl = $("#id_date_fin", form);

    // 1) Auto-format sur saisie NOM
    if (nomEl) {
      nomEl.addEventListener("input", function () {
        const before = this.value;
        const after = formatSchoolYear(before);
        if (after !== before) this.value = after;
        clearFieldError(this);
      });

      // Si champ vide et on met date_debut, on propose un nom auto
      if (dateDebutEl) {
        dateDebutEl.addEventListener("change", function () {
          if (!nomEl.value) {
            const guessed = guessYearFromDates(dateDebutEl.value);
            if (guessed) nomEl.value = guessed;
          }
          validateDates(dateDebutEl, dateFinEl);
        });
      }
    }

    // 2) Validation live dates
    if (dateDebutEl) {
      dateDebutEl.addEventListener("change", function () {
        validateDates(dateDebutEl, dateFinEl);
      });
    }
    if (dateFinEl) {
      dateFinEl.addEventListener("change", function () {
        validateDates(dateDebutEl, dateFinEl);
      });
    }

    // 3) Submit: bloque si invalide
    form.addEventListener("submit", function (e) {
      let ok = true;

      // Nom: si rempli en 8 chiffres sans "/" on corrige
      if (nomEl) {
        const cleaned = formatSchoolYear(nomEl.value);
        nomEl.value = cleaned;
        // si l’utilisateur a mis 2025/ (incomplet) on ne bloque pas
      }

      ok = validateDates(dateDebutEl, dateFinEl) && ok;

      if (!ok) {
        e.preventDefault();
        toast("error", "Formulaire invalide", "Corrige les erreurs avant d’enregistrer.");
        if (dateFinEl && dateFinEl.classList.contains("az-field-invalid")) dateFinEl.focus();
        return;
      }

      // feedback submit
      toast("success", "Enregistrement", "Données prêtes à être envoyées…");
    });

    // 4) Petite classe focus invalide (style via CSS global ou tu peux ajouter dans annee_form.css)
    injectTinyInvalidCSS();
  }

  function injectTinyInvalidCSS() {
    if ($("#azInvalidCSS")) return;
    const style = document.createElement("style");
    style.id = "azInvalidCSS";
    style.textContent = `
      .az-field-invalid{
        border-color: rgba(239,68,68,.75) !important;
        box-shadow: 0 0 0 3px rgba(239,68,68,.12) !important;
      }
    `;
    document.head.appendChild(style);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
// UX Switch: clic sur toute la ligne + accessibilité
(function () {
  const row = document.querySelector(".az-switch-row");
  if (!row) return;

  const input = row.querySelector('input[type="checkbox"]');
  if (!input) return;

  // Empêche double toggle si on clique sur le switch UI
  row.addEventListener("click", (e) => {
    // si clic sur un lien (pas le cas ici) => ignore
    if (e.target && e.target.closest("a")) return;
    // label toggle déjà le checkbox naturellement, donc rien à faire
  });

  // Optionnel: ajoute un data-state utile si tu veux
  const sync = () => row.setAttribute("data-on", input.checked ? "1" : "0");
  input.addEventListener("change", sync);
  sync();
})();
