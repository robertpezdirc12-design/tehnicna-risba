# -*- coding: utf-8 -*-
"""A4: kote in količine morajo prikazovati DEJANSKE lege in razmake.

Napaka: kotiralo se je zahtevano vrednost (razmak_nosilcev), dejanske
lege nosilcev pa so bile drugačne (3000 mm / 1000 mm -> 4 nosilci z
razmakom 933 mm, izpisano pa „1000 mm“).
"""
import pytest

from conftest import osnovni_cfg, besedilo_strani

import risba
from risba import pozicije_nosilcev


def test_pozicije_nosilcev_dejanski_razmak():
    xs, razmak = pozicije_nosilcev(3000, 1000)
    assert len(xs) == 4                       # ceil(3000/1000)+1
    assert razmak == pytest.approx((3000 - 200) / 3)
    assert razmak == pytest.approx(933.333, abs=0.01)
    # lege so znotraj ograje in enakomerno razporejene
    assert xs[0] == pytest.approx(100)
    assert xs[-1] == pytest.approx(2900)
    for i in range(len(xs) - 1):
        assert xs[i + 1] - xs[i] == pytest.approx(razmak)


def test_montazni_list_kotira_dejanski_razmak(tmp_path):
    cfg = osnovni_cfg(tmp_path / "a4.pdf")
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    assert kolicine is not None
    nosilci = [p for p in kolicine["postavke"] if p[3] == "nosilec_kos"]
    assert nosilci, kolicine["postavke"]
    assert nosilci[0][4] == 4                 # 4 nosilci
    # na montažnem listu je izpisan DEJANSKI razmak (2500 -> (2500-200)/3 = 767),
    # ne le omejitve (razmak_nosilcev 1000)
    t = besedilo_strani(izhod, 1)
    assert "dejanski 767 mm" in t
    assert "1000" in t                        # omejitev je še vedno vidna


def test_vijaki_ustrezajo_stevilu_nosilcev(tmp_path):
    cfg = osnovni_cfg(tmp_path / "a4b.pdf")
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    n = cfg["mere"]["lamele"]
    vijaki = [p for p in kolicine["postavke"] if p[3] == "vijak_kos"][0]
    assert vijaki[4] == n * 4 * 2             # n × n_nos × 2
    fasadni = [p for p in kolicine["postavke"] if p[3] == "fasadni_kos"][0]
    assert fasadni[4] == 4 * 2


def test_stevilo_nosilcev_za_ozko_ogrado():
    xs, razmak = pozicije_nosilcev(300, 1000)
    assert len(xs) >= 2
    assert all(0 <= x <= 300 for x in xs)


def test_nosilci_in_kosovnica_so_konsistentni(tmp_path):
    """A5: iste lege v risbi, montažnem listu in količinah."""
    cfg = osnovni_cfg(tmp_path / "a5.pdf")
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    xs, razmak = pozicije_nosilcev(cfg["mere"]["sirina"],
                                   cfg["mere"]["razmak_nosilcev"])
    nosilci = [p for p in kolicine["postavke"] if p[3] == "nosilec_kos"]
    assert nosilci[0][4] == len(xs)