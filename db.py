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
    """Crée la table devices si elle n'existe pas encore."""
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


if __name__ == "__main__":
    init_db()
