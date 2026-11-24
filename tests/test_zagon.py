# -*- coding: utf-8 -*-
"""Neinteraktivni zagon (issue #6, §9) — kode 0/1/2 in resničen CLI.

Revizija je to vejo preverila le s smoke testom zgrajenega EXE; tu so
meje pokrite neposredno, vključno z dejanskim klicem `vmesnik.py`.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest
import yaml

pytest.importorskip("tkinter")

from conftest import osnovni_cfg, stevilo_strani  # noqa: E402
import vmesnik  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]


def _cli(args, tmp_path, **okolje_dodatno):
    """Zažene pravi CLI v podprocesu (brez dedovanja headless zastavice)."""
    okolje = {k: v for k, v in os.environ.items()
              if k != "TEHNICNA_RISBA_HEADLESS"}
    okolje["PYTHONIOENCODING"] = "utf-8"
    okolje["TEHNICNA_RISBA_DATA"] = str(tmp_path / "data")
    okolje.update(okolje_dodatno)
    (tmp_path / "data").mkdir(exist_ok=True)
    return subprocess.run(
        [sys.executable, str(REPO / "vmesnik.py"), *args],
        cwd=str(tmp_path), env=okolje, capture_output=True,
        encoding="utf-8", errors="replace", timeout=300)


def test_brez_konfiguracije_vrne_2(capsys):
    assert vmesnik.zazeni_brez_zaslona([]) == 2
    assert "Uporaba" in capsys.readouterr().err


def test_manjkajoca_datoteka_vrne_1(tmp_path, capsys):
    assert vmesnik.zazeni_brez_zaslona([str(tmp_path / "ni.json")]) == 1
    assert "NAPAKA:" in capsys.readouterr().err


def test_neveljaven_json_vrne_1(tmp_path, capsys):
    pot = tmp_path / "pokvarjen.json"
    pot.write_text("{", encoding="utf-8")
    assert vmesnik.zazeni_brez_zaslona([str(pot)]) == 1
    assert "NAPAKA:" in capsys.readouterr().err


@pytest.mark.parametrize("koncnica", [".json", ".yaml"])
def test_zastavica_odstranjena_in_konfiguracija_prebrana(
        tmp_path, monkeypatch, capsys, koncnica):
    cfg = osnovni_cfg(tmp_path / "out.pdf")
    pot = tmp_path / ("cfg" + koncnica)
    if koncnica == ".json":
        pot.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    else:
        pot.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")

    klici = []

    def _generiraj(prebrano, dpi_png=200):
        klici.append(prebrano)
        return (str(tmp_path / "out.pdf"), None, {}, {})

    monkeypatch.setattr(vmesnik.risba, "generiraj", _generiraj)
    assert vmesnik.zazeni_brez_zaslona(["--brez-zaslona", str(pot)]) == 0
    assert "Izdelano:" in capsys.readouterr().out
    assert klici and klici[0]["izhod"].endswith("out.pdf")


def test_cli_izdela_pdf_iz_okolja(tmp_path):
    """Resničen podproces: TEHNICNA_RISBA_HEADLESS=1 + konfiguracija."""
    cfg = osnovni_cfg(tmp_path / "izhod.pdf")
    pot = tmp_path / "projekt.json"
    pot.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    r = _cli([str(pot)], tmp_path, TEHNICNA_RISBA_HEADLESS="1")
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "Izdelano:" in r.stdout
    pdf = tmp_path / "izhod.pdf"
    assert pdf.is_file()
    assert stevilo_strani(pdf) >= 2