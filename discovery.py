"""
discovery.py — Découverte des équipements (Partie 1 du CDC)

Lit le fichier de leases DHCP :
- Sur PC (dev)    : fake_dnsmasq.leases (simulé)
- Sur Pi OpenWrt  : /tmp/dhcp.leases (réel, généré par dnsmasq)

Le chemin est centralisé dans config.py — une seule ligne à changer
pour passer du PC au Pi.
"""

from pathlib import Path
from datetime import datetime, timezone
from config import LEASES_FILE


def parse_leases(path: Path = LEASES_FILE) -> list[dict]:
    """Parse le fichier de leases DHCP et retourne une liste de dicts."""
    devices = []
    if not path.exists():
        print(f"Fichier introuvable : {path}")
        return devices

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            ts, mac, ip, hostname = parts[0], parts[1], parts[2], parts[3]
            devices.append({
                "mac": mac,
                "ip": ip,
                "hostname": None if hostname == "*" else hostname,
                "lease_timestamp": ts,
            })
    return devices


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    for d in parse_leases():
        print(d)