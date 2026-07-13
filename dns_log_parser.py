"""
dns_log_parser.py — Parsing du log DNS (Partie 2 du CDC)

Lit le fichier de log DNS :
- Sur PC (dev)    : fake_dnsmasq.log (simulé)
- Sur Pi OpenWrt  : /tmp/log/dnsmasq.log (réel)

Le chemin est centralisé dans config.py.
"""

import re
from pathlib import Path
from datetime import datetime
from config import DNS_LOG_FILE

LOG_PATTERN = re.compile(
    r"^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"dnsmasq\[\d+\]:\s+query\[\w+\]\s+(?P<domain>\S+)\s+from\s+(?P<ip>[\d.]+)"
)


def parse_dns_log(path: Path = DNS_LOG_FILE, year: int = None) -> list[dict]:
    """Parse le fichier de log DNS et retourne une liste d'événements."""
    if year is None:
        year = datetime.now().year

    events = []
    if not path.exists():
        print(f"Fichier introuvable : {path}")
        return events

    with open(path) as f:
        for line in f:
            match = LOG_PATTERN.match(line.strip())
            if not match:
                continue
            data = match.groupdict()
            dt_str = f"{year} {data['month']} {data['day']} {data['time']}"
            timestamp = datetime.strptime(dt_str, "%Y %b %d %H:%M:%S")
            events.append({
                "ip": data["ip"],
                "domain": data["domain"],
                "timestamp": timestamp,
            })
    return events


if __name__ == "__main__":
    for e in parse_dns_log():
        print(e)