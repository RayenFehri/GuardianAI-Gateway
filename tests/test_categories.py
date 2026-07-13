"""Tests unitaires pour la classification des domaines par catégorie (categories.py)."""

from categories import classify_domain


def test_exact_domain_match():
    assert classify_domain("tiktok.com") == "reseaux_sociaux"


def test_subdomain_match():
    # "www.tiktok.com" doit être reconnu comme tiktok.com
    assert classify_domain("www.tiktok.com") == "reseaux_sociaux"


def test_unknown_domain_returns_autre():
    assert classify_domain("randomsite.xyz") == "autre"


def test_no_false_positive_substring_match():
    # Piège classique : "x.com" (Twitter/X) ne doit PAS matcher "netflix.com"
    # juste parce que "x.com" est une sous-chaîne de "netflix.com".
    assert classify_domain("netflix.com") == "streaming_video"
    assert classify_domain("x.com") == "reseaux_sociaux"


def test_education_domain():
    assert classify_domain("khanacademy.org") == "education"