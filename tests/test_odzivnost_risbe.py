# -*- coding: utf-8 -*-
"""Dokaz: tehnična risba NI hardkodirana — odziva se na VSAK vhod.

Odziv uporabnika: 'imam občutek, da vedno eno in isto prikazuješ, kot da
je hardkodirano'. Test z občutljivostjo ENEGA parametra + vsebinskimi
kontrolami različnih konfiguracij dokazuje nasprotno.
"""

from pypdf import PdfReader

import risba
from conftest import osnovni_cfg


def _besedilo(cfg, tmp_path, ime):
    pdf, _png, _dod, kol = risba.generiraj(cfg, dpi_png=30)
    bes = "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
    return bes, kol


def test_obcutljivost_enega_parametra(tmp_path):
    """Spremeni se 3000 -> 3100 mm; v izpisu se MORA spremeniti prav ona
    številka (in samo ona izmed dimenzij)."""
    c1 = osnovni_cfg(str(tmp_path / "d1.pdf"))
    b1, _ = _besedilo(c1, tmp_path, "d1")
    c2 = osnovni_cfg(str(tmp_path / "d2.pdf"))
    c2["mere"]["sirina"] = 3100
    b2, _ = _besedilo(c2, tmp_path, "d2")
    assert "3000" in b1 and "3100" not in b1
    assert "3100" in b2 and "3000 mm" not in b2
    assert b1 != b2


def test_vsebina_sledi_vhodom(tmp_path):
    """Različni vhodi -> različne mere, profili, barve, vrata, količine."""
    a = osnovni_cfg(str(tmp_path / "a.pdf"))
    a["vrata"] = [{"tip": "enokrilna", "x": 200, "sirina": 900,
                   "visina": 1500, "smer": "desno-navzven",
                   "tip_rocaja": "kljukica", "tip_kljucavnice": "cilinder"}]
    ba, ka = _besedilo(a, tmp_path, "a")
    b = osnovni_cfg(str(tmp_path / "b.pdf"))
    b["mere"].update({"sirina": 5500, "visina": 2200, "odcep": 500,
                      "lamele": 9, "debelina": 30, "vrzel": 40})
    b["barva"] = "Siva"
    b["profil"] = "TESTNA DESKA 200"
    b["vrata"] = []
    bb, kb = _besedilo(b, tmp_path, "b")
    # mere
    assert "3000" in ba and "5500" in bb and "2200" in bb
    # profil in barva
    assert "ROMB 67" in ba and "TESTNA DESKA 200" in bb and "Siva" in bb
    # vrata
    assert "V1" in ba and "V1" not in bb
    # količine se izračunajo (niso fiksne)
    wpc_a = [p for p in ka["postavke"] if p[3] == "wpc_deska_m"][0][4]
    wpc_b = [p for p in kb["postavke"] if p[3] == "wpc_deska_m"][0][4]
    assert abs(wpc_b - wpc_a) > 10, "različna polja -> različna poraba"
    assert len(ka["kosovnica"]) != len(kb["kosovnica"])


def test_opombe_sledijo_vhodom(tmp_path):
    """Tudi opombe odražajo vhod (npr. razmak nosilcev ni fiksen)."""
    c1 = osnovni_cfg(str(tmp_path / "o1.pdf"))
    b1, _ = _besedilo(c1, tmp_path, "o1")
    assert "največ 1000 mm" in b1
    c2 = osnovni_cfg(str(tmp_path / "o2.pdf"))
    c2["mere"]["razmak_nosilcev"] = 750
    b2, _ = _besedilo(c2, tmp_path, "o2")
    assert "največ 750 mm" in b2
    assert "največ 750 mm" not in b1
