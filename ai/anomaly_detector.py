"""
anomaly_detector.py — Détection d'anomalies sur les usages réseau

Analyse l'historique des événements DNS stockés en base PostgreSQL
pour détecter des comportements inhabituels :

  1. Usage nocturne      : requêtes DNS entre 23h et 6h
  2. Catégorie suspecte  : premier accès à une catégorie sensible
  3. Pic de catégorie    : hausse brutale vs la moyenne des 7 derniers jours
  4. Nouvel appareil     : un MAC jamais vu apparaît sur le réseau

Chaque détecteur retourne une liste de dicts "anomalie" contenant :
  - mac, ip          : l'équipement concerné
  - anomaly_type     : identifiant du type d'anomalie
  - severity         : 'info', 'warning', 'critical'
  - description      : message lisible en français

Usage :
    python3 -m ai.anomaly_detector          # test one-shot
"""

import logging
from datetime import datetime, timedelta
from db import get_connection
import numpy as np
from sklearn.ensemble import IsolationForest

log = logging.getLogger("guardian.ai")

# ════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════

# Heures considérées comme "nocturnes" (0-indexé, 24h)
NIGHT_START = 23  # 23h00
NIGHT_END = 6     # 06h00

# Catégories sensibles qui déclenchent une alerte dès le 1er accès
SUSPECT_CATEGORIES = {"adulte", "paris_jeux_argent"}

# Seuil de hausse pour déclencher un "pic de catégorie"
# 2.0 = la catégorie a au moins 2x plus de requêtes que la moyenne
SPIKE_THRESHOLD = 2.0

# Nombre minimum de requêtes pour considérer un pic (évite les faux positifs)
SPIKE_MIN_REQUESTS = 5


# ════════════════════════════════════════════════════════════
# DÉTECTEUR 1 : Usage Nocturne
# ════════════════════════════════════════════════════════════

