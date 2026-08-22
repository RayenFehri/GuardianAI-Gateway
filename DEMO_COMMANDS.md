# 🚀 GuardianAI Gateway — Guide de Démonstration

> **Projet :** Passerelle de contrôle parental sur Raspberry Pi  
> **Architecture :** Pi (hostapd + dnsmasq + iptables) + PostgreSQL + MQTT + Grafana  
> **Durée estimée de la démo :** 15–20 minutes

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

# 1. Démarre PostgreSQL + Mosquitto + Grafana
docker compose up -d

# 2. Vérifie que les 3 services tournent
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
# Branche le Pi et attends ~30 secondes qu'il démarre
ssh pi@10.17.245.6
# Mot de passe : ray+ray000
```

---

## 🔄 ÉTAPE 2 — Synchronisation du code (PC → Pi)

> ⚠️ À faire depuis un **nouveau terminal sur le PC** (pas depuis la session SSH)

```bash
rsync -av \
  --exclude='venv' --exclude='__pycache__' --exclude='.git' \
  ~/9raya/Projects/gateway_project/ \
  pi@10.17.245.6:~/gateway_project/
# Mot de passe : ray+ray000
```

---

## 🌐 ÉTAPE 3 — Configuration réseau du Pi

> À faire **une seule fois** après chaque redémarrage du Pi.

```bash
# Sur le Pi (terminal SSH)
cd ~/gateway_project
source venv/bin/activate

# Vérifie les services réseau
sudo systemctl status hostapd --no-pager | head -4
sudo systemctl status dnsmasq  --no-pager | head -4

# Active le routage IP (Internet pass-through)
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Règle NAT : partage la connexion Internet avec les appareils du Wi-Fi
sudo iptables -t nat -C POSTROUTING -o wlan0 -j MASQUERADE 2>/dev/null || \
  sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE

# Règles FORWARD : autorise le relais AP (uap0) ↔ Internet (wlan0)
sudo iptables -C FORWARD -i wlan0 -o uap0 -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
  sudo iptables -I FORWARD 1 -i wlan0 -o uap0 -m state --state RELATED,ESTABLISHED -j ACCEPT

sudo iptables -C FORWARD -i uap0 -o wlan0 -j ACCEPT 2>/dev/null || \
  sudo iptables -A FORWARD -i uap0 -o wlan0 -j ACCEPT

# Sauvegarde les règles pour les prochains redémarrages
sudo sh -c "iptables-save > /etc/iptables.rules"

# Vérifie l'ordre des règles (critique !)
sudo iptables -L FORWARD -v -n --line-numbers
```

✅ **Ordre correct des règles FORWARD :**
```
num   target       in     out    details
1     ACCEPT       wlan0  uap0   state RELATED,ESTABLISHED  ← réponses Internet
2     DOCKER-USER  *      *      ...                        ← Docker
3     DOCKER-FWD   *      *      ...                        ← Docker
?     DROP guardian uap0  *      MAC xx:xx (blocages)       ← avant ACCEPT !
?     ACCEPT       uap0   wlan0  tout passe                 ← doit être en dernier
```

---

## 🔍 ÉTAPE 4 — Découverte des appareils

```bash
# Sur le Pi — connecte un téléphone au WiFi "GuardianGateway" d'abord
export GATEWAY_ENV=pi
python3 main_discovery.py
```

✅ **Résultat attendu :**
```
2026-xx-xx XX:XX:XX [INFO] 1 équipement(s) détecté(s).
MAC: a2:50:d5:8f:0b:04  IP: 192.168.50.58  Hostname: OPPO-A74  Vendor: OPPO  -> Smartphone (90%)
```

---

## 🔒 ÉTAPE 5 — Blocage total d'un appareil (iptables)

> Le blocage le plus fort : coupe **tout** Internet pour l'appareil ciblé.

```bash
export GATEWAY_ENV=pi
MAC="a2:50:d5:8f:0b:04"   # ← à remplacer par le MAC détecté à l'étape 4

# 1. Ajoute la règle en base de données
python3 -c "from db import add_rule; add_rule('$MAC', 'block_device')"

# 2. Applique la synchronisation (bloque dans iptables)
sudo /home/pi/gateway_project/venv/bin/python3 -c "
import os; os.environ['GATEWAY_ENV']='pi'
from main_rules import apply_rules
apply_rules(dry_run=False)
"

