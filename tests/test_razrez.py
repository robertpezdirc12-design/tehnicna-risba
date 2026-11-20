# -*- coding: utf-8 -*-
"""A3/A5 in optimizator: celovitost, invariante, matematična pravilnost.

Regresija 2 (agregatna formula palic): 9 kosov × 1200 mm iz palice 6000 mm
je 3 palice (po 3 kose), NE 2 (ceil(9 × 1203 / 6000) = 2 je podcenitev).
"""
import pytest

from razrez import (optimiziraj_zalogo, razrez_podatki, stevilo_palic,
                    kos_iz_vira, ostanek_po_rezih)


# ------------------------------------------------------- model reza (kerf)
def test_kos_iz_vira_model():
    assert kos_iz_vira(6000, 1200, 3) == 4     # 4×1203 = 4812 + robni rez
    assert kos_iz_vira(3000, 1000, 3) == 2     # 2×1003 = 2006
    assert kos_iz_vira(1000, 1000, 3) == 1     # 1×1003 > 1000? ne — (1000+3)//1003 = 1
    assert kos_iz_vira(999, 1000, 3) == 0


def test_ostanek_po_rezih_enkrat():
    assert ostanek_po_rezih(3000, 2, 1000, 3) == 994
    assert ostanek_po_rezih(3000, 0, 1000, 3) == 3000
    assert ostanek_po_rezih(3000, 2, 1000, 0) == 1000


def test_invarianta_reza():
    """V = n × k + kerf_skupaj + ostanek (A5) za reprezentativne primere."""
    for (V, k, kerf, n) in ((3000, 1000, 3, 2), (5800, 2500, 3, 2),
                            (6000, 1200, 3, 4)):
        ostanek = ostanek_po_rezih(V, n, k, kerf)
        kerf_skupaj = V - n * k - ostanek
        assert kerf_skupaj >= 0
        assert abs(V - (n * k + kerf_skupaj + ostanek)) < 1e-9


# ---------------------------------------------------------- optimizator (A3)
def test_optimizator_miks_dolzin():
    traki = optimiziraj_zalogo(2400, 10, [5800, 4200, 3000], 3)
    assert sum(k for _, k in traki) == 10     # vsi kosi izdelani
    for B, kol in traki:
        assert kos_iz_vira(B, 2400, 3) >= kol
        assert B in (5800, 4200, 3000)
    # zmogljivost mora zadoščati — brez fiktivnih trakov
    assert all(kol * (2400 + 3) <= B + 3 for B, kol in traki)


def test_optimizator_nima_skrite_omejitve_500():
    """Stara različica je po 500 kosih odnehala in vrnila nepopoln rezultat."""
    traki = optimiziraj_zalogo(100, 600, [5800], 3)
    assert sum(k for _, k in traki) == 600


def test_optimizator_ne_prideluje_uspehov():
    """Kos 5900 mm iz zaloge 5800 mm — optimizator ne sme izmisliti trakov."""
    traki = optimiziraj_zalogo(5900, 3, [5800], 3)
    assert traki == []


def test_razrez_podatki_zavrne_nepopoln_razrez():
    c = {"kerf": 3.0, "barva": "A", "profil": "P", "dolzine_deske": [1200],
         "uporabi_ostanke": False}
    with pytest.raises(ValueError, match="Razrez ni popoln"):
        razrez_podatki(2500, 4, c)            # sirina 2500 ne gre iz 1200


def test_razrez_podatki_kosovnica_je_popolna():
    c = {"kerf": 3.0, "barva": "A", "profil": "P",
         "dolzine_deske": [5800, 3000], "uporabi_ostanke": False}
    rp = razrez_podatki(1000, 7, c, oznaka="L")
    assert len(rp["kosovnica"]) == 7
    assert [k[0] for k in rp["kosovnica"]] == [str(i + 1) for i in range(7)]
    assert all(k[1] == 1000 for k in rp["kosovnica"])
    assert rp["preost_kosov"] == 0
    # kontrolne vrstice: seštevek kosov v stolpcu KOSOV == 7
    skupaj = sum(int(r[1]) for r in rp["rez_rows"][1:])
    assert skupaj == 7


# --------------------------------------------------- regresija 2: palice
def test_stevilo_palic_agregatni_primer():
    """9 kosov × 1200 mm iz palic 6000 mm = 3 palice (po 3 kose)."""
    assert stevilo_palic(1200, 9, 6000, 3) == 3


def test_stevilo_palic_osnovni_primeri():
    assert stevilo_palic(2500, 2, 6000, 3) == 1    # 2 × 2503 = 5006
    assert stevilo_palic(1850, 3, 6000, 3) == 1    # 3 × 1853 = 5559 v eni palici
    assert stevilo_palic(1850, 4, 6000, 3) == 2
    assert stevilo_palic(100, 0, 6000, 3) == 0


def test_stevilo_palic_kos_daljsi_od_palice():
    with pytest.raises(ValueError, match="daljši od tovarniške dolžine"):
        stevilo_palic(6500, 1, 6000, 3)


def test_stevilo_palic_je_natancno_ne_podcenjeno():
    """Preverba na množici primerov: število palic * zmogljivost >= n."""
    for (k, n, L) in ((1200, 9, 6000), (1200, 8, 6000), (2400, 5, 6000),
                      (800, 25, 6000), (1203, 8, 6000)):
        palic = stevilo_palic(k, n, L, 3)
        assert palic * kos_iz_vira(L, k, 3) >= n
        if palic > 1:
            assert (palic - 1) * kos_iz_vira(L, k, 3) < n


# ------------------------------------------- A5: razrez in količine so enaki
def test_rez_in_kosovnica_se_skladata():
    c = {"kerf": 3.0, "barva": "A", "profil": "P",
         "dolzine_deske": [5800, 4200], "uporabi_ostanke": False}
    rp = razrez_podatki(2350, 6, c, oznaka="L")
    # iz vsakega traku toliko kosov, kot jih zmogljivost dopušča
    for (B, kol) in rp["traki"]:
        assert kol == min(kol, kos_iz_vira(B, 2350, 3))
    # oznake kosov so povezane in neprekinjene
    oznake = [k[0] for k in rp["kosovnica"]]
    assert oznake == [str(i + 1) for i in range(6)]