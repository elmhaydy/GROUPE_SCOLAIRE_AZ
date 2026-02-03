document.addEventListener('DOMContentLoaded', function() {
    // Animation d'entrée des cartes
    const cards = document.querySelectorAll('.az-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 150 * (index + 1));
    });

    // Confirmation de suppression
    const deleteBtn = document.querySelector('.az-btn-delete');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function(e) {
            if (!confirm('Voulez-vous vraiment supprimer ce parent ? Cette action est définitive.')) {
                e.preventDefault();
            }
        });
    }

    // Animation au survol des enfants
    const childItems = document.querySelectorAll('.az-child-item');
    childItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            const icon = item.querySelector('.az-child-link i');
            if (icon) icon.style.transform = 'translateX(3px)';
        });
        item.addEventListener('mouseleave', () => {
            const icon = item.querySelector('.az-child-link i');
            if (icon) icon.style.transform = 'translateX(0)';
        });
    });
});
