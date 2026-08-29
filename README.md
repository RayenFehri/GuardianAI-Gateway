<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white" alt="Python 3.13"/>
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL 16"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/MQTT-Mosquitto-3C5280?logo=eclipsemosquitto&logoColor=white" alt="MQTT"/>
  <img src="https://img.shields.io/badge/Grafana-Dashboard-F46800?logo=grafana&logoColor=white" alt="Grafana"/>
  <img src="https://img.shields.io/badge/Raspberry_Pi-OS-A22846?logo=raspberrypi&logoColor=white" alt="Raspberry Pi"/>
  <a href="https://github.com/RayenFehri/GuardianAI-Gateway/actions/workflows/ci.yml">
    <img src="https://github.com/RayenFehri/GuardianAI-Gateway/actions/workflows/ci.yml/badge.svg" alt="CI"/>
  </a>
</p>

# 🛡️ GuardianAI Gateway

> **Passerelle intelligente de contrôle parental sur Raspberry Pi** — Projet de stage

GuardianAI Gateway transforme un Raspberry Pi en point d'accès Wi-Fi intelligent qui **détecte automatiquement** les appareils connectés, **analyse les usages Internet** en temps réel, et permet aux parents de **contrôler l'accès réseau** de chaque équipement via des règles flexibles (blocage total, horaires, filtrage DNS par catégorie).

