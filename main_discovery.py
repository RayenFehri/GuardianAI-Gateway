"""
main_discovery.py — Orchestrateur de la Partie 1 du CDC

Pipeline complet :
  fichier de leases DHCP
      -> parsing (discovery.py)
      -> résolution fabricant (oui_lookup.py)
      -> classification du type d'équipement (classifier.py)
      -> sauvegarde en base (db.py)

Deux modes de fonctionnement :
  - One-shot : python3 main_discovery.py
  - Daemon   : python3 main_discovery.py --daemon
    (tourne en continu, poll toutes les POLL_INTERVAL secondes)
"""

import sys
import time
import logging
import logging.handlers
from discovery import parse_leases, now_iso
from oui_lookup import get_vendor
from classifier import classify_device
from db import init_db, upsert_device, list_devices
from config import POLL_INTERVAL
from mqtt_publisher import publish_device


# ============================================================
# LOGGING
# ============================================================
LOG_FILE = "/var/log/guardian_discovery.log"

logger = logging.getLogger("guardian.discovery")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

try:
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except PermissionError:
    pass  # Pas de droits root sur PC de dev → console seulement


def run_discovery():
    """Exécute un cycle complet de découverte des équipements."""
    init_db()
    leases = parse_leases()

    if not leases:
        logger.info("Aucun équipement dans le fichier de leases.")
        return

    logger.info("%d équipement(s) détecté(s).", len(leases))

    for lease in leases:
        vendor = get_vendor(lease["mac"])
        device_type, confidence = classify_device(lease["hostname"], vendor)

        device = {
            "mac":         lease["mac"],
            "ip":          lease["ip"],
            "hostname":    lease["hostname"] or "(inconnu)",
            "vendor":      vendor,
            "device_type": device_type,
            "confidence":  confidence,
            "timestamp":   now_iso(),
        }
        upsert_device(device)
        publish_device(device["mac"], device["ip"], device["hostname"],
               device["vendor"], device["device_type"], device["confidence"])

        logger.info(
            "MAC: %-18s IP: %-14s Hostname: %-20s Vendor: %-25s -> %s (%.0f%%)",
            device["mac"], device["ip"], device["hostname"],
            device["vendor"], device["device_type"], confidence * 100
        )


if __name__ == "__main__":
    daemon_mode = "--daemon" in sys.argv

    if daemon_mode:
        logger.info("=== Mode DAEMON — poll toutes les %ds ===", POLL_INTERVAL)
        while True:
            try:
                run_discovery()
            except Exception as e:
                logger.error("Erreur pendant la découverte : %s", e)
            time.sleep(POLL_INTERVAL)
    else:
        run_discovery()
        print("\n--- Contenu final de la base de données ---")
        for d in list_devices():
            print(dict(d))
