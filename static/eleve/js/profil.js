/* =========================================================
   AZ — Profil JS (NEBULA)
   - Copy-to-clipboard on [data-copy]
   - Toast feedback
   - Photo viewer (optional)
   ========================================================= */

(function () {
  // ---------- Toast ----------
  function ensureToast() {
    let t = document.querySelector(".az-toast");
    if (t) return t;

    t = document.createElement("div");
    t.className = "az-toast";
    t.innerHTML = `
      <i class="fa-solid fa-check"></i>
      <div>
        <b style="display:block;font-weight:1000">Copié</b>
        <span class="muted" style="font-size:.85rem">—</span>
      </div>
    `;
    document.body.appendChild(t);
    return t;
  }

  let toastTimer = null;
  function showToast(msg) {
    const t = ensureToast();
    const span = t.querySelector("span");
    if (span) span.textContent = msg || "Texte copié.";
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 1600);
  }

  // ---------- Copy ----------
  async function copyText(text) {
    const v = (text || "").trim();
    if (!v || v === "—") return;
    try {
      await navigator.clipboard.writeText(v);
      showToast(v);
    } catch (e) {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = v;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      showToast(v);
    }
  }

  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-copy]");
    if (!el) return;
    copyText(el.getAttribute("data-copy") || el.textContent);
  });

  // ---------- Photo viewer ----------
  const avatar = document.querySelector(".p2-avatar img");
  if (avatar) {
    // build viewer
    const pv = document.createElement("div");
    pv.className = "pv";
    pv.innerHTML = `
      <div class="pv-overlay" data-close="1"></div>
      <div class="pv-card" role="dialog" aria-modal="true">
        <button class="pv-close" type="button" data-close="1" aria-label="Fermer">
          <i class="fa-solid fa-xmark"></i>
        </button>
        <img src="${avatar.getAttribute("src")}" alt="Photo élève">
      </div>
    `;
    document.body.appendChild(pv);

    function openPV() {
      pv.classList.add("show");
      document.body.classList.add("no-scroll");
    }
    function closePV() {
      pv.classList.remove("show");
      document.body.classList.remove("no-scroll");
    }

    avatar.closest(".p2-avatar").addEventListener("click", openPV);
    pv.addEventListener("click", (e) => {
      if (e.target && e.target.getAttribute("data-close") === "1") closePV();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closePV();
    });
  }
})();
