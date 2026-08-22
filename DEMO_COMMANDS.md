# 🚀 GuardianAI Gateway — Guide de Démonstration

> **Projet :** Passerelle de contrôle parental sur Raspberry Pi  
> **Architecture :** Pi (hostapd + dnsmasq + iptables + systemd) + PostgreSQL + MQTT + Grafana  
> **Durée estimée :** 15–20 minutes

---

## 📋 Tableau de bord rapide

| Service | Adresse | Identifiants |
|---|---|---|
| Raspberry Pi SSH | `ssh pi@raspberrypi.local` | `pi` / `ray+ray000` |
| Grafana | http://localhost:3000 | `admin` / `guardian123` |
| PostgreSQL | `localhost:5433` | `gateway_admin` / `changeme123` |
| MQTT Broker | `localhost:1883` | anonyme |
| WiFi du Pi | `GuardianGateway` | — |

---

## ⚙️ ÉTAPE 0 — Démarrage de l'infrastructure (PC Fedora)

```bash
cd ~/9raya/Projects/gateway_project

# Démarre PostgreSQL + Mosquitto + Grafana
docker compose up -d

# Vérifie que les 3 services tournent
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

✅ **Résultat attendu :**
```
NAMES                STATUS          PORTS
gateway_grafana      Up X seconds    0.0.0.0:3000->3000/tcp
gateway_mosquitto    Up X seconds    0.0.0.0:1883->1883/tcp
gateway_postgres     Up X seconds    0.0.0.0:5433->5432/tcp
```

---

## 🍓 ÉTAPE 1 — Connexion au Raspberry Pi

```bash
# Le Pi démarre tout seul en ~45 secondes
ssh pi@raspberrypi.local
# Mot de passe : ray+ray000
```

---

## 🔄 ÉTAPE 2 — Synchronisation du code (PC → Pi)

> ⚠️ À faire depuis un **nouveau terminal sur le PC** après chaque modification du code

```bash
rsync -av \
  --exclude='venv' --exclude='__pycache__' --exclude='.git' \
  ~/9raya/Projects/gateway_project/ \
  pi@raspberrypi.local:~/gateway_project/
