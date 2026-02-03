(function () {
  const sel = document.getElementById("groupe");
  if (!sel) return;
  sel.addEventListener("change", () => {
    const form = sel.closest("form");
    if (form) form.submit();
  });
})();
