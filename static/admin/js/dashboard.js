/* ╔════════════════════════════════════════════════════════════════════════════╗ */
/* ║                    AZ DASHBOARD - SCRIPTS INTERACTIFS                      ║ */
/* ║              Gestion des graphiques, onglets et interactions               ║ */
/* ╚════════════════════════════════════════════════════════════════════════════╝ */

/**
 * Classe principale pour gérer le dashboard
 */
class AZDashboard {
  constructor() {
    this.charts = {};
    this.currentPeriod = 'monthly';
    this.init();
  }

  /**
   * Initialisation du dashboard
   */
  init() {
    this.setupCharts();
    this.setupTabs();
    this.setupButtons();
    this.setupEventListeners();
    this.updateDate();
  }

  /**
   * Configure les graphiques Chart.js
   */
  setupCharts() {
    // Graphique mensuel
    const monthlyChartElement = document.getElementById('monthlyChart');
    if (monthlyChartElement) {
      this.charts.monthly = this.createMonthlyChart(monthlyChartElement);
    }

    // Graphique de distribution
    const distributionChartElement = document.getElementById('distributionChart');
    if (distributionChartElement) {
      this.charts.distribution = this.createDistributionChart(distributionChartElement);
    }
  }

  /**
   * Crée le graphique mensuel
   */
  createMonthlyChart(canvas) {
    const ctx = canvas.getContext('2d');
    
    // Données par défaut (à remplacer par les données du backend)
    const monthlyData = this.getMonthlyData();

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: monthlyData.labels,
        datasets: [
          {
            label: 'Paiements',
            data: monthlyData.payments,
            backgroundColor: 'rgba(99, 102, 241, 0.8)',
            borderColor: 'rgba(99, 102, 241, 1)',
            borderRadius: 8,
            borderSkipped: false,
            hoverBackgroundColor: 'rgba(99, 102, 241, 1)',
          },
          {
            label: 'Impayés',
            data: monthlyData.unpaid,
            backgroundColor: 'rgba(239, 68, 68, 0.8)',
            borderColor: 'rgba(239, 68, 68, 1)',
            borderRadius: 8,
            borderSkipped: false,
            hoverBackgroundColor: 'rgba(239, 68, 68, 1)',
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              usePointStyle: true,
              padding: 15,
              font: { size: 12, weight: '600' },
              color: this.getTextColor()
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: this.getGridColor(),
              drawBorder: false
            },
            ticks: {
              color: this.getTextColor(),
              font: { size: 11 }
            }
          },
          x: {
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              color: this.getTextColor(),
              font: { size: 11 }
            }
          }
        }
      }
    });
  }

  /**
   * Crée le graphique de distribution
   */
  createDistributionChart(canvas) {
    const ctx = canvas.getContext('2d');
    
    // Récupérer les données du window object
    const repartitionLabels = window.AZ_DASH?.repartitionLabels || ['Niveau 1', 'Niveau 2', 'Niveau 3'];
    const repartitionData = window.AZ_DASH?.repartitionData || [30, 25, 45];

    const colors = [
      'rgba(99, 102, 241, 0.8)',
      'rgba(59, 130, 246, 0.8)',
      'rgba(16, 185, 129, 0.8)',
      'rgba(245, 158, 11, 0.8)',
      'rgba(236, 72, 153, 0.8)',
      'rgba(139, 92, 246, 0.8)'
    ];

    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: repartitionLabels,
        datasets: [{
          data: repartitionData,
          backgroundColor: colors.slice(0, repartitionLabels.length),
          borderColor: this.getBgColor(),
          borderWidth: 2,
          hoverOffset: 10
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'right',
            labels: {
              usePointStyle: true,
              padding: 15,
              font: { size: 12, weight: '500' },
              color: this.getTextColor()
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }

  /**
   * Récupère les données mensuelles
   */
  getMonthlyData() {
    const months = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'];
    const currentMonth = new Date().getMonth();
    const lastSixMonths = months.slice(Math.max(0, currentMonth - 5), currentMonth + 1);

    return {
      labels: lastSixMonths,
      payments: [12000, 15000, 18000, 16000, 19000, 21000],
      unpaid: [2000, 1500, 1200, 2500, 1800, 1000]
    };
  }

  /**
   * Configure les onglets
   */
  setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const tabName = button.dataset.tab;

        // Désactiver tous les onglets
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        // Activer l'onglet sélectionné
        button.classList.add('active');
        const activeTab = document.getElementById(`${tabName}Tab`);
        if (activeTab) {
          activeTab.classList.add('active');
        }
      });
    });
  }

  /**
   * Configure les boutons
   */
  setupButtons() {
    // Bouton d'actualisation
    const refreshBtn = document.getElementById('refreshDashboard');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.refreshDashboard();
      });
    }

    // Bouton d'export
    const exportBtn = document.getElementById('exportChart');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        this.exportChart();
      });
    }

    // Sélecteur de période
    const periodSelect = document.getElementById('chartPeriod');
    if (periodSelect) {
      periodSelect.addEventListener('change', (e) => {
        this.currentPeriod = e.target.value;
        this.updateChartPeriod();
      });
    }

    // Bouton d'envoi de rappels
    const remindersBtn = document.getElementById('sendReminders');
    if (remindersBtn) {
      remindersBtn.addEventListener('click', () => {
        this.sendReminders();
      });
    }
  }

  /**
   * Configure les écouteurs d'événements
   */
  setupEventListeners() {
    // Animations au survol des cartes
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
      card.addEventListener('mouseenter', () => {
        card.style.animation = 'none';
        setTimeout(() => {
          card.style.animation = '';
        }, 10);
      });
    });
  }

  /**
   * Actualise le dashboard
   */
  refreshDashboard() {
    const refreshBtn = document.getElementById('refreshDashboard');
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Actualisation...';

      setTimeout(() => {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Actualiser';
        
        // Afficher une notification
        this.showNotification('Dashboard actualisé avec succès', 'success');
      }, 1500);
    }
  }

  /**
   * Exporte le graphique
   */
  exportChart() {
    if (this.charts.monthly) {
      const image = this.charts.monthly.toBase64Image();
      const link = document.createElement('a');
      link.href = image;
      link.download = `dashboard-${new Date().toISOString().split('T')[0]}.png`;
      link.click();
      
      this.showNotification('Graphique exporté avec succès', 'success');
    }
  }

  /**
   * Met à jour la période du graphique
   */
  updateChartPeriod() {
    if (this.charts.monthly) {
      const data = this.getMonthlyData();
      this.charts.monthly.data.labels = data.labels;
      this.charts.monthly.data.datasets[0].data = data.payments;
      this.charts.monthly.data.datasets[1].data = data.unpaid;
      this.charts.monthly.update();
    }
  }

  /**
   * Envoie des rappels
   */
  sendReminders() {
    const remindersBtn = document.getElementById('sendReminders');
    if (remindersBtn) {
      remindersBtn.disabled = true;
      remindersBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Envoi en cours...';

      setTimeout(() => {
        remindersBtn.disabled = false;
        remindersBtn.innerHTML = '<i class="fas fa-bell"></i> Envoyer rappels';
        
        this.showNotification('Rappels envoyés à 15 parents', 'success');
      }, 2000);
    }
  }

  /**
   * Met à jour la date actuelle
   */
  updateDate() {
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      const today = new Date().toLocaleDateString('fr-FR', options);
      dateElement.textContent = today;
    }
  }

  /**
   * Affiche une notification
   */
  showNotification(message, type = 'info') {
    if (window.azAdmin) {
      window.azAdmin.showNotification('Dashboard', message, type);
    } else {
      console.log(`[${type.toUpperCase()}] ${message}`);
    }
  }

  /**
   * Récupère la couleur du texte selon le thème
   */
  getTextColor() {
    const theme = document.documentElement.getAttribute('data-theme') || 'dark';
    return theme === 'dark' ? '#f1f5f9' : '#1e293b';
  }

  /**
   * Récupère la couleur de la grille selon le thème
   */
  getGridColor() {
    const theme = document.documentElement.getAttribute('data-theme') || 'dark';
    return theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)';
  }

  /**
   * Récupère la couleur de fond selon le thème
   */
  getBgColor() {
    const theme = document.documentElement.getAttribute('data-theme') || 'dark';
    return theme === 'dark' ? '#0f172a' : '#ffffff';
  }

  /**
   * Recharge les graphiques lors du changement de thème
   */
  onThemeChange() {
    // Détruire les anciens graphiques
    Object.values(this.charts).forEach(chart => {
      if (chart) chart.destroy();
    });

    // Recréer les graphiques
    this.setupCharts();
  }
}

