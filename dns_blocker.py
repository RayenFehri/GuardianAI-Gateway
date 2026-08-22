"""
dns_blocker.py — Blocage de domaines par catégorie via dnsmasq (Partie 3B)

Écrit des règles dans /etc/dnsmasq.d/guardian_blocks.conf :
    address=/tiktok.com/0.0.0.0
→ Quand un appareil demande l'IP de tiktok.com → reçoit 0.0.0.0 → site inaccessible.

Nécessite les droits root (sudo) pour écrire dans /etc/dnsmasq.d/.
"""

import subprocess
from pathlib import Path
from categories import DOMAIN_CATEGORIES

BLOCK_FILE = Path("/etc/dnsmasq.d/guardian_blocks.conf")


def apply_dns_blocks(categories: set[str], dry_run: bool = False) -> int:
    """
    Applique le blocage pour un ensemble de catégories en une seule fois.
    Si l'ensemble est vide, retire tous les blocages.
    Évite de redémarrer dnsmasq si la configuration n'a pas changé.
    """
    if not categories:
        unblock_all(dry_run=dry_run)
        return 0

    domains = []
    for category in categories:
        domains.extend([d for d, c in DOMAIN_CATEGORIES.items() if c == category])
    
    # Dédoublonner et trier pour avoir un fichier stable
    domains = sorted(list(set(domains)))

    if not domains:
        unblock_all(dry_run=dry_run)
        return 0

    lines = [f"address=/{domain}/0.0.0.0\n" for domain in domains]
    content = f"# Catégories bloquées : {','.join(sorted(categories))}\n" + "".join(lines)

    # Optimisation : on ne réécrit/redémarre pas si rien n'a changé
    if BLOCK_FILE.exists():
        with open(BLOCK_FILE, "r") as f:
            if f.read() == content:
                return len(domains)

    if dry_run:
        print(f"[DRY-RUN] Écriture dans {BLOCK_FILE} ({len(domains)} domaines) :")
        return len(domains)

    with open(BLOCK_FILE, "w") as f:
        f.write(content)

    reload_dnsmasq(dry_run)
    print(f"{len(domains)} domaine(s) bloqué(s) au total pour {list(categories)}.")
    return len(domains)


def unblock_all(dry_run: bool = False):
    """Retire tous les blocages DNS (supprime le fichier de config)."""
    if dry_run:
        print(f"[DRY-RUN] Suppression de {BLOCK_FILE}")
        return

    if BLOCK_FILE.exists():
        BLOCK_FILE.unlink()
        reload_dnsmasq()
        print("Tous les blocages DNS retirés.")
    else:
        print("Aucun blocage DNS actif.")


def reload_dnsmasq(dry_run: bool = False):
    """Recharge dnsmasq pour appliquer les changements."""
    cmd = ["systemctl", "restart", "dnsmasq"]
    if dry_run:
        print(f"[DRY-RUN] {' '.join(cmd)}")
        return
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("dnsmasq rechargé.")
    except subprocess.CalledProcessError as e:
        print(f"Erreur reload dnsmasq : {e.stderr.decode().strip()}")


if __name__ == "__main__":
    print("=== Test DRY-RUN blocage catégorie 'reseaux_sociaux' ===")
    apply_dns_blocks({"reseaux_sociaux"}, dry_run=True)
