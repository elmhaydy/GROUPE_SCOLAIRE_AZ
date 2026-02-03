/* =========================================================
   AZ — Dashboard JS
   - Avis modal (details)
   - Today sessions state (now/next/done)
   ========================================================= */

(function () {
  // ---------------------------
  // Avis Modal
  // ---------------------------
  const modal = document.getElementById("azAvisModal");
  const mTitle = document.getElementById("azAvisTitle");
  const mDate = document.getElementById("azAvisDate");
  const mBody = document.getElementById("azAvisBody");

  function openModal({ title, date, body }) {
    if (!modal) return;
    mTitle.textContent = title || "—";
    mDate.textContent = date || "—";
    mBody.textContent = body || "—";
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("no-scroll");
  }

  function closeModal() {
    if (!modal) return;
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("no-scroll");
  }

  document.querySelectorAll(".az-avis").forEach((btn) => {
    btn.addEventListener("click", () => {
      openModal({
        title: btn.getAttribute("data-avis-title"),
        date: btn.getAttribute("data-avis-date"),
        body: btn.getAttribute("data-avis-body"),
      });
    });
  });

  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target && e.target.getAttribute("data-close") === "1") closeModal();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // ---------------------------
  // Today sessions state
  // ---------------------------
  const nowChip = document.getElementById("azNowChip");

  function toMin(hhmm) {
    const [h, m] = (hhmm || "").split(":").map((x) => parseInt(x, 10));
    if (Number.isNaN(h) || Number.isNaN(m)) return null;
    return h * 60 + m;
  }

  function updateNowChip() {
    if (!nowChip) return;
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    nowChip.querySelector("span").textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function refreshTodayStates() {
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();

    const items = Array.from(document.querySelectorAll(".az-today-item"));
    if (!items.length) return;

    // reset
    items.forEach((it) => {
      const badge = it.querySelector('[data-role="state"]');
      if (!badge) return;
      badge.classList.remove("now", "next", "ok", "warn");
      badge.textContent = "—";
    });

    // compute
    let nextCandidate = null;
    items.forEach((it) => {
      const s = toMin(it.getAttribute("data-start"));
      const e = toMin(it.getAttribute("data-end"));
      if (s == null || e == null) return;

      const badge = it.querySelector('[data-role="state"]');
      if (!badge) return;

      if (nowMin >= s && nowMin < e) {
        badge.classList.add("now");
        badge.textContent = "En cours";
      } else if (nowMin < s) {
        // future
        if (!nextCandidate || s < nextCandidate.start) {
          nextCandidate = { el: it, start: s };
        }
        badge.classList.add("next");
        badge.textContent = "À venir";
      } else {
        badge.classList.add("ok");
        badge.textContent = "Terminé";
      }
    });

    // mark the nearest upcoming as "Prochain"
    if (nextCandidate) {
      const badge = nextCandidate.el.querySelector('[data-role="state"]');
      if (badge) {
        badge.classList.remove("next");
        badge.classList.add("warn");
        badge.textContent = "Prochain";
      }
    }
  }

  updateNowChip();
  refreshTodayStates();
  setInterval(() => {
    updateNowChip();
    refreshTodayStates();
  }, 30000);
})();
