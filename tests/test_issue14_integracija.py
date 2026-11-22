# -*- coding: utf-8 -*-
"""Issue #14 G/E: integracija — montažni list, GUI izbira, shramba v cfg.

Načelo: le POTRJEN načrt upravlja razporeditvijo in nabavo; samodejni
ostane informativen (NI potrjen). Sistem ne zamenja izbranega tiho.
"""
import tkinter as tk

import pytest
from pypdf import PdfReader

import proizvodnja
import risba
from conftest import osnovni_cfg


def _besedilo(cfg):
    pdf, _p, _d, _k = risba.generiraj(cfg, dpi_png=30)
    return "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)


def test_montazni_kaze_samodejni_nacrt(tmp_path):
    b = _besedilo(osnovni_cfg(str(tmp_path / "a.pdf")))
    assert "NAČRT RAZREZA" in b
    assert "bilanca trakov" in b
    assert "NI potrjen" in b               # brez izbire = informativno


def test_potrjen_nacrt_upravlja_listom(tmp_path):
    c = osnovni_cfg(str(tmp_path / "b.pdf"))
    c["optimizacija"] = {"nacrt": "najmanj-palic", "kriterij": "palice"}
    b = _besedilo(c)
    assert "NAČRT RAZREZA: najmanj-palic" in b
    assert "kriterij: palice" in b
    assert "potrjen" in b
    assert "NI potrjen" not in b


def test_montazni_pokoncna_pravtako(tmp_path):
    from conftest import cfg_pokoncna
    c = cfg_pokoncna(str(tmp_path / "c.pdf"))
    b = _besedilo(c)
    assert "NAČRT RAZREZA" in b


def test_rezni_nacrt_iz_cfg_en_vir():
    cfg = {"mere": {"sirina": 2500, "visina": 1850, "odcep": 250},
           "stevilo_lamel": 13, "barva": "antracit", "profil": "ROMB 67",
           "kerf": 3, "dolzine_deske": [5800, 3000]}
    sk = proizvodnja.rezne_skupine(cfg)
    assert [s[0] for s in sk] == ["LAMELE", "VRATA"]
    r = proizvodnja.rezni_nacrt(sk, cfg)
    assert r["status_izbire"].startswith("samodejno")
    assert r["tabela_vse"], "primerjava mora imeti vrstice"
    # bilanca skupin se sešteje brez dvojnega štetja
    b = r["skupine"][0]["bilanca"]
    assert all(v >= 0 for v in b.values())


def _app():
    import vmesnik
    try:
        u = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    u.withdraw()
    u.update_idletasks()
    return u


def _najdi(w, razred):
    if isinstance(w, razred):
        return w
    for otrok in w.winfo_children():
        najden = _najdi(otrok, razred)
        if najden is not None:
            return najden
    return None


def test_vmesnik_dialog_izbira_nacrta(monkeypatch):
    """Dialog: tabela, izbira, shranitev v cfg — brez tihe zamenjave."""
    u = _app()
    try:
        monkeypatch.setattr("tkinter.messagebox.showinfo",
                            lambda *a, **k: None)
        u._rezni_nacrt_dialog()
        u.update_idletasks()
        # okno obrazca (načrt 13) ni ta dialog — izloči ga
        okno = [w for w in u.winfo_children()
                if isinstance(w, tk.Toplevel) and w is not u.obrazec_okno]
        assert okno, "dialog se mora odpreti"
        from tkinter import ttk
        tree = _najdi(okno[0], ttk.Treeview)
        assert tree is not None and tree.get_children()
        # izberi prvo vrstico in potrdi
        tree.selection_set(tree.get_children()[0])
        gumb = None

        def najdi_gumb(w):
            nonlocal gumb
            if isinstance(w, ttk.Button) and \
                    w.cget("text") == "Uporabi izbrani načrt":
                gumb = w
                return
            for otrok in w.winfo_children():
                najdi_gumb(otrok)

        najdi_gumb(okno[0])
        assert gumb, "gumb 'Uporabi izbrani načrt' mora obstajati"
        gumb.invoke()
        u.update_idletasks()
        assert u.optimizacija, "izbira mora biti shranjena"
        assert u.optimizacija["nacrt"]
        cfg = u._zberi_cfg()
        assert cfg["optimizacija"] == u.optimizacija
    finally:
        u.destroy()


def test_cfg_roundtrip_optimizacija():
    u = _app()
    try:
        u.optimizacija = {"nacrt": "bfd", "kriterij": "palice"}
        cfg = u._zberi_cfg()
        u.optimizacija = None
        u._nalozi_cfg_v_polja(cfg)
        assert u.optimizacija == {"nacrt": "bfd", "kriterij": "palice"}
    finally:
        u.destroy()
