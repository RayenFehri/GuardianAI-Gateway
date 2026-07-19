"""
Tests unitaires pour rule_engine.py (Partie 3 du CDC).

On teste uniquement la construction des commandes iptables via dry_run,
sans jamais exécuter de vraies commandes système (pas besoin de droits
root ni d'interface réseau réelle pour lancer ces tests).
"""

import subprocess
import pytest
from rule_engine import block_device, unblock_device, RULE_COMMENT


def test_block_device_dry_run_returns_true(capsys):
    result = block_device("AA:BB:CC:DD:EE:FF", dry_run=True)
    assert result is True


def test_block_device_dry_run_prints_correct_command(capsys):
    block_device("AA:BB:CC:DD:EE:FF", dry_run=True)
    captured = capsys.readouterr()
    assert "iptables" in captured.out
    assert "-j DROP" in captured.out
    assert "aa:bb:cc:dd:ee:ff" in captured.out  # normalisé en minuscule


def test_block_device_includes_comment_tag(capsys):
    block_device("AA:BB:CC:DD:EE:FF", dry_run=True)
    captured = capsys.readouterr()
    assert RULE_COMMENT in captured.out


def test_unblock_device_uses_delete_flag(capsys):
    unblock_device("AA:BB:CC:DD:EE:FF", dry_run=True)
    captured = capsys.readouterr()
    assert "-D FORWARD" in captured.out


def test_block_device_real_call_handles_missing_iptables(monkeypatch):
    """
    Si iptables n'est pas installé (ex: CI GitHub Actions), la fonction doit
    retourner False proprement plutôt que de planter avec une exception.
    """
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("iptables not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = block_device("AA:BB:CC:DD:EE:FF", dry_run=False)
    assert result is False