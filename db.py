"""
db.py — Connexion et accès à la base de données PostgreSQL (via Docker)
Partie 1 : stocke les équipements découverts sur le réseau.

Pré-requis : le conteneur Docker postgres doit tourner :
    docker compose up -d
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()  # charge les variables depuis le fichier .env

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "gateway_db"),
    "user": os.getenv("DB_USER", "gateway_admin"),
    "password": os.getenv("DB_PASSWORD", "changeme123"),
}


def get_connection():
    """Ouvre une nouvelle connexion à PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Crée les tables si elles n'existent pas encore."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY,
                ip TEXT,
                hostname TEXT,
                vendor TEXT,
                device_type TEXT,
                confidence REAL,
                first_seen TIMESTAMPTZ,
                last_seen TIMESTAMPTZ
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dns_events (
                id SERIAL PRIMARY KEY,
                ip TEXT,
                domain TEXT,
                category TEXT,
                timestamp TIMESTAMPTZ
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id SERIAL PRIMARY KEY,
                mac TEXT,                  -- équipement ciblé (NULL = tous les appareils)
                rule_type TEXT NOT NULL,   -- 'block_device', 'block_category', 'schedule'
                target TEXT,               -- catégorie ciblée si rule_type='block_category'
                start_time TIME,           -- pour les futures règles horaires
                end_time TIME,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    conn.commit()
    conn.close()
    print(f"Base initialisée sur {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")


def upsert_device(device: dict):
    """
    Insère un nouvel équipement ou met à jour ses infos s'il existe déjà
    (basé sur l'adresse MAC, qui est l'identifiant stable).
    Utilise ON CONFLICT, l'équivalent PostgreSQL de "upsert".
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO devices (mac, ip, hostname, vendor, device_type, confidence, first_seen, last_seen)
            VALUES (%(mac)s, %(ip)s, %(hostname)s, %(vendor)s, %(device_type)s, %(confidence)s, %(timestamp)s, %(timestamp)s)
            ON CONFLICT (mac) DO UPDATE SET
                ip = EXCLUDED.ip,
                hostname = EXCLUDED.hostname,
                vendor = EXCLUDED.vendor,
                device_type = EXCLUDED.device_type,
                confidence = EXCLUDED.confidence,
                last_seen = EXCLUDED.last_seen
        """, device)
    conn.commit()
    conn.close()


def list_devices():
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM devices ORDER BY last_seen DESC")
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_dns_events(events: list[dict]):
    """
    Insère une liste d'événements DNS en une seule fois (plus rapide qu'un
    insert par ligne). Chaque event est un dict : {ip, domain, category, timestamp}.
    """
    if not events:
        return
    conn = get_connection()
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO dns_events (ip, domain, category, timestamp) VALUES %s",
            [(e["ip"], e["domain"], e["category"], e["timestamp"]) for e in events],
        )
    conn.commit()
    conn.close()


def usage_stats_by_category():
    """
    Retourne, pour chaque (IP, catégorie), le nombre de requêtes DNS observées.
    C'est une première approximation simple de "temps passé par catégorie"
    (plus il y a de requêtes, plus l'usage a été long/actif).
    """
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT ip, category, COUNT(*) AS nb_requetes
            FROM dns_events
            GROUP BY ip, category
            ORDER BY ip, nb_requetes DESC
        """)
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_rule(mac: str, rule_type: str, target: str = None,
             start_time: str = None, end_time: str = None) -> int:
    """
    Crée une nouvelle règle de contrôle parental et retourne son id.

    rule_type : 'block_device'   -> bloque tout Internet pour ce mac
                'block_category' -> bloque une catégorie (ex: 'jeux') pour ce mac
                'schedule'       -> bloque entre start_time et end_time (futur)
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO rules (mac, rule_type, target, start_time, end_time, active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            RETURNING id
        """, (mac, rule_type, target, start_time, end_time))
        rule_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return rule_id


def list_rules(active_only: bool = False):
    """Liste toutes les règles, ou uniquement les règles actives."""
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if active_only:
            cur.execute("SELECT * FROM rules WHERE active = TRUE ORDER BY id")
        else:
            cur.execute("SELECT * FROM rules ORDER BY id")
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_rule_active(rule_id: int, active: bool):
    """Active ou désactive une règle (ex: le parent retire le blocage)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE rules SET active = %s WHERE id = %s", (active, rule_id))
    conn.commit()
    conn.close()


def delete_rule(rule_id: int):
    """Supprime définitivement une règle."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM rules WHERE id = %s", (rule_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()