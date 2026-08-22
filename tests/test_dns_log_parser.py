"""
Tests unitaires pour dns_log_parser.py (Partie 2 du CDC).

Vérifie en particulier que les requêtes émises par le Pi lui-même
(127.0.0.1) sont bien exclues des résultats, pour ne pas fausser les
statistiques d'usage (bug observé en conditions réelles sur le Pi :
1720 requêtes NTP du Pi noyaient les 116 requêtes réelles d'un téléphone).
"""

from pathlib import Path
from dns_log_parser import parse_dns_log


def _write_log(tmp_path: Path, content: str) -> Path:
    log_file = tmp_path / "test_dnsmasq.log"
    log_file.write_text(content)
    return log_file


def test_parses_real_device_query(tmp_path):
    content = "Jul 18 19:24:27 dnsmasq[123]: query[A] www.google.com from 192.168.50.52\n"
    log_file = _write_log(tmp_path, content)
    events = parse_dns_log(path=log_file, year=2026)
    assert len(events) == 1
    assert events[0]["ip"] == "192.168.50.52"
    assert events[0]["domain"] == "www.google.com"


def test_ignores_localhost_ntp_queries(tmp_path):
    content = (
        "Jul 18 20:03:42 dnsmasq[123]: query[A] 2.debian.pool.ntp.org from 127.0.0.1\n"
        "Jul 18 19:24:27 dnsmasq[123]: query[A] www.google.com from 192.168.50.52\n"
    )
    log_file = _write_log(tmp_path, content)
    events = parse_dns_log(path=log_file, year=2026)

    # Seule la requête du vrai appareil (192.168.50.52) doit être gardée
    assert len(events) == 1
    assert events[0]["ip"] == "192.168.50.52"
    assert all(e["ip"] != "127.0.0.1" for e in events)


def test_missing_file_returns_empty_list(tmp_path):
    missing_path = tmp_path / "does_not_exist.log"
    events = parse_dns_log(path=missing_path, year=2026)
    assert events == []


def test_malformed_lines_are_skipped(tmp_path):
    content = (
        "ceci n'est pas une ligne dnsmasq valide\n"
        "Jul 18 19:24:27 dnsmasq[123]: query[A] www.google.com from 192.168.50.52\n"
    )
    log_file = _write_log(tmp_path, content)
    events = parse_dns_log(path=log_file, year=2026)
    assert len(events) == 1