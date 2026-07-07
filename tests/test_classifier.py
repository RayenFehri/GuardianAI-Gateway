"""Tests unitaires pour la classification du type d'équipement (classifier.py)."""

from classifier import classify_device


def test_hostname_iphone_detected_as_smartphone():
    device_type, confidence = classify_device("iPhone-de-Lucas", "Apple")
    assert device_type == "Smartphone"
    assert confidence >= 0.8  # indice explicite dans le hostname => forte confiance


def test_hostname_priority_over_vendor():
    # Le hostname dit "android" alors que le vendor est Sony (MAC randomisée par ex.)
    # Le hostname doit l'emporter, car c'est un indice plus fiable.
    device_type, _ = classify_device("android-4f3e2", "Sony")
    assert device_type == "Smartphone"


def test_vendor_fallback_when_no_hostname_hint():
    device_type, confidence = classify_device("", "Sony")
    assert device_type == "Console"
    assert 0.4 <= confidence < 0.8  # confiance moyenne, déduite du vendor seul


def test_unknown_device_low_confidence():
    device_type, confidence = classify_device("unknown-device", "Unknown")
    assert device_type == "Unknown"
    assert confidence < 0.5


def test_smart_tv_detection():
    device_type, _ = classify_device("SamsungTV", "Samsung")
    assert device_type == "Smart TV"
