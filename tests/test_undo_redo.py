# -*- coding: utf-8 -*-
"""UI/UX Plan D: undo/redo (Ctrl+Z/Y) za polja in vrata.

Vzor iz raziskave: „undo se obnaša kot pravi urejevalnik — brez zatajenih
stanj“. Testi: sprememba polja, vrata, varovanje obnove pred novo
zgodovino, meje zgodovine.
"""
import pytest

tk = pytest.importorskip("tkinter")

import vmesnik


@pytest.fixture
def datoteka(tmp_path, monkeypatch):
    p = str(tmp_path / "zadnje.yaml")
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", p)
    return p


def _app():
    try:
        app = vmesnik.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    return app


def test_undo_vrne_staro_vrednost_redo_spet_novo(datoteka):
    app = _app()
    try:
        zac = app.v["sirina"].get()
        app.v["sirina"].set("1111")
        app._zgodovina_zabelezi()
        assert app.v["sirina"].get() == "1111"
        app._razveljavi()
        assert app.v["sirina"].get() == zac
        app._ponovi()
        assert app.v["sirina"].get() == "1111"
    finally:
        app.destroy()


def test_undo_vrat(datoteka):
    app = _app()
    try:
        app.vrata_sez.append({"tip": "enokrilna", "x": 100, "sirina": 900,
                              "visina": 2000, "smer": "desno-navzven"})
        app._vrata_osvezi()
        app._zgodovina_zabelezi()
        assert len(app.vrata_sez) == 1
        app._razveljavi()
        assert app.vrata_sez == []
        app._ponovi()
        assert len(app.vrata_sez) == 1
        assert app.vrata_sez[0]["sirina"] == 900
    finally:
        app.destroy()


def test_obnova_ne_ustvarja_novih_vnosov(datoteka):
    app = _app()
    try:
        app.v["visina"].set("2222")
        app._zgodovina_zabelezi()
        st = len(app._zgodovina)
        app._razveljavi()
        app._ponovi()
        assert len(app._zgodovina) == st     # brez novih vnosov
        assert app._zgodovina_i == st - 1
    finally:
        app.destroy()


def test_undo_na_zacetku_je_nedolocen(datoteka):
    app = _app()
    try:
        zac = app.v["sirina"].get()
        app._razveljavi()                    # na začetku — brez napake
        assert app.v["sirina"].get() == zac
    finally:
        app.destroy()


def test_zgodovina_je_omejena(datoteka):
    app = _app()
    try:
        for i in range(60):
            app.v["sirina"].set(str(1000 + i))
            app._zgodovina_zabelezi()
        assert len(app._zgodovina) <= vmesnik.App.MAX_ZGODOVINA
    finally:
        app.destroy()