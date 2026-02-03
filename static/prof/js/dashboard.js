/**
 * AZ GROUPS - Espace Prof
 * Dashboard Functionalities
 */

document.addEventListener('DOMContentLoaded', () => {
    const gSearch = document.getElementById('gSearch');
    const gGrid = document.getElementById('gGrid');
    const gCards = document.querySelectorAll('.g-card');
    const gCount = document.getElementById('gCount');

    // --- Group Search Functionality ---
    if (gSearch && gGrid) {
        gSearch.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase().trim();
            let visibleCount = 0;

            gCards.forEach(card => {
                const searchData = card.getAttribute('data-search') || '';
                if (searchData.includes(term)) {
                    card.style.display = 'flex';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            // Update count display if it exists
            if (gCount) {
                gCount.textContent = term ? `(${visibleCount} trouvé${visibleCount > 1 ? 's' : ''})` : '';
            }

            // Handle empty search results
            const existingEmpty = gGrid.querySelector('.search-empty-state');
            if (visibleCount === 0 && term !== '') {
                if (!existingEmpty) {
                    const emptyDiv = document.createElement('div');
                    emptyDiv.className = 'empty-state search-empty-state';
                    emptyDiv.innerHTML = `
                        <i class="fa-solid fa-magnifying-glass"></i>
                        <div>
                            <div class="empty-title">Aucun résultat</div>
                            <div class="muted">Aucun groupe ne correspond à "${term}"</div>
                        </div>
                    `;
                    gGrid.appendChild(emptyDiv);
                }
            } else if (existingEmpty) {
                existingEmpty.remove();
            }
        });
    }

    // --- Animation on Load ---
    const animateCards = () => {
        const cards = document.querySelectorAll('.azp-card, .kpi-card, .g-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50 * index);
        });
    };

    animateCards();
});
