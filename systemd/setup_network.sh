#!/bin/bash
# setup_network.sh — Configure le réseau GuardianAI au démarrage
# Lancé automatiquement par guardian-network.service

# NE PAS utiliser set -e : on veut continuer même si certaines règles existent déjà

echo "[guardian-network] Démarrage de la configuration réseau..."

# 1. Crée uap0 seulement si elle n'existe pas encore
if ! ip link show uap0 &>/dev/null; then
    echo "[guardian-network] Création de l'interface uap0..."
    iw dev wlan0 interface add uap0 type __ap
    ip addr add 192.168.50.1/24 dev uap0
    ip link set uap0 up
    echo "[guardian-network] uap0 créée et configurée."
else
    echo "[guardian-network] uap0 existe déjà, configuration ignorée."
fi

# 2. Active le routage IP (pass-through Internet)
echo 1 > /proc/sys/net/ipv4/ip_forward

# 3. Règle NAT : déguise le trafic Wi-Fi avec l'IP du Pi
iptables -t nat -C POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null || \
  iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE

# 4. Règles FORWARD : autorise le relais uap0 <-> wlan0
iptables -C FORWARD -i wlan0 -o uap0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
  iptables -I FORWARD 1 -i wlan0 -o uap0 -m state --state RELATED,ESTABLISHED -j ACCEPT

iptables -C FORWARD -i uap0 -o wlan0 -j ACCEPT 2>/dev/null || \
  iptables -A FORWARD -i uap0 -o wlan0 -j ACCEPT

echo "[guardian-network] Configuration réseau terminée."
