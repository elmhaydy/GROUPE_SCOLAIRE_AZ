/* ╔════════════════════════════════════════════════════════════════════════════╗ */
/* ║                    AZ ADMIN - SCRIPTS INTERACTIFS                          ║ */
/* ║              Administration Scolaire - Gestion du Thème & UI               ║ */
/* ╚════════════════════════════════════════════════════════════════════════════╝ */

/**
 * Classe principale pour gérer l'interface d'administration
 */
class AZAdmin {
  constructor() {
    this.theme = this.getTheme();
    this.isMobile = window.innerWidth <= 768;
    this.init();
  }

  /**
   * Initialisation de l'application
   */
  init() {
    this.setupThemeToggle();
    this.setupSidebarToggle();
    this.setupUserMenu();
    this.setupAlertClosing();
    this.setupResponsive();
    this.setupEventListeners();
  }

  /**
   * Récupère le thème sauvegardé ou utilise le thème par défaut
   */
  getTheme() {
    try {
      const saved = localStorage.getItem('az-theme');
      return (saved === 'light' || saved === 'dark') ? saved : 'dark';
    } catch (e) {
      return 'dark';
    }
  }

  /**
   * Sauvegarde le thème dans localStorage
   */
  saveTheme(theme) {
    try {
      localStorage.setItem('az-theme', theme);
    } catch (e) {
      console.warn('localStorage non disponible');
    }
  }

