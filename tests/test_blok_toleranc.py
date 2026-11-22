# -*- coding: utf-8 -*-
"""Načrt 9: blok splošnih toleranc (ISO 2768-m) — kota brez ± ni določena.

Vrednosti so javno objavljene vrednosti standarda ISO 2768-1 (razred m),
vir naveden na listu — ne izmišljene meritve.
"""
from pypdf import PdfReader

import risba
from conftest import osnovni_cfg


def _besedilo(cfg):
    pdf, _png, _dod, _kol = risba.generiraj(cfg, dpi_png=30)
    return "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)


def test_blok_ograja(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "o.pdf")))
    assert "SPLOŠNE TOLERANCE" in b
    assert "ISO 2768-m" in b
    # linearne vrednosti razreda m (izbrane mejne)
    for v in ("±0.1", "±0.2", "±0.3", "±0.5", "±0.8", "±1.2", "±2"):
        assert v in b, f"manjka {v}"
    # koti + iskreno pravilo
    assert "±1°" in b or "±1" in b
    assert "vir: ISO 2768-1" in b
    assert "Kote brez oznake" in b
    # opomba 1 se sklicuje na blok
    assert "glej blok SPLOŠNE" in b


def test_blok_pokoncna(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "p.pdf"), predloga="pokončna"))
    assert "SPLOŠNE TOLERANCE" in b
    assert "vir: ISO 2768-1" in b
    assert "glej blok SPLOŠNE" in b


def test_blok_vsebuje_vse_razrede_m(tmp_path):
    """Vseh 8 obsegov linearnih toleranc razreda m je na listu."""
    b = _besedilo(osnovni_cfg(str(tmp_path / "v.pdf")))
    for obseg in ("0.5–3", "3–6", "6–30", "30–120", "120–400",
                  "400–1000", "1000–2000", "2000–4000"):
        assert obseg in b, f"manjka obseg {obseg}"
