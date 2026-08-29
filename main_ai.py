"""
main_ai.py — Orchestrateur de la Partie 5 du CDC (Intelligence Artificielle)

Pipeline :
  base de données (dns_events + devices)
      -> détection d'anomalies (ai/anomaly_detector.py)
      -> sauvegarde en base (table ai_anomalies)
      -> publication MQTT (topic guardian/alerts)
      -> journalisation

Deux modes de fonctionnement :
  - One-shot : python3 main_ai.py
  - Daemon   : python3 main_ai.py --daemon
    (analyse toutes les POLL_INTERVAL secondes)
"""

import sys
import time
import logging
import logging.handlers
from ai.anomaly_detector import run_all_detectors
from db import init_db, insert_anomaly, is_anomaly_duplicate
from mqtt_publisher import publish_alert
from config import POLL_INTERVAL

# ════════════════════════════════════════════════════════════
# LOGGING
# ════════════════════════════════════════════════════════════
LOG_FILE = "/var/log/guardian_ai.log"

logger = logging.getLogger("guardian.ai")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

try:
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except PermissionError:
    pass  # Pas de droits root sur PC de dev → console seulement


def run_ai_analysis():
    """Exécute un cycle complet d'analyse IA."""
    init_db()
    anomalies = run_all_detectors()

    if not anomalies:
        logger.debug("Aucune anomalie détectée.")
        return

    new_count = 0
    for anomaly in anomalies:
        # Évite les doublons : ne pas re-signaler la même anomalie
        if is_anomaly_duplicate(
            anomaly.get("mac"),
            anomaly["anomaly_type"],
            hours_back=6
        ):
            continue

        # Sauvegarde en base
        insert_anomaly(anomaly)
        new_count += 1

        # Publication MQTT
        publish_alert(
            alert_type=anomaly["anomaly_type"],
            message=anomaly["description"],
            mac=anomaly.get("mac"),
        )

        # Log
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
            anomaly["severity"], "•"
        )
        logger.info(
            "%s [%s] %s",
            icon, anomaly["severity"].upper(), anomaly["description"]
        )

    if new_count > 0:
        logger.info("%d nouvelle(s) anomalie(s) signalée(s).", new_count)


if __name__ == "__main__":
    daemon_mode = "--daemon" in sys.argv
    report_mode = "--report" in sys.argv

    if report_mode:
        from ai.report_generator import generate_report
        days = 1
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            days = int(sys.argv[idx + 1])
        logger.info("Génération du rapport IA (%d jour(s))...", days)
        report = generate_report(days)
        print(report)

    elif daemon_mode:
        logger.info("=== Mode DAEMON — analyse IA toutes les %ds ===", POLL_INTERVAL)
        while True:
            try:
                run_ai_analysis()
            except Exception as e:
                logger.error("Erreur pendant l'analyse IA : %s", e)
            time.sleep(POLL_INTERVAL)
    else:
        run_ai_analysis()

