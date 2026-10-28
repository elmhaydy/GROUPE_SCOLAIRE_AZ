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

echo "==> [3/4] Application des migrations de la base de données..."
python manage.py migrate --noinput

echo "==> [4/4] Amorçage des données de démonstration commerciales..."
python manage.py seed_demo_data

echo "==> ✅ Déploiement et préparation terminés avec succès !"
