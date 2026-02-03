// static/admin/js/depenses/list.js
(() => {
  const form = document.getElementById("depenseFilterForm");
  if (!form) return;

  const annee = form.querySelector('[name="annee"]');
  const cat = form.querySelector('[name="cat"]');
  const mois = form.querySelector('[name="mois"]');
  const dateDe = form.querySelector('[name="date_de"]');
  const dateA = form.querySelector('[name="date_a"]');
  const q = form.querySelector('[name="q"]');

  const btnThisMonth = document.getElementById("btnThisMonth");

  const submitNow = () => {
    // si date_de > date_a => swap
    if (dateDe?.value && dateA?.value && dateDe.value > dateA.value) {
      const tmp = dateDe.value;
      dateDe.value = dateA.value;
      dateA.value = tmp;
    }
    form.submit();
  };

  // Auto-submit sur select/date
  [annee, cat, mois, dateDe, dateA].forEach(el => {
    if (!el) return;
    el.addEventListener("change", () => submitNow());
  });

  // Enter dans recherche => submit normal
  if (q) {
    q.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        // laisser le submit par défaut
      }
    });
  }

  // Ce mois => date range [1er..dernier jour]
  if (btnThisMonth && dateDe && dateA) {
    btnThisMonth.addEventListener("click", () => {
      const now = new Date();
      const y = now.getFullYear();
      const m = now.getMonth(); // 0..11

      const first = new Date(y, m, 1);
      const last = new Date(y, m + 1, 0);

      const toISO = (d) => {
        const mm = String(d.getMonth() + 1).padStart(2, "0");
        const dd = String(d.getDate()).padStart(2, "0");
        return `${d.getFullYear()}-${mm}-${dd}`;
      };

      dateDe.value = toISO(first);
      dateA.value = toISO(last);

      // bonus: vider le "mois" (sinon double filtre)
      if (mois) mois.value = "";

      submitNow();
    });
  }
})();
