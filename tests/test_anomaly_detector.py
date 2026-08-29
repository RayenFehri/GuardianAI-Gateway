"""
Tests unitaires pour ai/anomaly_detector.py (Partie 5 du CDC).

On teste la logique de chaque détecteur avec des données simulées
injectées directement en base, puis nettoyées après chaque test.
"""

import pytest
from datetime import datetime, timedelta
from db import get_connection, init_db


@pytest.fixture(autouse=True)
def setup_db():
    """Initialise les tables avant chaque test."""
    init_db()
    yield
    # Nettoyage après chaque test
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ai_anomalies")
            cur.execute("DELETE FROM dns_events WHERE ip = '10.99.99.99'")
            cur.execute("DELETE FROM devices WHERE mac = 'TE:ST:00:00:00:01'")
        conn.commit()
    finally:
        conn.close()


def _insert_test_device():
    """Insère un appareil de test."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO devices (mac, ip, hostname, vendor, device_type, confidence, first_seen, last_seen)
                VALUES ('TE:ST:00:00:00:01', '10.99.99.99', 'TestPhone', 'TestVendor', 'Smartphone', 0.9, NOW(), NOW())
                ON CONFLICT (mac) DO NOTHING
            """)
        conn.commit()
    finally:
        conn.close()


def _insert_dns_event(ip, domain, category, hours_ago=0, minute=0):
    """Insère un événement DNS de test à une heure précise."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            ts = datetime.now() - timedelta(hours=hours_ago, minutes=minute)
            cur.execute("""
                INSERT INTO dns_events (ip, domain, category, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (ip, domain, category, ts))
        conn.commit()
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════
# Tests du détecteur de catégorie suspecte
# ════════════════════════════════════════════════════════════

def test_suspect_category_detects_adult_content():
    """Un accès à la catégorie 'adulte' doit déclencher une alerte critique."""
    _insert_test_device()
    _insert_dns_event("10.99.99.99", "example-adult.com", "adulte")

    from ai.anomaly_detector import detect_suspect_category
    anomalies = detect_suspect_category(hours_back=1)

    assert len(anomalies) >= 1
    adult_anomalies = [a for a in anomalies if a["ip"] == "10.99.99.99"]
    assert len(adult_anomalies) == 1
    assert adult_anomalies[0]["severity"] == "critical"
    assert adult_anomalies[0]["anomaly_type"] == "suspect_category"


def test_suspect_category_ignores_normal_categories():
    """Les catégories normales (education, travail) ne déclenchent rien."""
    _insert_test_device()
    _insert_dns_event("10.99.99.99", "khanacademy.org", "education")

    from ai.anomaly_detector import detect_suspect_category
    anomalies = detect_suspect_category(hours_back=1)

    test_anomalies = [a for a in anomalies if a["ip"] == "10.99.99.99"]
    assert len(test_anomalies) == 0


# ════════════════════════════════════════════════════════════
# Tests du détecteur de nouvel appareil
# ════════════════════════════════════════════════════════════

def test_new_device_detected():
    """Un appareil fraîchement inséré doit être signalé."""
    _insert_test_device()

    from ai.anomaly_detector import detect_new_device
    anomalies = detect_new_device(hours_back=1)

    test_anomalies = [a for a in anomalies if a["mac"] == "TE:ST:00:00:00:01"]
    assert len(test_anomalies) == 1
    assert test_anomalies[0]["anomaly_type"] == "new_device"
    assert test_anomalies[0]["severity"] == "info"


# ════════════════════════════════════════════════════════════
# Tests de la déduplication
# ════════════════════════════════════════════════════════════

def test_anomaly_deduplication():
    """Une anomalie identique ne doit pas être re-signalée dans les 6h."""
    from db import insert_anomaly, is_anomaly_duplicate

    anomaly = {
        "mac": "TE:ST:00:00:00:01",
        "anomaly_type": "night_usage",
        "severity": "warning",
        "description": "Test",
    }
    insert_anomaly(anomaly)

    assert is_anomaly_duplicate("TE:ST:00:00:00:01", "night_usage", hours_back=6) is True
    assert is_anomaly_duplicate("TE:ST:00:00:00:01", "suspect_category", hours_back=6) is False


def test_ml_detector_returns_list():
    """detect_ml_anomaly() retourne une liste (vide si pas assez de données)."""
    from ai.anomaly_detector import detect_ml_anomaly
    result = detect_ml_anomaly()
    assert isinstance(result, list)



def test_get_daily_stats_returns_dict():
    """get_daily_stats() doit retourner un dict avec les clés attendues."""
    from ai.report_generator import get_daily_stats
    stats = get_daily_stats(days=1)
    assert isinstance(stats, dict)
    assert "devices" in stats
    assert "usage_par_ip" in stats
    assert "top_domains" in stats
    assert "anomalies" in stats


def test_build_prompt_returns_string():
    """build_prompt() doit retourner un prompt non vide."""
    from ai.report_generator import build_prompt
    fake_stats = {
        "date": "25/08/2026",
        "periode": "1 jour(s)",
        "devices": [],
        "usage_par_ip": {},
        "top_domains": [],
        "anomalies": [],
        "rules_actives": [],
    }
    prompt = build_prompt(fake_stats)
    assert isinstance(prompt, str)
    assert len(prompt) > 50


# ════════════════════════════════════════════════════════════
# Test du pipeline complet
# ════════════════════════════════════════════════════════════

def test_run_all_detectors_returns_list():
    """run_all_detectors() doit toujours retourner une liste."""
    from ai.anomaly_detector import run_all_detectors
    result = run_all_detectors()
    assert isinstance(result, list)

