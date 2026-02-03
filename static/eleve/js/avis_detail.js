/* =========================================================
   AZ — AVIS DETAIL JS
   - Copy content
   ========================================================= */
(function(){
  const btn = document.getElementById("copyAvis");
  if(!btn) return;

  // On copie titre + contenu (texte)
  btn.addEventListener("click", async () => {
    const title = document.querySelector(".a-d-title h3")?.innerText || "";
    const body = document.querySelector(".a-d-body")?.innerText || "";
    const text = `${title}\n\n${body}`.trim();

    try{
      await navigator.clipboard.writeText(text);
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Copié';
      setTimeout(() => {
        btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copier';
      }, 1200);
    }catch(e){
      alert("Impossible de copier automatiquement. Sélectionne le texte et copie manuellement.");
    }
  });
})();
