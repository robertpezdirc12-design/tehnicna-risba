# -*- coding: utf-8 -*-
"""Načrt 11: statusni tok V DELU → ZA POTRDITEV → IZVEDENO.

IZVEDENO je izjava odgovorne osebe — program ga NE preverja samodejno,
zato zahteva izrecno potrditev (varovalo) in brez nje status povrne.
"""
import tkinter as tk

import pytest
from pypdf import PdfReader

import jedro
import risba
from conftest import osnovni_cfg

# Počasnejši testi (večstransko generiranje PDF) — hitra zanka: -m "not pocasi"
pytestmark = pytest.mark.pocasi


def _besedilo(cfg):
    pdf, _png, _dod, _kol = risba.generiraj(cfg, dpi_png=30)
    return "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)


# ---------- žigi na listu ----------

def test_zig_osnutek(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "a.pdf")))
    assert "OSNUTEK" in b                # V DELU = osnutek
    assert "STATUS: V DELU" in b


def test_zig_za_potrditev(tmp_path):
    c = osnovni_cfg(str(tmp_path / "b.pdf"))
    c["status_dokumenta"] = "ZA POTRDITEV"
    b = _besedilo(c)
    assert "NI ZA IZDELAVO" in b          # rdeči žig
    assert "STATUS: ZA POTRDITEV" in b


def test_izvedeno_brez_ziga(tmp_path):
    """Končna (izvedena) risba je čista — brez žiga, status v bloku."""
    c = osnovni_cfg(str(tmp_path / "c.pdf"))
    c["status_dokumenta"] = "IZVEDENO"
    b = _besedilo(c)
    assert "STATUS: IZVEDENO" in b
    assert "OSNUTEK" not in b
    assert "NI ZA IZDELAVO" not in b


def test_status_na_montaznem_listu(tmp_path):
    c = osnovni_cfg(str(tmp_path / "d.pdf"))
    c["status_dokumenta"] = "ZA POTRDITEV"
    b = _besedilo(c)
    assert "STATUS: ZA POTRDITEV" in b   # tudi montažni list (glava)
    assert "REV." in b


# ---------- GUI: polje + varovalo ----------

def _naredi_app():
    import vmesnik
    try:
        u = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    u.withdraw()
    u.update_idletasks()
    return u


def test_vmesnik_polje_status():
    u = _naredi_app()
    try:
        assert u.cb_status.cget("values") == tuple(jedro.DOVOLJENI_STATUSI) \
            or list(u.cb_status.cget("values")) == list(jedro.DOVOLJENI_STATUSI)
        u.v["status_dokumenta"].set("ZA POTRDITEV")
        cfg = u._zberi_cfg()
        assert cfg["status_dokumenta"] == "ZA POTRDITEV"
    finally:
        u.destroy()


def test_varovalo_izvedeno_zavrnjeno(monkeypatch):
    """Brez potrditve se status POVRNE — program ne verjame na besedo."""
    u = _naredi_app()
    try:
        u.v["status_dokumenta"].set("ZA POTRDITEV")
        u._status_prejsnji = "ZA POTRDITEV"
        monkeypatch.setattr("tkinter.messagebox.askyesno",
                            lambda *a, **k: False)
        u.v["status_dokumenta"].set("IZVEDENO")
        u._status_spremenjen()
        assert u.v["status_dokumenta"].get() == "ZA POTRDITEV"
    finally:
        u.destroy()


def test_varovalo_izvedeno_potrjeno(monkeypatch):
    u = _naredi_app()
    try:
        u.v["status_dokumenta"].set("ZA POTRDITEV")
        u._status_prejsnji = "ZA POTRDITEV"
        monkeypatch.setattr("tkinter.messagebox.askyesno",
                            lambda *a, **k: True)
        u.v["status_dokumenta"].set("IZVEDENO")
        u._status_spremenjen()
        assert u.v["status_dokumenta"].get() == "IZVEDENO"
        assert u._status_prejsnji == "IZVEDENO"
    finally:
        u.destroy()


def test_status_ob_nalaganju_projekta():
    u = _naredi_app()
    try:
        u._nalozi_cfg_v_polja({"ime": "T", "status_dokumenta": "IZVEDENO",
                               "mere": {"sirina": 2500, "visina": 1800}})
        assert u.v["status_dokumenta"].get() == "IZVEDENO"
        assert u._status_prejsnji == "IZVEDENO"
    finally:
        u.destroy()
