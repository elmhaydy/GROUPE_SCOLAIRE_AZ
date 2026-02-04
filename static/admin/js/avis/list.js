(() => {
  "use strict";

  const modal = document.getElementById("avisModal");
  const titleEl = document.getElementById("avisModalTitle");
  const contentEl = document.getElementById("avisModalContent");

  function openModal(title, content){
    if (!modal) return;
    titleEl.textContent = title || "Aperçu";
    contentEl.textContent = content || "";
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
      const card = previewBtn.closest(".az-avis-item");
      const t = card?.dataset?.title || "";
      const c = card?.dataset?.content || "";
      openModal(t, c);
      return;
    }

    // close modal
    if (e.target.matches("[data-close]")){
      closeModal();
      return;
    }

    // confirm delete
    const del = e.target.closest(".az-btn-danger-soft");
    if (del && del.getAttribute("href") && del.getAttribute("href").includes("avis")){
      const ok = confirm("Supprimer cet avis ?");
      if (!ok) e.preventDefault();
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
