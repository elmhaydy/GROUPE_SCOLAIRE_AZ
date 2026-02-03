/* =========================================================
   AZ — Notes Saisie PRATIQUE
   - Recherche live
   - Entrée/↓ next, ↑ prev
   - Auto clamp 0..max, virgule OK
   - Mini boutons (— / 0 / Max)
   - Compteur modifs + beforeunload
   ========================================================= */

(function(){
  const form = document.getElementById("notesForm");
  const grid = document.getElementById("notesGrid");
  const search = document.getElementById("notesSearch");
  const countBadge = document.getElementById("countBadge");
  const btnFocusEmpty = document.getElementById("btnFocusEmpty");
  const btnSetZero = document.getElementById("btnSetZero");
  const btnSetMax = document.getElementById("btnSetMax");
  const btnClearAll = document.getElementById("btnClearAll");
  const saveBtn = document.getElementById("saveBtn");

  if(!form || !grid) return;

  const NOTE_MAX = (window.AZ_NOTES_SAISIE && Number(window.AZ_NOTES_SAISIE.NOTE_MAX)) || 20;

  const cards = Array.from(grid.querySelectorAll(".az-note-card"));
  const inputs = cards.map(c => c.querySelector("input.az-note")).filter(Boolean);

  let dirty = false;

  function normalize(v){
    return String(v ?? "").trim().replace(",", ".");
  }

  function parseNote(v){
    const s = normalize(v);
    if(s === "") return null;
    const n = Number(s);
    if(Number.isNaN(n)) return NaN;
    return n;
  }

  function clamp(n){
    if(n < 0) return 0;
    if(n > NOTE_MAX) return NOTE_MAX;
    return n;
  }

  function setError(input, msg){
    const card = input.closest(".az-note-card");
    const err = card ? card.querySelector(".az-note-error") : null;
    if(err) err.textContent = msg || "";
    input.classList.toggle("is-invalid", !!msg);
  }

  function validate(input, soft=false){
    const val = input.value;
    if(normalize(val) === ""){
      setError(input, "");
      return true;
    }
    const n = parseNote(val);
    if(Number.isNaN(n)){
      setError(input, "Note invalide.");
      return false;
    }
    if(n < 0 || n > NOTE_MAX){
      setError(input, `0 à ${NOTE_MAX} seulement.`);
      return soft ? true : false;
    }
    setError(input, "");
    return true;
  }

  function updateDirtyCount(){
    let changed = 0;
    inputs.forEach(i => {
      const prev = normalize(i.dataset.prev || "");
      const now = normalize(i.value || "");
      if(prev !== now) changed++;
    });
    if(countBadge){
      countBadge.innerHTML = `<i class="fa-solid fa-pen"></i> ${changed} modifiée(s)`;
    }
    dirty = changed > 0;
  }

  function focusFirstEmpty(){
    const empty = inputs.find(i => normalize(i.value) === "");
    (empty || inputs[0])?.focus();
  }

  // ===== Recherche live =====
  if(search){
    search.addEventListener("input", () => {
      const q = normalize(search.value).toLowerCase();
      cards.forEach(card => {
        const hay = (card.dataset.search || "").toLowerCase();
        const show = !q || hay.includes(q);
        card.style.display = show ? "" : "none";
      });
    });
  }

  // ===== Mini boutons par card =====
  grid.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-mini]");
    if(!btn) return;

    const card = btn.closest(".az-note-card");
    const input = card?.querySelector("input.az-note");
    if(!input) return;

    const action = btn.dataset.mini;
    if(action === "clear") input.value = "";
    if(action === "zero") input.value = "0";
    if(action === "max") input.value = String(NOTE_MAX);

    validate(input, true);
    updateDirtyCount();
    input.focus();
  });

  // ===== Navigation clavier =====
  function visibleInputs(){
    return inputs.filter(i => i.closest(".az-note-card")?.style.display !== "none");
  }

  function focusNext(current, dir){
    const list = visibleInputs();
    const idx = list.indexOf(current);
    if(idx === -1) return;

    const next = list[idx + dir];
    if(next) next.focus();
  }

  inputs.forEach((inp) => {
    inp.addEventListener("input", () => {
      validate(inp, true);
      updateDirtyCount();
    });

    inp.addEventListener("blur", () => {
      const n = parseNote(inp.value);
      if(n === null) return;
      if(Number.isNaN(n)) return;

      inp.value = String(Math.round(clamp(n) * 100) / 100);
      validate(inp, false);
      updateDirtyCount();
    });

    inp.addEventListener("keydown", (ev) => {
      if(ev.key === "Enter" || ev.key === "ArrowDown"){
        ev.preventDefault();
        focusNext(inp, +1);
      }
      if(ev.key === "ArrowUp"){
        ev.preventDefault();
        focusNext(inp, -1);
      }
    });
  });

  // ===== Boutons globaux =====
  btnFocusEmpty?.addEventListener("click", focusFirstEmpty);

  btnSetZero?.addEventListener("click", () => {
    visibleInputs().forEach(i => { if(normalize(i.value)==="") i.value="0"; });
    visibleInputs().forEach(i => validate(i, true));
    updateDirtyCount();
  });

  btnSetMax?.addEventListener("click", () => {
    visibleInputs().forEach(i => { if(normalize(i.value)==="") i.value=String(NOTE_MAX); });
    visibleInputs().forEach(i => validate(i, true));
    updateDirtyCount();
  });

  btnClearAll?.addEventListener("click", () => {
    visibleInputs().forEach(i => { i.value=""; validate(i, true); });
    updateDirtyCount();
    focusFirstEmpty();
  });

  // ===== Alerte quitter =====
  window.addEventListener("beforeunload", (e) => {
    if(!dirty) return;
    e.preventDefault();
    e.returnValue = "";
  });

  // ===== Submit =====
  form.addEventListener("submit", (e) => {
    let ok = true;
    visibleInputs().forEach(i => { if(!validate(i, false)) ok = false; });
    if(!ok){
      e.preventDefault();
      (form.querySelector("input.is-invalid") || visibleInputs()[0])?.focus();
      return;
    }
    if(saveBtn){
      saveBtn.disabled = true;
    }
  });

  // Init
  updateDirtyCount();
  focusFirstEmpty();

})();
