document.addEventListener('DOMContentLoaded', function() {
    const photoInput = document.querySelector('input[type="file"]');
    const photoPreview = document.getElementById('photoPreview');
    const form = document.querySelector('.az-eleve-form');
    const saveBtn = document.getElementById('saveBtn');

    // 1. Prévisualisation de la photo
    if (photoInput && photoPreview) {
        photoInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Si c'est une image, on l'affiche
                    if (photoPreview.tagName === 'IMG') {
                        photoPreview.src = e.target.result;
                    } else {
                        // Si c'est le placeholder (div), on le remplace par une image
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.id = 'photoPreview';
                        photoPreview.parentNode.replaceChild(img, photoPreview);
                    }
                }
                reader.readAsDataURL(file);
            }
        });
    }

    // 2. Animation du bouton de sauvegarde
    if (form) {
        form.addEventListener('submit', function() {
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';
            }
        });
    }

    // 3. Gestion du mode sombre (Optionnel : bascule manuelle si besoin)
    // Vous pouvez ajouter un bouton pour tester : <button onclick="document.body.classList.toggle('dark-mode')">🌙</button>
    
    // 4. Validation basique des champs requis
    const requiredFields = form.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            if (!this.value) {
                this.style.borderColor = 'var(--az-danger)';
            } else {
                this.style.borderColor = 'var(--az-border)';
            }
        });
    });

    // 5. Effet d'entrée fluide
    const card = document.querySelector('.az-eleve-card');
    if (card) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.6s ease-out';
        
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100);
    }
});
