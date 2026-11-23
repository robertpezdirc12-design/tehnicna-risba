# -*- coding: utf-8 -*-
"""Načrt 12: delovne točke (T1…Tn) + simbol usmerjenosti kosov (▲ VRH).

Poštenost: ▲ VRH je določitev RISBE; dejansko vidno stran profila
določa proizvajalec — zato mora biti na listu izrecno 'NI izmerjeno'.
"""
from pypdf import PdfReader

import risba
from conftest import osnovni_cfg, cfg_pokoncna

import pytest

# Počasnejši testi (večstransko generiranje PDF) — hitra zanka: -m "not pocasi"
pytestmark = pytest.mark.pocasi


def _besedilo(cfg):
    pdf, _p, _d, _k = risba.generiraj(cfg, dpi_png=30)
    return "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)


def test_delovne_tocke_ograja(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "a.pdf")))
    assert "T1" in b
    assert "delovne točke" in b
    assert "brez verižnega" in b


def test_delovne_tocke_pokoncna(tmp_path):
    b = _besedilo(cfg_pokoncna(str(tmp_path / "b.pdf")))
    assert "T1" in b
    assert "delovne točke" in b


def test_usmerjenost_na_nalepkah(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "c.pdf")))
    assert "▲ VRH" in b                        # nalepke + detajl + koraki
    assert b.count("▲ VRH") >= 5               # vsaka nalepka svojo oznako
    assert "preveri pri proizvajalcu" in b
    assert "NI izmerjeno" in b


def test_usmerjenost_v_montaznih_korakih(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "d.pdf")))
    assert "▲ VRH navzgor" in b
    b2 = _besedilo(cfg_pokoncna(str(tmp_path / "e.pdf")))
    assert "▲ VRH navzgor" in b2


def test_detajl_2_ima_simbol(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "f.pdf")))
    assert "▲ VRH — usmerjenost po risbi" in b


def test_opomba_brez_prekrivanja(tmp_path):
    """Opomba o delovnih točkah je ena vrstica na svoji legi brez tujega
    besedila v pasu (preverjeno po položajih fragmentov v PDF)."""
    pdf, _p, _d, _k = risba.generiraj(osnovni_cfg(str(tmp_path / "g.pdf")),
                                      dpi_png=30)
    izhod = []

    def obisk(text, cm, tm, _fd, _fs):
        t = " ".join(text.split())
        if t:
            izhod.append((t, cm[1] * tm[4] + cm[3] * tm[5] + cm[5],
                          cm[0] * tm[4] + cm[2] * tm[5] + cm[4]))

    for stran in PdfReader(pdf).pages[:1]:
        stran.extract_text(visitor_text=obisk)
    note = [t for t in izhod if any(k in t[0] for k in
            ("delovne", "veri", "seštev", "presečiš", "Tn ="))]
    assert note
    y0 = note[0][1]
    pas = [t for t in izhod if abs(t[1] - y0) < 3]
    assert pas, "opomba naj bo v pasu"
    ys = {round(t[1], 1) for t in pas}
    assert len(ys) == 1, f"v pasu je več vrstic: {ys} — prekrivanje"
    x_min = min(t[2] for t in pas)
    assert 60 < x_min < 130, f"opomba ni na pričakovani legi (x={x_min})"
