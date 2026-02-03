/* =========================================================
   AZ NAV — Dropdown sections (classic)
   - conserve .az-nav-section et .az-nav-item
   - ouvre automatiquement la section qui contient l'item .active
   ========================================================= */
(() => {
  "use strict";

  const nav = document.getElementById("azNav");
  if (!nav) return;

  const drops = nav.querySelectorAll(".az-nav-drop");

  // helper: open/close
  function setOpen(drop, open) {
    drop.dataset.open = open ? "true" : "false";
    const btn = drop.querySelector(".az-nav-drop-btn");
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  }

  // init: fermer tout par défaut, puis ouvrir celui qui contient .active
  drops.forEach((drop) => setOpen(drop, false));

  // open section of active item
  const active = nav.querySelector(".az-nav-item.active");
  if (active) {
    const parentDrop = active.closest(".az-nav-drop");
    if (parentDrop) setOpen(parentDrop, true);
  }

  // click handlers
  drops.forEach((drop) => {
    const btn = drop.querySelector(".az-nav-drop-btn");
    if (!btn) return;

    // si ton HTML met aria-expanded="true" initialement => on respecte
    const initialExpanded = btn.getAttribute("aria-expanded");
    if (initialExpanded === "true") setOpen(drop, true);

    btn.addEventListener("click", () => {
      const isOpen = drop.dataset.open !== "false";
      setOpen(drop, !isOpen);
    });
  });
})();
