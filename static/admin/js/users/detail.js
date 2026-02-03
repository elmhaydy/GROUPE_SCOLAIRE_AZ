/* user_details_modern.js */
document.addEventListener('DOMContentLoaded', function() {
    // Animation for info boxes
    const boxes = document.querySelectorAll('.info-box-modern');
    boxes.forEach((box, index) => {
        box.style.opacity = '0';
        box.style.transform = 'translateY(20px)';
        setTimeout(() => {
            box.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            box.style.opacity = '1';
            box.style.transform = 'translateY(0)';
        }, 100 + (index * 150));
    });

    // Hover effect for tags
    const tags = document.querySelectorAll('.tag-modern');
    tags.forEach(tag => {
        tag.addEventListener('mouseenter', () => {
            tag.style.transform = 'scale(1.05)';
            tag.style.transition = 'transform 0.2s ease';
        });
        tag.addEventListener('mouseleave', () => {
            tag.style.transform = 'scale(1)';
        });
    });

    // Confirmation for delete action
    const deleteForm = document.querySelector('form[action*="delete"]');
    if (deleteForm) {
        deleteForm.addEventListener('submit', function(e) {
            if (!confirm('Êtes-vous sûr de vouloir supprimer cet utilisateur ? Cette action est irréversible.')) {
                e.preventDefault();
            }
        });
    }
});
