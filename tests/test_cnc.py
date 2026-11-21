# -*- coding: utf-8 -*-
"""F5 (issue #5): CNC izvoz — CSV seznami rezov in informativni G-code.

Ročno izračunani primer: kosi [A=1000, B=800, C=500], zaloga [2000],
kerf 3. Po modelu B: 1000+800+500 + 2·3 = 2306 > 2000 -> dva trakova.
"""

import pytest

import cnc


KOSI = [("A", 1000.0), ("B", 800.0), ("C", 500.0)]
ZALOGA = [2000.0]
KERF = 3.0


def test_cutlist_polozaji(tmp_path):
    pot = str(tmp_path / "cutlist.csv")
    pot2, r = cnc.izvozi_cutlist(KOSI, ZALOGA, KERF, pot)
    assert pot2 == pot
    assert r["st_kosov"] == 3
    vrstice = open(pot, encoding="utf-8").read().strip().splitlines()
    assert vrstice[0].startswith("trak,")           # glava CSV
    assert len(vrstice) == 1 + 3                    # glava + 3 kosi
    # položaji: vsak kos leži znotraj svojega traku
    for vrstica in vrstice[1:]:
        st, B, ozn, dol, x0, x1 = vrstica.split(",")
        assert 0 <= float(x0) < float(x1) <= float(B) + 1e-6
        assert abs((float(x1) - float(x0)) - float(dol)) < 1e-6


def test_gcode_odprte_poti_rezi(tmp_path):
    pot = str(tmp_path / "razrez.nc")
    pot2, r = cnc.izvozi_gcode(KOSI, ZALOGA, KERF, pot)
    assert pot2 == pot
    vsebina = open(pot, encoding="utf-8").read()
    assert "G21" in vsebina and "G90" in vsebina      # mm, absolutno
    assert vsebina.count("G1 X") == 3                 # ena odprta pot na kos
    assert "M30" in vsebina                           # konec programa
    assert "PREVERI operater" in vsebina              # varnostni opomnik


def test_gcode_kos_vecji_od_zaloge_zavrnjen(tmp_path):
    with pytest.raises(ValueError, match="daljši"):
        cnc.izvozi_gcode([("X", 3000.0)], ZALOGA, KERF,
                         str(tmp_path / "napaka.nc"))


def test_dve_trakovi_pri_razdeljenem_toku(tmp_path):
    pot = str(tmp_path / "cutlist.csv")
    _p, r = cnc.izvozi_cutlist(KOSI, ZALOGA, KERF, pot)
    assert len(r["traki"]) >= 2                     # 2306 mm ne gre v 2000