/**
 * AZ GROUPS - Espace Prof
 * Profile Functionalities
 */

document.addEventListener('DOMContentLoaded', () => {
    const togglePwdBtn = document.getElementById('togglePwd');
    const pwdInputs = document.querySelectorAll('input[type="password"]');

    // --- Toggle Password Visibility ---
    if (togglePwdBtn) {
        togglePwdBtn.addEventListener('click', () => {
            const isPassword = pwdInputs[0].type === 'password';
            
            pwdInputs.forEach(input => {
                input.type = isPassword ? 'text' : 'password';
            });

            // Update button icon and text
            const icon = togglePwdBtn.querySelector('i');
            if (isPassword) {
                icon.className = 'fa-solid fa-eye-slash';
            } else {
                icon.className = 'fa-solid fa-eye';
            }
        });
    }

    // --- Form Validation Feedback (Visual Only) ---
    const forms = document.querySelectorAll('.azp-form');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const btn = form.querySelector('button[type="submit"]');
            if (btn) {
                btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Traitement...';
                btn.style.opacity = '0.7';
                btn.style.pointerEvents = 'none';
            }
        });
    });

    // --- Animation on Load ---
    const animateElements = () => {
        const elements = document.querySelectorAll('.azp-hero, .azp-card');
        elements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            
            setTimeout(() => {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, 100 * index);
        });
    };

    animateElements();
});
