# -*- coding: utf-8 -*-
"""Načrt 10: QC seznam (delavnica + teren) + potrditvena polja pri korakih.

Potrditvena polja so PRAZNA (obrazec) — nič ni označeno kot opravljeno.
"""
from pypdf import PdfReader

import risba
from conftest import osnovni_cfg

import pytest

# Počasnejši testi (večstransko generiranje PDF) — hitra zanka: -m "not pocasi"
pytestmark = pytest.mark.pocasi


def _besedilo_strani(cfg):
    pdf, _png, _dod, _kol = risba.generiraj(cfg, dpi_png=30)
    r = PdfReader(pdf)
    return "".join((p.extract_text() or "") for p in r.pages)


def test_qc_seznam_ograja(tmp_path):
    b = _besedilo_strani(osnovni_cfg(str(tmp_path / "o.pdf")))
    assert "KONTROLNI SEZNAM" in b and "QC" in b
    assert "DELAVNICA" in b and "TEREN" in b
    # kriteriji vezani na risbo
    assert "blok toleranc" in b
    assert "rezalni načrt" in b
    assert "DETAJL 1" in b
    # iskreno: statik
    assert "Statiko potrdil strokovnjak" in b


def test_qc_seznam_pokoncna(tmp_path):
    b = _besedilo_strani(osnovni_cfg(str(tmp_path / "p.pdf"),
                                     predloga="pokončna"))
    assert "KONTROLNI SEZNAM" in b
    assert "DELAVNICA" in b and "TEREN" in b


def test_montazni_koraki_s_potrditvenimi_polji(tmp_path):
    b = _besedilo_strani(osnovni_cfg(str(tmp_path / "k.pdf")))
    assert "MONTAŽNI KORAKI" in b
    assert "potrdi" in b                # naslov: 'MONTAŽNI KORAKI — potrdi ☐'
    assert "☐" in b                     # potrditvena polja pri korakih


def test_podpis_kontrole(tmp_path):
    b = _besedilo_strani(osnovni_cfg(str(tmp_path / "s.pdf")))
    assert "KONTROLA (QC podpis)" in b
    assert "IZDELAL (podpis)" in b
    assert "STRANKA (prejem dela)" in b
    assert "DATUM MONTAŽE" in b


def test_polja_so_prazna(tmp_path):
    """Obrazec: nobena kontrola NI označena kot opravljena."""
    b = _besedilo_strani(osnovni_cfg(str(tmp_path / "pz.pdf"))
    )
    # ☐ so prisotna kot prazna polja; kljukiranih oznak (☑/✔) ni
    assert "☑" not in b and "✔" not in b
