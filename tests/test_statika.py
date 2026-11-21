# -*- coding: utf-8 -*-
"""Plan 6: poenostavljen statični pregled — informativno (NI izračun!).

Vrednosti v testih so ROČNO izračunane iz zapisanih formul:
  M = q·L²/8; W = M/f; I = 5·q·L³·200/(384·E); steber M = q·L·h.
"""
import math

import pytest

import statika


def test_pregled_rocaj_rocni_izracun():
    # L = 1000 mm, q = 1.0 kN/m, f = 235 MPa, E = 210 000 MPa
    r = statika.pregled_rocaj(1000.0, 1.0, 235.0)
    assert abs(r["M_kNm"] - 0.125) < 1e-9          # 1·1²/8 = 0.125 kNm
    assert abs(r["W_pot_cm3"] - 125000 / 235 / 1000) < 1e-9
    assert abs(r["I_pot_cm4"] - 5 * 1.0 * 1e9 * 200 / (384 * 210000) / 1e4) < 1e-9


def test_pregled_steber_rocni_izracun():
    # h = 1100 mm, q = 1.0 kN/m, L = 1500 mm, f = 235 MPa
    s = statika.pregled_steber(1100.0, 1.0, 1500.0, 235.0)
    assert abs(s["F_kN"] - 1.5) < 1e-9             # q·L = 1500 N
    assert abs(s["M_kNm"] - 1.65) < 1e-9           # 1500·1100 = 1.65 kNm
    assert abs(s["W_pot_cm3"] - 1.65e6 / 235 / 1000) < 1e-9


def test_pregled_napake():
    with pytest.raises(ValueError):
        statika.pregled_rocaj(0, 1.0, 235)
    with pytest.raises(ValueError):
        statika.pregled_rocaj(1000, -1, 235)
    with pytest.raises(ValueError):
        statika.pregled_steber(1100, 1.0, 1500, 0)


def test_povzetek_vsebuje_opozorilo_in_vire():
    t = statika.povzetek(1500.0, 1100.0)
    assert "NI STATIČNI IZRAČUN" in t
    assert "BS 6180" in t
    assert "preveri slovenski" in t.lower() or "PREVERI slovenski" in t
    assert "BIVALNO" in t and "JAVNO" in t
    # zahtevani W/I sta izpisana kot minimum (ne trditev o zmogljivosti)
    assert "W ≥" in t and "I ≥" in t


def test_obtezbe_imajo_vire():
    for k, o in statika.OBTEZBE.items():
        vir = str(o["vir"])
        assert vir, k
        assert any(s in vir for s in ("BS 6180", "EN 1991", "PD 6688")), k


def test_fizika_skaliranje():
    # dvojna obtežba → dvojni moment; dvojna dolžina → 4× moment
    a = statika.pregled_rocaj(1000.0, 1.0, 235.0)
    b = statika.pregled_rocaj(1000.0, 2.0, 235.0)
    c = statika.pregled_rocaj(2000.0, 1.0, 235.0)
    assert abs(b["M_kNm"] - 2 * a["M_kNm"]) < 1e-9
    assert abs(c["M_kNm"] - 4 * a["M_kNm"]) < 1e-9
    assert math.isclose(c["I_pot_cm4"] / a["I_pot_cm4"], 8.0, rel_tol=1e-9)
