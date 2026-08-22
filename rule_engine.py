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

import logging
import subprocess
from config import LAN_INTERFACE, WAN_INTERFACE
from datetime import datetime, time as dtime

log = logging.getLogger(__name__)

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


def is_already_blocked(mac: str) -> bool:
    """
    Vérifie si une règle de blocage existe déjà pour ce MAC dans iptables.
    Utilise iptables -C (check) qui retourne 0 si la règle existe, 1 sinon.
    """
    cmd = [
        "iptables", "-C", "FORWARD",
        "-i", LAN_INTERFACE,
        "-m", "mac", "--mac-source", mac.lower(),
        "-m", "comment", "--comment", RULE_COMMENT,
        "-j", "DROP",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_blocked_macs(dry_run: bool = False) -> set[str]:
    """Retourne la liste des MACs actuellement bloqués par nos règles."""
    macs = set()
    if dry_run:
        return macs
    try:
        result = subprocess.run(
            ["iptables", "-L", "FORWARD", "-n", "-v"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if RULE_COMMENT in line and "MAC" in line:
                parts = line.split()
                if "MAC" in parts:
                    idx = parts.index("MAC")
                    if idx + 1 < len(parts):
                        macs.add(parts[idx + 1].lower())
    except Exception as e:
        log.error("Erreur lecture iptables : %s", e)
    return macs


def _get_accept_position() -> int:
    """
    Trouve la position de la règle ACCEPT uap0→wlan0 dans FORWARD.
    Les règles guardian DROP doivent être insérées AVANT cette position
    pour être évaluées en premier.
    Retourne 0 si la règle ACCEPT n'est pas trouvée.
    """
    try:
        result = subprocess.run(
            ["iptables", "-L", "FORWARD", "--line-numbers", "-n", "-v"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if "ACCEPT" in line and LAN_INTERFACE in line and WAN_INTERFACE in line:
                return int(line.split()[0])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return 0


def ensure_forward_accept(dry_run: bool = False) -> None:
    """
    S'assure que les règles ACCEPT pour le relais AP → Internet existent.
    Crée les règles si elles sont manquantes (idempotent).
    """
    if _get_accept_position() > 0:
        return  # Déjà en place

    log.info("Création des règles FORWARD ACCEPT (uap0 ↔ wlan0)...")
    _run(["iptables", "-A", "FORWARD",
          "-i", LAN_INTERFACE, "-o", WAN_INTERFACE, "-j", "ACCEPT"], dry_run=dry_run)
    _run(["iptables", "-I", "FORWARD", "1",
          "-i", WAN_INTERFACE, "-o", LAN_INTERFACE,
          "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"], dry_run=dry_run)


def block_device(mac: str, dry_run: bool = False) -> bool:
    """
    Bloque tout le trafic réseau d'un équipement, identifié par son adresse
    MAC, sur l'interface WiFi du Pi (LAN_INTERFACE, ex: uap0).
    Idempotent : n'ajoute pas de doublon si la règle existe déjà.

    Insère la règle AVANT la règle ACCEPT générale, pour qu'elle soit
    évaluée en priorité par iptables.
    """
    if not dry_run and is_already_blocked(mac):
        log.info("block_device(%s) : règle déjà présente, ignorée.", mac)
        return True  # déjà bloqué, pas de doublon

    # Trouve la position de la règle ACCEPT pour insérer AVANT
    pos = _get_accept_position()
    if pos > 0:
        cmd = [
            "iptables", "-I", "FORWARD", str(pos),
            "-i", LAN_INTERFACE,
            "-m", "mac", "--mac-source", mac.lower(),
            "-m", "comment", "--comment", RULE_COMMENT,
            "-j", "DROP",
        ]
    else:
        # Pas de règle ACCEPT trouvée → append classique
        cmd = [
            "iptables", "-A", "FORWARD",
            "-i", LAN_INTERFACE,
            "-m", "mac", "--mac-source", mac.lower(),
            "-m", "comment", "--comment", RULE_COMMENT,
            "-j", "DROP",
        ]
    success = _run(cmd, dry_run=dry_run)
    if success and not dry_run:
        log.info("block_device(%s) : règle ajoutée (position %d).", mac, pos if pos > 0 else -1)
    return success


def unblock_device(mac: str, dry_run: bool = False) -> bool:
    """
    Retire le blocage d'un équipement (annule block_device).
    Idempotent : ne plante pas si la règle n'existe pas.
    """
    if not dry_run and not is_already_blocked(mac):
        log.info("unblock_device(%s) : aucune règle à retirer.", mac)
        return True  # déjà débloqué

    cmd = [
        "iptables", "-D", "FORWARD",
        "-i", LAN_INTERFACE,
        "-m", "mac", "--mac-source", mac.lower(),
        "-m", "comment", "--comment", RULE_COMMENT,
        "-j", "DROP",
    ]
    success = _run(cmd, dry_run=dry_run)
    if success and not dry_run:
        log.info("unblock_device(%s) : règle retirée.", mac)
    return success


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



def should_be_blocked(start_time: str, end_time: str) -> bool:
    """
    Retourne True si l'heure actuelle est dans la plage [start_time, end_time].
    Gère le cas "nuit" où start > end (ex: 20:00 → 08:00).

    start_time / end_time : chaînes "HH:MM" ou "HH:MM:SS"
    """
    now = datetime.now().time().replace(second=0, microsecond=0)

    def parse(t):
        parts = str(t).split(":")
        return dtime(int(parts[0]), int(parts[1]))

    start = parse(start_time)
    end   = parse(end_time)

    if start <= end:
        # Plage normale : ex 08:00 → 18:00
        return start <= now <= end
    else:
        # Plage nocturne : ex 20:00 → 08:00
        return now >= start or now <= end


if __name__ == "__main__":
    # Test en dry-run (aucune commande réellement exécutée) : sûr sur un PC.
    print("=== Test du rule_engine en mode DRY-RUN ===")
    block_device("f0:67:28:90:81:1d", dry_run=True)
    unblock_device("f0:67:28:90:81:1d", dry_run=True)