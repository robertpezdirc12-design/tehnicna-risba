# -*- coding: utf-8 -*-
"""CLI: neveljavna konfiguracija je jasna napaka, ne sled sklada."""
import os
import subprocess
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parents[1]


def _zazeni(pot):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "risba.py", str(pot)], cwd=KOREN, env=env,
        capture_output=True, text=True, timeout=120)


def test_manjkajoca_konfiguracija_brez_sledi(tmp_path):
    r = _zazeni(tmp_path / "ni.yaml")
    assert r.returncode != 0
    izhod = r.stdout + r.stderr
    assert "Napaka pri branju konfiguracije" in izhod
    assert "Traceback" not in izhod


def test_konfiguracija_seznam_brez_sledi(tmp_path):
    pot = tmp_path / "seznam.yaml"
    pot.write_text("- a\n- b\n", encoding="utf-8")
    r = _zazeni(pot)
    assert r.returncode != 0
    izhod = r.stdout + r.stderr
    assert "Napaka pri branju konfiguracije" in izhod
    assert "sliko" in izhod
    assert "Traceback" not in izhod