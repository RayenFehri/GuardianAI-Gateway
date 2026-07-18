"""
classifier.py — Classification du type d'équipement (Partie 1 du CDC)

Combine plusieurs sources (fusion multi-sources, comme décrit dans le CDC) :
- le fabricant (vendor, déduit du MAC OUI)
- le hostname déclaré en DHCP
pour proposer un type d'équipement + un score de confiance.

C'est volontairement simple (des règles) pour commencer : tu pourras
remplacer ça par un vrai modèle ML plus tard si le temps le permet,
mais des règles bien pensées couvrent déjà 80% des cas réels.
"""

# Mots-clés cherchés dans le hostname (insensible à la casse)
HOSTNAME_HINTS = {
    "iphone": "Smartphone",
    "android": "Smartphone",
    "galaxy": "Smartphone",
    "pixel": "Smartphone",
    "ipad": "Tablette",
    "tab": "Tablette",
    "macbook": "Laptop",
    "laptop": "Laptop",
    "pc-": "PC",
    "desktop": "PC",
    "tv": "Smart TV",
    "bravia": "Smart TV",  # Sony TV
    "chromecast": "Objet IoT",
    "echo": "Objet IoT",
    "alexa": "Objet IoT",
    "printer": "Imprimante",
    "nas": "NAS",
    "oppo": "Smartphone",   # ex: "OPPO-A31" (identifié en conditions réelles)
    "xiaomi": "Smartphone",
    "redmi": "Smartphone",
}

# Vendor -> type par défaut si le hostname ne dit rien
VENDOR_HINTS = {
    "Apple": "Smartphone",       # à affiner (iPhone vs iPad vs Mac)
    "Samsung": "Smartphone",
    "Google": "Objet IoT",
    "Sony": "Console",
    "Microsoft": "Console",
    "Nintendo": "Console",
    "Raspberry Pi Foundation": "Raspberry Pi",
    "OPPO": "Smartphone",
}


def classify_device(hostname: str, vendor: str) -> tuple[str, float]:
    """
    Retourne (device_type, confidence) entre 0 et 1.
    Stratégie : hostname d'abord (plus précis), sinon vendor, sinon Unknown.
    """
    hostname_lower = (hostname or "").lower()

    for keyword, device_type in HOSTNAME_HINTS.items():
        if keyword in hostname_lower:
            return device_type, 0.9  # forte confiance : indice explicite

    if vendor in VENDOR_HINTS:
        return VENDOR_HINTS[vendor], 0.6  # confiance moyenne : déduit du vendor seul

    return "Unknown", 0.2


if __name__ == "__main__":
    print(classify_device("iPhone-de-Lucas", "Apple"))
    print(classify_device("", "Sony"))
    print(classify_device("android-4f3e2", "Samsung"))
    print(classify_device("raspberrypi", "Raspberry Pi Foundation"))