# 3. Vérifie que la règle est au BON endroit (avant la règle ACCEPT)
sudo iptables -L FORWARD -v -n --line-numbers | grep -E "guardian|ACCEPT.*uap0"
```

→ Sur le téléphone : **Internet totalement coupé** ❌

```bash
# Déblocage : désactive la règle en base
python3 -c "
from db import get_connection
c = get_connection(); cur = c.cursor()
cur.execute(\"UPDATE rules SET active=FALSE WHERE mac='$MAC' AND rule_type='block_device'\")
c.commit()
"

# Resynchronise (retire le blocage d'iptables)
sudo /home/pi/gateway_project/venv/bin/python3 -c "
import os; os.environ['GATEWAY_ENV']='pi'
from main_rules import apply_rules
apply_rules(dry_run=False)
"
```

→ Sur le téléphone : **Internet de retour** ✅

---

## ⏰ ÉTAPE 6 — Blocage horaire (schedule)

> Bloque automatiquement l'appareil dans une plage horaire donnée.

```bash
export GATEWAY_ENV=pi
MAC="a2:50:d5:8f:0b:04"

# Crée une règle "bloqué dans les 10 prochaines minutes"
python3 -c "
from db import add_rule
from datetime import datetime, timedelta
now = datetime.now()
start = (now - timedelta(minutes=1)).strftime('%H:%M')
end   = (now + timedelta(minutes=10)).strftime('%H:%M')
rid = add_rule('$MAC', 'schedule', start_time=start, end_time=end)
print(f'Règle #{rid} créée — blocage de {start} à {end}')
"

# Applique
sudo /home/pi/gateway_project/venv/bin/python3 -c "
import os; os.environ['GATEWAY_ENV']='pi'
from main_rules import apply_rules
apply_rules(dry_run=False)
"
```

→ L'appareil est bloqué pendant 10 minutes, puis se débloque tout seul au prochain cycle. ✅

---

## 🚫 ÉTAPE 7 — Blocage de sites par catégorie (dnsmasq DNS)

> Bloque des catégories entières de sites web (réseaux sociaux, jeux, etc.)  
> ⚠️ **Pour tester dans un navigateur web** (Chrome/Safari) — les apps mobiles peuvent avoir un cache DNS.

```bash
export GATEWAY_ENV=pi

# 1. Ajoute la règle de blocage de catégorie en base
python3 -c "from db import add_rule; add_rule(None, 'block_category', 'reseaux_sociaux')"

# 2. Applique la synchronisation (écrit dans dnsmasq + redémarre le service)
sudo /home/pi/gateway_project/venv/bin/python3 -c "
import os; os.environ['GATEWAY_ENV']='pi'
from main_rules import apply_rules
apply_rules(dry_run=False)
"

# 3. Vérifie le fichier généré
cat /etc/dnsmasq.d/guardian_blocks.conf | head -10

# 4. Teste localement que le DNS retourne 0.0.0.0
host tiktok.com 127.0.0.1
host instagram.com 127.0.0.1
```

→ Dans le navigateur du téléphone : **tiktok.com → ❌ bloqué**, **google.com → ✅ accessible**

```bash
# Déblocage (désactive la règle)
python3 -c "
from db import get_connection
c = get_connection(); cur = c.cursor()
cur.execute(\"UPDATE rules SET active=FALSE WHERE rule_type='block_category'\")
c.commit()
"

# Resynchronise (supprime le fichier dnsmasq + redémarre)
sudo /home/pi/gateway_project/venv/bin/python3 -c "
import os; os.environ['GATEWAY_ENV']='pi'
from main_rules import apply_rules
apply_rules(dry_run=False)
"
```

**Catégories disponibles :** `reseaux_sociaux`, `streaming_video`, `streaming_audio`, `jeux`, `education`, `travail`, `ia`, `adulte`, `paris_jeux_argent`

---

## 📡 ÉTAPE 8 — Monitoring MQTT temps réel (PC Fedora)

```bash
# Terminal 1 — écoute tous les événements en temps réel
docker exec gateway_mosquitto mosquitto_sub -t "guardian/#" -v

# Terminal 2 — génère des événements (lance la découverte)
cd ~/9raya/Projects/gateway_project
source venv/bin/activate
python3 main_discovery.py
```

✅ **Messages JSON affichés en temps réel dans Terminal 1 :**
```json
guardian/devices {"mac": "a2:50:...", "ip": "192.168.50.58", "vendor": "OPPO", ...}
guardian/rules   {"rule_id": 4, "action": "block", "mac": "a2:50:...", ...}
```

---

## 📊 ÉTAPE 9 — Dashboard Grafana

```
URL      : http://localhost:3000
Login    : admin
Password : guardian123
```

**Panneau 1 — Appareils connectés (Table)**
```sql
SELECT mac, ip, hostname, vendor, device_type,
       to_char(last_seen, 'HH24:MI:SS') AS last_seen
FROM devices ORDER BY last_seen DESC
```

**Panneau 2 — Types d'appareils (Pie chart)**
```sql
SELECT device_type AS "Type", COUNT(*) AS "Nombre"
FROM devices GROUP BY device_type ORDER BY "Nombre" DESC
```

**Panneau 3 — Règles actives (Table)**
```sql
SELECT id, rule_type, COALESCE(mac, '(tous)') AS mac,
       COALESCE(target, '—') AS cible,
       to_char(created_at, 'DD/MM HH24:MI') AS créée_le
FROM rules WHERE active = TRUE ORDER BY created_at DESC
```

**Panneau 4 — Top domaines consultés (Bar chart)**
```sql
SELECT domain, COUNT(*) AS nb_requetes
FROM dns_events GROUP BY domain ORDER BY nb_requetes DESC LIMIT 15
```

---

## 🔎 ÉTAPE 10 — Vérifications & Diagnostic

```bash
# Sur le Pi — état complet du système
echo "=== IP Forward ==="
cat /proc/sys/net/ipv4/ip_forward

echo "=== Règles FORWARD ==="
sudo iptables -L FORWARD -v -n --line-numbers

echo "=== NAT ==="
sudo iptables -t nat -L POSTROUTING -v -n

echo "=== DHCP Leases ==="
cat /var/lib/misc/dnsmasq.leases

echo "=== DNS Blocage ==="
cat /etc/dnsmasq.d/guardian_blocks.conf 2>/dev/null || echo "Aucun blocage DNS actif"

echo "=== Base de données ==="
python3 -c "
from db import list_devices, list_rules
print('Appareils:')
for d in list_devices(): print(' ', d['mac'], d['ip'], d['hostname'])
print('Règles actives:')
for r in list_rules(active_only=True): print(' ', r['id'], r['rule_type'], r['mac'], r['target'])
"
```

---

## 🧹 ÉTAPE 11 — Nettoyage des règles iptables (si besoin)

> À utiliser si les règles sont dans le mauvais ordre ou dupliquées.

```bash
# Sur le Pi — retire toutes nos règles guardian (sans toucher aux règles Docker/NAT)
sudo iptables-save | grep -v "guardian_gateway_rule" | sudo iptables-restore

# Puis relance la synchronisation propre
sudo /home/pi/gateway_project/venv/bin/python3 -c "
import os; os.environ['GATEWAY_ENV']='pi'
from main_rules import apply_rules
apply_rules(dry_run=False)
"
```

---

## 🛑 ÉTAPE 12 — Arrêt propre

```bash
# Sur le Pi — éteint proprement (évite la corruption de la carte SD)
sudo shutdown -h now

# Sur le PC — arrête les conteneurs Docker
cd ~/9raya/Projects/gateway_project
docker compose down
```

---

## 🚨 Dépannage rapide

| Problème | Vérification | Solution |
|---|---|---|
| Téléphone sans Internet | `sudo iptables -t nat -L POSTROUTING -v -n` | Ajouter la règle MASQUERADE (Étape 3) |
| Blocage MAC inefficace | `sudo iptables -L FORWARD -v -n --line-numbers` | La règle DROP doit être AVANT ACCEPT |
| dnsmasq ne démarre pas | `sudo systemctl status dnsmasq` | `sudo systemctl restart dnsmasq` |
| Grafana sans données | Vérifier la datasource PostgreSQL | Port `5433`, pas `5432` |
| MQTT ne reçoit rien | `docker ps` | `docker compose up -d` |
