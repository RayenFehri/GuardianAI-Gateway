#!/bin/sh
# install.sh — Installation automatique sur Raspberry Pi OpenWrt
#
# Ce script fait tout automatiquement sur le Pi :
#   1. Met à jour les paquets OpenWrt
#   2. Installe Python3 et les dépendances
#   3. Installe Docker (pour PostgreSQL)
#   4. Clone le repo GitHub
#   5. Lance PostgreSQL via Docker
#   6. Configure le cron pour lancer les scripts automatiquement
#
# Usage (sur le Pi, en SSH) :
#   chmod +x install.sh
#   ./install.sh

set -e  # Arrête le script si une commande échoue

echo "========================================"
echo " GuardianAI Gateway — Installation Pi  "
echo "========================================"

# ── 1. Mise à jour des paquets OpenWrt ──────────────────────
echo ""
echo "[1/6] Mise à jour des paquets OpenWrt..."
opkg update

# ── 2. Installation de Python3 ──────────────────────────────
echo ""
echo "[2/6] Installation de Python3..."
opkg install python3 python3-pip

# Vérifie que Python est bien installé
python3 --version

# ── 3. Installation de Docker ───────────────────────────────
echo ""
echo "[3/6] Installation de Docker..."
opkg install docker dockerd docker-compose

# Démarre Docker
/etc/init.d/dockerd start
/etc/init.d/dockerd enable

echo "Attente du démarrage de Docker (10s)..."
sleep 10

# ── 4. Récupération du code ─────────────────────────────────
echo ""
echo "[4/6] Clonage du projet depuis GitHub..."
cd /root

# Remplace l'URL par celle de ton repo GitHub
git clone https://github.com/RayenFehri/GuardianAI-Gateway.git gateway_project
cd gateway_project

# Copie le fichier .env
cp .env.example .env

# Modifie GATEWAY_ENV pour dire qu'on est sur le Pi
echo "GATEWAY_ENV=pi" >> .env

# ── 5. Lancement de PostgreSQL ──────────────────────────────
echo ""
echo "[5/6] Lancement de PostgreSQL via Docker..."
docker compose up -d

echo "Attente que PostgreSQL soit prêt (15s)..."
sleep 15

# ── 6. Installation des dépendances Python ──────────────────
echo ""
echo "[6/6] Installation des dépendances Python..."
pip3 install -r requirements.txt

# ── 7. Configuration du cron ────────────────────────────────
echo ""
echo "[7/7] Configuration du cron..."

# Lance la découverte des équipements toutes les minutes
# Lance l'analyse DNS toutes les minutes
(crontab -l 2>/dev/null; echo "* * * * * cd /root/gateway_project && python3 main_discovery.py >> /tmp/gateway_discovery.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "* * * * * cd /root/gateway_project && python3 main_usage_analysis.py >> /tmp/gateway_usage.log 2>&1") | crontab -

# Vérifie le cron
echo "Cron configuré :"
crontab -l

echo ""
echo "========================================"
echo " Installation terminée avec succès !   "
echo " Teste avec : python3 main_discovery.py"
echo "========================================"