/**
 * AZ GROUPS - Espace Prof
 * Interactive Functionalities
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const body = document.body;
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const overlay = document.getElementById('azOverlay');
    const userMenuToggle = document.getElementById('userMenuToggle');
    const userMenu = document.getElementById('userMenu');
    const themeToggle = document.getElementById('azThemeToggleDropdown');
    const themeIcon = document.getElementById('azThemeIconDropdown');
    const themeLabel = document.getElementById('azThemeLabelDropdown');
    const navDropBtns = document.querySelectorAll('.az-nav-drop-btn');
    const alertCloseBtns = document.querySelectorAll('.az-alert-close');

    // --- Sidebar Toggle ---
    const toggleSidebar = () => {
        if (window.innerWidth > 1024) {
            body.classList.toggle('sidebar-collapsed');
        } else {
            body.classList.toggle('sidebar-open');
        }
    };

    if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
    if (overlay) overlay.addEventListener('click', () => body.classList.remove('sidebar-open'));

    // --- User Menu Dropdown ---
    if (userMenuToggle && userMenu) {
        userMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            userMenu.classList.toggle('show');
        });

        document.addEventListener('click', (e) => {
            if (!userMenu.contains(e.target) && !userMenuToggle.contains(e.target)) {
                userMenu.classList.remove('show');
            }
        });
    }

    // --- Theme Management ---
    const setTheme = (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('az-theme', theme);
        updateThemeUI(theme);
    };

    const updateThemeUI = (theme) => {
        if (!themeIcon || !themeLabel) return;
        
        if (theme === 'light') {
            themeIcon.className = 'fas fa-sun';
            themeLabel.textContent = 'Mode clair';
        } else {
            themeIcon.className = 'fas fa-moon';
            themeLabel.textContent = 'Mode sombre';
        }
    };

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        });
    }

    // Initialize UI based on current theme
    const savedTheme = localStorage.getItem('az-theme') || 'dark';
    updateThemeUI(savedTheme);

    // --- Navigation Dropdowns ---
    navDropBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const parent = btn.closest('.az-nav-drop');
            const isOpen = parent.getAttribute('data-open') === 'true';
            parent.setAttribute('data-open', !isOpen);
        });
    });

    // --- Alert Dismissal ---
    alertCloseBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const alert = btn.closest('.az-alert');
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 300);
        });
    });

    // --- Responsive Handling ---
    window.addEventListener('resize', () => {
        if (window.innerWidth > 1024) {
            body.classList.remove('sidebar-open');
        }
    });
});
