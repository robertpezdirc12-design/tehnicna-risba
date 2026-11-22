# -*- coding: utf-8 -*-
"""Načrt 13: glavno okno = opravilna vrstica + delovni prostor.

Ves obrazec (podatki projekta) je skrit v pogovornem oknu
(Urejanje → Podatki projekta…); glavno okno vsebuje samo delovni
prostor (predogled risbe) in tanko vrstico stanja.
"""
import tkinter as tk

import pytest

import vmesnik


def _app():
    try:
        return vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")


def test_glavno_okno_je_samo_delovni_prostor():
    app = _app()
    try:
        app.withdraw()
        app.update_idletasks()
        # obrazec je ob zagonu SKRIT in živi v pogovornem oknu
        assert app.obrazec_okno.state() == "withdrawn"
        assert str(app.cb_pred).startswith(str(app.obrazec_okno))
        assert str(app.zivi_platno).startswith(str(app.obrazec_okno))
        assert str(app.tv_vrata).startswith(str(app.obrazec_okno))
        assert str(app._vsebina).startswith(str(app.obrazec_okno))
        # v glavnem oknu sta samo delovni prostor in vrstica stanja
        # (razen pogovornih oken, ki so ločena)
        ne_toplevel = {str(w) for w in app.winfo_children()
                       if not isinstance(w, (tk.Toplevel, tk.Menu))}
        assert ne_toplevel == {str(app.predogled.master),
                               str(app.status_vrstica)}, ne_toplevel
        assert str(app.predogled).startswith(str(app))
        assert str(app.status).startswith(str(app))
    finally:
        app.destroy()


def test_pokazi_in_zapri_brez_izgube_podatkov():
    app = _app()
    try:
        app._pokazi_obrazec()
        app.update_idletasks()
        assert app.obrazec_okno.state() == "normal"
        app.v["ime"].set("Preizkus obrazca")
        app._zapri_obrazec()
        assert app.obrazec_okno.state() == "withdrawn"
        # podatki ostanejo tudi po skritju okna
        assert app._zberi_cfg()["ime"] == "Preizkus obrazca"
    finally:
        app.destroy()


def test_vrstica_stanja_se_skrije():
    app = _app()
    try:
        app.st_status.set(False)
        app._preklopi_status_vrstico()
        assert not app.status_vrstica.winfo_manager()
        app.st_status.set(True)
        app._preklopi_status_vrstico()
        assert app.status_vrstica.winfo_manager() == "pack"
    finally:
        app.destroy()
