(function () {
  const form = document.getElementById("smsFilters");
  const selStatus = document.getElementById("id_status");
  const selPeriod = document.getElementById("id_period");

  // Auto apply when dropdown changes (modern UX)
  function autoSubmit(el) {
    if (!form || !el) return;
    el.addEventListener("change", () => form.submit());
  }
  autoSubmit(selStatus);
  autoSubmit(selPeriod);

  // Modal
  const modal = document.getElementById("smsModal");
  const meta = document.getElementById("smsModalMeta");
  const msg = document.getElementById("smsModalMessage");
  const err = document.getElementById("smsModalError");

  function openModal() {
    if (!modal) return;
    modal.setAttribute("aria-hidden", "false");
    document.documentElement.classList.add("azsmsH-modal-open");
  }

  function closeModal() {
    if (!modal) return;
    modal.setAttribute("aria-hidden", "true");
    document.documentElement.classList.remove("azsmsH-modal-open");
  }

  // Click on row action
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-sms-view");
    if (!btn) return;

    const row = btn.closest(".azsmsH-row");
    if (!row) return;

    const parent = row.dataset.parent || "—";
    const phone = row.dataset.phone || "—";
    const status = row.dataset.status || "—";
    const date = row.dataset.date || "—";
    const message = row.dataset.msg || "";
    const error = row.dataset.error || "";

    meta.textContent = `📅 ${date}  •  👤 ${parent}  •  ☎ ${phone}  •  ✅ ${status}`;
    msg.textContent = message.trim() ? message : "—";
    err.textContent = error.trim() ? ("Erreur : " + error) : "";

    err.style.display = error.trim() ? "" : "none";

    openModal();
  });

  // Close triggers
  document.addEventListener("click", (e) => {
    if (e.target.matches("[data-close]") || e.target.closest("[data-close]")) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
})();
