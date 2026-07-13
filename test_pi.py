"""
test_pi.py — Vérifie que tout est bien configuré sur le Pi OpenWrt

Lance ce script juste après l'installation pour vérifier que :
  1. Les fichiers dnsmasq sont accessibles
  2. La connexion PostgreSQL fonctionne
  3. Les scripts principaux tournent sans erreur

Usage (sur le Pi) :
    python3 test_pi.py
"""

import sys
from pathlib import Path


def check(label: str, ok: bool, detail: str = ""):
    status = "✅ OK" if ok else "❌ ERREUR"
    print(f"  {status}  {label}")
    if not ok and detail:
        print(f"         → {detail}")
    return ok


def main():
    print("\n========================================")
    print(" GuardianAI Gateway — Vérification Pi  ")
    print("========================================\n")

    all_ok = True

    # ── 1. Vérifie config.py ────────────────────────────────
    print("[ 1 ] Configuration :")
    try:
        from config import ENVIRONMENT, LEASES_FILE, DNS_LOG_FILE, DB_CONFIG
        all_ok &= check("config.py importé", True)
        all_ok &= check(f"Environnement = '{ENVIRONMENT}'", True)
        all_ok &= check(f"Fichier leases : {LEASES_FILE}", LEASES_FILE.exists(),
                        "dnsmasq ne tourne peut-être pas encore")
        all_ok &= check(f"Fichier DNS log : {DNS_LOG_FILE}", DNS_LOG_FILE.exists(),
                        "Active le logging DNS dans dnsmasq")
    except Exception as e:
        all_ok &= check("config.py", False, str(e))

    # ── 2. Vérifie la base de données ───────────────────────
    print("\n[ 2 ] Base de données PostgreSQL :")
    try:
        import psycopg2
        from config import DB_CONFIG
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        all_ok &= check("Connexion PostgreSQL", True)
    except Exception as e:
        all_ok &= check("Connexion PostgreSQL", False,
                        f"{e}\n         → Lance : docker compose up -d")

    # ── 3. Vérifie les modules Python ───────────────────────
    print("\n[ 3 ] Modules Python :")
    modules = ["psycopg2", "dotenv"]
    for mod in modules:
        try:
            __import__(mod)
            all_ok &= check(f"import {mod}", True)
        except ImportError:
            all_ok &= check(f"import {mod}", False,
                            f"pip3 install {mod}")

    # ── 4. Test discovery ───────────────────────────────────
    print("\n[ 4 ] Découverte des équipements :")
    try:
        from discovery import parse_leases
        devices = parse_leases()
        all_ok &= check(
            f"{len(devices)} équipement(s) détecté(s)",
            len(devices) > 0,
            "Aucun équipement — vérifie que dnsmasq tourne"
        )
    except Exception as e:
        all_ok &= check("parse_leases()", False, str(e))

    # ── 5. Test DNS parser ──────────────────────────────────
    print("\n[ 5 ] Analyse DNS :")
    try:
        from dns_log_parser import parse_dns_log
        events = parse_dns_log()
        all_ok &= check(
            f"{len(events)} requête(s) DNS trouvée(s)",
            True  # 0 événement est OK si le log vient de démarrer
        )
    except Exception as e:
        all_ok &= check("parse_dns_log()", False, str(e))

    # ── Résumé ──────────────────────────────────────────────
    print("\n========================================")
    if all_ok:
        print(" ✅ Tout est OK — le Pi est prêt !     ")
    else:
        print(" ❌ Des erreurs sont à corriger         ")
        print("    Relis les messages ci-dessus        ")
    print("========================================\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()