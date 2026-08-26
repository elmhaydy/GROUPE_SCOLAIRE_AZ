<div align="center">

# 🎓 GROUPE SCOLAIRE AZ
### Système de Gestion Scolaire, Pédagogique & Financière Intégré

![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql)
![Bootstrap/Vanilla](https://img.shields.io/badge/CSS3-AZ--Design--System-1572B6?style=for-the-badge&logo=css3)
![License](https://img.shields.io/badge/License-Propriétaire-red?style=for-the-badge)

<br>

**[🌐 En savoir plus](https://www.linkedin.com/in/el-mehdi-bougrin)** &nbsp;•&nbsp; **[📄 Documentation](#-fonctionnalités-clés)** &nbsp;•&nbsp; **[🚀 Prise en main](#-installation--prise-en-main)**

</div>

---

## 📌 À propos du Projet

**GROUPE SCOLAIRE AZ** est une solution logicielle complète d'administration et de gestion scolaire conçue pour répondre aux exigences des établissements d'enseignement modernes (Maternelle, Primaire, Collège et Lycée).

La plateforme centralise la gestion administrative de la scolarité, le suivi financier et les encaissements, le contrôle des présences, la saisie des évaluations ainsi que la communication avec les tuteurs légaux.

---

## ✨ Fonctionnalités Clés

### 🏫 1. Pédagogie & Structure Scolaire
- **Gestion des Années Scolaires** : Basculement d'année active, clôture et archivage automatique.
- **Niveaux & Degrés** : Arborescence personnalisable (Maternelle, Primaire, Collège, Lycée).
- **Groupes / Classes** : Affectation des élèves, gestion des capacités et professeurs principaux.
- **Emplois du Temps & Séances** : Attribution des matières, salles de cours et enseignants.

### 👨‍🎓 2. Gestion des Élèves & Tuteurs Légaux
- **Fiches Élèves Détaillées** : Photo d'identité avec visionneuse grand écran (*Lightbox zoom*), matricule unique, historique académique.
- **Dossiers Inscription** : Suivi des statuts (Inscrit, En cours, Réinscrit, Radié).
- **Gestion Multi-Parents** : Rattachement des pères, mères et tuteurs légaux avec coordonnées de contact direct.

### 💰 3. Suivi Financier & Recouvrement (Module Financier Avancé)
- **Échéanciers Automatiques sur 10 Mois** : Calcul en temps réel des frais d'inscription et mensualités de scolarité.
- **Assistant de Règlement (*Transaction Wizard*)** : Prise en charge des paiements en Espèces, Chèque ou Virement.
- **Impression des Reçus Officiels** : Génération de reçus imprimables avec référence unique.
- **Suivi des Impayés & Relances** : Module de relance automatisé par **WhatsApp**, **SMS** et **Email** pour les mensualités en retard.
- **Gestion des Dépenses** : Suivi des frais de fonctionnement de l'établissement par catégories.

### ⏱️ 4. Absences & Évaluations Pédagogiques
- **Feuilles d'Appel Numériques** : Saisie quotidienne ou par séance des absences et retards.
- **Suivi des Enseignants** : Gestion des absences et remplacements des professeurs.
- **Notes & Bulletins** : Saisie des contrôles et génération des bulletins trimestriels.

### ⚡ 5. Performance & Ergonomie Gmail-Style
- **Pagination Rapide à 50 Éléments / Page** : Déploiement d'un sélecteur de page style Gmail sur les 11 listes principales (*Élèves, Inscriptions, Paiements, Enseignants, Parents, Absences, Dépenses, Avis, Utilisateurs, Relances, Audit*).
- **Menu d'Actions Interactif Kebab (3 points)** : Accès rapide aux actions de consultation, modification, édition de reçu et suppression.

### 🔐 6. Sécurité & Système de Vérification
- **Réinitialisation par Code de Vérification à 6 chiffres (OTP)** : Envoi d'emails au design scolaire moderne avec code unique valable 15 minutes.
- **Profils de Sécurité Utilisateurs** : Blocage automatique de 15 minutes après 5 tentatives de connexion échouées.
- **Journal d'Audit Généralisé (AuditLog)** : Traçabilité à 100% de toutes les opérations de Création, Modification (*diff avant/après*) et Suppression avec horodatage, auteur et adresse IP.

### 📑 7. Pages Institutionnelles & Support
- **Centre d'Aide & FAQ (`/core/aide/`)** : Guides interactifs et réponses aux questions fréquentes.
- **Politique de Confidentialité (`/core/confidentialite/`)** : Conforme à la Loi marocaine n° 09-08 sur la protection des données personnelles.
- **Conditions d'Utilisation (`/core/conditions/`)** : Règlement d'utilisation de la plateforme.
- **Formulaire de Contact (`/core/contact/`)** : Support technique et administratif direct.

---

## 🛠️ Stack Technique

- **Backend** : Python 3.13, Django 5.2
- **Base de Données** : PostgreSQL 16 (ou SQLite3 pour le développement local)
- **Frontend** : HTML5 Semantic, Vanilla CSS (*AZ Design System*), JavaScript ES6 (sans dépendance lourde)
- **Emailing** : Moteur SMTP Gmail avec templates HTML réactifs et sécurisés
- **Icônes & Typographie** : FontAwesome 6 Pro, Google Fonts (*Inter*)

---

## 📁 Architecture du Projet

```text
GROUPE_SCOLAIRE_AZ/
├── accounts/               # Authentification, Sécurité, Profils et Code de Vérification
├── config/                 # Configuration Django (settings.py, urls.py, wsgi.py)
├── core/                   # Cœur de l'application (Vues, Modèles, Signaux d'audit, Finance)
│   ├── models.py           # Modèles Élèves, Parents, Inscriptions, Paiements, Structure
│   ├── models_audit.py     # Modèle Journal d'Audit
│   ├── audit_signals.py    # Enregistrement automatique des signaux d'audit
│   ├── views_finance.py    # Assistant de transaction & échéanciers
│   ├── views_audit.py      # Journal des logs d'audit
│   └── views_info.py       # Vues Aide, Confidentialité, CGU, Contact
├── prof/                   # Espace dédié aux Enseignants
├── eleve/                  # Espace dédié aux Élèves & Parents
├── templates/              # Gabarits HTML (Admin, Accounts, Emails, Info)
│   ├── admin/              # Dashboard et vues administratives
│   ├── accounts/           # Templates de Login, Code de vérification, Mots de passe
│   └── emails/             # Modèles d'emails HTML scolaires
├── static/                 # Fichiers statiques (CSS, JS, Images, Logo)
├── manage.py               # Script d'exécution Django
└── .env                    # Fichier de variables d'environnement
```

---

## 🚀 Installation & Prise en Main

### 1. Prérequis
- **Python 3.11+** installé sur votre machine.
- **Git** pour le suivi de version.
- **PostgreSQL** (optionnel, SQLite par défaut en local).

### 2. Cloner le Projet
```bash
git clone https://github.com/votre-compte/GROUPE_SCOLAIRE_AZ.git
cd GROUPE_SCOLAIRE_AZ
```

### 3. Créer et Activer l'Environnement Virtuel
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / MacOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Installer les Dépendances
```bash
pip install -r requirements.txt
```

### 5. Configurer le fichier `.env`
Créez un fichier `.env` à la racine du projet avec les configurations suivantes :
```env
DEBUG=1
SECRET_KEY=votre_cle_secrete_django

# Configuration Base de Données (Optionnel si SQLite)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=az_db_groups
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
DB_HOST=127.0.0.1
DB_PORT=5432

# Configuration SMTP Emailing (Code de vérification)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre.email@gmail.com
EMAIL_HOST_PASSWORD=votre_mot_de_passe_application_google
DEFAULT_FROM_EMAIL=votre.email@gmail.com
```

### 6. Appliquer les Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Créer un Compte Administrateur
```bash
python manage.py createsuperuser
```

### 8. Lancer le Serveur de Développement
```bash
python manage.py runserver
```

Rendez-vous ensuite sur `http://127.0.0.1:8000/accounts/login/` pour vous connecter !

---

## 👤 Auteur & Conception

Ce projet a été conçu et développé avec passion par :

<div align="center">

### **El_Mehdi_Bougrin**
*Développeur Full Stack & Ingénieur Logiciel*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-El__Mehdi__Bougrin-0A66C2?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/el-mehdi-bougrin)

</div>

---

<div align="center">
© 2026 Groupe Scolaire AZ • Tous droits réservés.
</div>
