/* =========================================================
   AZ MODAL — FINAL
   Compatible avec ton HTML:
   - .az-modal
   - [data-close="1"]
   - data-az-modal-open="URL" (sur les boutons de la liste)
   ========================================================= */

(function () {
  // 1) Crée un container overlay "global" (pour AJAX)
  function ensureOverlayRoot() {
    let root = document.getElementById("azOverlayRoot");
    if (root) return root;

    root = document.createElement("div");
    root.id = "azOverlayRoot";
    root.style.display = "none";
    root.innerHTML = `<div class="az-overlay-slot"></div>`;
    document.body.appendChild(root);
    return root;
  }

  function showModalHTML(html) {
    const root = ensureOverlayRoot();
    root.style.display = "block";
    const slot = root.querySelector(".az-overlay-slot");
    slot.innerHTML = html;

    // focus premier bouton
    const focusEl = slot.querySelector("button, [href], input, select, textarea");
    if (focusEl) setTimeout(() => focusEl.focus(), 30);
  }

  function closeModal() {
    // Si modal dans overlay ajax
    const root = document.getElementById("azOverlayRoot");
    if (root) {
      const slot = root.querySelector(".az-overlay-slot");
      if (slot && slot.querySelector(".az-modal")) {
        slot.innerHTML = "";
        root.style.display = "none";
        return;
      }
    }

    // Si modal est rendu directement dans la page
    const modal = document.querySelector(".az-modal");
    if (modal) modal.remove();
  }

  async function fetchModal(url) {
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!res.ok) throw new Error("Modal fetch failed: " + res.status);
    return await res.text();
  }

  // 2) Ouvrir via bouton data-az-modal-open
  document.addEventListener("click", async (e) => {
    const opener = e.target.closest("[data-az-modal-open]");
    if (!opener) return;

    e.preventDefault();

    const url =
      opener.getAttribute("data-az-modal-open") ||
      opener.getAttribute("href");

    if (!url) return;

    try {
      const html = await fetchModal(url);
      showModalHTML(html);
    } catch (err) {
      console.error(err);
      // fallback: ouvrir la page si fetch échoue
      window.location.href = url;
    }
  });

  // 3) Fermer via data-close="1"
  document.addEventListener("click", (e) => {
    const closer = e.target.closest('[data-close="1"]');
    if (!closer) return;
    e.preventDefault();
    closeModal();
  });

  // 4) Fermer via ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // (option) exposer au global
  window.AZModal = { close: closeModal };
})();
