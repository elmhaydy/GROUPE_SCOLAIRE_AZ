/* =========================================================
   AZ — Password Change JS
   - show/hide password
   - strength meter (simple)
   - confirm match hint
   ========================================================= */

(function(){
  const pw1 = document.getElementById("pw1");
  const pw2 = document.getElementById("pw2");
  const bar = document.getElementById("pwBar");
  const meterText = document.getElementById("pwMeterText");
  const matchHint = document.getElementById("pwMatchHint");
  const rules = document.getElementById("pwRules");

  // ---- Toggle eyes
  document.querySelectorAll("[data-eye]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-eye");
      const input = document.getElementById(id);
      if (!input) return;
      const isPw = input.getAttribute("type") === "password";
      input.setAttribute("type", isPw ? "text" : "password");

      const ico = btn.querySelector("i");
      if (ico){
        ico.classList.toggle("fa-eye", !isPw);
        ico.classList.toggle("fa-eye-slash", isPw);
      }
    });
  });

  function setRule(ruleKey, ok){
    if (!rules) return;
    const li = rules.querySelector(`[data-rule="${ruleKey}"]`);
    if (!li) return;
    li.classList.toggle("ok", !!ok);
  }

  function strength(p){
    const s = (p || "");
    let score = 0;

    const hasLen = s.length >= 8;
    const hasNum = /\d/.test(s);
    const hasLow = /[a-z]/.test(s);
    const hasUp  = /[A-Z]/.test(s);
    const hasSym = /[^A-Za-z0-9]/.test(s);

    // score
    if (s.length >= 6) score += 1;
    if (hasLen) score += 2;
    if (hasNum) score += 2;
    if (hasLow && hasUp) score += 2;
    if (hasSym) score += 1;

    // rules UI
    setRule("len", hasLen);
    setRule("num", hasNum);
    setRule("mix", hasLow && hasUp);

    // map to %
    const pct = Math.min(100, Math.max(0, Math.round((score / 8) * 100)));

    let label = "Faible";
    if (pct >= 75) label = "Fort";
    else if (pct >= 45) label = "Moyen";

    return { pct, label };
  }

  function update(){
    // meter
    if (pw1 && bar && meterText){
      const { pct, label } = strength(pw1.value);
      bar.style.width = pct + "%";
      meterText.textContent = `Force : ${pw1.value ? label : "—"}`;
    }

    // match
    if (pw1 && pw2 && matchHint){
      if (!pw2.value){
        matchHint.textContent = "—";
      } else if (pw1.value === pw2.value){
        matchHint.textContent = "✅ Les mots de passe correspondent.";
        matchHint.style.color = "";
      } else {
        matchHint.textContent = "⚠️ Les mots de passe ne correspondent pas.";
        matchHint.style.color = "color-mix(in srgb, var(--text), #ef4444 55%)";
      }
    }
  }

  if (pw1) pw1.addEventListener("input", update);
  if (pw2) pw2.addEventListener("input", update);
  update();
})();
