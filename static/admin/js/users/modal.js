(function () {
  const root = document.getElementById("az-modal-root");
  if (!root) return;

  async function openModal(url) {
    const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    const html = await res.text();
    root.innerHTML = html;

    // fermer sur ESC
    document.addEventListener("keydown", onEsc);
  }

  function closeModal() {
    root.innerHTML = "";
    document.removeEventListener("keydown", onEsc);
  }

  function onEsc(e) {
    if (e.key === "Escape") closeModal();
  }

  // click bouton open
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-az-open-modal]");
    if (btn) {
      e.preventDefault();
      openModal(btn.getAttribute("data-az-open-modal"));
      return;
    }

    // click close
    if (e.target.closest("[data-az-close]")) {
      closeModal();
      return;
    }
  });
})();
