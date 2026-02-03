/* users_modern.js */
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    const themeIcon = themeToggle.querySelector('i');

    // Theme Management
    const applyTheme = (theme) => {
        htmlElement.setAttribute('data-theme', theme);
        localStorage.setItem('admin-theme', theme);
        
        if (theme === 'dark') {
            themeIcon.classList.replace('fa-moon', 'fa-sun');
            themeIcon.style.transform = 'rotate(360deg)';
        } else {
            themeIcon.classList.replace('fa-sun', 'fa-moon');
            themeIcon.style.transform = 'rotate(0deg)';
        }
    };

    const savedTheme = localStorage.getItem('admin-theme') || 
                      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    
    applyTheme(savedTheme);

    themeToggle.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-theme');
        applyTheme(currentTheme === 'light' ? 'dark' : 'light');
    });

    // Row Animation Delay
    const rows = document.querySelectorAll('.modern-table tbody tr');
    rows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(10px)';
        setTimeout(() => {
            row.style.transition = 'all 0.4s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, index * 50);
    });

    // Tooltip initialization (if using bootstrap or custom)
    // Add any other interactive logic here
});
/* admin/js/users/list.js
   AZ — Users list
   - Auto submit quand on change le rôle
   - Enter dans recherche => submit normal
   - (option) bouton ESC pour clear search
*/

(function(){
  const form = document.getElementById("usersFilterForm");
  if (!form) return;

  const role = document.getElementById("usersRole");
  const q = document.getElementById("usersQ");

  // Auto submit sur changement de rôle
  if (role){
    role.addEventListener("change", () => form.submit());
  }

  // ESC pour vider la recherche
  if (q){
    q.addEventListener("keydown", (e) => {
      if (e.key === "Escape"){
        q.value = "";
        form.submit();
      }
    });
  }
})();
