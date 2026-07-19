"""
rule_engine.py — Application des règles de contrôle parental (Partie 3 du CDC)

Traduit les règles stockées en base en commandes iptables réelles, appliquées
sur l'interface WiFi du Pi (uap0, où sont connectés les appareils enfants).

Sur le vrai Pi, ce module a besoin des droits root pour manipuler iptables
(lancer les scripts avec sudo, ou via un cron root).

Stratégie retenue pour la Partie 3 :
  - block_device : DROP total du trafic de ce MAC (identifié via -m mac)
    Utiliser le MAC plutôt que l'IP évite le contournement par changement
    d'IP (l'appareil garde la même adresse MAC tant qu'il est physiquement
    le même).
"""

import subprocess
from config import LAN_INTERFACE

# Préfixe utilisé pour retrouver/nettoyer facilement nos propres règles
# iptables, sans toucher aux règles système existantes (NAT, etc.)
RULE_COMMENT = "guardian_gateway_rule"


def _run(cmd: list[str], dry_run: bool = False) -> bool:
    """
    Exécute une commande iptables. En dry_run, affiche seulement la commande
    sans l'exécuter (utile pour développer/tester sur un PC sans droits root
    ni interface réseau réelle).
    """
    printable = " ".join(cmd)
    if dry_run:
        print(f"[DRY-RUN] {printable}")
        return True
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erreur iptables : {printable}\n  -> {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print("iptables introuvable sur ce système (normal sur un PC de dev).")
        return False


def block_device(mac: str, dry_run: bool = False) -> bool:
    """
    Bloque tout le trafic réseau d'un équipement, identifié par son adresse
    MAC, sur l'interface WiFi du Pi (LAN_INTERFACE, ex: uap0).
    """
    cmd = [
        "iptables", "-A", "FORWARD",
        "-i", LAN_INTERFACE,
        "-m", "mac", "--mac-source", mac.lower(),
        "-m", "comment", "--comment", RULE_COMMENT,
        "-j", "DROP",
    ]
    return _run(cmd, dry_run=dry_run)


def unblock_device(mac: str, dry_run: bool = False) -> bool:
    """Retire le blocage d'un équipement (annule block_device)."""
    cmd = [
        "iptables", "-D", "FORWARD",
        "-i", LAN_INTERFACE,
        "-m", "mac", "--mac-source", mac.lower(),
        "-m", "comment", "--comment", RULE_COMMENT,
        "-j", "DROP",
    ]
    return _run(cmd, dry_run=dry_run)


def list_active_iptables_rules(dry_run: bool = False) -> str:
    """Retourne la sortie de `iptables -L FORWARD` pour debug/vérification."""
    cmd = ["iptables", "-L", "FORWARD", "-v", "-n"]
    if dry_run:
        print(f"[DRY-RUN] {' '.join(cmd)}")
        return ""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Impossible de lister les règles iptables : {e}")
        return ""


if __name__ == "__main__":
    # Test en dry-run (aucune commande réellement exécutée) : sûr sur un PC.
    print("=== Test du rule_engine en mode DRY-RUN ===")
    block_device("f0:67:28:90:81:1d", dry_run=True)
    unblock_device("f0:67:28:90:81:1d", dry_run=True)