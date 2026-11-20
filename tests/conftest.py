# -*- coding: utf-8 -*-
"""Skupne osnove za regresijske teste (issue #2).

Skladišče ostankov je vedno izolirano v začasno mapo (TEHNICNA_RISBA_DATA),
da testi nikoli ne posežejo v uporabnikove podatke.
"""
import os
import sys

import pytest

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOREN not in sys.path:
    sys.path.insert(0, KOREN)

from pypdf import PdfReader   # noqa: E402


@pytest.fixture(autouse=True)
def izolirano_skladisce(tmp_path, monkeypatch):
    """Vsak test dobi svoje skladišče ostankov v tmp mapi."""
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    monkeypatch.setenv("TEHNICNA_RISBA_DATA", str(data))
    yield data


def stevilo_strani(pot_pdf):
    """Zanesljivo štetje strani PDF s parserjem (pypdf), ne z bajti."""
    return len(PdfReader(pot_pdf).pages)


def besedilo_strani(pot_pdf, i):
    """Besedilo i-te strani (0-indeks) — za preverbo vsebine strani."""
    return (PdfReader(pot_pdf).pages[i].extract_text() or "")


def osnovni_cfg(izhod, predloga="ograja", **spremembe):
    """Veljavna osnovna konfiguracija (prečna ograja) za teste."""
    cfg = {
        "ime": "PO-TEST", "risba_st": "PO-009", "stranka": "Test d.o.o.",
        "objekt": "Testni objekt", "datum": "01.06.2026", "merilo": "auto",
        "format": "A3", "izhod": str(izhod), "foto": "", "barva": "Antracit",
        "profil": "ROMB 67", "material": "Aluminij", "material_lamel": "WPC",
        "dobavitelj": "WoodCore", "podlaga": "beton", "pritrditev": "vrh",
        "vijak_lamela": "RF M8×70 Inox", "vijak_nosilec": "fasadni Ø8×80",
        "predloga": predloga, "deli": None, "opombe": None,
        "dolzina_deske": 5800, "dolzina_palice": 6000,
        "dolzine_deske": [5800, 4200, 3000], "kerf": 3.0,
        "uporabi_ostanke": False, "faktor": 0.35, "faza": "Izvedbena",
        "pozicija": "POZ", "klik_cel_zaslon": False, "preprost_nacin": False,
        "mere": {
            "sirina": 2500, "visina": 1850, "globina": 40, "odcep": 250,
            "lamela_v": 120, "lamele": 11, "vrzel": 30, "profil_v": 80,
            "rocaj_v": 40, "debelina": 21,
            "steber_sirina": 60, "steber_debelina": 60,
            "deska_sirina": 100, "deska_debelina": 21,
            "razmak_nosilcev": 1000, "razmak_stebrov": 1200,
        },
    }
    cfg.update(spremembe)
    return cfg


def cfg_pokoncna(izhod, **spremembe):
    """Veljavna konfiguracija za pokončno predlogo (B2 testni primer:
    3000 / 3 stebri 60×60 / 20 desk 100×20 / vrzel 20)."""
    cfg = osnovni_cfg(izhod, predloga="pokončna")
    cfg["mere"] = dict(cfg["mere"], **MERE_POK_PRIMER)
    cfg.update({k: v for k, v in spremembe.items() if k != "mere"})
    if "mere" in spremembe:
        cfg["mere"].update(spremembe["mere"])
    return cfg


@pytest.fixture
def cfg_ograja(tmp_path):
    return osnovni_cfg(tmp_path / "ograja.pdf")


@pytest.fixture
def cfg_pok(tmp_path):
    return cfg_pokoncna(tmp_path / "pok.pdf")


# primer iz poročila (B2): 3000 / 3 stebri 60×60 / 20 desk 100×20 / vrzel 20
MERE_POK_PRIMER = {"sirina": 3000, "visina": 1850, "odcep": 250,
                   "lamela_v": 100, "lamele": 20, "vrzel": 20,
                   "razmak_stebrov": 1500}