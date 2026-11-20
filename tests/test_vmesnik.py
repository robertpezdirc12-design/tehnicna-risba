# -*- coding: utf-8 -*-
"""B5 in regresija 4 (GUI): shranjevanje/nalaganje nastavitev.

Napaki: (1) `_zberi_cfg` je shranil ključ 'pritrditev', `_nalozi_zadnje` pa
bral 'pritrditev_nacin' — nastavitev se ni obnovila; (2) main je po
nalaganju z `_privzeti()` prepisal vse naložene vrednosti s privzetimi.
"""
import pytest

tk = pytest.importorskip("tkinter")

import vmesnik


def _app():
    try:
        app = vmesnik.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    return app


@pytest.fixture
def datoteka(tmp_path, monkeypatch):
    p = str(tmp_path / "zadnje.yaml")
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", p)
    return p


def test_zberi_cfg_vkljucuje_pravilna_kljuca(datoteka):
    app = _app()
    try:
        app.v["pritrditev_nacin"].set("vrh")
        cfg = app._zberi_cfg()
    finally:
        app.destroy()
    assert cfg["pritrditev"] == "vrh"            # ključ za risbo (naslovnica)
    assert cfg["pritrditev_nacin"] == "vrh"      # ključ za shranjevanje/branje


def test_pritrditev_se_pravilno_shrani_in_obnovi(datoteka):
    app = _app()
    try:
        app.v["pritrditev_nacin"].set("vrh")
        app._shrani_zadnje()
    finally:
        app.destroy()
    app2 = _app()                                # ob zagonu _nalozi_zadnje
    try:
        assert app2.v["pritrditev_nacin"].get() == "vrh"
    finally:
        app2.destroy()


def test_zagon_ne_pripise_privzetih_cez_nalozene(datoteka):
    """Regresija 4: zagon ne sme prepisati naloženih nastavitev s privzetimi."""
    app = _app()
    try:
        app.v["objekt"].set("MOJ OBJEKT")
        app.v["stranka"].set("Stranka d.o.o.")
        app.v["risba_st"].set("PO-777")
        app.v["pritrditev_nacin"].set("bočno")
        app._shrani_zadnje()
    finally:
        app.destroy()
    app2 = _app()
    try:
        assert app2.v["objekt"].get() == "MOJ OBJEKT"
        assert app2.v["stranka"].get() == "Stranka d.o.o."
        assert app2.v["risba_st"].get() == "PO-777"
        assert app2.v["pritrditev_nacin"].get() == "bočno"
    finally:
        app2.destroy()


def test_privzeta_uporaba_ostankov_je_izklopljena(datoteka):
    """A3/A5: ob zagonu je 'Uporabi ostanke' privzeto izklopljeno (varno)."""
    app = _app()
    try:
        assert app.st_ost.get() is False
    finally:
        app.destroy()


def test_gumb_odpisi_ostanke_je_sam_ob_spremembi(datoteka):
    """B1: gumb je omogočen le, ko dejansko obstaja sprememba skladišča."""
    app = _app()
    try:
        assert str(app.btn_ost["state"]) == "disabled"
    finally:
        app.destroy()