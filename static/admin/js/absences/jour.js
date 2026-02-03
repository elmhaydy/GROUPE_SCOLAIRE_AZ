/* =========================================================
   AZ — Absences du jour
   - Print
   - Auto-submit on change (date/annee/groupe)
   - Mobile labels for AZ grid table
   ========================================================= */
(function(){
  const form = document.getElementById("jourFilters");
  const btnPrint = document.getElementById("btn_print");
  const idDate = document.getElementById("id_date");
  const idAnnee = document.getElementById("id_annee");
  const idGroupe = document.getElementById("id_groupe");

  if (btnPrint) btnPrint.addEventListener("click", () => window.print());

  // Auto-submit propre (sans spam)
  let t = null;
  function smartSubmit(){
    if (!form) return;
    clearTimeout(t);
    t = setTimeout(() => form.submit(), 250);
  }

  [idDate, idAnnee, idGroupe].forEach(el => {
    if (!el) return;
    el.addEventListener("change", smartSubmit);
  });

  // Mobile labels (AZ grid table)
  const rows = document.querySelectorAll(".az-jour-table .az-tbody .az-row");
  if (!rows.length) return;

  const labels = ["Élève","Groupe","Type","Séance","Justifié","Actions"];
  rows.forEach(row => {
    const cells = row.querySelectorAll(".az-cell");
    cells.forEach((cell, i) => {
      if (!cell.hasAttribute("data-label") && labels[i]) {
        cell.setAttribute("data-label", labels[i]);
      }
    });
  });
})();