def detect_night_usage(hours_back: int = 24) -> list[dict]:
    """
    Détecte les appareils ayant généré des requêtes DNS pendant
    les heures nocturnes (entre NIGHT_START et NIGHT_END).

    Logique SQL :
      - On filtre les dns_events des dernières `hours_back` heures
      - On ne garde que ceux dont l'heure est >= 23 OU < 6
      - On groupe par IP pour compter les requêtes nocturnes
    """
    conn = get_connection()
    anomalies = []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ip, COUNT(*) AS nb,
                       MIN(timestamp) AS first_at,
                       MAX(timestamp) AS last_at
                FROM dns_events
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                  AND (EXTRACT(HOUR FROM timestamp) >= %s
                       OR EXTRACT(HOUR FROM timestamp) < %s)
                GROUP BY ip
                HAVING COUNT(*) >= 3
                ORDER BY nb DESC
            """, (hours_back, NIGHT_START, NIGHT_END))

            for row in cur.fetchall():
                ip, nb, first_at, last_at = row
                # Chercher le MAC et hostname correspondants
                mac, hostname = _resolve_device(cur, ip)
                anomalies.append({
                    "mac": mac,
                    "ip": ip,
                    "anomaly_type": "night_usage",
                    "severity": "warning",
                    "description": (
                        f"Usage nocturne détecté : {hostname or ip} "
                        f"a généré {nb} requête(s) entre "
                        f"{first_at.strftime('%Hh%M')} et {last_at.strftime('%Hh%M')}."
                    ),
                })
    finally:
        conn.close()
    return anomalies


# ════════════════════════════════════════════════════════════
# DÉTECTEUR 2 : Catégorie Suspecte (1er accès)
# ════════════════════════════════════════════════════════════

def detect_suspect_category(hours_back: int = 24) -> list[dict]:
    """
    Alerte dès qu'un appareil accède pour la première fois à une
    catégorie sensible (adulte, paris/jeux d'argent).

    On compare les événements récents avec l'historique complet :
    si un domaine d'une catégorie suspecte apparaît pour la 1ère fois
    pour cet appareil, on génère une alerte critique.
    """
    conn = get_connection()
    anomalies = []
    try:
        with conn.cursor() as cur:
            # Événements récents dans des catégories suspectes
            placeholders = ",".join(["%s"] * len(SUSPECT_CATEGORIES))
            cur.execute(f"""
                SELECT DISTINCT ip, domain, category
                FROM dns_events
                WHERE timestamp > NOW() - INTERVAL '{hours_back} hours'
                  AND category IN ({placeholders})
            """, tuple(SUSPECT_CATEGORIES))

            for ip, domain, category in cur.fetchall():
                # Vérifier si c'est un PREMIER accès (pas d'historique antérieur)
                cur.execute("""
                    SELECT COUNT(*) FROM dns_events
                    WHERE ip = %s AND category = %s
                      AND timestamp <= NOW() - INTERVAL '%s hours'
                """, (ip, category, hours_back))
                previous_count = cur.fetchone()[0]

                if previous_count == 0:
                    mac, hostname = _resolve_device(cur, ip)
                    anomalies.append({
                        "mac": mac,
                        "ip": ip,
                        "anomaly_type": "suspect_category",
                        "severity": "critical",
                        "description": (
                            f"⚠️ Premier accès à la catégorie '{category}' "
                            f"par {hostname or ip} (domaine : {domain})."
                        ),
                    })
    finally:
        conn.close()
    return anomalies


# ════════════════════════════════════════════════════════════
# DÉTECTEUR 3 : Pic de Catégorie
# ════════════════════════════════════════════════════════════

def detect_category_spike() -> list[dict]:
    """
    Compare l'activité d'aujourd'hui par catégorie et par appareil
    avec la moyenne des 7 derniers jours. Si le ratio dépasse
    SPIKE_THRESHOLD, on signale un pic.

    Exemple : si un appareil fait habituellement 10 requêtes "jeux"
    par jour et qu'il en fait 25 aujourd'hui → ratio 2.5 → alerte.
    """
    conn = get_connection()
    anomalies = []
    try:
        with conn.cursor() as cur:
            # Activité d'aujourd'hui par (ip, catégorie)
            cur.execute("""
                SELECT ip, category, COUNT(*) AS today_count
                FROM dns_events
                WHERE timestamp::date = CURRENT_DATE
                  AND category != 'autre'
                GROUP BY ip, category
                HAVING COUNT(*) >= %s
            """, (SPIKE_MIN_REQUESTS,))
            today_stats = cur.fetchall()

            for ip, category, today_count in today_stats:
                # Moyenne des 7 derniers jours (hors aujourd'hui)
                cur.execute("""
                    SELECT COALESCE(
                        COUNT(*)::float / GREATEST(
                            (CURRENT_DATE - MIN(timestamp::date))::int, 1
                        ), 0
                    ) AS daily_avg
                    FROM dns_events
                    WHERE ip = %s AND category = %s
                      AND timestamp::date < CURRENT_DATE
                      AND timestamp > NOW() - INTERVAL '7 days'
                """, (ip, category))
                daily_avg = cur.fetchone()[0] or 0

                if daily_avg > 0:
                    ratio = today_count / daily_avg
                    if ratio >= SPIKE_THRESHOLD:
                        mac, hostname = _resolve_device(cur, ip)
                        anomalies.append({
                            "mac": mac,
                            "ip": ip,
                            "anomaly_type": "category_spike",
                            "severity": "warning",
                            "description": (
                                f"Pic d'activité '{category}' pour {hostname or ip} : "
                                f"{today_count} requêtes aujourd'hui "
                                f"(moyenne 7j : {daily_avg:.0f}, ratio : x{ratio:.1f})."
                            ),
                        })
    finally:
        conn.close()
    return anomalies


# ════════════════════════════════════════════════════════════
# DÉTECTEUR 4 : Nouvel Appareil Inconnu
# ════════════════════════════════════════════════════════════

def detect_new_device(hours_back: int = 1) -> list[dict]:
    """
    Alerte quand un appareil est vu pour la première fois dans
    la dernière heure (first_seen récent).
    """
    conn = get_connection()
    anomalies = []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT mac, ip, hostname, vendor, device_type
                FROM devices
                WHERE first_seen > NOW() - INTERVAL '%s hours'
            """, (hours_back,))

            for mac, ip, hostname, vendor, device_type in cur.fetchall():
                label = hostname or vendor or mac
                anomalies.append({
                    "mac": mac,
                    "ip": ip,
                    "anomaly_type": "new_device",
                    "severity": "info",
                    "description": (
                        f"Nouvel appareil détecté : {label} "
                        f"({device_type or 'type inconnu'}, "
                        f"fabricant : {vendor or 'inconnu'})."
                    ),
                })
    finally:
        conn.close()
    return anomalies


# ════════════════════════════════════════════════════════════
# UTILITAIRES
# ════════════════════════════════════════════════════════════

