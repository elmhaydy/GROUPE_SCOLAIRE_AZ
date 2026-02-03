/* =========================================================
   AZ — AVIS (LIST) JS
   - Search filter
   ========================================================= */
(function(){
  const input = document.getElementById("avisSearch");
  const clear = document.getElementById("avisClear");
  const cards = Array.from(document.querySelectorAll(".a-card"));
  const empty = document.getElementById("avisEmpty");

  function normalize(str){
    return (str || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function apply(){
    const q = normalize(input ? input.value : "");
    let shown = 0;

    cards.forEach(c => {
      const hay = normalize(c.getAttribute("data-haystack") || c.textContent);
      const ok = !q || hay.includes(q);
      c.style.display = ok ? "" : "none";
      if(ok) shown++;
    });

    if (empty) empty.style.display = shown === 0 ? "" : "none";
  }

  if (input) input.addEventListener("input", apply);
  if (clear) clear.addEventListener("click", () => {
    if (input) input.value = "";
    apply();
    input && input.focus();
  });

  apply();
})();
