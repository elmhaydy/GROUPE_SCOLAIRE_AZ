/* =========================================================
   AZ MODAL — NEBULA (PRO)
   - Ouvre via [data-az-modal-open]
   - Ferme via [data-close="1"] / [data-az-close] / ESC / backdrop
   - POST AJAX dans le modal (optionnel) + refresh auto
   ========================================================= */
console.log("AZ MODAL NEBULA LOADED ✅");

(function () {
  let isOpening = false;

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

  function getSlot() {
    const root = ensureOverlayRoot();
    return root.querySelector(".az-overlay-slot");
  }

  function showModalHTML(html) {
    const root = ensureOverlayRoot();
    root.style.display = "block";
    const slot = getSlot();
    slot.innerHTML = html;

    // Focus premier élément focusable
    const focusEl = slot.querySelector("button, [href], input, select, textarea");
    if (focusEl) setTimeout(() => focusEl.focus(), 30);
  }

  function closeModal() {
    const root = document.getElementById("azOverlayRoot");
    if (root) {
      const slot = root.querySelector(".az-overlay-slot");
      if (slot && slot.querySelector(".az-modal")) {
        slot.innerHTML = "";
        root.style.display = "none";
        return;
      }
    }

    const modal = document.querySelector(".az-modal");
    if (modal) modal.remove();
  }

  async function fetchModal(url) {
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error("Modal fetch failed: " + res.status);
    return await res.text();
  }

  function shouldIgnoreOpen(e, el) {
    // Ctrl/cmd click, middle click => ouvrir normalement
    if (e.ctrlKey || e.metaKey || e.button === 1) return true;
    // target blank => ouvrir normalement
    if (el && el.getAttribute("target") === "_blank") return true;
    return false;
  }

  // ✅ OUVERTURE
document.addEventListener("click", async (e) => {
  const opener = e.target.closest("[data-az-modal-open]");
  if (!opener) return;

  if (shouldIgnoreOpen(e, opener)) return;

  e.preventDefault();

  const url = opener.getAttribute("data-az-modal-open") || opener.getAttribute("href");
  if (!url) return;

  if (isOpening) return;
  isOpening = true;

  try {
    const html = await fetchModal(url);
    showModalHTML(html);
  } catch (err) {
    console.error(err);
    window.location.href = url; // fallback
  } finally {
    isOpening = false;
  }
}, true); // ✅ IMPORTANT: capture = true


  // ✅ FERMETURE (boutons + backdrop)
  document.addEventListener("click", (e) => {
    const closer = e.target.closest('[data-close="1"], [data-az-close]');
    if (closer) {
      e.preventDefault();
      closeModal();
      return;
    }

    // clic direct sur le backdrop
    if (e.target && e.target.classList && e.target.classList.contains("az-modal-backdrop")) {
      e.preventDefault();
      closeModal();
    }
  });

  // ✅ ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // ✅ POST AJAX dans le modal (ex: suppression)
  document.addEventListener("submit", async (e) => {
    const form = e.target;
    if (!form) return;

    // On ne gère en AJAX que les forms qui sont DANS un modal AZ
    const modal = form.closest(".az-modal");
    if (!modal) return;

    // Option: si tu veux désactiver l’AJAX sur un form précis, ajoute data-az-noajax
    if (form.hasAttribute("data-az-noajax")) return;

    e.preventDefault();

    const action = form.getAttribute("action") || window.location.href;
    const method = (form.getAttribute("method") || "post").toUpperCase();

    const btn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (btn) btn.disabled = true;

    try {
      const fd = new FormData(form);

      const res = await fetch(action, {
        method,
        body: fd,
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });

      // Si le serveur renvoie un HTML modal (erreurs), on remplace
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      if (ct.includes("text/html")) {
        const html = await res.text();
        showModalHTML(html);
        return;
      }

      // Sinon: succès => fermer et refresh (simple et fiable)
      if (res.ok) {
        closeModal();
        window.location.reload();
      } else {
        console.error("Modal submit failed", res.status);
        window.location.reload();
      }
    } catch (err) {
      console.error(err);
      window.location.reload();
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  window.AZModal = { close: closeModal };
})();
