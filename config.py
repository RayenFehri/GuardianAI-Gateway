"""
config.py — Configuration centrale du projet GuardianAI Gateway

C'est ici qu'on définit tous les paramètres qui changent entre
l'environnement de développement (PC Fedora) et la production (Pi OpenWrt).

Pour passer du PC au Pi, il suffit de changer ENVIRONMENT = "pi"
et tout le reste s'adapte automatiquement.
"""

import os
from pathlib import Path

# ============================================================
# ENVIRONNEMENT : "dev" (PC Fedora) ou "pi" (Raspberry Pi)
# Change cette ligne quand tu déploies sur le Pi
# ============================================================
ENVIRONMENT = os.getenv("GATEWAY_ENV", "dev")

BASE_DIR = Path(__file__).parent

# ============================================================
# CHEMINS DES FICHIERS
# ============================================================
if ENVIRONMENT == "pi":
    # Chemins réels sur OpenWrt
    LEASES_FILE = Path("/tmp/dhcp.leases")
    DNS_LOG_FILE = Path("/tmp/log/dnsmasq.log")
else:
    # Fichiers simulés pour le développement sur PC
    LEASES_FILE = BASE_DIR / "fake_dnsmasq.leases"
    DNS_LOG_FILE = BASE_DIR / "fake_dnsmasq.log"

# ============================================================
# BASE DE DONNÉES PostgreSQL
# ============================================================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "dbname": os.getenv("DB_NAME", "gateway_db"),
    "user": os.getenv("DB_USER", "gateway_admin"),
    "password": os.getenv("DB_PASSWORD", "changeme123"),
}

# ============================================================
# PARAMÈTRES RÉSEAU
# ============================================================
# Sous-réseau local du Pi (à adapter selon ta box)
LAN_SUBNET = os.getenv("LAN_SUBNET", "192.168.1.0/24")

# Interface réseau du Pi (eth0 sur OpenWrt)
LAN_INTERFACE = os.getenv("LAN_INTERFACE", "eth0")

# ============================================================
# PARAMÈTRES DES SCRIPTS
# ============================================================
# Intervalle de polling en secondes (utilisé par le cron)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))

# Niveau de log : DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


if __name__ == "__main__":
    print(f"Environnement   : {ENVIRONMENT}")
    print(f"Fichier leases  : {LEASES_FILE}")
    print(f"Fichier DNS log : {DNS_LOG_FILE}")
    print(f"Base de données : {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    print(f"Réseau LAN      : {LAN_SUBNET}")