/**
 * Initialisation au chargement du DOM
 */
document.addEventListener('DOMContentLoaded', () => {
  window.azDashboard = new AZDashboard();

  // Ajouter les animations CSS
  const style = document.createElement('style');
  style.textContent = `
    @keyframes az-fade-in {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .stat-card {
      animation: az-fade-in 0.5s ease-out;
    }

    .stat-card:nth-child(2) {
      animation-delay: 0.1s;
    }

    .stat-card:nth-child(3) {
      animation-delay: 0.2s;
    }

    .stat-card:nth-child(4) {
      animation-delay: 0.3s;
    }
  `;
  document.head.appendChild(style);

  // Écouter les changements de thème
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'data-theme') {
        window.azDashboard.onThemeChange();
      }
    });
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
});

/**
 * Utilitaires pour les statistiques
 */
const AZDashboardUtils = {
  /**
   * Formate un nombre en devise
   */
  formatCurrency(value, currency = 'MAD') {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0
    }).format(value);
  },

  /**
   * Formate un nombre avec séparateurs
   */
  formatNumber(value) {
    return new Intl.NumberFormat('fr-FR').format(value);
  },

  /**
   * Calcule le pourcentage
   */
  calculatePercentage(value, total) {
    if (total === 0) return 0;
    return ((value / total) * 100).toFixed(1);
  },

  /**
   * Calcule la tendance
   */
  calculateTrend(current, previous) {
    if (previous === 0) return 0;
    return (((current - previous) / previous) * 100).toFixed(1);
  },

  /**
   * Récupère la couleur selon la tendance
   */
  getTrendColor(trend) {
    if (trend > 0) return 'success';
    if (trend < 0) return 'warning';
    return 'neutral';
  },

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
   * Récupère les initiales d'un nom
   */
  getInitials(name) {
    return name
      .split(' ')
      .map(part => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }
};

/**
 * Gestion des animations de chargement
 */
const AZDashboardLoading = {
  /**
   * Affiche un skeleton loader
   */
  showSkeleton(element) {
    element.innerHTML = `
      <div class="skeleton-loader">
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
      </div>
    `;
  },

  /**
   * Masque le skeleton loader
   */
  hideSkeleton(element) {
    const skeleton = element.querySelector('.skeleton-loader');
    if (skeleton) {
      skeleton.remove();
    }
  }
};

/**
 * Styles pour les skeleton loaders
 */
const skeletonStyle = document.createElement('style');
skeletonStyle.textContent = `
  .skeleton-loader {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .skeleton-line {
    height: 12px;
    background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
    background-size: 200% 100%;
    border-radius: 4px;
    animation: loading 1.5s infinite;
  }

  @keyframes loading {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  html[data-theme="dark"] .skeleton-line {
    background: linear-gradient(90deg, #334155 25%, #475569 50%, #334155 75%);
  }
`;
document.head.appendChild(skeletonStyle);

/**
 * Export des classes pour utilisation externe
 */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AZDashboard,
    AZDashboardUtils,
    AZDashboardLoading
  };
}
