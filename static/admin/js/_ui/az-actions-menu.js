/* =========================================
   AZ • Actions Menu (⋯)
   utilisé dans les listes (élèves, enseignants, etc.)
   ========================================= */

(function () {
  "use strict";

  const MENUS = "[data-menu], .az-actions-menu";
  const BTN = "[data-menu-btn], .az-kebab";
  const PANEL = "[data-menu-panel], .az-menu";

  function closeAll(except) {
    document.querySelectorAll(`${MENUS}.is-open`).forEach((menu) => {
      if (except && menu === except) return;

      menu.classList.remove("is-open");
      const row = menu.closest(".az-row");
      if (row) row.classList.remove("az-row-open");

      const btn = menu.querySelector(BTN);
      if (btn) btn.setAttribute("aria-expanded", "false");
    });
  }

  document.addEventListener("click", (e) => {

    const btn = e.target.closest(BTN);
    const menu = e.target.closest(MENUS);

    /* ===== Click sur bouton ⋯ ===== */
    if (btn && menu) {
      e.preventDefault();

      const isOpen = menu.classList.contains("is-open");

      closeAll(menu);

      const nextState = !isOpen;
      menu.classList.toggle("is-open", nextState);
      const row = menu.closest(".az-row");
      if (row) row.classList.toggle("az-row-open", nextState);
      btn.setAttribute("aria-expanded", String(nextState));

      return;
    }

    /* ===== Click sur item du menu ===== */
    if (e.target.closest(PANEL)) {
      closeAll();
      return;
    }

    /* ===== Click ailleurs ===== */
    closeAll();
  });

  /* ===== ESC ferme le menu ===== */
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });

  /* ===== Scroll ferme le menu ===== */
  window.addEventListener("scroll", () => {
    closeAll();
  });

})();