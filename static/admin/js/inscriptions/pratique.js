(function () {
  "use strict";

  const form = document.getElementById("inscriptionFlexibleForm");
  if (!form) return;

  const parentsContainer = document.getElementById("parentsContainer");
  const elevesContainer = document.getElementById("elevesContainer");
  const addParentBtn = document.getElementById("addParentBtn");
  const addEleveBtn = document.getElementById("addEleveBtn");
  const parentsJsonInput = document.getElementById("id_parents_json");
  const elevesJsonInput = document.getElementById("id_eleves_json");
  const saveBtn = document.getElementById("saveBtn");

  const parentTpl = document.getElementById("parentCardTemplate");
  const eleveTpl = document.getElementById("eleveCardTemplate");

  const apiUrl = window.AZ_GROUPES_API || "";
  const annees = Array.isArray(window.AZ_ANNEES) ? window.AZ_ANNEES : [];

  let parentCounter = 0;
  let eleveCounter = 0;

  function uid(prefix) {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function refreshParentIndexes() {
    [...parentsContainer.querySelectorAll(".parent-card")].forEach((card, idx) => {
      const span = card.querySelector(".parent-index");
      if (span) span.textContent = idx + 1;
    });
  }

  function refreshEleveIndexes() {
    [...elevesContainer.querySelectorAll(".eleve-card")].forEach((card, idx) => {
      const span = card.querySelector(".eleve-index");
      if (span) span.textContent = idx + 1;
    });
  }

  function getParentsData() {
    return [...parentsContainer.querySelectorAll(".parent-card")].map(card => ({
      temp_id: card.dataset.parentId,
      nom: card.querySelector(".parent-nom")?.value?.trim() || "",
      prenom: card.querySelector(".parent-prenom")?.value?.trim() || "",
      telephone: card.querySelector(".parent-telephone")?.value?.trim() || "",
      email: card.querySelector(".parent-email")?.value?.trim() || "",
      adresse: card.querySelector(".parent-adresse")?.value?.trim() || "",
      lien: card.querySelector(".parent-lien")?.value || "TUTEUR"
    }));
  }

  function refreshParentCheckboxes() {
    const parents = getParentsData();

    document.querySelectorAll(".eleve-parents-box").forEach(box => {
      const checked = new Set(
        [...box.querySelectorAll('input[type="checkbox"]:checked')].map(x => x.value)
      );

      box.innerHTML = "";

      if (!parents.length) {
        box.innerHTML = '<div class="az-mini-empty">Ajoute d’abord un parent.</div>';
        return;
      }

      parents.forEach((p, idx) => {
        const id = p.temp_id;
        const label = `${p.prenom || "Parent"} ${p.nom || idx + 1} (${p.lien || "TUTEUR"})`;

        const row = document.createElement("label");
        row.className = "az-check-row";
        row.innerHTML = `
          <input type="checkbox" value="${id}">
          <span>${label}</span>
        `;

        const input = row.querySelector("input");
        if (checked.has(id)) input.checked = true;

        box.appendChild(row);
      });
    });
  }

  function buildAnneesOptions(selectEl) {
    selectEl.innerHTML = '<option value="">— Choisir —</option>';
    annees.forEach(a => {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = a.nom;
      selectEl.appendChild(opt);
    });
  }

  async function loadGroupesForEleve(anneeSelect, groupeSelect) {
    const anneeId = anneeSelect.value;
    groupeSelect.innerHTML = '<option value="">Chargement...</option>';

    if (!anneeId) {
      groupeSelect.innerHTML = '<option value="">— Choisir une année d\'abord —</option>';
      return;
    }

    try {
      const res = await fetch(`${apiUrl}?annee_id=${encodeURIComponent(anneeId)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      });
      if (!res.ok) throw new Error("HTTP " + res.status);

      const data = await res.json();
      const results = Array.isArray(data.results) ? data.results : [];

      groupeSelect.innerHTML = '<option value="">— Choisir un groupe —</option>';
      results.forEach(item => {
        const opt = document.createElement("option");
        opt.value = item.id;
        opt.textContent = item.label || item.nom || `Groupe #${item.id}`;
        groupeSelect.appendChild(opt);
      });

    } catch (e) {
      console.error(e);
      groupeSelect.innerHTML = '<option value="">Erreur chargement</option>';
    }
  }

  function addParentCard(defaults = {}) {
    parentCounter += 1;

    const node = parentTpl.content.firstElementChild.cloneNode(true);
    const tempId = defaults.temp_id || uid("parent");
    node.dataset.parentId = tempId;

    node.querySelector(".parent-nom").value = defaults.nom || "";
    node.querySelector(".parent-prenom").value = defaults.prenom || "";
    node.querySelector(".parent-telephone").value = defaults.telephone || "";
    node.querySelector(".parent-email").value = defaults.email || "";
    node.querySelector(".parent-adresse").value = defaults.adresse || "";
    node.querySelector(".parent-lien").value = defaults.lien || "TUTEUR";

    node.querySelector(".remove-parent-btn").addEventListener("click", () => {
      node.remove();
      refreshParentIndexes();
      refreshParentCheckboxes();
    });

    node.querySelectorAll("input, select").forEach(el => {
      el.addEventListener("input", refreshParentCheckboxes);
      el.addEventListener("change", refreshParentCheckboxes);
    });

    parentsContainer.appendChild(node);
    refreshParentIndexes();
    refreshParentCheckboxes();
  }

  function addEleveCard(defaults = {}) {
    eleveCounter += 1;

    const node = eleveTpl.content.firstElementChild.cloneNode(true);
    const tempId = defaults.temp_id || uid("eleve");
    node.dataset.eleveId = tempId;

    const anneeSelect = node.querySelector(".eleve-annee");
    const groupeSelect = node.querySelector(".eleve-groupe");

    buildAnneesOptions(anneeSelect);

    node.querySelector(".eleve-nom").value = defaults.nom || "";
    node.querySelector(".eleve-prenom").value = defaults.prenom || "";
    node.querySelector(".eleve-sexe").value = defaults.sexe || "";
    node.querySelector(".eleve-date-naissance").value = defaults.date_naissance || "";
    node.querySelector(".eleve-lieu-naissance").value = defaults.lieu_naissance || "";
    node.querySelector(".eleve-telephone").value = defaults.telephone || "";
    node.querySelector(".eleve-adresse").value = defaults.adresse || "";
    node.querySelector(".eleve-dernier-etablissement").value = defaults.dernier_etablissement || "";
    node.querySelector(".eleve-statut").value = defaults.statut || "VALIDEE";

    if (annees.length === 1 && !defaults.annee_id) {
      anneeSelect.value = String(annees[0].id);
      loadGroupesForEleve(anneeSelect, groupeSelect);
    }

    if (defaults.annee_id) {
      anneeSelect.value = String(defaults.annee_id);
      loadGroupesForEleve(anneeSelect, groupeSelect).then(() => {
        if (defaults.groupe_id) groupeSelect.value = String(defaults.groupe_id);
      });
    }

    anneeSelect.addEventListener("change", () => loadGroupesForEleve(anneeSelect, groupeSelect));

    node.querySelector(".remove-eleve-btn").addEventListener("click", () => {
      node.remove();
      refreshEleveIndexes();
    });

    elevesContainer.appendChild(node);
    refreshEleveIndexes();
    refreshParentCheckboxes();
  }

  function validateBeforeSubmit() {
    const parents = getParentsData();
    const eleveCards = [...elevesContainer.querySelectorAll(".eleve-card")];

    if (!parents.length) {
      alert("Ajoute au moins un parent.");
      return false;
    }

    if (!eleveCards.length) {
      alert("Ajoute au moins un élève.");
      return false;
    }

    return true;
  }

  function serializeForm() {
    const parents = getParentsData();

    const eleves = [...elevesContainer.querySelectorAll(".eleve-card")].map((card, idx) => {
      const photoInput = card.querySelector(".eleve-photo");
      if (photoInput && !photoInput.name) {
        photoInput.name = `eleve_photo_${idx + 1}`;
      }

      const parentIds = [...card.querySelectorAll('.eleve-parents-box input[type="checkbox"]:checked')]
        .map(x => x.value);

      return {
        temp_id: card.dataset.eleveId,
        nom: card.querySelector(".eleve-nom")?.value?.trim() || "",
        prenom: card.querySelector(".eleve-prenom")?.value?.trim() || "",
        sexe: card.querySelector(".eleve-sexe")?.value || "",
        date_naissance: card.querySelector(".eleve-date-naissance")?.value || "",
        lieu_naissance: card.querySelector(".eleve-lieu-naissance")?.value?.trim() || "",
        telephone: card.querySelector(".eleve-telephone")?.value?.trim() || "",
        adresse: card.querySelector(".eleve-adresse")?.value?.trim() || "",
        dernier_etablissement: card.querySelector(".eleve-dernier-etablissement")?.value?.trim() || "",
        annee_id: card.querySelector(".eleve-annee")?.value || "",
        groupe_id: card.querySelector(".eleve-groupe")?.value || "",
        statut: card.querySelector(".eleve-statut")?.value || "VALIDEE",
        parent_ids: parentIds,
        photo_field: photoInput?.name || ""
      };
    });

    parentsJsonInput.value = JSON.stringify(parents);
    elevesJsonInput.value = JSON.stringify(eleves);
  }

  addParentBtn.addEventListener("click", () => addParentCard());
  addEleveBtn.addEventListener("click", () => addEleveCard());

  form.addEventListener("submit", function (e) {
    if (!validateBeforeSubmit()) {
      e.preventDefault();
      return;
    }

    serializeForm();

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Traitement...';
  });

  addParentCard();
  addEleveCard();
})();