/* admin/js/groupes/list.js
   Micro-animations + UX (optionnel)
   - hover "tilt" léger sur les lignes (desktop)
   - highlight du terme recherché (q) dans le nom du groupe & niveau
   - auto-submit sur Enter déjà ok; ici on ajoute "Reset" rapide via ESC dans input
*/

(function(){
  const root = document.documentElement;

  // 1) Tilt léger (desktop seulement)
  const supportsFinePointer = window.matchMedia && window.matchMedia("(pointer:fine)").matches;
  if (supportsFinePointer) {
    document.querySelectorAll(".az-row").forEach(row => {
      let raf = null;

      function onMove(e){
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
          const r = row.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width;   // 0..1
          const y = (e.clientY - r.top) / r.height;   // 0..1
          const rx = (0.5 - y) * 2; // -1..1
          const ry = (x - 0.5) * 2; // -1..1
          // rotation très légère
          row.style.transform = `translateY(-2px) rotateX(${rx * 1.2}deg) rotateY(${ry * 1.2}deg)`;
        });
      }

      function onLeave(){
        if (raf) cancelAnimationFrame(raf);
        row.style.transform = "";
      }

      row.addEventListener("mousemove", onMove);
      row.addEventListener("mouseleave", onLeave);
    });
  }

  // 2) Highlight terme recherché dans cellules (niveau + groupe)
  const params = new URLSearchParams(window.location.search);
  const q = (params.get("q") || "").trim();
  if (q.length >= 2) {
    const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(${esc(q)})`, "ig");

    document.querySelectorAll(".az-row .az-cell").forEach(cell => {
      // on cible surtout les cellules texte (niveau/groupe)
      const txt = cell.textContent || "";
      // ignore si cell contient déjà badge (année/capacité) ou actions (boutons)
      if (cell.querySelector(".az-actions")) return;
      if (cell.querySelector(".az-badge")) return;

      if (re.test(txt)) {
        // Safe highlight : on remplace uniquement le texte (pas de HTML existant)
        const span = document.createElement("span");
        span.innerHTML = txt.replace(re, `<mark class="az-mark">$1</mark>`);
        cell.textContent = "";
        cell.appendChild(span);
      }
    });

    // inject CSS mark (si pas dans ton global)
    if (!document.getElementById("az-mark-style")) {
      const st = document.createElement("style");
      st.id = "az-mark-style";
      st.textContent = `
        .az-mark{
          padding: 0 .2em;
          border-radius: 6px;
          background: rgba(99,102,241,.18);
          color: inherit;
        }
        html[data-theme="dark"] .az-mark{
          background: rgba(99,102,241,.28);
        }
      `;
      document.head.appendChild(st);
    }
  }

  // 3) Esc dans input recherche => reset
  const qInput = document.querySelector('input[name="q"]');
  if (qInput) {
    qInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        // reset propre
        window.location.href = window.location.pathname;
      }
    });
  }
})();
// admin/js/groupes/list.js (optionnel)
(function(){
  const q = document.querySelector('input[name="q"]');
  if (!q) return;

  // Auto-focus (si pas mobile)
  const isMobile = window.matchMedia && window.matchMedia("(max-width: 768px)").matches;
  if (!isMobile) q.focus();

  // Petit shake si user submit vide (optionnel, soft)
  const form = q.closest("form");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    if (q.value.trim() === "") return; // ok, filtrer sans q possible
  });
})();
