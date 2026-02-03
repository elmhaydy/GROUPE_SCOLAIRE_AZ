// static/admin/js/depenses/form.js
(() => {
  const form = document.getElementById("depenseForm");
  if (!form) return;

  const dz = document.getElementById("depDropzone");
  const meta = document.getElementById("fileMeta");
  const fileName = document.getElementById("fileName");
  const preview = document.getElementById("filePreview");
  const btnClear = document.getElementById("btnClearFile");

  // Django rend le input file via {{ form.justificatif }}
  const inputFile = dz ? dz.querySelector('input[type="file"]') : null;
  if (!dz || !inputFile) return;

  const setUIEmpty = () => {
    if (meta) meta.hidden = true;
    if (preview) {
      preview.hidden = true;
      preview.innerHTML = "";
    }
    if (fileName) fileName.textContent = "—";
  };

  const renderPreview = (file) => {
    if (!preview) return;

    preview.innerHTML = "";
    preview.hidden = false;

    const type = (file.type || "").toLowerCase();

    // Image
    if (type.startsWith("image/")) {
      const img = document.createElement("img");
      img.alt = "Aperçu justificatif";
      img.src = URL.createObjectURL(file);
      preview.appendChild(img);
      return;
    }

    // PDF
    if (type === "application/pdf") {
      const iframe = document.createElement("iframe");
      iframe.title = "Aperçu PDF";
      iframe.src = URL.createObjectURL(file);
      preview.appendChild(iframe);
      return;
    }

    // Other
    preview.innerHTML = `<div class="az-muted"><b>Fichier sélectionné</b> (pas d’aperçu pour ce type).</div>`;
  };

  const updateFromInput = () => {
    const file = inputFile.files && inputFile.files[0] ? inputFile.files[0] : null;

    if (!file) {
      setUIEmpty();
      return;
    }

    if (fileName) fileName.textContent = file.name;
    if (meta) meta.hidden = false;

    renderPreview(file);
  };

  // Click dropzone => open file picker (déjà géré par input overlay)
  // Drag events
  ["dragenter", "dragover"].forEach(ev => {
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dz.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach(ev => {
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dz.classList.remove("is-dragover");
    });
  });

  dz.addEventListener("drop", (e) => {
    const files = e.dataTransfer && e.dataTransfer.files ? e.dataTransfer.files : null;
    if (!files || !files.length) return;

    // set files to input
    inputFile.files = files;
    updateFromInput();
  });

  inputFile.addEventListener("change", updateFromInput);

  if (btnClear) {
    btnClear.addEventListener("click", () => {
      inputFile.value = "";
      setUIEmpty();
    });
  }

  // init state
  updateFromInput();
})();