---

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Stack technique](#-stack-technique)
- [Prérequis](#-prérequis)
- [Installation — Environnement de développement](#-installation--environnement-de-développement)
- [Déploiement — Raspberry Pi](#-déploiement--raspberry-pi)
- [Utilisation](#-utilisation)
- [Structure du projet](#-structure-du-projet)
- [Modules](#-modules)
- [Base de données](#-base-de-données)
- [Topics MQTT](#-topics-mqtt)
- [Tests](#-tests)
- [Intégration continue](#-intégration-continue)
- [Dépannage](#-dépannage)
- [Roadmap](#-roadmap)
- [Licence](#-licence)

---

## ✨ Fonctionnalités

### Partie 1 — Découverte des équipements
- 📡 Lecture automatique des baux DHCP (dnsmasq)
- 🏭 Résolution du fabricant via l'adresse MAC (base OUI IEEE)
- 🤖 Classification automatique du type d'appareil (smartphone, Smart TV, console, PC…)
- 💾 Stockage et historique en base PostgreSQL

### Partie 2 — Analyse des usages Internet
- 🔍 Parsing des logs DNS en temps réel
- 🏷️ Catégorisation des domaines visités (réseaux sociaux, streaming, éducation, jeux…)
- 📊 Statistiques d'usage par équipement et par catégorie

### Partie 3 — Contrôle parental
- 🔒 **Blocage total** d'un appareil par adresse MAC (iptables)
- ⏰ **Blocage horaire** automatique avec plages personnalisables (support nocturne)
- 🚫 **Filtrage DNS par catégorie** (réseaux sociaux, adulte, jeux…) via dnsmasq
- 🔄 Synchronisation idempotente — état désiré vs état réel

### Partie 5 — Intelligence Artificielle
- 🧠 **Détection d'anomalies** : usage nocturne, pics de catégorie, contenu suspect
- 🆕 **Alertes nouvel appareil** : notification quand un MAC inconnu se connecte
- 🔔 Publication automatique des alertes via MQTT (`guardian/alerts`)
- 🛡️ Déduplication intelligente (pas de spam d'alertes)

### Infrastructure
- 📡 Publication MQTT en temps réel (appareils, DNS, règles, alertes)
- 📈 Dashboard Grafana avec visualisation des données
- 🚀 Déploiement automatisé via services systemd (plug-and-play)
- ✅ Pipeline CI avec GitHub Actions

---

## 🏗️ Architecture

```
PC de développement (Fedora)           Raspberry Pi
┌──────────────────────────┐           ┌──────────────────────────────┐
│  Docker Compose          │           │  systemd (auto au boot)      │
│  ┌────────────────────┐  │           │  ┌────────────────────────┐  │
│  │  PostgreSQL :5433  │◄─┼───────────┤  │ guardian-network       │  │
│  └────────────────────┘  │  TCP      │  │  → uap0 + NAT + FW    │  │
│  ┌────────────────────┐  │           │  ├────────────────────────┤  │
│  │  Mosquitto  :1883  │◄─┼───────────┤  │ guardian-discovery     │  │
│  │  (MQTT broker)     │  │  TCP      │  │  → DHCP + OUI + class  │  │
│  └────────────────────┘  │           │  ├────────────────────────┤  │
│  ┌────────────────────┐  │           │  │ guardian-rules         │  │
│  │  Grafana    :3000  │  │           │  │  → iptables + dnsmasq  │  │
│  └────────────────────┘  │           │  └────────────────────────┘  │
└──────────────────────────┘           │                              │
                                       │  Wi-Fi « GuardianGateway »  │
                                       │  📱 Appareils connectés     │
                                       └──────────────────────────────┘
```

**Flux de données :**

```
dnsmasq.leases ──► discovery.py ──► oui_lookup.py ──► classifier.py ──► db.py ──► PostgreSQL
                                                                           │
dnsmasq.log ────► dns_log_parser.py ──► categories.py ──► db.py ──────────┘
                                                                           │
db.py (rules) ──► rule_engine.py ──► iptables (MAC)                        │
                  dns_blocker.py ──► dnsmasq (DNS)                         │
                                                                           ▼
                                                              mqtt_publisher.py ──► Mosquitto ──► Grafana
```

---

## 🛠️ Stack technique

| Composant | Technologie | Rôle |
|---|---|---|
| Langage | Python 3.13 | Scripts principaux, moteur de règles |
| Base de données | PostgreSQL 16 | Appareils, événements DNS, règles |
| Conteneurisation | Docker Compose | PostgreSQL + Mosquitto + Grafana |
| Messaging | Eclipse Mosquitto (MQTT) | Événements temps réel |
| Monitoring | Grafana | Dashboard de visualisation |
| Réseau | dnsmasq + hostapd + iptables | AP Wi-Fi, DHCP, DNS, filtrage |
| Déploiement | systemd | Services automatiques au boot |
| CI/CD | GitHub Actions | Tests automatisés sur chaque push |
| Tests | pytest | Tests unitaires |

---

## 📦 Prérequis

### Développement (PC)
- Python 3.13+
- Docker & Docker Compose
- Git

### Production (Raspberry Pi)
- Raspberry Pi (avec Wi-Fi)
- Raspberry Pi OS
- `hostapd` + `dnsmasq` installés
- Accès SSH

---

## 💻 Installation — Environnement de développement

```bash
# 1. Cloner le dépôt
git clone https://github.com/RayenFehri/GuardianAI-Gateway.git
cd GuardianAI-Gateway

# 2. Configurer l'environnement
cp .env.example .env

# 3. Créer l'environnement virtuel Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Démarrer l'infrastructure Docker (PostgreSQL + Mosquitto + Grafana)
docker compose up -d

# 5. Vérifier les services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

> **Note :** En mode dev (`GATEWAY_ENV=dev`), les scripts utilisent des fichiers simulés (`fake_dnsmasq.leases`, `fake_dnsmasq.log`) au lieu des vrais fichiers système.

### Variables d'environnement (`.env`)

| Variable | Défaut | Description |
|---|---|---|
| `GATEWAY_ENV` | `dev` | `dev` (PC) ou `pi` (Raspberry Pi) |
| `DB_HOST` | `localhost` | Hôte PostgreSQL |
| `DB_PORT` | `5433` | Port PostgreSQL (Docker) |
| `DB_NAME` | `gateway_db` | Nom de la base |
| `DB_USER` | `gateway_admin` | Utilisateur DB |
| `DB_PASSWORD` | `changeme123` | Mot de passe DB |
| `LAN_SUBNET` | `192.168.50.0/24` | Sous-réseau Wi-Fi du Pi |
| `LAN_INTERFACE` | `uap0` | Interface AP Wi-Fi |
| `WAN_INTERFACE` | `wlan0` | Interface Internet |
| `POLL_INTERVAL` | `60` | Intervalle de polling (secondes) |
| `LOG_LEVEL` | `INFO` | Niveau de log |

---

## 🍓 Déploiement — Raspberry Pi

### Installation automatique

```bash
# Sur le Pi (via SSH)
chmod +x install.sh
./install.sh
```

Le script `install.sh` effectue automatiquement :
1. Mise à jour des paquets
2. Installation de Python 3 et pip
3. Installation de Docker
4. Clonage du dépôt GitHub
5. Lancement de PostgreSQL via Docker
6. Installation des dépendances Python
7. Configuration du cron

### Services systemd (plug-and-play)

Les trois services se lancent automatiquement au démarrage du Pi :

```bash
# Installer les services
sudo bash systemd/install_services.sh

# Vérifier l'état
sudo systemctl status guardian-network guardian-discovery guardian-rules
```

| Service | Rôle | Type |
|---|---|---|
| `guardian-network` | Configure uap0, NAT et iptables FORWARD | `oneshot` (au boot) |
| `guardian-discovery` | Détection continue des appareils (daemon) | `simple` (continu) |
| `guardian-rules` | Application continue des règles (daemon) | `simple` (continu) |

### Synchronisation du code (PC → Pi)

```bash
rsync -av \
  --exclude='venv' --exclude='__pycache__' --exclude='.git' \
  ~/9raya/Projects/gateway_project/ \
  pi@raspberrypi.local:~/gateway_project/
```

---

## 🚀 Utilisation

### Découverte des équipements

```bash
# Mode one-shot
python3 main_discovery.py

# Mode daemon (poll continu)
python3 main_discovery.py --daemon
```

### Analyse des usages DNS

```bash
python3 main_usage_analysis.py
```

### Contrôle parental — Gestion des règles

```bash
# Mode dry-run (PC de dev, sans droits root)
python3 main_rules.py --dry-run

# Mode daemon (Pi, production)
python3 main_rules.py --daemon
```

#### Créer des règles via Python

```python
from db import add_rule, set_rule_active, delete_rule

# Bloquer totalement un appareil
add_rule("a2:50:d5:8f:0b:04", "block_device")

# Blocage horaire (20h → 08h)
add_rule("a2:50:d5:8f:0b:04", "schedule", start_time="20:00", end_time="08:00")

# Bloquer une catégorie DNS pour tout le réseau
add_rule(None, "block_category", "reseaux_sociaux")

# Désactiver / supprimer une règle
set_rule_active(rule_id=1, active=False)
delete_rule(rule_id=1)
```

#### Catégories DNS disponibles

`reseaux_sociaux` · `streaming_video` · `streaming_audio` · `jeux` · `education` · `adulte` · `ia` · `travail` · `paris_jeux_argent`

> Les domaines sont configurables dans `domain_categories.json` sans modifier le code Python.

### Monitoring MQTT

```bash
# Écouter tous les événements en temps réel
docker exec gateway_mosquitto mosquitto_sub -t "guardian/#" -v
```

### Dashboard Grafana

- **URL :** http://localhost:3000
- **Identifiants :** `admin` / `guardian123`
- **Datasource :** PostgreSQL sur `localhost:5433`

---

## 📁 Structure du projet

```
gateway_project/
│
├── config.py                  # Configuration centrale (dev / Pi)
├── .env.example               # Template des variables d'environnement
│
├── main_discovery.py          # 🔍 Orchestrateur Partie 1 — Découverte
├── main_usage_analysis.py     # 📊 Orchestrateur Partie 2 — Analyse DNS
├── main_rules.py              # 🔒 Orchestrateur Partie 3 — Contrôle parental
│
├── discovery.py               # Parsing des leases DHCP
├── oui_lookup.py              # Résolution fabricant via MAC (IEEE OUI)
├── classifier.py              # Classification du type d'équipement
├── dns_log_parser.py          # Parsing des logs DNS (dnsmasq)
├── categories.py              # Classification des domaines par catégorie
├── domain_categories.json     # Base de domaines/catégories (extensible)
├── db.py                      # Accès PostgreSQL (CRUD complet)
├── rule_engine.py             # Application des règles iptables
├── dns_blocker.py             # Blocage DNS par catégorie (dnsmasq)
├── mqtt_publisher.py          # Publication MQTT (temps réel)
│
├── ai/                        # 🧠 Module Intelligence Artificielle
│   ├── __init__.py
│   └── anomaly_detector.py    # Détection d'anomalies (4 détecteurs)
├── main_ai.py                 # Orchestrateur IA (one-shot / daemon)
│
├── docker-compose.yml         # PostgreSQL + Mosquitto + Grafana
├── requirements.txt           # Dépendances Python
├── install.sh                 # Script d'installation pour le Pi
│
├── systemd/                   # Services systemd (déploiement Pi)
│   ├── guardian-network.service
│   ├── guardian-discovery.service
│   ├── guardian-rules.service
│   ├── install_services.sh
│   └── setup_network.sh
│
├── tests/                     # Tests unitaires (pytest)
│   ├── test_anomaly_detector.py
│   ├── test_categories.py
│   ├── test_classifier.py
│   ├── test_dns_log_parser.py
│   ├── test_oui_lookup.py
│   └── test_rule_engine.py
│
├── .github/workflows/ci.yml   # Pipeline CI (GitHub Actions)
├── DEMO_COMMANDS.md            # Guide de démonstration complet
│
├── fake_dnsmasq.leases        # Fichier simulé (dev)
└── fake_dnsmasq.log           # Fichier simulé (dev)
```

---

## 🧩 Modules

### `discovery.py`
Parse le fichier de baux DHCP (`dnsmasq.leases`) pour extraire les appareils connectés au réseau (MAC, IP, hostname).

### `oui_lookup.py`
Résout le fabricant d'un appareil à partir de son adresse MAC en interrogeant la base IEEE OUI.

### `classifier.py`
Classifie le type d'appareil (Smartphone, Smart TV, Console, PC…) en combinant le hostname et le fabricant.

### `dns_log_parser.py`
Parse les logs DNS de dnsmasq pour extraire les requêtes (IP source, domaine, timestamp).

### `categories.py`
Catégorise les domaines visités (réseaux sociaux, streaming, éducation…) à partir du fichier `domain_categories.json`. Support de l'ajout dynamique de domaines.

### `db.py`
Couche d'accès à PostgreSQL — gère les tables `devices`, `dns_events`, `rules` et `ai_anomalies`. Fournit les opérations CRUD, les statistiques d'usage et la déduplication des anomalies IA.

### `rule_engine.py`
Traduit les règles de contrôle parental en commandes `iptables`. Supporte le blocage par MAC avec détection de doublons (idempotent), le blocage horaire avec gestion des plages nocturnes, et le mode dry-run pour le développement.

### `dns_blocker.py`
Gère le filtrage DNS par catégorie en écrivant des règles de blocage dans `/etc/dnsmasq.d/guardian_blocks.conf`. Optimisé pour ne recharger dnsmasq que si la configuration change.

### `mqtt_publisher.py`
Publie les événements du système en JSON sur le broker MQTT Mosquitto. Client singleton avec reconnexion automatique. Dégradation gracieuse si le broker est indisponible.

### `ai/anomaly_detector.py`
Module de détection d'anomalies comportementales. Contient 4 détecteurs indépendants :
- **Usage nocturne** : requêtes DNS entre 23h et 6h
- **Catégorie suspecte** : premier accès à un contenu adulte ou de paris
- **Pic de catégorie** : hausse > 2x par rapport à la moyenne sur 7 jours
- **Nouvel appareil** : MAC jamais vu connecté au réseau

### `main_ai.py`
Orchestrateur de la Partie 5 (IA). Exécute les détecteurs, déduplique les résultats (fenêtre de 6h), sauvegarde en base (`ai_anomalies`) et publie les alertes via MQTT. Supporte les modes one-shot et daemon.

---

## 🗄️ Base de données

### Table `devices`

| Colonne | Type | Description |
|---|---|---|
| `mac` | `TEXT` (PK) | Adresse MAC de l'appareil |
| `ip` | `TEXT` | Adresse IP actuelle |
| `hostname` | `TEXT` | Nom d'hôte réseau |
| `vendor` | `TEXT` | Fabricant (OUI) |
| `device_type` | `TEXT` | Type classifié (Smartphone, PC…) |
| `confidence` | `REAL` | Score de confiance de la classification |
| `first_seen` | `TIMESTAMPTZ` | Première détection |
| `last_seen` | `TIMESTAMPTZ` | Dernière détection |

### Table `dns_events`

| Colonne | Type | Description |
|---|---|---|
| `id` | `SERIAL` (PK) | Identifiant auto-incrémenté |
| `ip` | `TEXT` | IP de l'appareil source |
| `domain` | `TEXT` | Domaine requêté |
| `category` | `TEXT` | Catégorie du domaine |
| `timestamp` | `TIMESTAMPTZ` | Horodatage de la requête |

### Table `rules`

| Colonne | Type | Description |
|---|---|---|
| `id` | `SERIAL` (PK) | Identifiant auto-incrémenté |
| `mac` | `TEXT` | MAC ciblé (`NULL` = tous les appareils) |
| `rule_type` | `TEXT` | `block_device`, `schedule`, `block_category` |
| `target` | `TEXT` | Cible (catégorie DNS pour `block_category`) |
| `start_time` | `TIME` | Début de la plage horaire |
| `end_time` | `TIME` | Fin de la plage horaire |
| `active` | `BOOLEAN` | Règle active ou désactivée |
| `created_at` | `TIMESTAMPTZ` | Date de création |

---

## 📡 Topics MQTT

Tous les messages sont publiés en JSON avec un champ `timestamp` automatique.

| Topic | Déclencheur | Contenu |
|---|---|---|
| `guardian/devices` | Appareil détecté | `mac`, `ip`, `hostname`, `vendor`, `device_type`, `confidence` |
| `guardian/dns` | Requête DNS catégorisée | `ip`, `domain`, `category` |
| `guardian/rules` | Règle appliquée/retirée | `rule_id`, `action`, `mac`, `rule_type`, `target` |
| `guardian/alerts` | Alerte système | `alert_type`, `message`, `mac` |

---

## ✅ Tests

```bash
# Lancer tous les tests
pytest -v

# Lancer un test spécifique
pytest tests/test_categories.py -v

# Avec couverture
pytest --cov=. --cov-report=term-missing
```

Les tests couvrent :
- **`test_categories.py`** — Classification des domaines
- **`test_classifier.py`** — Classification des appareils
- **`test_dns_log_parser.py`** — Parsing des logs DNS
- **`test_oui_lookup.py`** — Résolution OUI / fabricant
- **`test_rule_engine.py`** — Moteur de règles (plages horaires)

---

## 🔁 Intégration continue

Le pipeline CI (`.github/workflows/ci.yml`) s'exécute automatiquement sur chaque **push** et **pull request** vers `main` :

1. Checkout du code
2. Installation de Python 3.13
3. Installation des dépendances (`requirements.txt`)
4. Exécution des tests unitaires (`pytest -v`)

---

## 🚨 Dépannage

| Problème | Vérification | Solution |
|---|---|---|
| Services pas démarrés | `sudo systemctl status guardian-*` | `sudo systemctl start guardian-network guardian-discovery guardian-rules` |
| Téléphone sans Internet | `sudo iptables -t nat -L POSTROUTING -v -n` | Vérifier la règle MASQUERADE |
| Blocage MAC inefficace | `sudo iptables -L FORWARD --line-numbers` | La règle DROP doit être en **position 1** |
| Erreur connexion DB | `sudo journalctl -u guardian-rules -n 10` | Vérifier `.env` → `DB_HOST=<IP du PC>` |
| Grafana sans données | Datasource PostgreSQL | Port `5433`, pas `5432` |
| Wi-Fi invisible | `ip a \| grep uap0` | `sudo systemctl restart guardian-network` |

---

## 🗺️ Roadmap

- [x] **Partie 1** — Découverte et classification des équipements
- [x] **Partie 2** — Analyse des usages Internet (DNS)
- [x] **Partie 3** — Contrôle parental (iptables + DNS + horaires)
- [x] **Infrastructure** — MQTT + Grafana + systemd + CI
- [x] **Partie 5** — IA (détection d'anomalies comportementales)
- [ ] **Partie 4** — Dashboard Web interactif
- [ ] **Partie 5+** — IA avancée (suggestions intelligentes, rapports LLM)

---

## 📄 Licence

Projet réalisé dans le cadre d'un stage. Tous droits réservés.

---

<p align="center">
  <b>GuardianAI Gateway</b> — Protéger, analyser, contrôler 🛡️
</p>
