#!/bin/bash
# install_services.sh — Installe les services systemd GuardianAI sur le Pi
# Usage : sudo bash systemd/install_services.sh

set -e
PROJ=/home/pi/gateway_project

echo "[1/4] Copie des fichiers service..."
cp $PROJ/systemd/guardian-network.service   /etc/systemd/system/
cp $PROJ/systemd/guardian-discovery.service /etc/systemd/system/
cp $PROJ/systemd/guardian-rules.service     /etc/systemd/system/

echo "[2/4] Rend le script réseau exécutable..."
chmod +x $PROJ/systemd/setup_network.sh

echo "[3/4] Recharge systemd..."
systemctl daemon-reload

echo "[4/4] Active les services au démarrage..."
systemctl enable guardian-network.service
systemctl enable guardian-discovery.service
systemctl enable guardian-rules.service

echo ""
echo "✅ Services installés ! Redémarre le Pi pour tester :"
echo "   sudo reboot"
