"""
main_rules.py — Orchestrateur de la Partie 3 du CDC (Contrôle Parental)

Pipeline :
  lit les règles actives en base (db.py)
      -> applique chaque règle 'block_device' via rule_engine.py
      -> affiche un résumé

Sur le vrai Pi, ce script doit tourner via cron (toutes les minutes),
avec les droits root (nécessaires pour iptables) :

    * * * * * cd /root/GuardianAI-Gateway && sudo venv/bin/python3 main_rules.py

Sur un PC de dev (sans droits root ni interface réseau réelle), lance-le
avec l'option --dry-run pour voir les commandes sans les exécuter :

    python3 main_rules.py --dry-run
"""

import sys
from db import init_db, list_rules
from rule_engine import block_device, unblock_device


def apply_rules(dry_run: bool = False):
    init_db()
    rules = list_rules(active_only=True)
    print(f"{len(rules)} règle(s) active(s) trouvée(s) en base.\n")

    for rule in rules:
        if rule["rule_type"] == "block_device":
            if not rule["mac"]:
                print(f"  Règle #{rule['id']} ignorée : aucun MAC renseigné.")
                continue
            success = block_device(rule["mac"], dry_run=dry_run)
            status = "appliquée" if success else "ÉCHEC"
            print(f"  Règle #{rule['id']} (block_device {rule['mac']}) -> {status}")
        else:
            print(f"  Règle #{rule['id']} : type '{rule['rule_type']}' "
                  f"pas encore géré par le moteur (à venir).")


if __name__ == "__main__":
    dry_run_mode = "--dry-run" in sys.argv
    if dry_run_mode:
        print("=== Mode DRY-RUN : aucune commande iptables ne sera exécutée ===\n")
    apply_rules(dry_run=dry_run_mode)