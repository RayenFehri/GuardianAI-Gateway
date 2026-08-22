"""
main_rules.py — Orchestrateur de la Partie 3 du CDC (Contrôle Parental)

Pipeline :
  lit les règles actives en base (db.py)
      -> applique chaque règle via rule_engine.py et dns_blocker.py
      -> journalise chaque action dans /var/log/guardian_rules.log

Sur le vrai Pi, ce script tourne via cron (toutes les minutes),
avec les droits root (nécessaires pour iptables et dnsmasq) :

    * * * * * /home/pi/gateway_project/venv/bin/python3 /home/pi/gateway_project/main_rules.py

Sur un PC de dev (sans droits root ni interface réseau réelle), lance-le
avec l'option --dry-run pour voir les commandes sans les exécuter :

    python3 main_rules.py --dry-run
"""

import sys
import logging
import logging.handlers
from db import init_db, list_rules
from rule_engine import block_device, unblock_device, should_be_blocked
from mqtt_publisher import publish_rule
from config import POLL_INTERVAL


# ============================================================
# LOGGING — fichier + console
# ============================================================
LOG_FILE = "/var/log/guardian_rules.log"

logger = logging.getLogger("guardian")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Handler fichier (avec rotation : max 1MB, garde 3 fichiers)
try:
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except PermissionError:
    pass  # Pas de droits root sur PC de dev → uniquement la console


def apply_rules(dry_run: bool = False):
    init_db()
    rules = list_rules(active_only=True)
    # On log en mode DEBUG pour ne pas polluer les logs toutes les minutes
    logger.debug("%d règle(s) active(s) trouvée(s) en base.", len(rules))

    expected_blocked_macs = set()
    expected_categories = set()
    mac_to_rule = {}

    # 1. Calculer l'état désiré (Expected State)
    for rule in rules:
        mac = rule["mac"].lower() if rule["mac"] else None
        
        if rule["rule_type"] == "block_device":
            if mac:
                expected_blocked_macs.add(mac)
                mac_to_rule[mac] = rule
        elif rule["rule_type"] == "schedule":
            if mac and rule["start_time"] and rule["end_time"]:
                if should_be_blocked(rule["start_time"], rule["end_time"]):
                    expected_blocked_macs.add(mac)
                    mac_to_rule[mac] = rule
        elif rule["rule_type"] == "block_category":
            if rule["target"]:
                expected_categories.add(rule["target"])
        else:
            logger.warning("Règle #%d : type '%s' inconnu.", rule["id"], rule["rule_type"])

    # 2. Synchronisation des MACs (iptables)
    from rule_engine import get_blocked_macs
    currently_blocked_macs = get_blocked_macs(dry_run=dry_run)

    # Débloquer ce qui ne doit plus l'être (Règle supprimée, inactive ou hors horaire)
    for mac in currently_blocked_macs - expected_blocked_macs:
        success = unblock_device(mac, dry_run=dry_run)
        if success:
            publish_rule(0, "unblock", mac, "sync_cleanup")
            logger.info("Synchronisation : DÉBLOQUÉ %s (règle supprimée/inactive/hors-plage)", mac)

    # Bloquer ce qui doit l'être mais ne l'est pas encore
    for mac in expected_blocked_macs - currently_blocked_macs:
        success = block_device(mac, dry_run=dry_run)
        if success:
            r = mac_to_rule.get(mac, {"id": 0, "rule_type": "sync"})
            publish_rule(r["id"], "block", mac, r["rule_type"])
            logger.info("Synchronisation : BLOQUÉ %s (Règle #%d)", mac, r["id"])

    # 3. Synchronisation des catégories DNS (dnsmasq)
    try:
        from dns_blocker import apply_dns_blocks
        apply_dns_blocks(expected_categories, dry_run=dry_run)
    except Exception as e:
        logger.error("Erreur lors de la synchronisation DNS : %s", e)


if __name__ == "__main__":
    import time
    dry_run_mode = "--dry-run" in sys.argv
    daemon_mode  = "--daemon"  in sys.argv

    if dry_run_mode:
        logger.info("=== Mode DRY-RUN : aucune commande ne sera exécutée ===")

    if daemon_mode:
        logger.info("=== Mode DAEMON — synchronisation toutes les %ds ===", POLL_INTERVAL)
        while True:
            try:
                apply_rules(dry_run=dry_run_mode)
            except Exception as e:
                logger.error("Erreur pendant apply_rules : %s", e)
            time.sleep(POLL_INTERVAL)
    else:
        apply_rules(dry_run=dry_run_mode)
