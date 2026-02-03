/* user_form_modern.js */
document.addEventListener('DOMContentLoaded', function() {
    const autoPasswordCheckbox = document.querySelector('input[name="auto_password"]');
    const passwordField = document.querySelector('input[name="password"]');
    const passwordWrapper = passwordField ? passwordField.closest('.field-group') : null;

    if (autoPasswordCheckbox && passwordWrapper) {
        const togglePasswordVisibility = () => {
            if (autoPasswordCheckbox.checked) {
                passwordWrapper.style.opacity = '0.4';
                passwordWrapper.style.pointerEvents = 'none';
                passwordField.required = false;
            } else {
                passwordWrapper.style.opacity = '1';
                passwordWrapper.style.pointerEvents = 'auto';
                passwordField.required = true;
            }
        };

        autoPasswordCheckbox.addEventListener('change', togglePasswordVisibility);
        togglePasswordVisibility(); // Initial state
    }

    // Add focus animation to labels
    const inputs = document.querySelectorAll('.form-grid input, .form-grid select');
    inputs.forEach(input => {
        input.addEventListener('focus', () => {
            const label = input.previousElementSibling;
            if (label && label.tagName === 'LABEL') {
                label.style.color = 'var(--primary)';
                label.style.transform = 'translateX(5px)';
                label.style.transition = 'all 0.3s ease';
            }
        });

        input.addEventListener('blur', () => {
            const label = input.previousElementSibling;
            if (label && label.tagName === 'LABEL') {
                label.style.color = 'var(--text-muted)';
                label.style.transform = 'translateX(0)';
            }
        });
    });
});
