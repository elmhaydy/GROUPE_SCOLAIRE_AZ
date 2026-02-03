/* role_form_modern.js */
document.addEventListener('DOMContentLoaded', function() {
    const checkboxes = document.querySelectorAll('.perm-item input[type="checkbox"]');

    // Initial state for styling
    checkboxes.forEach(cb => {
        if (cb.checked) {
            cb.closest('.perm-item').classList.add('is-checked');
        }
    });

    // Toggle styling on change
    checkboxes.forEach(cb => {
        cb.addEventListener('change', function() {
            if (this.checked) {
                this.closest('.perm-item').classList.add('is-checked');
            } else {
                this.closest('.perm-item').classList.remove('is-checked');
            }
        });
    });

    // Optional: Add "Select All" functionality for each model
    const modelBoxes = document.querySelectorAll('.model-box');
    modelBoxes.forEach(box => {
        const title = box.querySelector('.model-name');
        const boxCheckboxes = box.querySelectorAll('input[type="checkbox"]');
        
        const selectAllBtn = document.createElement('span');
        selectAllBtn.innerHTML = '<i class="fas fa-check-double"></i>';
        selectAllBtn.style.cursor = 'pointer';
        selectAllBtn.style.fontSize = '0.8rem';
        selectAllBtn.style.color = 'var(--primary)';
        selectAllBtn.title = 'Tout sélectionner';
        
        title.appendChild(selectAllBtn);
        
        selectAllBtn.addEventListener('click', () => {
            const allChecked = Array.from(boxCheckboxes).every(cb => cb.checked);
            boxCheckboxes.forEach(cb => {
                cb.checked = !allChecked;
                if (cb.checked) {
                    cb.closest('.perm-item').classList.add('is-checked');
                } else {
                    cb.closest('.perm-item').classList.remove('is-checked');
                }
            });
        });
    });
});
