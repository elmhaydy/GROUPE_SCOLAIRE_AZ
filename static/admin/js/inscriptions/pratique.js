/* =========================================================
   AZ — Inscriptions Pratique — JS (FINAL)
   - Recharge les groupes selon l'année choisie
   - API: window.AZ_GROUPES_API (injectée dans template)
   - Compatible réponses API:
     A) { results: [{id, label}] }
     B) [{id, nom}] / [{id, label}]
   ========================================================= */

(function () {
  "use strict";

  // ---------- Elements ----------
  const annee = document.getElementById("id_annee") || document.querySelector('select[name="annee"]');
  const groupe = document.getElementById("id_groupe") || document.querySelector('select[name="groupe"]');
  const help = document.getElementById("groupeHelp");
  const form = document.querySelector(".az-main-form");
  const saveBtn = document.getElementById("saveBtn");

  const apiUrl = window.AZ_GROUPES_API || "";
  if (!annee || !groupe || !apiUrl) return;

  // ---------- Helpers UI ----------
  function setHelp(txt) {
    if (!help) return;
    help.textContent = txt;
  }

  function setHelpHtml(html) {
    if (!help) return;
    help.innerHTML = html;
  }

  function setDisabled(disabled) {
    groupe.disabled = disabled;
    groupe.style.opacity = disabled ? "0.75" : "1";
  }

  function resetGroupes(placeholder = "— Choisir un groupe —") {
    const current = groupe.value; // garder si possible
    groupe.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = placeholder;
    groupe.appendChild(opt0);

    return current;
  }

  // ---------- Normalisation API ----------
  function normalizeItems(payload) {
    // Payload possible:
    // 1) {results: [{id,label}]}
    // 2) [{id,nom}] ou [{id,label}]
    const arr = Array.isArray(payload) ? payload : (payload && payload.results) ? payload.results : [];
    return arr.map((x) => ({
      id: x.id,
      label: x.label || x.nom || x.name || `Groupe #${x.id}`,
    }));
  }

  // ---------- Loader ----------
  async function loadGroupes() {
    const anneeId = annee.value;
    const prev = resetGroupes("Chargement...");
    setDisabled(true);

    if (!anneeId) {
      resetGroupes("— Choisir une année d'abord —");
      setHelp("Choisis une année pour charger les groupes.");
      return;
    }

    try {
      setHelpHtml('<i class="fas fa-spinner fa-spin"></i> Chargement des groupes...');

      const res = await fetch(`${apiUrl}?annee_id=${encodeURIComponent(anneeId)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!res.ok) throw new Error("HTTP " + res.status);

      const data = await res.json();
      const items = normalizeItems(data);

      resetGroupes(items.length ? "— Choisir un groupe —" : "Aucun groupe disponible");

      for (const item of items) {
        const opt = document.createElement("option");
        opt.value = item.id;
        opt.textContent = item.label;

        if (prev && String(prev) === String(item.id)) opt.selected = true;
        groupe.appendChild(opt);
      }

      setDisabled(false);
      setHelp(items.length ? "Le groupe dépend de l’année sélectionnée." : "Aucun groupe trouvé pour cette année.");
    } catch (e) {
      console.error("Erreur chargement groupes:", e);
      resetGroupes("Erreur de chargement");
      setDisabled(true);
      setHelp("Impossible de charger les groupes. Vérifie l’API / réseau.");
    }
  }

  // ---------- Submit UX ----------
  if (form) {
    form.addEventListener("submit", function () {
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Traitement en cours...';
      }
    });
  }

  // ---------- Focus 1er champ ----------
  const firstInput = document.querySelector('input[name="eleve_nom"]');
  if (firstInput) firstInput.focus();

  // ---------- Validation visuelle (simple) ----------
  if (form) {
    const inputs = form.querySelectorAll("input, select, textarea");
    inputs.forEach((input) => {
      input.addEventListener("blur", function () {
        if (this.hasAttribute("required") && !this.value) {
          this.style.borderColor = "var(--az-danger)";
        } else {
          this.style.borderColor = "";
        }
      });
    });
  }

  // ---------- Preview Photo Élève ----------
  (function () {
    const input = document.querySelector('input[type="file"][name="eleve_photo"]');
    const box = document.getElementById("photoPreview");
    const img = document.getElementById("photoPreviewImg");
    const reset = document.getElementById("photoReset");

    if (!input || !box || !img || !reset) return;

    let currentUrl = null;

    input.addEventListener("change", () => {
      const f = input.files && input.files[0];

      // cleanup ancienne url
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
        currentUrl = null;
      }

      if (!f) {
        box.style.display = "none";
        img.src = "";
        return;
      }

      currentUrl = URL.createObjectURL(f);
      img.src = currentUrl;
      box.style.display = "flex";
      box.style.gap = "10px";
      box.style.alignItems = "center";
    });

    reset.addEventListener("click", () => {
      input.value = "";
      box.style.display = "none";
      img.src = "";
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
        currentUrl = null;
      }
    });
  })();

  // ---------- Events ----------
  document.addEventListener("DOMContentLoaded", loadGroupes);
  annee.addEventListener("change", loadGroupes);
})();
