/* settings_modern.js */
document.addEventListener('DOMContentLoaded', function() {
    const chips = document.querySelectorAll('[data-settings-filter]');
    const cards = document.querySelectorAll('.settings-card');

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            const filter = chip.getAttribute('data-settings-filter');

            // Update active chip
            chips.forEach(c => c.classList.remove('is-active'));
            chip.classList.add('is-active');

            // Filter cards with animation
            cards.forEach(card => {
                const kind = card.getAttribute('data-kind');
                
                if (filter === 'all' || kind === filter) {
                    card.style.display = 'flex';
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'scale(1)';
                    }, 10);
                } else {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        card.style.display = 'none';
                    }, 300);
                }
            });
        });
    });

    // Initial animation for cards
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 + (index * 100));
    });
});
