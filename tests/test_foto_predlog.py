"""Testi za predlog mer iz fotografije (vmesnik ↔ photo_fence_proposal).

Filozofija: mere iz fotografije so PREDLOG za vnos, ne avtoriteta.
Sistem NIČESAR ne zapolni sam (le uporabnik prek potrditvenih polj);
brez reference nobena mera ne sme biti označena kot izmerjena.
"""

from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PFP = os.path.join(_HERE, "photo_fence_proposal")
for _p in (PFP, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import vmesnik  # noqa: E402
from model import Mera  # noqa: E402

IZMERJENO = "izmerjeno"
NEZNANO = "neznano"


# ----------------------------------------------------------- preslikava mer


def test_predlog_vrstic_vezava_kljucev():
    mere = {
        "visina_ograje": Mera(1800.0, IZMERJENO, "test"),
        "dolzina_ograje": Mera(4500.0, "izracunano", "test"),
        "visina_lamele": Mera(80.0, "ocenjeno", "test"),
        "vrzel": Mera(20.0, "ocenjeno", "test"),
        "stevilo_lamel": Mera(31.0, "izracunano", "test", enota="kos"),
    }
    vrstice = vmesnik.foto_predlog_vrstic(mere)
    vezave = {k: ime for k, ime, _m in vrstice}
    assert vezave == {
        "visina": "visina_ograje",
        "sirina": "dolzina_ograje",
        "lamela_v": "visina_lamele",
        "vrzel": "vrzel",
        "lamele": "stevilo_lamel",
    }


def test_predlog_vrstic_brez_vrednosti_ni_predlog():
    mere = {
        "visina_ograje": Mera(None, NEZNANO, "ritem ni zaznan"),
        "dolzina_ograje": Mera(None, NEZNANO, "ritem ni zaznan"),
    }
    assert vmesnik.foto_predlog_vrstic(mere) == []


def test_predlog_vrstic_neznane_mere_ne_tvega():
    """Mera brez vrednosti se ne more zapisati v polje."""
    mere = {
        "visina_ograje": Mera(None, NEZNANO, "x"),
        "visina_lamele": Mera(80.0, "ocenjeno", "x"),
        "neznana_mera": Mera(5.0, IZMERJENO, "brez ciljnega polja"),
    }
    vrstice = vmesnik.foto_predlog_vrstic(mere)
    assert [k for k, _i, _m in vrstice] == ["lamela_v"]


# ------------------------------------------------- merilni del brez risanja


@pytest.fixture()
def prizor(tmp_path):
    import napravi_testne_slike

    pot = str(tmp_path / "prizor.png")
    napravi_testne_slike.narisi_prizor(
        pot, dolzina_mm=4500.0, visina_mm=1800.0)
    return pot


def test_izracunaj_mere_pot_osnovno(prizor):
    import avtomatska_skica

    podatki = avtomatska_skica.izracunaj_mere_pot(prizor)
    assert set(podatki) >= {"mere", "ritem", "opozorila", "rect_pas",
                            "vis_px", "sir_px"}
    assert set(podatki["mere"]) >= {"visina_ograje", "dolzina_ograje",
                                    "visina_lamele", "vrzel", "stevilo_lamel"}
    # vsaka mera ima veljaven status in skladnost vrednost/status
    for m in podatki["mere"].values():
        assert m.status in ("izmerjeno", "izracunano", "ocenjeno", "neznano",
                            "zaznano")
        if m.vrednost_mm is None:
            assert m.status == NEZNANO
        else:
            assert m.vrednost_mm > 0


def test_brez_reference_nic_izmerjenega(prizor):
    """Brez referenčne mere nobena dimenzija ni 'izmerjeno' — pogodba
    'brez ugibanja'. (Štetje lamel je lahko izracunano — to je štetje.)"""
    import avtomatska_skica

    mere = avtomatska_skica.izracunaj_mere_pot(prizor)["mere"]
    for ime in ("visina_ograje", "dolzina_ograje", "visina_lamele", "vrzel"):
        m = mere[ime]
        assert m.status in ("ocenjeno", "neznano"), (ime, m.status)
    assert any("Brez referenčne mere" in o
               for o in avtomatska_skica.izracunaj_mere_pot(prizor)["opozorila"])


def test_z_referenco_je_visina_izmerjena(prizor):
    import avtomatska_skica

    podatki = avtomatska_skica.izracunaj_mere_pot(
        prizor, referenca=("visina_ograje", 1800.0))
    visina = podatki["mere"]["visina_ograje"]
    assert visina.status == IZMERJENO
    assert visina.vrednost_mm == pytest.approx(1800.0, rel=0.01)


def test_predlog_vrstic_iz_prizora(prizor):
    """Cel tok: fotografija → vrstice za dialog (brez risanja)."""
    import avtomatska_skica

    podatki = avtomatska_skica.izracunaj_mere_pot(prizor)
    vrstice = vmesnik.foto_predlog_vrstic(podatki["mere"])
    kljuci = {k for k, _i, _m in vrstice}
    assert "lamele" in kljuci          # štetje je vedno na voljo
    assert kljuci <= set(vmesnik.FOTO_POLJA.values())