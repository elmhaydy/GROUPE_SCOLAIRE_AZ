/* static/admin/js/absence_prof/form.js */
(function () {
  const selEns = document.getElementById("id_enseignant");
  const selSea = document.getElementById("id_seance");
  const dateInput = document.getElementById("id_date");
  const info = document.getElementById("seance_info");
  const warn = document.getElementById("seance_warn");

  if (!selEns || !selSea) return;

  const allOptions = Array.from(selSea.querySelectorAll("option")).filter(o => o.value);

  const MAP_JOUR = { LUN: 1, MAR: 2, MER: 3, JEU: 4, VEN: 5, SAM: 6 }; // JS getDay(): 0=dimanche

  function minutesBetween(hhmm1, hhmm2) {
    const [h1, m1] = (hhmm1 || "0:0").split(":").map(Number);
    const [h2, m2] = (hhmm2 || "0:0").split(":").map(Number);
    return (h2 * 60 + m2) - (h1 * 60 + m1);
  }

  function setInfo(text) {
    if (info) info.textContent = text;
  }

  function showWarn(text) {
    if (!warn) return;
    if (!text) {
      warn.style.display = "none";
      warn.textContent = "";
      return;
    }
    warn.style.display = "block";
    warn.textContent = text;
    // petit style sans casser ton thème
    warn.style.padding = "8px 10px";
    warn.style.borderRadius = "12px";
    warn.style.border = "1px solid rgba(255,80,80,.35)";
    warn.style.background = "rgba(255,80,80,.08)";
  }

  function getSelectedOption() {
    const opt = selSea.options[selSea.selectedIndex];
    if (!opt || !opt.value) return null;
    return opt;
  }

  function updateInfoFromSelected() {
    const opt = getSelectedOption();
    if (!opt) {
      setInfo("Durée : —");
      showWarn("");
      return;
    }

    const debut = opt.dataset.debut;
    const fin = opt.dataset.fin;
    const mins = minutesBetween(debut, fin);

    if (mins <= 0) {
      setInfo("Durée : —");
    } else {
      const h = mins / 60;
      setInfo(`Durée : ${h}h (${mins} min)`);
    }

    // warning jour/date si possible
    validateDateVsSeance();
  }

  function renderSeances() {
    const ensId = selEns.value;

    selSea.innerHTML = "";

    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = ensId ? "— Choisir une séance —" : "— Choisir un prof d’abord —";
    selSea.appendChild(ph);

    if (!ensId) {
      setInfo("Durée : —");
      showWarn("");
      return;
    }

    let count = 0;
    allOptions.forEach(opt => {
      if (opt.dataset.enseignant === ensId) {
        selSea.appendChild(opt.cloneNode(true));
        count++;
      }
    });

    if (count === 0) {
      const o = document.createElement("option");
      o.value = "";
      o.textContent = "Aucune séance pour ce prof";
      selSea.appendChild(o);
    }

    selSea.value = "";
    updateInfoFromSelected();
  }

  function validateDateVsSeance() {
    const opt = getSelectedOption();
    if (!opt || !dateInput || !dateInput.value) {
      showWarn("");
      return;
    }

    const seanceJour = opt.dataset.jour; // "LUN"/"MAR"/...
    const expected = MAP_JOUR[seanceJour];
    if (!expected) {
      showWarn("");
      return;
    }

    const d = new Date(dateInput.value);
    const jsDay = d.getDay(); // 0..6
    const isoDay = jsDay === 0 ? 7 : jsDay; // 1..7

    if (isoDay !== expected) {
      showWarn("⚠️ Attention : la date choisie ne correspond pas au jour de la séance.");
    } else {
      showWarn("");
    }
  }

  selEns.addEventListener("change", renderSeances);
  selSea.addEventListener("change", updateInfoFromSelected);
  if (dateInput) dateInput.addEventListener("change", validateDateVsSeance);

  // init (si prof pré-sélectionné côté serveur)
  renderSeances();

  // si un prof est déjà sélectionné, on garde sa valeur et on re-render
  // (renderSeances reset le select séance, mais pas le prof)
  // on force juste l’info
  updateInfoFromSelected();
})();
