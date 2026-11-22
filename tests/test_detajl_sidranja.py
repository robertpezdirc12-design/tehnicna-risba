# -*- coding: utf-8 -*-
"""Načrt 8: DETAJL 1 — SIDRANJE, dimenzioniran in povezan s tabelo.

Poštenost: vrednosti so ≈ priporočene ('potrdi strokovnjak') ali iskren '??'
(NEZNANO) — nikoli izmišljene.
"""
from pypdf import PdfReader

import jedro
import risba
from conftest import osnovni_cfg


# ---------- en vir resnice ----------

def test_priporoceno_sidranje_poznane_podlage():
    assert jedro.priporoceno_sidranje("beton") == ("Beton C20/25", "anker M10", 60)
    assert jedro.priporoceno_sidranje("Beton C30/37")[2] == 60
    assert jedro.priporoceno_sidranje("zid")[2] == 70
    assert jedro.priporoceno_sidranje("opeka")[2] == 70
    assert jedro.priporoceno_sidranje("les")[2] == 40
    assert jedro.priporoceno_sidranje("jeklo")[2] == 40


def test_priporoceno_sidranje_neznano():
    """Nepoznana/prazna podlaga -> brez izmišljanja (None, None, None)."""
    assert jedro.priporoceno_sidranje("") == (None, None, None)
    assert jedro.priporoceno_sidranje(None) == (None, None, None)
    assert jedro.priporoceno_sidranje("asfalt") == (None, None, None)


def test_napisi_sidranja_iskreno():
    g, r = risba.napisi_sidranja("beton")
    assert "≈ 60 mm" in g and "potrdi strokovnjak" in g
    assert "??" in r and "določi projektant" in r
    g2, _ = risba.napisi_sidranja("")
    assert "??" in g2 and "določi projektant" in g2
    assert "60" not in g2          # brez podlage NE navedemo globine


# ---------- risba: detajl v PDF (obe predlogi) ----------

def _besedilo(cfg, tmp, ime):
    pdf, _png, _dod, _kol = risba.generiraj(cfg, dpi_png=30)
    return "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)


def test_detajl_ograja_beton(tmp_path):
    c = osnovni_cfg(str(tmp_path / "o.pdf"))
    c["podlaga"] = "beton"
    b = _besedilo(c, tmp_path, "o")
    assert "DETAJL 1" in b and "SIDRANJE" in b
    assert "globina sidra" in b and "60 mm" in b
    assert "oddaljenost roba sidra" in b and "??" in b
    assert "NERAZMERJENO" in b              # iskreno: detajl ni v merilu
    assert "DETAJL PRITRJEVANJA" not in b   # staro ime je odstranjeno


def test_detajl_ograja_brez_podlage(tmp_path):
    """Brez podlage je globina ?? — NE izmišljena."""
    c = osnovni_cfg(str(tmp_path / "o2.pdf"))
    c["podlaga"] = ""
    b = _besedilo(c, tmp_path, "o2")
    assert "globina sidra ??" in b
    assert "≈ 60 mm" not in b and "≈ 70 mm" not in b and "≈ 40 mm" not in b


def test_detajl_pokoncna_zid(tmp_path):
    c = osnovni_cfg(str(tmp_path / "p.pdf"), predloga="pokončna")
    c["podlaga"] = "zid"
    b = _besedilo(c, tmp_path, "p")
    assert "DETAJL 1" in b and "SIDRANJE" in b
    assert "globina sidra" in b and "70 mm" in b


def test_tabela_in_detajl_enak_vir(tmp_path):
    """Montažni list: tabela SIDRANJE kaže DETAJL 1 in ENAKE vrednosti."""
    c = osnovni_cfg(str(tmp_path / "m.pdf"))
    c["podlaga"] = "beton"
    pdf, _p, _d, _k = risba.generiraj(c, dpi_png=30)
    b = "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
    assert "SIDRANJE (priporočeno)" in b and "DETAJL 1" in b
    for vred in ("60 mm", "70 mm", "40 mm"):
        assert vred in b
    # vrednosti prihajajo iz enega vira
    for _kljuci, _vrsta, _sidro, glob in jedro.SIDRANJA_PODLAGE:
        assert f"{glob} mm" in b
