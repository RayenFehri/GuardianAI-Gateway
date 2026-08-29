"""
report_generator.py — Génération de rapports en langage naturel (Mistral AI)

Agrège les données d'activité réseau depuis PostgreSQL, puis envoie
un résumé structuré au LLM qui génère un rapport lisible par un parent
non technique, avec des suggestions de règles personnalisées.

Usage :
    python3 -m ai.report_generator          # rapport du jour
    python3 -m ai.report_generator --days 7 # rapport de la semaine
"""

import os
import logging
from datetime import datetime
from db import get_connection

log = logging.getLogger("guardian.ai")


def get_daily_stats(days: int = 1) -> dict:
    """
    Agrège les statistiques d'activité réseau des N derniers jours.
    Retourne un dict avec toutes les données nécessaires au rapport.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Appareils actifs
            cur.execute("""
                SELECT mac, ip, hostname, device_type,
                       MAX(last_seen) AS derniere_activite
                FROM devices
                WHERE last_seen > NOW() - INTERVAL '%s days'
                GROUP BY mac, ip, hostname, device_type
                ORDER BY derniere_activite DESC
            """, (days,))
            devices = [
                {"mac": r[0], "ip": r[1], "hostname": r[2],
                 "type": r[3], "last_seen": str(r[4])}
                for r in cur.fetchall()
            ]

            # 2. Requêtes DNS par appareil et par catégorie
            cur.execute("""
                SELECT ip, category, COUNT(*) AS nb
                FROM dns_events
                WHERE timestamp > NOW() - INTERVAL '%s days'
                GROUP BY ip, category
                ORDER BY nb DESC
            """, (days,))
            usage = {}
            for ip, category, nb in cur.fetchall():
                if ip not in usage:
                    usage[ip] = {}
                usage[ip][category] = nb

            # 3. Top domaines visités
            cur.execute("""
                SELECT domain, category, COUNT(*) AS nb
                FROM dns_events
                WHERE timestamp > NOW() - INTERVAL '%s days'
                GROUP BY domain, category
                ORDER BY nb DESC
                LIMIT 15
            """, (days,))
            top_domains = [
                {"domain": r[0], "category": r[1], "count": r[2]}
                for r in cur.fetchall()
            ]

            # 4. Anomalies détectées par l'IA
            cur.execute("""
                SELECT anomaly_type, severity, description, detected_at
                FROM ai_anomalies
                WHERE detected_at > NOW() - INTERVAL '%s days'
                ORDER BY detected_at DESC
            """, (days,))
            anomalies = [
                {"type": r[0], "severity": r[1],
                 "description": r[2], "date": str(r[3])}
                for r in cur.fetchall()
            ]

            # 5. Règles actuellement actives
            cur.execute("""
                SELECT mac, rule_type, target, start_time, end_time
                FROM rules WHERE active = TRUE
            """)
            rules = [
                {"mac": r[0], "type": r[1], "target": r[2],
                 "start": str(r[3]) if r[3] else None,
                 "end": str(r[4]) if r[4] else None}
                for r in cur.fetchall()
            ]

    finally:
        conn.close()

    return {
        "date": datetime.now().strftime("%d/%m/%Y"),
        "periode": f"{days} jour(s)",
        "devices": devices,
        "usage_par_ip": usage,
        "top_domains": top_domains,
        "anomalies": anomalies,
        "rules_actives": rules,
    }


def build_prompt(stats: dict) -> str:
    """
    Construit le prompt envoyé au LLM avec toutes les données agrégées.
    """
    prompt = f"""Tu es l'assistant IA de la passerelle parentale "GuardianAI Gateway".
Tu dois rédiger un rapport d'activité réseau destiné à un PARENT non technique.

Voici les données d'activité du réseau familial pour la période : {stats['periode']}
Date du rapport : {stats['date']}

=== APPAREILS CONNECTÉS ({len(stats['devices'])}) ===
"""
    for d in stats["devices"]:
        prompt += f"- {d['hostname'] or d['mac']} ({d['type'] or 'inconnu'}) — IP: {d['ip']}\n"

    prompt += f"\n=== ACTIVITÉ DNS PAR APPAREIL ===\n"
    for ip, categories in stats["usage_par_ip"].items():
        # Trouver le hostname
        hostname = ip
        for d in stats["devices"]:
            if d["ip"] == ip:
                hostname = d["hostname"] or ip
                break
        total = sum(categories.values())
        prompt += f"\n{hostname} ({total} requêtes) :\n"
        for cat, nb in sorted(categories.items(), key=lambda x: -x[1]):
            pct = (nb / total * 100) if total > 0 else 0
            prompt += f"  - {cat}: {nb} ({pct:.0f}%)\n"

    prompt += f"\n=== TOP DOMAINES ===\n"
    for d in stats["top_domains"]:
        prompt += f"- {d['domain']} ({d['category']}) : {d['count']} requêtes\n"

    if stats["anomalies"]:
        prompt += f"\n=== ANOMALIES DÉTECTÉES PAR L'IA ({len(stats['anomalies'])}) ===\n"
        for a in stats["anomalies"]:
            prompt += f"- [{a['severity'].upper()}] {a['description']}\n"

    if stats["rules_actives"]:
        prompt += f"\n=== RÈGLES DE CONTRÔLE ACTIVES ===\n"
        for r in stats["rules_actives"]:
            prompt += f"- {r['type']} sur {r['mac'] or 'tous'}"
            if r["target"]:
                prompt += f" (cible: {r['target']})"
            if r["start"] and r["end"]:
                prompt += f" de {r['start']} à {r['end']}"
            prompt += "\n"

    prompt += """
=== INSTRUCTIONS ===
Rédige un rapport clair et concis en français avec :

1. **Résumé** : Vue d'ensemble de l'activité (2-3 phrases)
2. **Détails par appareil** : Usage principal de chaque appareil
3. **Alertes** : Si des anomalies ont été détectées, les expliquer simplement
4. **Suggestions** : Propose 2-3 règles de contrôle parental concrètes basées sur les données
   (ex: "Bloquer les réseaux sociaux après 21h", "Limiter le streaming à 2h/jour")
   Chaque suggestion doit préciser : quel appareil, quelle action, pourquoi

Utilise des emojis pour rendre le rapport visuellement agréable.
Sois bienveillant mais direct. Le parent doit comprendre en 30 secondes.
"""
    return prompt


def generate_report(days: int = 1) -> str:
    """
    Génère un rapport complet en appelant l'API Mistral AI.
    Retourne le texte du rapport.
    """
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "❌ Erreur : MISTRAL_API_KEY non définie dans le fichier .env"

    # 1. Récupérer les statistiques
    stats = get_daily_stats(days)

    if not stats["devices"] and not stats["top_domains"]:
        return "ℹ️ Aucune activité réseau à reporter pour cette période."

    # 2. Construire le prompt
    prompt = build_prompt(stats)

    # 3. Appeler Mistral AI
    try:
        from mistralai.client import Mistral
        client = Mistral(api_key=api_key)
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        report = response.choices[0].message.content
        return report
    except Exception as e:
        log.error("Erreur API Mistral : %s", e)
        return f"❌ Erreur lors de l'appel à Mistral AI : {e}"


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    days = 1
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        days = int(sys.argv[idx + 1])

    print(f"\n📊 Génération du rapport ({days} jour(s))...\n")
    report = generate_report(days)
    print(report)
