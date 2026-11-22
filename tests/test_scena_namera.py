# -*- coding: utf-8 -*-
"""Načrt 14: scena delovnega prostora — slika, namera, merilo.

Poštenost: brez merila so mere iz slike NEZNANO; nič se ne zapiše v
projekt brez izrecne akcije uporabnika (Canva-pattern: zamenjava samo z
jasno namero).
"""
import os
import tkinter as tk

import pytest

import vmesnik


def _app():
    try:
        return vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")


def _slika(tmp_path, ime="s.png", velikost=(200, 100)):
    from PIL import Image
    pot = str(tmp_path / ime)
    Image.new("RGB", velikost, (120, 130, 140)).save(pot)
    return pot


class _Dogodek:
    def __init__(self, x, y):
        self.x, self.y = x, y


def test_scena_vstavi_in_odstrani(tmp_path):
    app = _app()
    try:
        pot = _slika(tmp_path)
        # vrstica namera je ob zagonu skrita
        assert app.namera_vrstica.winfo_manager() == ""
        app._scena_nalozi(pot)
        assert app.scena["pot"] == os.path.abspath(pot)
        assert app.predogled._izvirna is not None      # slika vidna
        assert app.namera_vrstica.winfo_manager() == "pack"
        assert "Slika v prostoru" in app.status.cget("text")
        assert "NEZNANO" in app.status.cget("text")    # brez merila
        app._scena_pocisti()
        assert app.scena["pot"] is None
        assert app.scena["merilo"] is None
        assert app.namera_vrstica.winfo_manager() == ""
        assert "odstranjena" in app.status.cget("text")
    finally:
        app.destroy()


def test_brez_merila_neznano(tmp_path, monkeypatch):
    """Brez merila NI izmišljenih številk — obvestilo NEZNANO."""
    app = _app()
    try:
        pot = _slika(tmp_path)
        app._scena_nalozi(pot)
        sporocila = []
        monkeypatch.setattr("tkinter.messagebox.showinfo",
                            lambda *a, **k: sporocila.append(a))
        app._merjenje_zacni()
        assert app.scena["merilo"] is None
        assert any("NEZNANO" in str(a) for a in sporocila)
        # način klikanja NI aktiviran (povratni klic je nespremenjen)
        assert app.predogled.na_klik == app._klik_predogled
    finally:
        app.destroy()


def test_merilo_iz_dveh_tock_in_merjenje(tmp_path, monkeypatch):
    app = _app()
    try:
        pot = _slika(tmp_path)
        app._scena_nalozi(pot)
        monkeypatch.setattr(app.predogled, "slika_koordinate",
                            lambda e: (e.x, e.y))
        monkeypatch.setattr("tkinter.simpledialog.askfloat",
                            lambda *a, **k: 1500.0)
        app._merilo_zacni()
        app._merilo_klik(_Dogodek(100, 50))
        assert "druga točka" in app.status.cget("text")
        app._merilo_klik(_Dogodek(400, 50))
        # 300 px / 1500 mm = 0,2 px na mm
        assert app.scena["merilo"] == pytest.approx(0.2)
        assert app.scena["merilo_vir"] == "2 točki + znana dolžina"
        st = app.status.cget("text")
        assert "izmerjeno po sliki" in st and "PREVERI na objektu" in st
        # merjenje z merilom: 100 px = 500 mm
        app._merjenje_zacni()
        app._merjenje_klik(_Dogodek(0, 0))
        app._merjenje_klik(_Dogodek(100, 0))
        assert "500.0 mm" in app.status.cget("text")
        assert "izmerjeno po sliki" in app.status.cget("text")
    finally:
        app.destroy()


def test_foto_v_projekt_in_rotacija(tmp_path):
    app = _app()
    try:
        pot = _slika(tmp_path)
        app._scena_nalozi(pot)
        app._scena_foto_v_projekt()
        assert app.v["foto"].get() == os.path.abspath(pot)
        # rotacija: delovna kopija se spremeni, izvorna datoteka ostane
        app._scena_obrni(90)
        assert app.scena["delovna"] != app.scena["pot"]
        assert os.path.isfile(app.scena["delovna"])
        assert app.scena["pot"] == os.path.abspath(pot)
    finally:
        app.destroy()


def test_brez_tihih_zapisov_v_projekt(tmp_path, monkeypatch):
    """Vstavljanje/merjenje/rotacija NE pišejo v cfg — le izrecna akcija."""
    app = _app()
    try:
        pot = _slika(tmp_path)
        app._scena_nalozi(pot)
        monkeypatch.setattr("tkinter.simpledialog.askfloat",
                            lambda *a, **k: 100.0)
        monkeypatch.setattr(app.predogled, "slika_koordinate",
                            lambda e: (e.x, e.y))
        app._merilo_zacni()
        app._merilo_klik(_Dogodek(0, 0))
        app._merilo_klik(_Dogodek(50, 0))
        app._scena_obrni(90)
        cfg = app._zberi_cfg()
        assert cfg.get("foto", "") != os.path.abspath(pot)
    finally:
        app.destroy()


def test_odpri_projekt_sprejme_sliko(tmp_path, monkeypatch):
    """Uporabnikova težava: okno za odpiranje je bilo omejeno na *.yaml —
    fotografije sploh ni bilo mogoče izbrati. Zdaj 'Odpri projekt…'
    sprejme tudi sliko in jo odloži v delovni prostor (scena)."""
    app = _app()
    try:
        pot = _slika(tmp_path, "fotografija.jpg")
        monkeypatch.setattr("tkinter.filedialog.askopenfilename",
                            lambda **k: pot)
        sporocila = []
        monkeypatch.setattr("tkinter.messagebox.showinfo",
                            lambda *a, **k: sporocila.append(a))
        app._odpri_projekt()
        assert app.scena["pot"] == os.path.abspath(pot)
        assert app.namera_vrstica.winfo_manager() == "pack"
        assert any("delovnem prostoru" in str(a) for a in sporocila)
    finally:
        app.destroy()


def test_odpri_projekt_yaml_se_vedno_deluje(tmp_path, monkeypatch):
    app = _app()
    try:
        pot = str(tmp_path / "projekt.yaml")
        with open(pot, "w", encoding="utf-8") as f:
            f.write("ime: Testni projekt\nsirina: 2000\n")
        monkeypatch.setattr("tkinter.filedialog.askopenfilename",
                            lambda **k: pot)
        monkeypatch.setattr("tkinter.messagebox.showinfo",
                            lambda *a, **k: None)
        app._odpri_projekt()
        assert app.v["ime"].get() == "Testni projekt"
        assert app.scena["pot"] is None        # YAML NI šel v sceno
    finally:
        app.destroy()
