"""
config.py — Configuration centrale du projet GuardianAI Gateway

C'est ici qu'on définit tous les paramètres qui changent entre
l'environnement de développement (PC Fedora) et la production (Pi OpenWrt).

Pour passer du PC au Pi, il suffit de changer ENVIRONMENT = "pi"
et tout le reste s'adapte automatiquement.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # charge les variables depuis le fichier .env

# ============================================================
# ENVIRONNEMENT : "dev" (PC Fedora) ou "pi" (Raspberry Pi)
# Défini dans le fichier .env (GATEWAY_ENV=dev ou GATEWAY_ENV=pi)
# ============================================================
ENVIRONMENT = os.getenv("GATEWAY_ENV", "dev")

BASE_DIR = Path(__file__).parent

# ============================================================
# CHEMINS DES FICHIERS
# ============================================================
if ENVIRONMENT == "pi":
    # Chemins réels sur Raspberry Pi OS (dnsmasq installé via apt)
    LEASES_FILE = Path("/var/lib/misc/dnsmasq.leases")
    DNS_LOG_FILE = Path("/var/log/dnsmasq.log")
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
LAN_SUBNET = os.getenv("LAN_SUBNET", "192.168.50.0/24")

# Interface WiFi du Pi en mode Access Point (hostapd + dnsmasq)
LAN_INTERFACE = os.getenv("LAN_INTERFACE", "uap0")

# Interface WAN (connexion Internet du Pi)
WAN_INTERFACE = os.getenv("WAN_INTERFACE", "wlan0")

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
