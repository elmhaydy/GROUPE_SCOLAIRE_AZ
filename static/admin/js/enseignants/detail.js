/* =========================================================
   AZ — Enseignant Detail (JS)
   - sticky header
   - mobile labels (data-label) auto
   - small UX
   ========================================================= */
(function () {
  const header = document.querySelector(".az-ensd-header[data-sticky]");
  const table = document.querySelector(".az-ensd-table");
  const thead = document.querySelector(".az-ensd-thead");
  const rows = document.querySelectorAll(".az-ensd-tr");

  // ---------- Sticky header ----------
  function onScrollSticky() {
    if (!header) return;
    const y = window.scrollY || document.documentElement.scrollTop;
    header.classList.toggle("is-sticky", y > 10);
  }
  window.addEventListener("scroll", onScrollSticky, { passive: true });
  onScrollSticky();

  // ---------- Add mobile labels automatically ----------
  // We map headers -> cells based on order
  function addDataLabels() {
    if (!thead || !rows.length) return;

    const labels = Array.from(thead.children).map(el => (el.textContent || "").trim());

    rows.forEach((row) => {
      const cells = Array.from(row.querySelectorAll(".az-ensd-td"));
      cells.forEach((cell, idx) => {
        if (!cell.getAttribute("data-label") && labels[idx]) {
          cell.setAttribute("data-label", labels[idx]);
        }
      });
    });
  }
  addDataLabels();

  // ---------- Avatar hover (optional) ----------
  const avatar = document.querySelector(".az-ensd-avatar img");
  if (avatar) {
    avatar.addEventListener("mouseenter", () => {
      avatar.style.transform = "scale(1.03)";
      avatar.style.transition = "transform .18s ease";
    });
    avatar.addEventListener("mouseleave", () => {
      avatar.style.transform = "scale(1)";
    });
  }
})();
