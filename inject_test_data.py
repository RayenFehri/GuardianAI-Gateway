import random
from datetime import datetime, timedelta
from db import get_connection, init_db

def inject_test_data():
    """
    Injecte des données de test réalistes dans la base pour tester les fonctionnalités
    du projet (Partie IA, statistiques, dashboard).
    """
    print("🔄 Initialisation de la base de données...")
    init_db()
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            print("🗑️ Nettoyage des anciennes données...")
            cur.execute("TRUNCATE TABLE ai_anomalies, dns_events, rules, devices RESTART IDENTITY CASCADE")
            
            # ==========================================
            # 1. APPAREILS
            # ==========================================
            print("📱 Ajout d'appareils...")
            devices = [
                ('AA:BB:CC:DD:EE:01', '192.168.50.10', 'PC-Parents', 'Apple', 'Ordinateur'),
                ('AA:BB:CC:DD:EE:02', '192.168.50.11', 'iPad-Enfants', 'Apple', 'Tablette'),
                ('AA:BB:CC:DD:EE:03', '192.168.50.12', 'Galaxy-A54', 'Samsung', 'Smartphone'),
            ]
            
            for mac, ip, hostname, vendor, device_type in devices:
                cur.execute("""
                    INSERT INTO devices (mac, ip, hostname, vendor, device_type, confidence, first_seen, last_seen)
                    VALUES (%s, %s, %s, %s, %s, 0.9, NOW() - INTERVAL '8 days', NOW())
                """, (mac, ip, hostname, vendor, device_type))

            # ==========================================
            # 2. RÈGLES
            # ==========================================
            print("🛡️ Ajout de règles...")
            # Règle de blocage nocturne pour l'iPad
            cur.execute("""
                INSERT INTO rules (mac, rule_type, target, start_time, end_time, active)
                VALUES ('AA:BB:CC:DD:EE:02', 'schedule', 'all', '22:00:00', '07:00:00', TRUE)
            """)

            # ==========================================
            # 3. ÉVÉNEMENTS DNS (HISTORIQUE DE 7 JOURS)
            # ==========================================
            print("🌐 Génération de l'historique DNS (ça peut prendre quelques secondes)...")
            
            domaines_normaux = [
                ('google.com', 'education'), ('wikipedia.org', 'education'), 
                ('lemonde.fr', 'information'), ('meteo.fr', 'information')
            ]
            domaines_sociaux = [
                ('tiktok.com', 'reseaux_sociaux'), ('instagram.com', 'reseaux_sociaux'), 
                ('snapchat.com', 'reseaux_sociaux')
            ]
            domaines_jeux = [
                ('roblox.com', 'jeux'), ('fortnite.com', 'jeux'), ('minecraft.net', 'jeux')
            ]
            domaines_streaming = [
                ('youtube.com', 'streaming_video'), ('netflix.com', 'streaming_video')
            ]
            
            now = datetime.now()
            
            # --- Profil PC-Parents : Usage normal de jour (travail/info) ---
            for day in range(7):
                for hour in range(8, 20):  # De 8h à 20h
                    if random.random() < 0.7:  # 70% de chances d'activité dans l'heure
                        for _ in range(random.randint(5, 15)):
                            ts = now - timedelta(days=day, hours=now.hour-hour, minutes=random.randint(0, 59))
                            dom, cat = random.choice(domaines_normaux + domaines_streaming)
                            cur.execute("INSERT INTO dns_events (ip, domain, category, timestamp) VALUES (%s,%s,%s,%s)",
                                        ('192.168.50.10', dom, cat, ts))

            # --- Profil iPad-Enfants : Jeux et YouTube l'après-midi + Pic d'activité hier ---
            for day in range(7):
                for hour in range(16, 20):  # Après l'école
                    # Pic d'activité hier (day 1) pour déclencher 'detect_category_spike'
                    nb_req = random.randint(30, 50) if day == 1 else random.randint(5, 15)
                    for _ in range(nb_req):
                        ts = now - timedelta(days=day, hours=now.hour-hour, minutes=random.randint(0, 59))
                        dom, cat = random.choice(domaines_jeux + domaines_streaming)
                        cur.execute("INSERT INTO dns_events (ip, domain, category, timestamp) VALUES (%s,%s,%s,%s)",
                                    ('192.168.50.11', dom, cat, ts))

            # --- Profil Galaxy-A54 : Réseaux sociaux + Anomalies ML/Règles ---
            for day in range(7):
                for hour in range(12, 22):
                    if random.random() < 0.8:
                        for _ in range(random.randint(10, 30)):
                            ts = now - timedelta(days=day, hours=now.hour-hour, minutes=random.randint(0, 59))
                            dom, cat = random.choice(domaines_sociaux)
                            cur.execute("INSERT INTO dns_events (ip, domain, category, timestamp) VALUES (%s,%s,%s,%s)",
                                        ('192.168.50.12', dom, cat, ts))
            
            # -> ANOMALIE 1 : Usage nocturne cette nuit pour le Galaxy-A54 (déclenche 'detect_night_usage' et 'ML Isolation Forest')
            for _ in range(45):
                ts = now - timedelta(hours=now.hour - 3, minutes=random.randint(0, 59)) # 3h du matin
                dom, cat = random.choice(domaines_sociaux)
                cur.execute("INSERT INTO dns_events (ip, domain, category, timestamp) VALUES (%s,%s,%s,%s)",
                            ('192.168.50.12', dom, cat, ts))
                
            # -> ANOMALIE 2 : Catégorie suspecte à l'instant (déclenche 'detect_suspect_category')
            cur.execute("INSERT INTO dns_events (ip, domain, category, timestamp) VALUES (%s,%s,%s,%s)",
                        ('192.168.50.12', 'casino-en-ligne.com', 'paris_jeux_argent', now))

            # ==========================================
            # 4. NOUVEL APPAREIL
            # ==========================================
            # -> ANOMALIE 3 : Appareil inconnu qui vient de se connecter (déclenche 'detect_new_device')
            cur.execute("""
                INSERT INTO devices (mac, ip, hostname, vendor, device_type, confidence, first_seen, last_seen)
                VALUES ('FF:FF:FF:EE:DD:CC', '192.168.50.99', 'Unknown-Device', 'Unknown', 'Autre', 0.1, NOW(), NOW())
            """)

        conn.commit()
        print("✅ Données de test injectées avec succès !")
    finally:
        conn.close()

if __name__ == "__main__":
    inject_test_data()
