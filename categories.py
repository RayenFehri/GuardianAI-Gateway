"""
categories.py — Classification des domaines en catégories d'usage (Partie 2 du CDC)

Approche simple par correspondance de domaine (dictionnaire), comme décrit
en section 4.2.2 du CDC. Suffisant pour un stage : pas besoin de ML pour
commencer, un ML viendrait affiner cette classification plus tard (Partie 5).
"""

# Domaine (ou fragment de domaine) -> catégorie
# Liste volontairement réduite pour le prototype ; à enrichir progressivement.
DOMAIN_CATEGORIES = {
    # Réseaux sociaux
    "tiktok.com": "reseaux_sociaux",
    "instagram.com": "reseaux_sociaux",
    "facebook.com": "reseaux_sociaux",
    "snapchat.com": "reseaux_sociaux",
    "twitter.com": "reseaux_sociaux",
    "x.com": "reseaux_sociaux",

    # Streaming vidéo
    "youtube.com": "streaming_video",
    "netflix.com": "streaming_video",
    "twitch.tv": "streaming_video",
    "akamai.net": "streaming_video",

    # Streaming audio
    "spotify.com": "streaming_audio",
    "deezer.com": "streaming_audio",
    "soundcloud.com": "streaming_audio",

    # Jeux en ligne
    "battlenet.com": "jeux",
    "ea.com": "jeux",
    "roblox.com": "jeux",
    "epicgames.com": "jeux",
    "steampowered.com": "jeux",

    # Éducation
    "khanacademy.org": "education",
    "coursera.org": "education",
    "duolingo.com": "education",
    "wikipedia.org": "education",

    # Travail / Productivité
    "office365.com": "travail",
    "google.com": "travail",
    "slack.com": "travail",
    "zoom.us": "travail",

    # IA / LLM
    "openai.com": "ia",
    "claude.ai": "ia",
    "gemini.google.com": "ia",
}


def classify_domain(domain: str) -> str:
    """
    Retourne la catégorie d'un domaine, ou 'autre' si aucune correspondance.
    Vérifie que le domaine correspond exactement OU se termine par
    ".<domaine_connu>" — pour éviter les faux positifs comme "x.com"
    qui matcherait à tort une sous-chaîne de "netflix.com".
    """
    domain_lower = domain.lower()
    for known_domain, category in DOMAIN_CATEGORIES.items():
        if domain_lower == known_domain or domain_lower.endswith("." + known_domain):
            return category
    return "autre"


if __name__ == "__main__":
    tests = ["www.tiktok.com", "khanacademy.org", "randomsite.xyz", "api.openai.com"]
    for d in tests:
        print(d, "->", classify_domain(d))