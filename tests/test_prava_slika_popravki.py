# -*- coding: utf-8 -*-
"""Popravki po preizkusu s PRAVO sliko (docs/plan-15-prava-slika-popravki.md).

1) 3D je moral pokazati L-obliko (prednja + stranska ograja) — prej je
   bil narisan le raven segment, 'globina' pa je bila le razmerje osi
   (uporabnik: '3d ni to to').
2) Merjenje: majhna slika (npr. 320×240) je bila napihnjena čez okno
   ('zelen ekran') brez opozorila — zdaj opozorilo + oster prikaz
   pikslov pri povečavi.
"""
import tkinter as tk

import pytest

import tridimenzionalno
from conftest import osnovni_cfg


def _cfg_z_globino(globina):
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"]["globina"] = globina
    return cfg


def test_3d_l_oblika_stranski_segment(monkeypatch):
    """Z globino > 0 morata obstajati prednji IN stranski segment."""
    klici = []
    orig = tridimenzionalno._skatla

    def vohun(kol, x0, x1, y0, y1, z0, z1, barva):
        klici.append((x0, x1, y0, y1, z0, z1))
        return orig(kol, x0, x1, y0, y1, z0, z1, barva)

    monkeypatch.setattr(tridimenzionalno, "_skatla", vohun)
    cfg = _cfg_z_globino(1200)
    fig = tridimenzionalno.sestavi_3d(cfg)
    # stranski segment: lamele segajo v y prek 600 mm in so tanke v x
    stranski = [k for k in klici if k[3] > 600 and (k[1] - k[0]) <= 200]
    assert stranski, "stranski segment (L-oblika) ni narisan"
    # prednji segment: lamele segajo v x in so tanke v y
    prednji = [k for k in klici if k[1] > 1000 and (k[3] - k[2]) <= 200]
    assert prednji, "prednji segment ni narisan"
    # tla segajo čez obe stranici (z: -20..0)
    tla = [k for k in klici if k[4] <= -20 and k[3] > 600]
    assert tla, "tla (balkonska plošča) ne segajo čez stranico"
    # naslov je iskren
    naslov = fig.axes[0].get_title()
    assert "L-oblika" in naslov
    assert "NI model iz slike" in naslov


def test_3d_brez_stranice_je_ravna_ograja(monkeypatch):
    klici = []
    orig = tridimenzionalno._skatla

    def vohun(kol, x0, x1, y0, y1, z0, z1, barva):
        klici.append((x0, x1, y0, y1, z0, z1))
        return orig(kol, x0, x1, y0, y1, z0, z1, barva)

    monkeypatch.setattr(tridimenzionalno, "_skatla", vohun)
    fig = tridimenzionalno.sestavi_3d(_cfg_z_globino(0))
    assert not [k for k in klici if k[3] > 600 and (k[1] - k[0]) <= 200]
    assert "ravna ograja" in fig.axes[0].get_title()


def test_3d_barva_lamel_sledi_cfg(monkeypatch):
    """Barva lamel v 3D sledi izbrani barvi (jedro.barva_hex)."""
    klici = []
    orig = tridimenzionalno._skatla

    def vohun(kol, x0, x1, y0, y1, z0, z1, barva):
        klici.append(barva)
        return orig(kol, x0, x1, y0, y1, z0, z1, barva)

    monkeypatch.setattr(tridimenzionalno, "_skatla", vohun)
    cfg = _cfg_z_globino(40)
    cfg["mere"]["barva"] = "Teak"
    tridimenzionalno.sestavi_3d(cfg)
    assert "#a9764f" in klici        # WPC_BARVE["Teak"]


# ---------------------------------------------------------- merjenje
def _merjenje_app(pot):
    try:
        import merjenje
        return merjenje.App(pot)
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")


def test_merjenje_mala_slika_opozori(tmp_path, monkeypatch):
    """320×240 ('zeleni ekran') mora sprožiti jasno opozorilo o
    netočnosti — nikoli tiho napihnjena slika brez pojasnila."""
    from PIL import Image
    pot = str(tmp_path / "mala.png")
    Image.new("RGB", (320, 240), (60, 140, 70)).save(pot)
    sporocila = []
    monkeypatch.setattr("tkinter.messagebox.showwarning",
                        lambda *a, **k: sporocila.append(a))
    app = _merjenje_app(pot)
    try:
        assert app.mala_slika
        assert "NETOČNE" in app.status.cget("text")
        assert any("Majhna slika" in str(a) for a in sporocila)
    finally:
        app.destroy()


def test_merjenje_velika_slika_brez_opozorila(tmp_path, monkeypatch):
    from PIL import Image
    pot = str(tmp_path / "velika.png")
    Image.new("RGB", (1600, 900), (120, 110, 100)).save(pot)
    sporocila = []
    monkeypatch.setattr("tkinter.messagebox.showwarning",
                        lambda *a, **k: sporocila.append(a))
    app = _merjenje_app(pot)
    try:
        assert not app.mala_slika
        assert not sporocila
    finally:
        app.destroy()


def test_meritev_majhne_slike_je_oznacena(tmp_path, monkeypatch):
    """Meritev na majhni sliki dobi oznako 'netočno' (poštenost)."""
    from PIL import Image
    pot = str(tmp_path / "mala2.png")
    Image.new("RGB", (320, 240), (60, 140, 70)).save(pot)
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **k: None)
    app = _merjenje_app(pot)
    try:
        app.scale = 0.5
        app.nacin = "meri"
        app.v_ime.set("visina")

        from types import SimpleNamespace
        d1 = SimpleNamespace(x=10, y=10)
        d2 = SimpleNamespace(x=110, y=10)
        app._klik(d1)
        app._klik(d2)
        assert app.meritve
        ime, mm, _par = app.meritve[0]
        assert "netočno" in ime
        # platno 800×600 : slika 320×240 => faktor 2,5;
        # 100 px platna = 40 px slike; 40 px / 0,5 px/mm = 80 mm
        assert mm == pytest.approx(80.0)
    finally:
        app.destroy()
