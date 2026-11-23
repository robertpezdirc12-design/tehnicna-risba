# -*- coding: utf-8 -*-
"""Primerjalni snapshot količin (F2, issue #5).

Zaklene trenutno vedenje proizvodnega modela v fiksnih konfiguracijah —
po vsakem refaktorju (razbitje monolita, F4, F5) se output NE sme
spremeniti, razen če je sprememba namerna in snapshot posodobljen z
obrazložitvijo.

Zlata datoteka: tests/fixtures/snapshot_model.json
"""
import json
import os

import pytest

import risba

ZLATA = os.path.join(os.path.dirname(__file__), "fixtures",
                     "snapshot_model.json")


def _pricakuj(cfg):
    """Kanalizira vse izračune količin v primerljiv slovar."""
    cfg = risba.zdruzi(cfg)          # enako kot generiraj/dxf — polne mere
    m = risba.proizvodni_model(cfg)
    vp = risba.vrata_podatki(cfg)
    return {
        "model": {k: m[k] for k in sorted(m)},
        "kolicine": risba.vrata_vrstice_kolicin(vp),
        "potrebscine": risba.vrata_vrstice_potrebscine(vp),
    }


def _konfiguracije(tmp_path):
    osn: dict = {
        "ime": "SNAP", "risba_st": "SN-001", "stranka": "Test d.o.o.",
        "datum": "01.06.2026", "izhod": str(tmp_path / "s.pdf"),
        "merilo": "auto", "format": "A3",
    }
    pokoncna = dict(osn)
    pokoncna["predloga"] = "pokončna"
    pokoncna["mere"] = {"sirina": 3000, "visina": 1800, "odcep": 250,
                        "deska_sirina": 100, "vrzel": 20,
                        "razmak_stebrov": 1500}
    pokoncna["vrata"] = [{"tip": "enokrilna", "x": 430, "sirina": 1000,
                          "visina": 1330}]
    pokoncna["prehodi"] = [{"x": 1800, "sirina": 400, "visina": 600}]
    ograja = dict(osn)
    ograja["predloga"] = "ograja"
    ograja["mere"] = {"sirina": 2500, "visina": 1850, "odcep": 250,
                      "lamele": 11, "vrzel": 30, "razmak_nosilcev": 1000}
    ograja["vrata"] = [{"tip": "dvokrilna", "x": 600, "sirina": 1600,
                        "visina": 2000}]
    return {"pokoncna": pokoncna, "ograja": ograja}


def test_snapshot_kolicin(tmp_path):
    dobljeno = {ime: _pricakuj(cfg)
                for ime, cfg in _konfiguracije(tmp_path).items()}
    # JSON normalizira terke v sezname — primerjaj po round-tripu.
    dobljeno = json.loads(json.dumps(dobljeno, ensure_ascii=False))
    if not os.path.exists(ZLATA):
        pytest.fail("manjka zlata datoteka — zaženi "
                    "test_snapshot_pomozno_ustvari_zlato")
    with open(ZLATA, encoding="utf-8") as f:
        zloto = json.load(f)
    if dobljeno != zloto:
        izpis_d = json.dumps(dobljeno, ensure_ascii=False, sort_keys=True)
        izpis_z = json.dumps(zloto, ensure_ascii=False, sort_keys=True)
        pytest.fail(
            "Kolicine so se spremenile! Ce je sprememba namerna (F4/F5), "
            "posodobi snapshot in obrazlozi commit. Diff:\n"
            "  dobljeno: " + izpis_d + "\n"
            "  zlato:    " + izpis_z)


def test_snapshot_pomozno_ustvari_zlato(tmp_path):
    """Pomočnik: generira zlato datoteko, če je ni.

    Počisti fixtures/snapshot_model.json in poženi testa — ta test ga
    znova ustvari, glavni test pa v istem teku potrdi.
    """
    if os.path.exists(ZLATA):
        pytest.skip("zlata datoteka že obstaja")
    dobljeno = {ime: _pricakuj(cfg)
                for ime, cfg in _konfiguracije(tmp_path).items()}
    os.makedirs(os.path.dirname(ZLATA), exist_ok=True)
    with open(ZLATA, "w", encoding="utf-8") as f:
        json.dump(dobljeno, f, ensure_ascii=False, indent=1, sort_keys=True)
    assert os.path.exists(ZLATA)