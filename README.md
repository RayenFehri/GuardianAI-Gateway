# AI Smart Parental Gateway — Prototype de stage

![CI](https://github.com/<ton-user>/<ton-repo>/actions/workflows/ci.yml/badge.svg)

Prototype d'assistant parental intelligent intégré à une gateway réseau,
développé dans le cadre d'un stage. Le système analyse les usages Internet
des équipements connectés au réseau domestique et aide les parents à mettre
en place des règles adaptées.

## Fonctionnalités (Partie 1 — Découverte des équipements)

- Lecture des baux DHCP (qui s'est connecté au réseau)
- Résolution du fabricant via l'adresse MAC (OUI)
- Classification automatique du type d'équipement (smartphone, Smart TV, console...)
- Stockage en base PostgreSQL

## Stack technique

- Python 3.13
- PostgreSQL 16 (via Docker)
- pytest (tests automatisés)
- GitHub Actions (intégration continue)

## Installation

```bash
git clone <url-du-repo>
cd gateway_project

# Copier le fichier d'environnement
cp .env.example .env

# Environnement virtuel Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Démarrer PostgreSQL
docker compose up -d

# Lancer la découverte
python3 main_discovery.py
```

## Lancer les tests

```bash
pytest -v
```

## Structure du projet

```
gateway_project/
├── discovery.py       # Lecture des leases DHCP
├── oui_lookup.py      # Résolution fabricant via MAC
├── classifier.py      # Classification du type d'équipement
├── db.py              # Accès PostgreSQL
├── main_discovery.py  # Orchestrateur
├── tests/             # Tests automatisés (pytest)
├── docker-compose.yml # Conteneur PostgreSQL
└── .github/workflows/ # Pipeline CI (GitHub Actions)
```

## Roadmap

- [x] Partie 1 — Découverte et classification des équipements
- [ ] Partie 2 — Analyse des usages (DNS)
- [ ] Partie 3 — Contrôle parental (règles)
- [ ] Partie 4 — Dashboard Web
- [ ] Partie 5 — IA (détection d'anomalies, suggestions)
