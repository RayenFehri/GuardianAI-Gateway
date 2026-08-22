"""
categories.py — Classification des domaines en catégories d'usage (Partie 2 du CDC)

Les données sont externalisées dans domain_categories.json — tu peux ajouter
un domaine sans toucher à ce fichier Python :
    from categories import add_domain
    add_domain("bereal.com", "reseaux_sociaux")

Approche simple par correspondance de domaine, comme décrit en section 4.2.2
du CDC. Un ML viendrait affiner cette classification en Partie 5.
"""

import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "domain_categories.json"


def _load() -> dict[str, str]:
    """
    Charge le fichier JSON et retourne un dict plat {domaine: catégorie}.
    Format JSON : {"categorie": ["domaine1", "domaine2", ...], ...}
    """
    with open(_DATA_FILE, encoding="utf-8") as f:
        raw: dict[str, list[str]] = json.load(f)

    flat = {}
    for category, domains in raw.items():
        for domain in domains:
            flat[domain] = category
    return flat


# Chargé une seule fois au démarrage du module
DOMAIN_CATEGORIES: dict[str, str] = _load()


def classify_domain(domain: str) -> str:
    """
    Retourne la catégorie d'un domaine, ou 'autre' si aucune correspondance.
    Vérifie que le domaine correspond exactement OU se termine par
    ".<domaine_connu>" — pour éviter les faux positifs.
    """
    domain_lower = domain.lower()
    for known_domain, category in DOMAIN_CATEGORIES.items():
        if domain_lower == known_domain or domain_lower.endswith("." + known_domain):
            return category
    return "autre"


def add_domain(domain: str, category: str) -> None:
    """
    Ajoute un domaine dans le fichier JSON et recharge le module.
    Permet d'enrichir les catégories sans modifier le code Python.

    Exemple :
        add_domain("bereal.com", "reseaux_sociaux")
    """
    with open(_DATA_FILE, encoding="utf-8") as f:
        raw: dict[str, list[str]] = json.load(f)

    if category not in raw:
        raw[category] = []

    if domain not in raw[category]:
        raw[category].append(domain)
        raw[category].sort()

        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)

        # Recharge le dict global
        global DOMAIN_CATEGORIES
        DOMAIN_CATEGORIES = _load()
        print(f"Domaine '{domain}' ajouté dans la catégorie '{category}'.")
    else:
        print(f"Domaine '{domain}' déjà présent dans '{category}'.")


def list_categories() -> dict[str, int]:
    """Retourne le nombre de domaines par catégorie."""
    counts: dict[str, int] = {}
    for category in DOMAIN_CATEGORIES.values():
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    print(f"=== {len(DOMAIN_CATEGORIES)} domaines chargés depuis {_DATA_FILE.name} ===\n")
    for cat, count in list_categories().items():
        print(f"  {cat:<25} : {count} domaine(s)")
    print()
    tests = ["www.tiktok.com", "khanacademy.org", "randomsite.xyz", "api.openai.com"]
    for d in tests:
        print(f"  {d} -> {classify_domain(d)}")