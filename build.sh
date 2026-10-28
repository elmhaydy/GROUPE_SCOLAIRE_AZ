#!/usr/bin/env bash
# ==============================================================================
# Script de Build Automatique Render.com - Atlas School ERP
# ==============================================================================
# Ce script est exécuté lors de chaque déploiement sur Render (Build Command).
# Il installe les dépendances, rassemble les fichiers statiques, applique les
# migrations PostgreSQL et amorce la base avec les données de démo 1-clic.
# ==============================================================================

set -o errexit  # Arrête le script en cas d'erreur sur une commande

echo "==> [1/4] Installation des dépendances Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> [2/4] Collecte et compression des fichiers statiques (WhiteNoise)..."
python manage.py collectstatic --noinput

echo "==> [3/4] Vérification de la base de données et application des migrations..."
if [ -z "$DATABASE_URL" ]; then
  echo "========================================================================"
  echo "❌ ERREUR CRITIQUE : Variable d'environnement DATABASE_URL manquante !"
  echo "========================================================================"
  echo "Le déploiement Render requiert une base de données PostgreSQL."
  echo "Pour configurer la base de données gratuite sur Render :"
  echo "  1. Allez sur le Dashboard Render (https://dashboard.render.com)."
  echo "  2. Cliquez sur 'New +' > 'PostgreSQL' (Nom : atlas-db, Plan : Free)."
  echo "  3. Copiez l'URL 'Internal Database URL' (commence par postgresql://...)."
  echo "  4. Allez sur votre Web Service > Onglet 'Environment'."
  echo "  5. Ajoutez la variable DATABASE_URL avec cette valeur collée."
  echo "  6. Relancez le build (Manual Deploy > Deploy latest commit)."
  echo "========================================================================"
  exit 1
fi

python manage.py migrate --noinput

echo "==> [4/4] Amorçage des données de démonstration commerciales..."
python manage.py seed_demo_data

echo "==> ✅ Déploiement et préparation terminés avec succès !"