  /**
   * Bascule entre les thèmes clair et sombre
   */
  toggleTheme() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', this.theme);
    this.saveTheme(this.theme);
    this.updateThemeIcon();
  }

  /**
   * Met à jour l'icône du thème
   */
  updateThemeIcon() {
    const themeIcon = document.getElementById('azThemeIcon');
    const themeIconDropdown = document.getElementById('azThemeIconDropdown');
    const themeLabelDropdown = document.getElementById('azThemeLabelDropdown');

    if (themeIcon) {
      themeIcon.className = this.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }

    if (themeIconDropdown) {
      themeIconDropdown.className = this.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }

    if (themeLabelDropdown) {
      themeLabelDropdown.textContent = this.theme === 'dark' ? 'Mode clair' : 'Mode sombre';
    }
  }

  /**
   * Configure le basculement du thème
   */
  setupThemeToggle() {
    const themeBtn = document.getElementById('azThemeToggle');
    const themeDropdownBtn = document.getElementById('azThemeToggleDropdown');

    if (themeBtn) {
      themeBtn.addEventListener('click', () => this.toggleTheme());
    }

    if (themeDropdownBtn) {
      themeDropdownBtn.addEventListener('click', () => {
        this.toggleTheme();
        this.closeUserMenu();
      });
    }

    this.updateThemeIcon();
  }

  /**
   * Configure le basculement du sidebar mobile
   */
  setupSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('azOverlay');

    if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
      });
    }

    if (overlay) {
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
      });
    }

    // Fermer le sidebar lors du clic sur un lien
    const navItems = document.querySelectorAll('.az-nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        if (this.isMobile) {
          sidebar.classList.remove('active');
          overlay.classList.remove('active');
        }
      });
    });
  }

  /**
   * Configure le menu utilisateur
   */
  setupUserMenu() {
    const userMenuToggle = document.getElementById('userMenuToggle');
    const userMenu = document.getElementById('userMenu');

    if (userMenuToggle && userMenu) {
      userMenuToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        userMenu.classList.toggle('active');
        userMenuToggle.classList.toggle('active');
      });

      // Fermer le menu lors du clic en dehors
      document.addEventListener('click', (e) => {
        if (!userMenuToggle.contains(e.target) && !userMenu.contains(e.target)) {
          this.closeUserMenu();
        }
      });

      // Fermer le menu lors du clic sur un élément
      const menuItems = userMenu.querySelectorAll('.az-user-menu-item');
      menuItems.forEach(item => {
        item.addEventListener('click', () => {
          this.closeUserMenu();
        });
      });
    }
  }

  /**
   * Ferme le menu utilisateur
   */
  closeUserMenu() {
    const userMenuToggle = document.getElementById('userMenuToggle');
    const userMenu = document.getElementById('userMenu');

    if (userMenu && userMenuToggle) {
      userMenu.classList.remove('active');
      userMenuToggle.classList.remove('active');
    }
  }

  /**
   * Configure la fermeture des alertes
   */
  setupAlertClosing() {
    const alerts = document.querySelectorAll('.az-alert');

    alerts.forEach(alert => {
      const closeBtn = alert.querySelector('.az-alert-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => {
          alert.style.animation = 'az-slide-out 0.3s ease-out forwards';
          setTimeout(() => alert.remove(), 300);
        });
      }

      // Auto-fermeture après 5 secondes
      setTimeout(() => {
        if (alert.parentNode) {
          alert.style.animation = 'az-slide-out 0.3s ease-out forwards';
          setTimeout(() => alert.remove(), 300);
        }
      }, 5000);
    });
  }

  /**
   * Configure la réactivité
   */
  setupResponsive() {
    window.addEventListener('resize', () => {
      const wasMobile = this.isMobile;
      this.isMobile = window.innerWidth <= 768;

      if (wasMobile && !this.isMobile) {
        // Passage de mobile à desktop
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('azOverlay');
        if (sidebar) sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
      }
    });
  }

  /**
   * Configure les écouteurs d'événements supplémentaires
   */
  setupEventListeners() {
    // Notification badge
    const notificationBtn = document.querySelector('.az-notification-btn');
    if (notificationBtn) {
      notificationBtn.addEventListener('click', () => {
        this.showNotification('Notifications', 'Aucune nouvelle notification');
      });
    }

    // Gestion des boutons d'action
    this.setupActionButtons();
  }

  /**
   * Configure les boutons d'action
   */
  setupActionButtons() {
    const buttons = document.querySelectorAll('[data-action]');
    buttons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = btn.dataset.action;
        this.handleAction(action, e);
      });
    });
  }

  /**
   * Gère les actions personnalisées
   */
  handleAction(action, event) {
    switch (action) {
      case 'delete':
        this.confirmDelete(event.target);
        break;
      case 'edit':
        this.editItem(event.target);
        break;
      case 'view':
        this.viewItem(event.target);
        break;
      default:
        console.log('Action non reconnue:', action);
    }
  }

  /**
   * Affiche une notification
   */
  showNotification(title, message, type = 'info') {
    const alertClass = `az-alert az-alert-${type}`;
    const icon = this.getIconForType(type);
    
    const alert = document.createElement('div');
    alert.className = alertClass;
    alert.innerHTML = `
      <i class="fas fa-${icon}"></i>
      <span>${message}</span>
      <button class="az-alert-close">&times;</button>
    `;

    const messagesContainer = document.querySelector('.az-messages') || 
                             document.querySelector('.az-content');
    if (messagesContainer) {
      messagesContainer.insertBefore(alert, messagesContainer.firstChild);
      
      const closeBtn = alert.querySelector('.az-alert-close');
      closeBtn.addEventListener('click', () => {
        alert.style.animation = 'az-slide-out 0.3s ease-out forwards';
        setTimeout(() => alert.remove(), 300);
      });

      setTimeout(() => {
        if (alert.parentNode) {
          alert.style.animation = 'az-slide-out 0.3s ease-out forwards';
          setTimeout(() => alert.remove(), 300);
        }
      }, 5000);
    }
  }

  /**
   * Retourne l'icône appropriée pour le type
   */
  getIconForType(type) {
    const icons = {
      'success': 'check-circle',
      'error': 'exclamation-circle',
      'warning': 'exclamation-triangle',
      'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
  }

  /**
   * Confirme la suppression
   */
  confirmDelete(element) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet élément ?')) {
      this.showNotification('Suppression', 'Élément supprimé avec succès', 'success');
    }
  }

  /**
   * Édite un élément
   */
  editItem(element) {
    this.showNotification('Édition', 'Ouverture du formulaire d\'édition...', 'info');
  }

  /**
   * Affiche un élément
   */
  viewItem(element) {
    this.showNotification('Affichage', 'Ouverture des détails...', 'info');
  }
}

/**
 * Initialisation au chargement du DOM
 */
document.addEventListener('DOMContentLoaded', () => {
  window.azAdmin = new AZAdmin();

  // Ajouter une animation de sortie aux alertes
  const style = document.createElement('style');
  style.textContent = `
    @keyframes az-slide-out {
      to {
        opacity: 0;
        transform: translateY(-10px);
      }
    }
  `;
  document.head.appendChild(style);
});

/**
 * Utilitaires globaux
 */
