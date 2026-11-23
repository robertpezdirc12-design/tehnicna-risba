# -*- coding: utf-8 -*-
"""Katalog `mechanical` v kosovnicah in naročilih — reference brez ugibanja.

Kataloška referenca kupljenega dela se mora razrešiti v vrstico s provenenco;
prosta besedila (npr. sidro) ostanejo brez vira in se ne izmišljajo.
"""
import pytest

import proizvodnja
import vrata
from mechanical.resolver import ManjkajocaVarianta
from conftest import osnovni_cfg, cfg_pokoncna


# --- vrata: katalog reference -----------------------------------------------

def test_vrata_katalog_reference_se_razresijo():
    viri = vrata.kataloski_viri()
    assert set(viri) == {"M8x40", "MAT-M8", "POD-M8"}
    v = viri["M8x40"]
    assert v["standard"] == "ISO 4017"
    assert v["dimenzije"]["thread_pitch_P_mm"] == 1.25
    assert v["dimenzije"]["head_height_k_mm"]["nominal"] == 5.3
    assert v["provenenca"] and v["provenenca"][0]["accessed"] == "2026-11-23"
    assert viri["MAT-M8"]["standard"] == "ISO 4032"
    assert viri["MAT-M8"]["dimenzije"]["height_m_mm"]["max"] == 6.80
    assert viri["POD-M8"]["standard"] == "ISO 7089"
    assert viri["POD-M8"]["dimenzije"]["outer_diameter_d2_mm"]["nominal"] == 16.0


def test_vrata_opisi_kazejo_standard():
    """Opisi kupljenih delov v dokumentih kažejo standard (ne le domnevo)."""
    assert "(ISO 4017)" in vrata.KATALOG["vijak_m8x40"]["opis"]
    assert "(ISO 4032)" in vrata.KATALOG["matica_m8"]["opis"]
    assert "(ISO 7089)" in vrata.KATALOG["podlozka_m8"]["opis"]
    # sidro nima kataloškega vira — zavestno ostane brez reference
    assert "katalog" not in vrata.KATALOG["sidro_m10"]


def test_kataloski_viri_filtriranje_po_kosovnici():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "x": 100,
                               "sirina": 1000, "visina": 2100}, 3000, 2100)
    kos = vrata.kosovnica_vrat(g, "V1")
    oznake = {vr[0] for vr in kos["kupljeni"]}
    viri = vrata.kataloski_viri(kos)
    assert "M8x40" in viri
    assert set(viri) <= oznake          # le kosi, res prisotni v kosovnici
    assert "MAT-M8" not in oznake or "MAT-M8" in viri


def test_kataloski_viri_neznan_designation_je_napaka(monkeypatch):
    ref = dict(vrata.KATALOG["vijak_m8x40"]["katalog"])
    monkeypatch.setitem(vrata.KATALOG["vijak_m8x40"], "katalog",
                        {**ref, "designation": "M8x99"})
    with pytest.raises(ManjkajocaVarianta):
        vrata.kataloski_viri()


# --- naročila: dokazila v izpisih ------------------------------------------

REF_M8X70 = {"profil": "iso", "standard": "ISO 4017", "designation": "M8x70"}


def test_narocilo_ograja_kataloski_blok():
    cfg = osnovni_cfg("a.pdf", vijak_lamela_ref=dict(REF_M8X70))
    k = proizvodnja.izracunaj_kolicine(cfg)
    assert "PRITRDILA — katalog (dokazila):" in k["narocilo"]
    assert "ISO 4017 M8x70" in k["narocilo"]
    assert "dostopano 2026-11-23" in k["narocilo"]
    assert "vir:" in k["narocilo"]


def test_narocilo_pokoncna_kataloski_blok():
    cfg = cfg_pokoncna("b.pdf", vijak_lamela_ref=dict(REF_M8X70))
    k = proizvodnja.izracunaj_kolicine(cfg)
    assert "PRITRDILA — katalog (dokazila):" in k["narocilo"]
    assert "ISO 4017 M8x70" in k["narocilo"]


def test_narocilo_brez_referenc_ostane_nespremenjeno():
    """Brez referenc ni bloka — obstoječi izpisi se ne spreminjajo."""
    for cfg in (osnovni_cfg("c.pdf"), cfg_pokoncna("d.pdf")):
        k = proizvodnja.izracunaj_kolicine(cfg)
        assert "PRITRDILA — katalog" not in k["narocilo"]


def test_narocilo_slaba_referenca_je_napaka():
    cfg = osnovni_cfg("e.pdf",
                      vijak_lamela_ref={**REF_M8X70, "designation": "M8x99"})
    with pytest.raises(ManjkajocaVarianta):
        proizvodnja.izracunaj_kolicine(cfg)


def test_narocilo_nepopolna_referenca_je_napaka():
    cfg = osnovni_cfg("f.pdf", vijak_lamela_ref={"standard": "ISO 4017"})
    with pytest.raises(ValueError, match="nepopolna"):
        proizvodnja.izracunaj_kolicine(cfg)


def test_vrata_dokazila_v_narocilu():
    cfg = osnovni_cfg("g.pdf", vrata=[
        # višina 1500: odcep 250 + 2100 bi presegel ograjo 1850 (vrata bi bila
        # zavrnjena) — meja je preverjena v test_vrata/test_jedro
        {"tip": "enokrilna", "x": 500, "sirina": 1000, "visina": 1500},
    ])
    k = proizvodnja.izracunaj_kolicine(cfg)
    assert "VRATA/PREHODI:" in k["narocilo"]
    assert "PRITRDILA VRAT — katalog (dokazila):" in k["narocilo"]
    assert "ISO 4017 M8x40" in k["narocilo"]


def test_vrata_dokazila_prazna_brez_kataloga():
    """Prehod (sidro … brez kataloške reference) ne proizvaja dokazil."""
    g = vrata.geometrija_prehoda({"tip": "prehodna", "x": 100, "sirina": 1200,
                                  "visina": 2100}, 3000, 2100)
    vp = {"vrata": [],
          "prehodi": [{"oznaka": "P1", "kosovnica": vrata.kosovnica_prehoda(g)}]}
    assert proizvodnja.vrata_dokazila_vrstice(vp) == []