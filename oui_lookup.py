"""
oui_lookup.py — Résolution du fabricant à partir de l'adresse MAC (OUI)
Partie 1 : une des sources de fingerprinting listées dans le CDC.

Les 3 premiers octets d'une adresse MAC (l'OUI) identifient le fabricant
de la carte réseau. On utilise ici une petite table locale pour prototyper
sans dépendre d'Internet. Plus tard, tu pourras télécharger la base
officielle complète ici : https://standards-oui.ieee.org/oui/oui.txt
et la charger dans OUI_TABLE (ou dans un fichier oui.txt à part).
"""

# Table réduite pour le prototype — à enrichir progressivement.
# Clé = 6 premiers caractères hex de la MAC (sans les ':'), en majuscules.
OUI_TABLE = {
    "AC233F": "Apple",
    "F4F5E8": "Apple",
    "3C0754": "Apple",
    "B827EB": "Raspberry Pi Foundation",
    "DCA632": "Raspberry Pi Foundation",
    "E45F01": "Raspberry Pi Foundation",
    "001A11": "Google",
    "F4F26D": "Google",
    "702F4B": "Samsung",
    "8C7967": "Samsung",
    "94B86D": "Samsung",  # Smart TV Samsung fréquent
    "001DD8": "Microsoft",  # Xbox
    "7CED8D": "Microsoft",
    "0004E2": "Sony",  # PlayStation
    "AC72B9": "Sony",
    "9CB6D0": "Sony",
    "9803D8": "Nintendo",
    "001B7A": "Nintendo",
}


def normalize_mac(mac: str) -> str:
    return mac.replace(":", "").replace("-", "").upper()


def get_vendor(mac: str) -> str:
    """Retourne le fabricant probable, ou 'Unknown' si non trouvé."""
    oui = normalize_mac(mac)[:6]
    return OUI_TABLE.get(oui, "Unknown")


if __name__ == "__main__":
    tests = ["AC:23:3F:11:22:33", "b8:27:eb:aa:bb:cc", "00:11:22:33:44:55"]
    for m in tests:
        print(m, "->", get_vendor(m))
