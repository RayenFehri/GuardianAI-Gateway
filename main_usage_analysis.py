"""
main_usage_analysis.py — Orchestrateur de la Partie 2 du CDC

Pipeline complet :
  fichier de log DNS
      -> parsing (dns_log_parser.py)
      -> classification par catégorie (categories.py)
      -> sauvegarde en base (db.py, table dns_events)
      -> affichage des statistiques d'usage par équipement/catégorie

Sur le vrai Pi, tu lanceras ce script régulièrement (cron) pour ingérer
les nouvelles lignes du log au fur et à mesure.
"""

from dns_log_parser import parse_dns_log
from categories import classify_domain
from db import init_db, insert_dns_events, usage_stats_by_category


def run_usage_analysis():
    init_db()
    raw_events = parse_dns_log()
    print(f"{len(raw_events)} requête(s) DNS trouvée(s) dans le log.\n")

    enriched_events = []
    for event in raw_events:
        category = classify_domain(event["domain"])
        enriched_events.append({
            "ip": event["ip"],
            "domain": event["domain"],
            "category": category,
            "timestamp": event["timestamp"],
        })
        print(f"  {event['timestamp']}  {event['ip']:<15} {event['domain']:<20} -> {category}")

    insert_dns_events(enriched_events)

    print("\n--- Statistiques d'usage par équipement et catégorie ---")
    for stat in usage_stats_by_category():
        print(f"  IP: {stat['ip']:<15} Catégorie: {stat['category']:<18} "
              f"Requêtes: {stat['nb_requetes']}")


if __name__ == "__main__":
    run_usage_analysis()