def _resolve_device(cursor, ip: str) -> tuple[str, str]:
    """Retrouve le MAC et hostname d'un appareil à partir de son IP."""
    cursor.execute(
        "SELECT mac, hostname FROM devices WHERE ip = %s LIMIT 1", (ip,)
    )
    row = cursor.fetchone()
    if row:
        return row[0], row[1]
    return None, None


def _extract_features() -> tuple[np.ndarray, list[dict]]:
    """
    Transforme les dns_events des 7 derniers jours en features numériques.
    Chaque ligne = 1 heure d'activité pour 1 appareil.
    Retourne (tableau NumPy, métadonnées pour identifier chaque ligne).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ip,
                    DATE_TRUNC('hour', timestamp) AS heure_fenetre,
                    COUNT(*) AS nb_requetes,
                    COUNT(*) FILTER (WHERE category = 'reseaux_sociaux') AS nb_social,
                    COUNT(*) FILTER (WHERE category = 'jeux') AS nb_jeux,
                    COUNT(*) FILTER (WHERE category IN ('streaming_video', 'streaming_audio')) AS nb_streaming,
                    COUNT(DISTINCT domain) AS nb_domaines,
                    EXTRACT(HOUR FROM DATE_TRUNC('hour', timestamp)) AS heure,
                    CASE WHEN EXTRACT(DOW FROM DATE_TRUNC('hour', timestamp)) IN (0, 6)
                         THEN 1 ELSE 0 END AS weekend
                FROM dns_events
                WHERE timestamp > NOW() - INTERVAL '7 days'
                GROUP BY ip, DATE_TRUNC('hour', timestamp)
                ORDER BY heure_fenetre
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return np.array([]), []

    metadata = [{"ip": r[0], "heure_fenetre": r[1]} for r in rows]
    features = np.array([[r[2], r[3], r[4], r[5], r[6], r[7], r[8]] for r in rows], dtype=float)
    return features, metadata


def detect_ml_anomaly() -> list[dict]:
    """
    Détecteur basé sur Isolation Forest (scikit-learn).
    Apprend le comportement normal depuis l'historique DNS,
    puis signale les fenêtres horaires anormales.
    """
    features, metadata = _extract_features()

    # Pas assez de données pour entraîner le modèle (minimum 24 fenêtres)
    if len(features) < 24:
        log.debug("ML : pas assez de données (%d lignes, minimum 24).", len(features))
        return []

    model = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
    model.fit(features)
    predictions = model.predict(features)
    scores = model.decision_function(features)

    anomalies = []
    for i, pred in enumerate(predictions):
        if pred == -1:  # -1 = anomalie, 1 = normal
            meta = metadata[i]
            conn2 = get_connection()
            try:
                with conn2.cursor() as cur2:
                    mac, hostname = _resolve_device(cur2, meta["ip"])
            finally:
                conn2.close()
            heure = meta["heure_fenetre"].strftime("%d/%m à %Hh")
            anomalies.append({
                "mac": mac,
                "ip": meta["ip"],
                "anomaly_type": "ml_anomaly",
                "severity": "warning",
                "description": (
                    f"Comportement inhabituel détecté par IA pour "
                    f"{hostname or meta['ip']} le {heure} "
                    f"(score : {scores[i]:.3f})."
                ),
            })
    return anomalies




# ════════════════════════════════════════════════════════════
# EXÉCUTION COMPLÈTE
# ════════════════════════════════════════════════════════════

def run_all_detectors() -> list[dict]:
    """
    Exécute tous les détecteurs d'anomalies et retourne la liste
    consolidée des anomalies trouvées.
    """
    all_anomalies = []

    detectors = [
        ("Usage nocturne",      detect_night_usage),
        ("Catégorie suspecte",  detect_suspect_category),
        ("Pic de catégorie",    detect_category_spike),
        ("Nouvel appareil",     detect_new_device),
        ("ML Isolation Forest", detect_ml_anomaly),       
    ]


    for name, detector_fn in detectors:
        try:
            results = detector_fn()
            if results:
                log.info("[%s] %d anomalie(s) détectée(s).", name, len(results))
            all_anomalies.extend(results)
        except Exception as e:
            log.error("[%s] Erreur : %s", name, e)

    return all_anomalies


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    print("=== Test des détecteurs d'anomalies ===\n")
    anomalies = run_all_detectors()
    if not anomalies:
        print("Aucune anomalie détectée.")
    else:
        for a in anomalies:
            icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
                a["severity"], "•"
            )
            print(f"  {icon} [{a['severity'].upper()}] {a['description']}")
