# -*- coding: utf-8 -*-
"""CLI zastavici, ki ju doslej ni preverjal noben test: --dxf in
--potrosi-ostanke (resničen podproces, izolirano skladišče)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import osnovni_cfg

# Polna generacija PDF v podprocesu (~25 s/test) — hitra zanka ju preskoči.
pytestmark = pytest.mark.pocasi

REPO = Path(__file__).resolve().parents[1]


def _cli(pot, tmp_path, *args):
    env = {k: v for k, v in os.environ.items()
           if k != "TEHNICNA_RISBA_HEADLESS"}
    env["TEHNICNA_RISBA_DATA"] = str(tmp_path / "data")
    env["PYTHONIOENCODING"] = "utf-8"
    (tmp_path / "data").mkdir(exist_ok=True)
    return subprocess.run(
        [sys.executable, str(REPO / "risba.py"), str(pot), *args],
        cwd=str(tmp_path), env=env, capture_output=True,
        encoding="utf-8", errors="replace", timeout=300)


def _projekt(tmp_path, **spremembe):
    cfg = osnovni_cfg(tmp_path / "out.pdf", **spremembe)
    pot = tmp_path / "projekt.yaml"
    pot.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return pot


def test_cli_dxf_izvozi_datoteko(tmp_path):
    pot = _projekt(tmp_path)
    r = _cli(pot, tmp_path, "--dxf")
    assert r.returncode == 0, (r.stdout, r.stderr)
    dxf = tmp_path / "out.dxf"
    assert dxf.is_file() and dxf.stat().st_size > 1000
    import ezdxf
    doc = ezdxf.readfile(str(dxf))
    assert len(list(doc.modelspace())) > 0


def test_cli_potrosi_ostanke_odpise_in_naredi_kopijo(tmp_path):
    pot = _projekt(tmp_path, uporabi_ostanke=True)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    ostanki = data / "ostanki.yaml"
    ostanki.write_text("- dolzina: 5800\n  barva: Antracit\n  profil: ROMB 67\n",
                       encoding="utf-8")

    r = _cli(pot, tmp_path, "--potrosi-ostanke")
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "[OK] Ostanki odpisani" in r.stdout
    assert (data / "ostanki.yaml.bak").is_file()

    stari = yaml.safe_load((data / "ostanki.yaml.bak").read_text(encoding="utf-8"))
    novi = yaml.safe_load(ostanki.read_text(encoding="utf-8"))
    assert stari[0]["dolzina"] == 5800
    assert novi and all(o["dolzina"] < 5800 for o in novi)