document.addEventListener("DOMContentLoaded", () => {
  // =========================
  // 1) Animation des cartes (propre)
  // =========================
  const cards = Array.from(document.querySelectorAll(".az-card"));
  cards.forEach((card, i) => {
    card.classList.add("az-reveal");
    setTimeout(() => card.classList.add("is-in"), 90 + i * 90);
  });

  // =========================
  // 2) Confirmation suppression (NEBULA)
  // =========================
  const deleteBtn = document.querySelector(".az-btn-delete");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", (e) => {
      const msg =
        deleteBtn.getAttribute("data-confirm") ||
        "Êtes-vous sûr de vouloir supprimer cet élève ? Cette action est irréversible.";
      if (!window.confirm(msg)) e.preventDefault();
    });
  }

  // =========================
  // 3) Avatar hover (classe CSS)
  // =========================
  const avatarWrap = document.querySelector(".az-avatar-wrapper");
  if (avatarWrap) {
    avatarWrap.addEventListener("mouseenter", () => avatarWrap.classList.add("is-hover"));
    avatarWrap.addEventListener("mouseleave", () => avatarWrap.classList.remove("is-hover"));
  }

  // =========================
  // 4) Copier le matricule (clic)
  // cible: <span class="value highlight">MAT</span>
  // =========================
  const matriculeEl = document.querySelector(".az-card-identity .value.highlight");
  if (matriculeEl) {
    matriculeEl.style.cursor = "pointer";
    matriculeEl.title = "Cliquer pour copier";

    matriculeEl.addEventListener("click", async () => {
      const text = (matriculeEl.textContent || "").trim();
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        toast(`Matricule copié : ${text}`);
        matriculeEl.classList.add("is-copied");
        setTimeout(() => matriculeEl.classList.remove("is-copied"), 650);
      } catch {
        // fallback (vieux navigateurs)
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "fixed";
        ta.style.top = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        toast(`Matricule copié : ${text}`);
      }
    });
  }

  // =========================
  // 5) Print (si tu ajoutes un bouton)
  // =========================
  window.printProfile = () => window.print();

  // =========================
  // Toast minimal (sans lib)
  // =========================
  function toast(message) {
    let el = document.querySelector(".az-toast");
    if (!el) {
      el = document.createElement("div");
      el.className = "az-toast";
      document.body.appendChild(el);
    }

    el.textContent = message;
    el.classList.add("is-show");

    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("is-show"), 1800);
  }
});