const AZUtils = {
  /**
   * Formate une date
   */
  formatDate(date) {
    return new Date(date).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  },

  /**
   * Formate une heure
   */
  formatTime(time) {
    return new Date(`2000-01-01 ${time}`).toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  },

  /**
   * Valide un email
   */
  validateEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
  },

  /**
   * Valide un téléphone
   */
  validatePhone(phone) {
    const regex = /^[\d\s\-\+\(\)]+$/;
    return regex.test(phone) && phone.replace(/\D/g, '').length >= 10;
  },

  /**
   * Copie du texte dans le presse-papiers
   */
  copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      if (window.azAdmin) {
        window.azAdmin.showNotification('Copie', 'Texte copié dans le presse-papiers', 'success');
      }
    });
  },

  /**
   * Génère un ID unique
   */
  generateId() {
    return `az-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  },

  /**
   * Débounce une fonction
   */
  debounce(func, delay) {
    let timeoutId;
    return function (...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
  },

  /**
   * Throttle une fonction
   */
  throttle(func, limit) {
    let inThrottle;
    return function (...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
};

/**
 * API REST simplifiée
 */
const AZApi = {
  /**
   * Effectue une requête GET
   */
  async get(url) {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      return await response.json();
    } catch (error) {
      console.error('Erreur GET:', error);
      throw error;
    }
  },

  /**
   * Effectue une requête POST
   */
  async post(url, data) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
      });
      return await response.json();
    } catch (error) {
      console.error('Erreur POST:', error);
      throw error;
    }
  },

  /**
   * Effectue une requête PUT
   */
  async put(url, data) {
    try {
      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
      });
      return await response.json();
    } catch (error) {
      console.error('Erreur PUT:', error);
      throw error;
    }
  },

  /**
   * Effectue une requête DELETE
   */
  async delete(url) {
    try {
      const response = await fetch(url, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      return await response.json();
    } catch (error) {
      console.error('Erreur DELETE:', error);
      throw error;
    }
  }
};

/**
 * Gestion des formulaires
 */
const AZForm = {
  /**
   * Valide un formulaire
   */
  validate(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    const inputs = form.querySelectorAll('[required]');
    let isValid = true;

    inputs.forEach(input => {
      if (!input.value.trim()) {
        this.showError(input, 'Ce champ est requis');
        isValid = false;
      } else {
        this.clearError(input);
      }
    });

    return isValid;
  },

  /**
   * Affiche une erreur sur un champ
   */
  showError(input, message) {
    input.classList.add('az-input-error');
    const error = document.createElement('span');
    error.className = 'az-input-error-message';
    error.textContent = message;
    
    const existing = input.parentNode.querySelector('.az-input-error-message');
    if (existing) existing.remove();
    
    input.parentNode.appendChild(error);
  },

  /**
   * Efface une erreur sur un champ
   */
  clearError(input) {
    input.classList.remove('az-input-error');
    const error = input.parentNode.querySelector('.az-input-error-message');
    if (error) error.remove();
  },

  /**
   * Récupère les données d'un formulaire
   */
  getFormData(formId) {
    const form = document.getElementById(formId);
    if (!form) return null;

    const formData = new FormData(form);
    const data = {};

    formData.forEach((value, key) => {
      data[key] = value;
    });

    return data;
  },

  /**
   * Remplit un formulaire avec des données
   */
  setFormData(formId, data) {
    const form = document.getElementById(formId);
    if (!form) return;

    Object.keys(data).forEach(key => {
      const input = form.querySelector(`[name="${key}"]`);
      if (input) {
        input.value = data[key];
      }
    });
  },

  /**
   * Réinitialise un formulaire
   */
  reset(formId) {
    const form = document.getElementById(formId);
    if (form) {
      form.reset();
      const errors = form.querySelectorAll('.az-input-error-message');
      errors.forEach(error => error.remove());
      const inputs = form.querySelectorAll('.az-input-error');
      inputs.forEach(input => input.classList.remove('az-input-error'));
    }
  }
};

/**
 * Gestion des modales
 */
const AZModal = {
  /**
   * Ouvre une modale
   */
  open(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  },

  /**
   * Ferme une modale
   */
  close(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = 'auto';
    }
  },

  /**
   * Bascule une modale
   */
  toggle(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.toggle('active');
    }
  }
};

/**
 * Gestion des tableaux
 */
const AZTable = {
  /**
   * Trie un tableau
   */
  sort(tableId, columnIndex) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    rows.sort((a, b) => {
      const aValue = a.cells[columnIndex].textContent.trim();
      const bValue = b.cells[columnIndex].textContent.trim();
      return aValue.localeCompare(bValue);
    });

    rows.forEach(row => tbody.appendChild(row));
  },

  /**
   * Filtre un tableau
   */
  filter(tableId, searchTerm, columnIndex = 0) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');
    const term = searchTerm.toLowerCase();

    rows.forEach(row => {
      const cell = row.cells[columnIndex];
      if (cell && cell.textContent.toLowerCase().includes(term)) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  },

  /**
   * Exporte un tableau en CSV
   */
  exportCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;

    let csv = [];
    const rows = table.querySelectorAll('tr');

    rows.forEach(row => {
      const cols = row.querySelectorAll('td, th');
      const csvRow = Array.from(cols).map(col => `"${col.textContent.trim()}"`).join(',');
      csv.push(csvRow);
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + csv.join('\n');
    const link = document.createElement('a');
    link.setAttribute('href', encodeURI(csvContent));
    link.setAttribute('download', filename);
    link.click();
  }
};
