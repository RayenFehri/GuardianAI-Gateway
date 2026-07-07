"""
discovery.py — Découverte des équipements (Partie 1 du CDC)

Sur le vrai Raspberry Pi (une fois configuré avec dnsmasq), ce fichier
se trouve à : /var/lib/misc/dnsmasq.leases
Format d'une ligne : <timestamp> <mac> <ip> <hostname> <client-id>

En attendant le Pi, on lit un faux fichier généré à la main
(fake_dnsmasq.leases) qui a exactement le même format.
"""

from pathlib import Path
from datetime import datetime, timezone

# Sur le vrai Pi, remplace ce chemin par : "/var/lib/misc/dnsmasq.leases"
LEASES_FILE = Path(__file__).parent / "fake_dnsmasq.leases"


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
                continue  # ligne malformée, on l'ignore
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
