(function () {
  "use strict";

  function init() {
    const modal = document.getElementById("azModal");
    const body = document.getElementById("azModalBody");

    if (!modal || !body) {
      console.warn("AZ Modal introuvable");
      return;
    }

    let lastFocus = null;

    function openModal() {
      lastFocus = document.activeElement;
      modal.classList.add("is-open");
      modal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }

    function closeModal() {
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      body.innerHTML = `<div class="az-sub">Chargement...</div>`;

      if (lastFocus && typeof lastFocus.focus === "function") {
        lastFocus.focus();
      }
    }

    async function loadModal(url) {
      if (!url) return;

      openModal();

      try {
        const res = await fetch(url, {
          headers: {
            "X-Requested-With": "XMLHttpRequest"
          },
          credentials: "same-origin"
        });

        if (!res.ok) {
          body.innerHTML = `<div class="az-alert az-alert-danger">Erreur ${res.status}</div>`;
          return;
        }

        body.innerHTML = await res.text();

        const first = body.querySelector("input, select, textarea, button, a");
        if (first) first.focus();

      } catch (err) {
        console.error("Erreur loadModal:", err);
        body.innerHTML = `<div class="az-alert az-alert-danger">Erreur de chargement.</div>`;
      }
    }

    async function submitModalForm(form) {
      const submitBtn = form.querySelector('button[type="submit"]');
      const oldHtml = submitBtn ? submitBtn.innerHTML : "";

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Traitement...`;
      }

      try {
        const formData = new FormData(form);

        const res = await fetch(form.action, {
          method: (form.method || "POST").toUpperCase(),
          body: formData,
          headers: {
            "X-Requested-With": "XMLHttpRequest"
          },
          credentials: "same-origin"
        });

        const contentType = res.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
          const data = await res.json();

          if (data.ok) {
            closeModal();

            if (data.redirect_url) {
              window.location.href = data.redirect_url;
            } else {
              window.location.reload();
            }
            return;
          }

          if (data.html) {
            body.innerHTML = data.html;
            return;
          }

          if (data.message) {
            body.innerHTML = `<div class="az-alert az-alert-danger">${data.message}</div>`;
            return;
          }
        }

        body.innerHTML = await res.text();

      } catch (err) {
        console.error("Erreur submitModalForm:", err);
        body.innerHTML = `<div class="az-alert az-alert-danger">Erreur formulaire.</div>`;
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = oldHtml;
        }
      }
    }

    async function reloadFilteredModal(form) {
      const formData = new FormData(form);
      const params = new URLSearchParams();

      for (const [key, value] of formData.entries()) {
        params.append(key, value);
      }

      const url = `${form.action}?${params.toString()}`;
      await loadModal(url);
    }

    modal.addEventListener("click", function (e) {
      if (e.target.closest("[data-azm-close]")) {
        e.preventDefault();
        closeModal();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (!modal.classList.contains("is-open")) return;
      if (e.key === "Escape") closeModal();
    });

    document.addEventListener("click", function (e) {
      const trigger = e.target.closest("[data-az-modal], [data-delete-modal], [data-user-modal], [data-az-modal-open]");
      if (!trigger) return;

      e.preventDefault();
      e.stopPropagation();

      const url = trigger.getAttribute("data-modal-url") || trigger.getAttribute("href");
      if (!url) return;

      loadModal(url);
    }, true);

    document.addEventListener("submit", function (e) {
      const form = e.target.closest("form[data-az-modal-form], form[data-delete-form]");
      if (!form) return;

      e.preventDefault();
      submitModalForm(form);
    });

    document.addEventListener("change", function (e) {
      const filter = e.target.closest("[data-reinsc-filter]");
      if (!filter) return;

      const form = filter.closest("form[data-az-modal-form]");
      if (!form) return;

      reloadFilteredModal(form);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();