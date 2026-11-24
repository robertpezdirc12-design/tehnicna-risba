# -*- coding: utf-8 -*-
"""Okrogli tek glavnega vmesnika: obrazec → cfg → obrazec.

Najpomembnejša trditev tega modula ni pokritost, ampak **invarianta**:
kar GUI prebere iz obrazca, mora znova napolniti ista polja z istimi
vrednostmi. Če se tu kaj izgubi, uporabnik pri shranjevanju projekta
tiho izgubi podatek.
"""

from __future__ import annotations

import pathlib
import sys
import tkinter as tk

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import vmesnik  # noqa: E402
from conftest import osnovni_cfg  # noqa: E402


@pytest.fixture
def app():
    # Tk v tem okolju občasno ne more ustvariti okna (npr. tema/prikaz).
    # Poskusimo trikrat in ob neuspehu SKIP z dejanskim razlogom — tako se
    # v CI ne skrije prava napaka za splošnim sporočilom.
    zadnja = None
    for _ in range(3):
        try:
            a = vmesnik.App()
            break
        except tk.TclError as e:            # pragma: no cover — okolje
            zadnja = e
    else:                                    # pragma: no cover — okolje
        pytest.skip(f"Tk okolje ni na voljo: {zadnja}")
    a.withdraw()
    a.update_idletasks()
    yield a
    try:
        a.destroy()
    except tk.TclError:
        pass


def test_okrogli_tek_obrazec_cfg_obrazec(app, tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    app._nalozi_cfg_v_polja(cfg)
    nazaj = app._zberi_cfg()

    assert nazaj["ime"] == cfg["ime"]
    assert nazaj["risba_st"] == cfg["risba_st"]
    for kljuc in ("sirina", "visina", "globina", "lamele", "lamela_v",
                  "debelina", "odcep", "razmak_nosilcev", "vrzel"):
        assert nazaj["mere"][kljuc] == cfg["mere"][kljuc], kljuc
    assert nazaj["dolzine_deske"] == cfg["dolzine_deske"]
    assert nazaj["pritrditev_nacin"] == cfg["pritrditev"]


def test_cela_stevila_ostanejo_cela(app, tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["mere"]["sirina"] = 2500.0
    app._nalozi_cfg_v_polja(cfg)
    assert app.v["sirina"].get() == "2500"      # ne "2500.0"


def test_neveljavna_mera_je_razlozena(app):
    app.v["sirina"].set("široko")
    with pytest.raises(ValueError, match="mora biti število"):
        app._preberi_mere()
    app.v["sirina"].set("-5")
    with pytest.raises(ValueError, match="pozitivno"):
        app._preberi_mere()


def test_neveljavne_cene_in_ostala_polja(app, tmp_path):
    app._nalozi_cfg_v_polja(osnovni_cfg(tmp_path / "x.pdf"))
    app.v["cene_vijak_kos"].set("dva")
    with pytest.raises(ValueError, match="število ali prazno"):
        app._zberi_cfg()
    app.v["cene_vijak_kos"].set("")
    app.v["kerf"].set("debela")
    with pytest.raises(ValueError, match="število ali prazno"):
        app._zberi_cfg()


def test_manjkajoca_fotografija_je_napaka(app, tmp_path):
    app._nalozi_cfg_v_polja(osnovni_cfg(tmp_path / "x.pdf"))
    app.v["foto"].set(str(tmp_path / "ni-slike.png"))
    with pytest.raises(ValueError, match="ne obstaja"):
        app._zberi_cfg()


def test_zivi_povzetek_z_veljavnim_vnosom(app, tmp_path):
    app._nalozi_cfg_v_polja(osnovni_cfg(tmp_path / "x.pdf"))
    app._zivi_osvezi()
    assert "ni veljaven" not in app.zivi_status.cget("text")


def test_zivi_povzetek_z_neveljavnim_vnosom(app):
    app.v["sirina"].set("ni-število")
    app._zivi_osvezi()
    assert "ni veljaven" in app.zivi_status.cget("text")


def test_preprosti_nacin_skrije_in_pokaze_polja(app):
    app.st_preprost.set(True)
    app._preklopi_nacin()
    assert "Preprosti način" in app.status.cget("text")
    # polja so res skrita (grid_remove pusti widget, a brez upravljalnika)
    polje = (app.polja.get("podjetje") or app.polja.get("stranka") or [None])[0]
    if polje is not None:
        assert polje.winfo_manager() == ""
    app.status.config(text="")
    app.st_preprost.set(False)
    app._preklopi_nacin()
    assert app.status.cget("text") == ""
    if polje is not None:
        assert polje.winfo_manager() == "grid"


def test_vrstica_stanja_se_skrije_in_pokaze(app):
    # okno je withdrawn, zato winfo_ismapped() ni merodajen — upravljalnik je
    app.st_status.set(False)
    app._preklopi_status_vrstico()
    assert app.status_vrstica.winfo_manager() == ""
    app.st_status.set(True)
    app._preklopi_status_vrstico()
    assert app.status_vrstica.winfo_manager() == "pack"


def test_status_spremenjen_ne_pade(app):
    app.v["stranka"].set("Nova stranka")
    app._status_spremenjen()
    assert isinstance(app.status.cget("text"), str)
