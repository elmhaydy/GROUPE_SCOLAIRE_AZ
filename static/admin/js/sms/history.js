(function () {
  const form = document.getElementById("smsFilters");
  const selStatus = document.getElementById("id_status");
  const selPeriod = document.getElementById("id_period");
  const selEvent = document.getElementById("id_event");

  // Auto apply when dropdown changes (quick filtering)
  function autoSubmit(el) {
    if (!form || !el) return;
    el.addEventListener("change", () => form.submit());
  }
  autoSubmit(selStatus);
  autoSubmit(selPeriod);
  autoSubmit(selEvent);

  // Modal handling
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
    const event = row.dataset.event || "—";
    const message = row.dataset.msg || "";
    const error = row.dataset.error || "";

    meta.textContent = `📅 ${date}  •  👤 ${parent}  •  ☎ ${phone}  •  🗂 ${event}  •  ✅ ${status}`;
    msg.textContent = message.trim() ? message : "—";
    err.textContent = error.trim() ? "Erreur : " + error : "";
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
