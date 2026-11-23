# -*- coding: utf-8 -*-
"""Odpiranje DXF v nameščenem CAD-u (GstarCAD) — docs/gstarcad-povezava.md.

Pravilo iz pregleda GstarCAD 2027: lastniških datotek NE kopiramo v
repozitorij — le zaženemo nameščen program z našo datoteko. Testi morajo
delovati tudi na strojih BREZ nameščenega CAD-a (zato injekcija poti).
"""
from __future__ import annotations

import os

import dxf_izvoz


def test_najdi_cad_zazna_gcad(tmp_path):
    """Če je gcad.exe na iskani poti, ga najde in poimenuje."""
    cad = tmp_path / "GstarCAD 2027"
    cad.mkdir()
    (cad / "gcad.exe").write_bytes(b"MZ")
    pot, opis = dxf_izvoz.najdi_cad([str(cad / "gcad.exe")])
    assert pot == str(cad / "gcad.exe")
    assert "gcad.exe" in opis


def test_najdi_cad_iskreno_ko_ga_ni():
    """Brez kandidatov vrne (None, ...) — NE laže, da je CAD najden."""
    pot, opis = dxf_izvoz.najdi_cad([])
    assert pot is None
    assert "ni zaznan" in opis


def test_odpri_v_cad_zazene_program(tmp_path, monkeypatch):
    """Zaznan CAD se zažene z našo datoteko kot argumentom."""
    dxf = tmp_path / "ograja.dxf"
    dxf.write_text("0\nSECTION\n", encoding="utf-8")
    zagnano = []
    monkeypatch.setattr(
        dxf_izvoz, "najdi_cad",
        lambda: (r"C:\Program Files\GstarCAD 2027\gcad.exe", "najden CAD"))
    opis = dxf_izvoz.odpri_v_cad(
        str(dxf), zazenj=lambda ukaz: zagnano.append(ukaz))
    assert zagnano and zagnano[0][0].endswith("gcad.exe")
    assert zagnano[0][1] == os.path.abspath(str(dxf))
    assert "najden CAD" in opis


def test_odpri_v_cad_brez_cad_uporabi_povezavo(tmp_path, monkeypatch):
    """Brez CAD-a odpre s privzeto sistemsko povezavo (os.startfile)."""
    dxf = tmp_path / "ograja.dxf"
    dxf.write_text("x", encoding="utf-8")
    zagnano = []
    monkeypatch.setattr(dxf_izvoz, "najdi_cad",
                        lambda: (None, "CAD ni zaznan"))
    monkeypatch.setattr(os, "startfile",  # Windows-only metoda
                        lambda p: zagnano.append(p), raising=False)
    opis = dxf_izvoz.odpri_v_cad(str(dxf))
    assert zagnano == [os.path.abspath(str(dxf))]
    assert "ni zaznan" in opis


def test_odpri_v_cad_manjkajoca_datoteka(tmp_path):
    """Manjkajoča datoteka je napaka (ne tiho)."""
    try:
        dxf_izvoz.odpri_v_cad(str(tmp_path / "ni.dxf"))
    except FileNotFoundError:
        return
    raise AssertionError("pričakovana FileNotFoundError")


def test_meni_vsebuje_odpri_v_cad():
    """Funkcija je VIDNA v GUI-ju (ne skrita) — meni Datoteka."""
    import tkinter as tk
    import vmesnik
    try:
        app = vmesnik.App()
    except tk.TclError:
        import pytest
        pytest.skip("Tk okolje ni na voljo")
    try:
        meni = app.nametowidget(app.cget("menu"))
        besedila = []
        for i in range(meni.index("end") + 1):
            if meni.type(i) != "cascade":
                continue
            pod = meni.nametowidget(meni.entrycget(i, "menu"))
            for j in range(pod.index("end") + 1):
                if pod.type(j) == "command":
                    besedila.append(pod.entrycget(j, "label"))
        assert any("Odpri DXF v CAD-u" in b for b in besedila), besedila
    finally:
        app.destroy()

def test_gui_odpri_v_cad_poklice_modul(tmp_path, monkeypatch):
    """GUI metoda pokliče dxf_izvoz.odpri_v_cad — ujame tudi manjkajoč
    import (F821/NameError ob klicu, ne le ob zagonu testov)."""
    import tkinter as tk
    import tkinter.messagebox as mb
    import pytest
    import vmesnik
    monkeypatch.setattr(mb, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(mb, "showwarning", lambda *a, **k: None)
    monkeypatch.setattr(mb, "showerror", lambda *a, **k: None)
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        dxf = tmp_path / "risba.dxf"
        dxf.write_text("x", encoding="utf-8")
        app.v["izhod"].set(str(tmp_path / "risba.pdf"))
        klici = []

        def _odpri(p):
            klici.append(p)
            return "OK"

        monkeypatch.setattr(dxf_izvoz, "odpri_v_cad", _odpri)
        app._odpri_v_cad()
        assert klici == [str(dxf)], klici
    finally:
        app.destroy()
