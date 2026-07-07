"""
main_discovery.py — Orchestrateur de la Partie 1 du CDC

Pipeline complet :
  fichier de leases DHCP
      -> parsing (discovery.py)
      -> résolution fabricant (oui_lookup.py)
      -> classification du type d'équipement (classifier.py)
      -> sauvegarde en base (db.py)

Sur le vrai Pi, tu lanceras ce script toutes les 30-60 secondes via cron
(cf. UC-01 du CDC : détection d'un nouvel équipement).
"""

from discovery import parse_leases, now_iso
from oui_lookup import get_vendor
from classifier import classify_device
from db import init_db, upsert_device, list_devices


def run_discovery():
    init_db()
    leases = parse_leases()
    print(f"{len(leases)} équipement(s) trouvé(s) dans le fichier de leases.\n")

    for lease in leases:
        vendor = get_vendor(lease["mac"])
        device_type, confidence = classify_device(lease["hostname"], vendor)

        device = {
            "mac": lease["mac"],
            "ip": lease["ip"],
            "hostname": lease["hostname"] or "(inconnu)",
            "vendor": vendor,
            "device_type": device_type,
            "confidence": confidence,
            "timestamp": now_iso(),
        }
        upsert_device(device)

        print(f"  MAC: {device['mac']:<18} "
              f"IP: {device['ip']:<14} "
              f"Hostname: {device['hostname']:<20} "
              f"Vendor: {device['vendor']:<25} "
              f"-> Type: {device['device_type']:<15} (confiance: {device['confidence']:.0%})")

    print("\n--- Contenu final de la base de données ---")
    for d in list_devices():
        print(dict(d))


if __name__ == "__main__":
    run_discovery()
