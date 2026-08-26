(() => {
  "use strict";

  const modal = document.getElementById("avisModal");
  const titleEl = document.getElementById("avisModalTitle");
  const contentEl = document.getElementById("avisModalContent");

  function openModal(data){
    if (!modal) return;

    const { title, content, cible, cibleDetail, date, visible } = data;
    titleEl.textContent = title || "Détails de l'avis";

    const isVisible = visible === "True";
    const parentBadgeClass = isVisible ? "az-badge-success" : "az-badge-warning";
    const parentBadgeIcon = isVisible ? "fa-eye" : "fa-eye-slash";
    const parentBadgeText = isVisible ? "Visible aux parents" : "Masqué aux parents";

    contentEl.innerHTML = `
      <div class="az-modal-avis-details" style="display:flex; flex-direction:column; gap:16px;">
        <div class="az-modal-badges" style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; padding-bottom:12px; border-bottom:1px solid var(--az-border, rgba(148,163,184,0.2));">
          <span class="az-badge az-badge-info">
            <i class="fa-solid fa-bullhorn"></i> Cible : <b>${cible || "Tous"}</b>
          </span>

          ${cibleDetail ? `
            <span class="az-badge az-badge-muted">
              <i class="fa-solid fa-crosshairs"></i> <b>${cibleDetail}</b>
            </span>
          ` : ""}

          <span class="az-badge ${parentBadgeClass}">
            <i class="fa-solid ${parentBadgeIcon}"></i> <b>${parentBadgeText}</b>
          </span>

          ${date ? `
            <span class="az-badge az-badge-muted" style="margin-left:auto;">
              <i class="fa-regular fa-clock"></i> Publié le <b>${date}</b>
            </span>
          ` : ""}
        </div>

        <div>
          <div style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.05em; font-weight:800; color:var(--az-text-tertiary, #94a3b8); margin-bottom:6px;">
            Contenu du message
          </div>
          <div style="background:var(--az-bg-secondary, rgba(248,250,252,0.8)); border:1px solid var(--az-border, rgba(148,163,184,0.18)); border-radius:12px; padding:16px; color:var(--az-text-primary, #0f172a); font-size:0.95rem; line-height:1.65; white-space:pre-wrap; word-break:break-word;">${content || "—"}</div>
        </div>
      </div>
    `;

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeModal(){
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  document.addEventListener("click", (e) => {
    const previewBtn = e.target.closest(".js-avis-preview");
    if (previewBtn){
      const card = previewBtn.closest("[data-title]");
      if (card) {
        const title = card.dataset.title || "";
        const content = card.dataset.content || "";
        const cible = card.dataset.cible || "Tous";
        const cibleDetail = card.dataset.cibleDetail || "";
        const date = card.dataset.date || "";
        const visible = card.dataset.visible || "True";

        openModal({ title, content, cible, cibleDetail, date, visible });
      }

      const menu = previewBtn.closest("[data-menu]");
      if (menu) {
        menu.classList.remove("is-open");
      }
      return;
    }

    // close modal
    if (e.target.matches("[data-close]")){
      closeModal();
      return;
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });
})();

(function(){
  const form = document.getElementById("avisFilters");
  if(!form) return;

  ["id_cible","id_period"].forEach(id=>{
    const el = document.getElementById(id);
    if(el) el.addEventListener("change", ()=> form.submit());
  });
})();
