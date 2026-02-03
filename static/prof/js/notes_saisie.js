/**
 * AZ GROUPS - Espace Prof
 * Advanced Notes Entry Functionalities
 */

document.addEventListener('DOMContentLoaded', () => {
    const table = document.getElementById('notesTable');
    const maxNote = parseFloat(table.getAttribute('data-max')) || 20;
    const inputs = Array.from(document.querySelectorAll('.note-input'));
    const searchInput = document.getElementById('q');
    const rows = document.querySelectorAll('.nrow');

    // --- 1. Keyboard Navigation & Validation ---
    inputs.forEach((input, index) => {
        // Highlight row on focus
        input.addEventListener('focus', () => {
            input.closest('.nrow').classList.add('active-row');
            input.select(); // Auto-select content for quick overwrite
        });

        input.addEventListener('blur', () => {
            input.closest('.nrow').classList.remove('active-row');
            validateInput(input);
        });

        input.addEventListener('keydown', (e) => {
            // Arrow Down or Enter -> Next Input
            if (e.key === 'ArrowDown' || e.key === 'Enter') {
                e.preventDefault();
                const next = inputs[index + 1];
                if (next) next.focus();
            }
            // Arrow Up -> Previous Input
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prev = inputs[index - 1];
                if (prev) prev.focus();
            }
        });

        // Real-time validation
        input.addEventListener('input', () => {
            validateInput(input);
        });
    });

    function validateInput(input) {
        const val = input.value.replace(',', '.');
        const num = parseFloat(val);
        const statusCell = input.closest('tr').querySelector('td:last-child');

        if (val === '') {
            input.classList.remove('error', 'success');
            statusCell.innerHTML = '<span class="badge warn"><i class="fa-solid fa-hourglass-half"></i> Vide</span>';
            return;
        }

        if (isNaN(num) || num < 0 || num > maxNote) {
            input.classList.add('error');
            input.classList.remove('success');
            statusCell.innerHTML = '<span class="badge error" style="color:#ef4444; background:rgba(239,68,68,0.1)"><i class="fa-solid fa-circle-xmark"></i> Invalide</span>';
        } else {
            input.classList.remove('error');
            input.classList.add('success');
            statusCell.innerHTML = '<span class="badge ok"><i class="fa-solid fa-check"></i> Saisie</span>';
        }
    }

    // --- 2. Quick Fill Actions ---
    document.querySelectorAll('[data-fill]').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.getAttribute('data-fill');
            const val = type === 'max' ? maxNote : 0;
            
            if (confirm(`Voulez-vous remplir toutes les notes vides par ${val} ?`)) {
                inputs.forEach(input => {
                    if (input.value === '') {
                        input.value = val;
                        validateInput(input);
                    }
                });
            }
        });
    });

    document.querySelector('[data-clear]').addEventListener('click', () => {
        if (confirm('Voulez-vous effacer TOUTES les notes de cette page ?')) {
            inputs.forEach(input => {
                input.value = '';
                validateInput(input);
            });
        }
    });

    // --- 3. Search/Filter ---
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase().trim();
            rows.forEach(row => {
                const text = row.getAttribute('data-search') || '';
                row.style.display = text.includes(term) ? '' : 'none';
            });
        });
    }

    // --- 4. Form Submission ---
    const form = document.querySelector('form');
    form.addEventListener('submit', (e) => {
        const hasErrors = document.querySelectorAll('.note-input.error').length > 0;
        if (hasErrors) {
            e.preventDefault();
            alert('Veuillez corriger les notes invalides avant d\'enregistrer.');
        } else {
            const btn = form.querySelector('button[type="submit"]');
            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Enregistrement...';
            btn.style.pointerEvents = 'none';
            btn.style.opacity = '0.7';
        }
    });
});
