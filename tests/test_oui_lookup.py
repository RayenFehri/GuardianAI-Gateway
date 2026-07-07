"""Tests unitaires pour la résolution du fabricant (oui_lookup.py)."""

from oui_lookup import get_vendor, normalize_mac


def test_normalize_mac_removes_separators():
    assert normalize_mac("AC:23:3F:11:22:33") == "AC233F112233"
    assert normalize_mac("ac-23-3f-11-22-33") == "AC233F112233"


def test_get_vendor_known_apple():
    assert get_vendor("AC:23:3F:11:22:33") == "Apple"


def test_get_vendor_known_raspberry():
    assert get_vendor("b8:27:eb:aa:bb:cc") == "Raspberry Pi Foundation"


def test_get_vendor_unknown_mac():
    assert get_vendor("00:11:22:33:44:55") == "Unknown"


def test_get_vendor_case_insensitive():
    # Le même OUI en minuscule et majuscule doit donner le même résultat
    assert get_vendor("ac:23:3f:00:00:00") == get_vendor("AC:23:3F:00:00:00")
