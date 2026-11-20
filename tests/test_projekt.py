"""Testi YAML sheme v2, migracije v1→v2 in PDF-ja z vrati (issue #3).

Kontrolne vrednosti (QA načrt):
- migracija ohrani VSE ključe v1 (množica ključev + vrednosti),
- migracija je idempotentna in NE piše nazaj v izvirno datoteko,
- round-trip (shrani → naloži) brez izgube,
- PDF z vrati: štetje strani s pypdf + velikost > 1000 B + vsebina.
"""
from __future__ import annotations

import copy
import os

import pytest
import yaml

import migracija
import risba
from conftest import (besedilo_strani, cfg_pokoncna, osnovni_cfg,
                      stevilo_strani)

FIXTURE_V1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "fixtures", "projekt_v1.yaml")


# ---------------------------------------------------------------------------
# Shema in migracija
# ---------------------------------------------------------------------------

def test_v1_brez_oznake_sheme():
    with open(FIXTURE_V1, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert "shema" not in cfg
    assert migracija.prepoznaj_shemo(cfg) == 1


def test_migracija_doda_shemo_2_in_segmente():
    with open(FIXTURE_V1, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    nov = migracija.migriraj_shemo(cfg)
    assert nov["shema"] == 2
    assert isinstance(nov["segmenti"], list) and len(nov["segmenti"]) == 1
    seg = nov["segmenti"][0]
    assert seg["ime"] == "Glavni"
    assert seg["mere"]["sirina"] == 3000          # iz v1 mere


def test_migracija_ohrani_vse_kljuce_v1():
    with open(FIXTURE_V1, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    nov = migracija.migriraj_shemo(cfg)
    for k, v in cfg.items():
        assert k in nov, f"ključ {k} izgubljen pri migraciji"
        if k != "mere":
            assert nov[k] == v, f"vrednost {k} spremenjena pri migraciji"
    assert nov["lastno_polje_v1"] == "ohranjeno pri migraciji"
    assert nov["mere"] == cfg["mere"]


def test_migracija_je_idempotentna():
    with open(FIXTURE_V1, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    ena = migracija.migriraj_shemo(cfg)
    dve = migracija.migriraj_shemo(ena)
    assert ena == dve


def test_migracija_ne_pise_v_izvirno_datoteko(tmp_path):
    pot = tmp_path / "projekt.yaml"
    with open(FIXTURE_V1, encoding="utf-8") as f:
        izvirno = f.read()
    with open(pot, "w", encoding="utf-8") as f:
        f.write(izvirno)
    migracija.nalozi_projekt(str(pot))
    with open(pot, encoding="utf-8") as f:
        assert f.read() == izvirno


def test_neznana_shema_zavrnjena():
    with pytest.raises(ValueError, match="Neznana shema"):
        migracija.migriraj_shemo({"shema": 3})


def test_neveljaven_tip_projekta_zavrnjen():
    with pytest.raises(ValueError, match="slika"):
        migracija.migriraj_shemo(["seznam"])


def test_neznana_polja_se_ohranijo(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", nepoznano_polje=42)
    nov = migracija.migriraj_shemo(cfg)
    assert nov["nepoznano_polje"] == 42


# ---------------------------------------------------------------------------
# Round-trip shranjevanje/nalaganje
# ---------------------------------------------------------------------------

def test_round_trip_brez_izgube(tmp_path):
    with open(FIXTURE_V1, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg = migracija.migriraj_shemo(cfg)
    pot = tmp_path / "rt.yaml"
    migracija.shrani_projekt(cfg, str(pot))
    nalozen = migracija.nalozi_projekt(str(pot))
    assert nalozen == cfg
    # drugi krog — kanonično enako
    pot2 = tmp_path / "rt2.yaml"
    migracija.shrani_projekt(nalozen, str(pot2))
    with open(pot, encoding="utf-8") as f1, open(pot2, encoding="utf-8") as f2:
        assert f1.read() == f2.read()


def test_projekt_z_vrati_in_segmenti_round_trip(tmp_path):
    cfg = osnovni_cfg(tmp_path / "v.yaml")
    cfg["shema"] = 2
    cfg["segmenti"] = [
        {"ime": "S1", "tip": "ograja", "mere": {"sirina": 2400},
         "vrata": [{"tip": "enokrilna", "x": 100, "sirina": 900,
                    "visina": 2000, "diagonala": True}],
         "prehodi": [{"x": 1500, "sirina": 1000}]},
        {"ime": "S2", "tip": "pokončna", "mere": {"sirina": 1800}, "kot": 90},
    ]
    pot = tmp_path / "segmenti.yaml"
    migracija.shrani_projekt(cfg, str(pot))
    nalozen = migracija.nalozi_projekt(str(pot))
    assert nalozen == migracija.migriraj_shemo(cfg)
    s1 = nalozen["segmenti"][0]
    assert s1["vrata"][0]["diagonala"] is True
    assert s1["prehodi"][0]["sirina"] == 1000
    assert nalozen["segmenti"][1]["kot"] == 90.0


def test_shranjen_v2_ima_oznako_sheme(tmp_path):
    cfg = osnovni_cfg(tmp_path / "y.pdf")
    pot = tmp_path / "projekt.yaml"
    migracija.shrani_projekt(cfg, str(pot))
    with open(pot, encoding="utf-8") as f:
        zapisano = yaml.safe_load(f)
    assert zapisano["shema"] == 2


# ---------------------------------------------------------------------------
# PDF z vrati (integracija)
# ---------------------------------------------------------------------------

def test_pdf_z_vrati_strani_in_vsebina(tmp_path):
    cfg = osnovni_cfg(tmp_path / "vrata.pdf",
                      vrata=[{"tip": "enokrilna", "x": 200, "sirina": 1000,
                              "visina": 1500}],
                      prehodi=[{"x": 1500, "sirina": 1000, "visina": 1500}])
    izhod, _png, _dod, kol = risba.generiraj(cfg)
    assert os.path.getsize(izhod) > 1000
    assert stevilo_strani(izhod) == 3            # risba + montažni + predračun
    besedilo = besedilo_strani(izhod, 0).upper()
    assert "V1 (ENOKRILNA)" in besedilo          # oznaka vrat na risbi
    assert "P1 (PREHOD)" in besedilo             # oznaka prehoda na risbi
    assert "1000 MM" in besedilo                  # kotirana širina odprtine
    # količine vsebujejo vratne postavke (tečaji, vijaki)
    nazivi = [p[0] for p in kol["postavke"]]
    assert any("VRATA" in n and "TEČ" in n.upper() for n in nazivi)
    assert any("VRATA" in n and "VIJAK" in n.upper() for n in nazivi)


def test_pdf_brez_vrat_je_nespremenjen(tmp_path):
    """Pariteta: konfiguracija brez vrata ima enako število strani kot prej."""
    cfg = osnovni_cfg(tmp_path / "brez.pdf")
    izhod, _png, _dod, _kol = risba.generiraj(cfg)
    assert stevilo_strani(izhod) == 3
    assert os.path.getsize(izhod) > 1000
    assert "VRATA" not in besedilo_strani(izhod, 0).upper()


def test_prekrivanje_vrat_zavrne_pdf(tmp_path):
    cfg = osnovni_cfg(tmp_path / "napaka.pdf",
                      vrata=[{"tip": "enokrilna", "x": 0, "sirina": 1000,
                              "visina": 1500},
                             {"tip": "enokrilna", "x": 500, "sirina": 1000,
                              "visina": 1500}])
    with pytest.raises(ValueError, match="prekriv"):
        risba.generiraj(cfg)
    assert not os.path.exists(tmp_path / "napaka.pdf")


def test_vrata_cez_rob_zavrne_pdf(tmp_path):
    cfg = osnovni_cfg(tmp_path / "rob.pdf",
                      vrata=[{"tip": "enokrilna", "x": 2000, "sirina": 1000,
                              "visina": 1500}])
    with pytest.raises(ValueError, match="rob segmenta|čez rob"):
        risba.generiraj(cfg)
    assert not os.path.exists(tmp_path / "rob.pdf")


def test_pokoncna_z_vrati_kolicine(tmp_path):
    cfg = cfg_pokoncna(tmp_path / "pok.pdf",
                       vrata=[{"tip": "pasja", "x": 100, "sirina": 700,
                               "visina": 600}])
    izhod, _png, _dod, kol = risba.generiraj(cfg)
    assert os.path.getsize(izhod) > 1000
    nazivi = [p[0] for p in kol["postavke"]]
    assert any("VRATA" in n for n in nazivi)

# ---------------------------------------------------------------------------
# GUI (Tk) — vrata v vmesniku (preskoči brez Tk)
# ---------------------------------------------------------------------------

def test_gui_vrata_v_cfg_in_zadnjih(tmp_path, monkeypatch):
    pytest.importorskip("tkinter")
    import vmesnik
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", str(tmp_path / "zadnje.yaml"))
    try:
        app = vmesnik.App()
    except Exception:
        pytest.skip("Tk okolje ni na voljo")
    app.withdraw()
    try:
        vrata_sez = [{"tip": "enokrilna", "x": 100, "sirina": 900,
                      "visina": 1500}]
        app.vrata_sez = [dict(v) for v in vrata_sez]
        app._vrata_osvezi()
        cfg = app._zberi_cfg()
        assert cfg["vrata"] == vrata_sez                # vrata v cfg
        app._shrani_zadnje()
        # nalaganje nazaj v ISTEM oknu (regresija 4: ne prepiše vrat)
        app.vrata_sez = []
        app._nalozi_zadnje()
        assert app.vrata_sez == vrata_sez
    finally:
        app.destroy()


def test_gui_vrata_validacija_prekrivanja(tmp_path, monkeypatch):
    pytest.importorskip("tkinter")
    import vmesnik
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", str(tmp_path / "zadnje.yaml"))
    try:
        app = vmesnik.App()
    except Exception:
        pytest.skip("Tk okolje ni na voljo")
    app.withdraw()
    try:
        app.v["sirina"].set("3000")
        app.v["visina"].set("2300")
        app.v["odcep"].set("60")
        app.vrata_sez = [
            {"tip": "enokrilna", "x": 100, "sirina": 900, "visina": 1500},
            {"tip": "enokrilna", "x": 500, "sirina": 900, "visina": 1500},
        ]
        app._vrata_osvezi()
        napake = app._vrata_preveri()
        assert any("prekrivata" in n for n in napake)
        # brez napak, če se ne prekrivata
        app.vrata_sez = [
            {"tip": "enokrilna", "x": 100, "sirina": 900, "visina": 1500},
            {"tip": "prehodna", "x": 1500, "sirina": 1000, "visina": 1500},
        ]
        app._vrata_osvezi()
        assert app._vrata_preveri() == []
    finally:
        app.destroy()
