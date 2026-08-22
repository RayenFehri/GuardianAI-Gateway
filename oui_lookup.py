"""
oui_lookup.py — Résolution du fabricant à partir de l'adresse MAC (OUI)
Partie 1 : une des sources de fingerprinting listées dans le CDC.

Stratégie à 3 niveaux :
  1. Base IEEE complète via le package mac-vendor-lookup (~50 000 fabricants)
  2. Si non trouvé ou package absent → table locale OUI_TABLE (fabricants courants)
  3. Si toujours rien → retourne "Unknown"

Pour mettre à jour la base IEEE (nécessite Internet) :
    python3 -c "from mac_vendor_lookup import MacLookup; MacLookup().update_vendors()"
"""

# Table locale de fallback — couvre les fabricants les plus courants
# dans un réseau domestique, au cas où mac-vendor-lookup ne trouve pas.
OUI_TABLE = {
    "AC233F": "Apple",
    "F4F5E8": "Apple",
    "3C0754": "Apple",
    "B827EB": "Raspberry Pi Foundation",
    "DCA632": "Raspberry Pi Foundation",
    "E45F01": "Raspberry Pi Foundation",
    "2CCF67": "Raspberry Pi Foundation",  # Pi 4/5
    "D83ADD": "Raspberry Pi Foundation",
    "001A11": "Google",
    "F4F26D": "Google",
    "702F4B": "Samsung",
    "8C7967": "Samsung",
    "94B86D": "Samsung",
    "001DD8": "Microsoft",
    "7CED8D": "Microsoft",
    "0004E2": "Sony",
    "AC72B9": "Sony",
    "9CB6D0": "Sony",
    "9803D8": "Nintendo",
    "001B7A": "Nintendo",
    "F06728": "OPPO",
    "3425C4": "Xiaomi",
    "7851D7": "Xiaomi",
    "F8A45F": "Xiaomi",
}

# Chargement du package IEEE (optionnel — dégradé gracieusement si absent)
try:
    from mac_vendor_lookup import MacLookup as _MacLookup
    _mac_lookup = _MacLookup()
    _IEEE_AVAILABLE = True
except ImportError:
    _mac_lookup = None
    _IEEE_AVAILABLE = False


def normalize_mac(mac: str) -> str:
    """Normalise une adresse MAC : retire les séparateurs, met en majuscules."""
    return mac.replace(":", "").replace("-", "").replace(".", "").upper()


def get_vendor(mac: str) -> str:
    """
    Retourne le fabricant probable d'un équipement à partir de son adresse MAC.

    Ordre de recherche :
      1. Base IEEE complète (mac-vendor-lookup) — ~50 000 entrées
      2. Table locale OUI_TABLE                 — fallback hors-ligne
      3. "Unknown"                              — si aucune correspondance
    """
    oui = normalize_mac(mac)[:6]

    # Niveau 1 — Base IEEE complète
    if _IEEE_AVAILABLE:
        try:
            vendor = _mac_lookup.lookup(mac)
            if vendor:
                return vendor
        except Exception:
            pass  # MAC non trouvé dans la base IEEE → on passe au fallback

    # Niveau 2 — Table locale
    local = OUI_TABLE.get(oui)
    if local:
        return local

    # Niveau 3 — Inconnu
    return "Unknown"


def is_ieee_available() -> bool:
    """Indique si la base IEEE complète est disponible."""
    return _IEEE_AVAILABLE


if __name__ == "__main__":
    print(f"Base IEEE disponible : {is_ieee_available()}")
    print()
    tests = [
        ("AC:23:3F:11:22:33", "Apple attendu"),
        ("b8:27:eb:aa:bb:cc", "Raspberry Pi attendu"),
        ("00:11:22:33:44:55", "Unknown attendu"),
        ("DC:A6:32:00:11:22", "Raspberry Pi attendu"),
    ]
    for mac, label in tests:
        result = get_vendor(mac)
        print(f"{mac}  →  {result:30s}  ({label})")
