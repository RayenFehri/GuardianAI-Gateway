"""Tests unitaires pour la résolution du fabricant (oui_lookup.py)."""

from oui_lookup import get_vendor, normalize_mac


def test_normalize_mac_removes_separators():
    assert normalize_mac("AC:23:3F:11:22:33") == "AC233F112233"
    assert normalize_mac("ac-23-3f-11-22-33") == "AC233F112233"


def test_get_vendor_known_raspberry():
    # B8:27:EB est l'OUI officiel de Raspberry Pi Foundation — présent
    # dans notre table locale ET dans la base IEEE → fiable
    assert get_vendor("b8:27:eb:aa:bb:cc") == "Raspberry Pi Foundation"


def test_get_vendor_known_raspberry_2():
    # DC:A6:32 — autre OUI officiel Pi (Pi 4)
    # La base IEEE retourne parfois "Raspberry Pi Trading Ltd" au lieu de
    # "Raspberry Pi Foundation" — les deux sont corrects
    result = get_vendor("dc:a6:32:00:11:22")
    assert "Raspberry Pi" in result


def test_get_vendor_unknown_mac():
    # Les adresses MAC localement administrées (bit 1 du premier octet = 1)
    # ne sont jamais attribuées par IEEE → toujours "Unknown"
    # 02:xx:xx:xx:xx:xx est dans la plage localement administrée
    result = get_vendor("02:00:00:00:00:00")
    assert result == "Unknown"


def test_get_vendor_case_insensitive():
    # Le même OUI en minuscule et majuscule doit donner le même résultat
    assert get_vendor("b8:27:eb:00:00:00") == get_vendor("B8:27:EB:00:00:00")