```

---

## 🤖 ÉTAPE 3 — Vérification des services automatiques (Pi)

> ✨ **Nouveauté :** Depuis la v2, le Pi se configure **tout seul** au démarrage.
> Brancher la prise suffit — aucune commande manuelle nécessaire.

```bash
# Sur le Pi (SSH) — vérifie que les 3 services tournent
sudo systemctl status guardian-network.service guardian-discovery.service guardian-rules.service --no-pager
```

✅ **Résultat attendu (3 lignes vertes) :**
```
guardian-network.service    active (exited)   ← réseau configuré au boot
guardian-discovery.service  active (running)  ← détecte les appareils en continu
guardian-rules.service      active (running)  ← applique les blocages en continu
```

```bash
# Voir les logs en temps réel
sudo journalctl -u guardian-discovery.service -f
# (Ctrl+C pour quitter)
```

---

## 🔍 ÉTAPE 4 — Découverte automatique des appareils

> Les appareils sont détectés automatiquement dès qu'ils se connectent au Wi-Fi.
> Le service `guardian-discovery` tourne en fond et scanne toutes les 60 secondes.

**Connecte un téléphone au Wi-Fi `GuardianGateway`**, puis sur le PC :

```bash
# Vois les appareils détectés en base de données
cd ~/9raya/Projects/gateway_project
source venv/bin/activate
python3 -c "
from db import list_devices
for d in list_devices():
    print(f\"  {d['mac']}  {d['ip']:<15} {d['hostname']:<20} → {d['device_type']}\")
"
```

---

## 🔒 ÉTAPE 5 — Blocage total d'un appareil (iptables)

> Le blocage le plus fort : coupe **tout** Internet pour l'appareil ciblé.
> La règle est lue depuis la base de données et appliquée **automatiquement** par `guardian-rules`.

```bash
# Sur le PC Fedora
cd ~/9raya/Projects/gateway_project
source venv/bin/activate
MAC="a2:50:d5:8f:0b:04"   # ← remplacer par le MAC détecté à l'étape 4

# 1. Crée la règle en base de données
python3 -c "from db import add_rule; r=add_rule('$MAC', 'block_device'); print(f'Règle #{r} créée')"
```

→ Dans les **60 secondes**, le service `guardian-rules` détecte la nouvelle règle et bloque le téléphone automatiquement.

```bash
# Vérifie que la règle iptables est bien en place (position 1 = prioritaire)
# Sur le Pi (SSH) :
sudo iptables -L FORWARD -v -n --line-numbers | grep -E "guardian|ACCEPT.*uap0"
```

✅ **Résultat attendu :**
```
1   DROP   MAC a2:50:d5:8f:0b:04  /* guardian_gateway_rule */   ← en position 1
2   ACCEPT wlan0 → uap0   state RELATED,ESTABLISHED
5   ACCEPT uap0 → wlan0
```

→ Sur le téléphone : **Internet totalement coupé** ❌

```bash
# Déblocage : désactive la règle en base
python3 -c "
from db import get_connection
c = get_connection()
cur = c.cursor()
cur.execute(\"UPDATE rules SET active=FALSE WHERE mac='$MAC'\")
c.commit()
print('Règle désactivée')
"
```

→ Dans les 60 secondes, le téléphone retrouve Internet automatiquement ✅

---

## ⏰ ÉTAPE 6 — Blocage horaire automatique (schedule)

```bash
# Sur le PC Fedora
cd ~/9raya/Projects/gateway_project
source venv/bin/activate
MAC="a2:50:d5:8f:0b:04"

# Bloque pendant les 10 prochaines minutes
python3 -c "
from db import add_rule
from datetime import datetime, timedelta
now = datetime.now()
start = (now - timedelta(minutes=1)).strftime('%H:%M')
end   = (now + timedelta(minutes=10)).strftime('%H:%M')
rid = add_rule('$MAC', 'schedule', start_time=start, end_time=end)
print(f'Règle #{rid} — blocage de {start} à {end}')
"
```

→ Le téléphone est bloqué automatiquement pendant 10 minutes, puis débloqué tout seul. ✅

---

## 🚫 ÉTAPE 7 — Blocage de sites par catégorie (dnsmasq DNS)

```bash
# Sur le PC Fedora
cd ~/9raya/Projects/gateway_project
source venv/bin/activate

# Bloque tous les réseaux sociaux
python3 -c "from db import add_rule; r=add_rule(None, 'block_category', 'reseaux_sociaux'); print(f'Règle #{r} créée')"
```

→ Dans les 60 secondes, dnsmasq est reconfiguré automatiquement.

```bash
# Vérifie le fichier de blocage généré sur le Pi :
cat /etc/dnsmasq.d/guardian_blocks.conf | head -5

# Teste localement :
host tiktok.com 127.0.0.1     # → doit retourner 0.0.0.0
host google.com 127.0.0.1     # → doit retourner une vraie IP
```

**Catégories disponibles :** `reseaux_sociaux`, `streaming_video`, `streaming_audio`, `jeux`, `education`, `adulte`, `ia`, `travail`, `paris_jeux_argent`

---

## 📡 ÉTAPE 8 — Monitoring MQTT temps réel

```bash
# Terminal 1 (PC) — écoute tous les événements
docker exec gateway_mosquitto mosquitto_sub -t "guardian/#" -v

# Terminal 2 (PC) — déclenche un événement
cd ~/9raya/Projects/gateway_project && source venv/bin/activate
python3 main_discovery.py
```

✅ **Messages JSON en temps réel :**
```json
guardian/devices {"mac": "a2:50:...", "device_type": "Smartphone", ...}
guardian/rules   {"rule_id": 4, "action": "block", "mac": "a2:50:...", ...}
```

---

## 📊 ÉTAPE 9 — Dashboard Grafana

**URL :** http://localhost:3000 — Login : `admin` / `guardian123`

**Requêtes SQL pour les panneaux :**

```sql
-- Panneau 1 : Appareils connectés
SELECT mac, ip, hostname, device_type,
       to_char(last_seen, 'DD/MM HH24:MI') AS last_seen
FROM devices ORDER BY last_seen DESC;

-- Panneau 2 : Règles actives
SELECT id, rule_type,
       COALESCE(mac, '(tous)') AS mac,
       COALESCE(target, '—') AS cible,
       to_char(created_at, 'DD/MM HH24:MI') AS créée_le
FROM rules WHERE active = TRUE ORDER BY created_at DESC;

-- Panneau 3 : Top domaines consultés
SELECT domain, COUNT(*) AS nb_requetes
FROM dns_events GROUP BY domain
ORDER BY nb_requetes DESC LIMIT 15;
```

---

## 🔎 ÉTAPE 10 — Diagnostic complet du système

```bash
# Sur le Pi (SSH)
echo "=== Services systemd ===" && \
sudo systemctl is-active guardian-network guardian-discovery guardian-rules

echo "=== IP Forward ===" && cat /proc/sys/net/ipv4/ip_forward

echo "=== Règles FORWARD ===" && \
sudo iptables -L FORWARD -v -n --line-numbers

echo "=== DNS Blocage ===" && \
cat /etc/dnsmasq.d/guardian_blocks.conf 2>/dev/null || echo "Aucun blocage DNS actif"

echo "=== DHCP Leases ===" && cat /var/lib/misc/dnsmasq.leases
```

---

## 🧹 ÉTAPE 11 — Nettoyage des règles iptables (si besoin)

```bash
# Sur le Pi — retire toutes nos règles guardian proprement
sudo iptables-save | grep -v "guardian_gateway_rule" | sudo iptables-restore

# Relance la synchronisation
sudo systemctl restart guardian-rules.service
```

---

## 🛑 ÉTAPE 12 — Arrêt propre

```bash
# Sur le Pi
sudo shutdown -h now

# Sur le PC
docker compose down
```

---

## 🚨 Dépannage rapide

| Problème | Vérification | Solution |
|---|---|---|
| Services pas démarrés | `sudo systemctl status guardian-*` | `sudo systemctl start guardian-network guardian-discovery guardian-rules` |
| Téléphone sans Internet | `sudo iptables -t nat -L POSTROUTING -v -n` | Vérifier la règle MASQUERADE |
| Blocage MAC inefficace | `sudo iptables -L FORWARD --line-numbers` | La règle DROP doit être en **position 1** |
| Erreur connexion DB | `sudo journalctl -u guardian-rules -n 10` | Vérifier `.env` → `DB_HOST=<IP du PC>` |
| Grafana sans données | Datasource PostgreSQL | Port `5433`, pas `5432` |
| Wi-Fi invisible | `ip a \| grep uap0` | `sudo systemctl restart guardian-network` |

---

## 🏗️ Architecture du système

```
PC Fedora                          Raspberry Pi
┌─────────────────────┐            ┌─────────────────────────────┐
│  Docker             │            │  systemd (auto au boot)     │
│  ┌───────────────┐  │  TCP:5433  │  ┌─────────────────────┐   │
│  │  PostgreSQL   │◄─┼────────────┤  │ guardian-network    │   │
│  └───────────────┘  │            │  │  → uap0 + NAT       │   │
│  ┌───────────────┐  │            │  ├─────────────────────┤   │
│  │  Mosquitto    │◄─┼────────────┤  │ guardian-discovery  │   │
│  │  MQTT broker  │  │  TCP:1883  │  │  → détecte appareils│   │
│  └───────────────┘  │            │  ├─────────────────────┤   │
│  ┌───────────────┐  │            │  │ guardian-rules      │   │
│  │  Grafana      │  │            │  │  → iptables + DNS   │   │
│  └───────────────┘  │            │  └─────────────────────┘   │
└─────────────────────┘            │                             │
                                   │  Réseau Wi-Fi "GuardianGW" │
                                   │  📱 Téléphone enfant       │
                                   └─────────────────────────────┘
```
