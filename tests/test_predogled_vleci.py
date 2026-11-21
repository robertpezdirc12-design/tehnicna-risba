# -*- coding: utf-8 -*-
"""UI/UX Plan H: vleci-za-premik na predogledu (pogled, ne geometrija).

Vzor magicplan/QtoTakeoff: neposredna manipulacija — kolešček poveča,
vlečenje premakne, klik (brez premika) izvede ukaz.
"""
import types

import pytest

tk = pytest.importorskip("tkinter")

import vmesnik


@pytest.fixture
def datoteka(tmp_path, monkeypatch):
    p = str(tmp_path / "zadnje.yaml")
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", p)
    return p


def _png(tmp_path, sir=200, vis=120):
    if not vmesnik.IMA_PIL:
        pytest.skip("PIL ni na voljo")
    from PIL import Image
    p = str(tmp_path / "t.png")
    Image.new("RGB", (sir, vis), (200, 210, 220)).save(p)
    return p


def _platno(tmp_path):
    try:
        app = vmesnik.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    return app


def test_predogled_prikaze_sliko(datoteka, tmp_path):
    app = _platno(tmp_path)
    try:
        app.predogled.nastavi(_png(tmp_path))
        assert app.predogled._izvirna is not None
        assert app.predogled.find_all(), "platno je prazno"
    finally:
        app.destroy()


def test_povecava_in_premik(datoteka, tmp_path):
    app = _platno(tmp_path)
    try:
        pl = app.predogled
        pl.nastavi(_png(tmp_path))
        pl.update_idletasks()
        f0 = pl.faktor
        pl._kolesce_smer(-1)                     # povečaj
        assert pl.faktor > f0
        pl._kolesce_smer(1)                      # pomanjšaj
        assert pl.faktor < f0 * 1.01
        # vlečenje premakne pogled
        e1 = types.SimpleNamespace(x=50, y=50)
        pl._dol(e1)
        pl._vleci(types.SimpleNamespace(x=80, y=65))
        assert pl.ox == 30 and pl.oy == 15
        assert pl._premik is True                # premik = NI klik
    finally:
        app.destroy()


def test_klik_brez_premika_sprozi_ukaz(datoteka, tmp_path):
    app = _platno(tmp_path)
    try:
        pl = app.predogled
        pl.nastavi(_png(tmp_path))
        kliki = []
        pl.na_klik = lambda e: kliki.append(e)
        e1 = types.SimpleNamespace(x=50, y=50)
        pl._dol(e1)
        pl._gor(e1)                              # klik brez premika
        assert len(kliki) == 1
        # vlečenje NE sproži klika
        pl._dol(e1)
        pl._vleci(types.SimpleNamespace(x=90, y=80))
        pl._gor(e1)
        assert len(kliki) == 1
    finally:
        app.destroy()


def test_dvoklik_prilagodi_desni_ponastavi(datoteka, tmp_path):
    app = _platno(tmp_path)
    try:
        pl = app.predogled
        pl.nastavi(_png(tmp_path))
        pl.faktor = 3.0
        pl.ox = pl.oy = 40.0
        pl._ponastavi()
        assert pl.faktor == 1.0 and pl.ox == 0.0
        pl.faktor = 0.2
        pl._prilagodi()
        assert pl.faktor <= 1.0                  # prilagojeno oknu (fit)
        assert pl.ox == 0.0 and pl.oy == 0.0     # premik se ponastavi
    finally:
        app.destroy()