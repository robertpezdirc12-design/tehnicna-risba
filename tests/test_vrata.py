"""Testi geometrije in količin za vrata/prehode (issue #3).

Ročno izračunane pričakovane vrednosti (invariant verige:
r_bok + w_1 + r_med + ... + r_bok = S_o):
- enokrilna 1000x2100: w_k = (1000-2*5)/1 = 990; h_k = 2100-50-5 = 2045
- dvokrilna 3000x2155: w_k = (3000-2*5-10)/2 = 1490; h_k = 2155-50-5 = 2100
- pasja 700x655: w_k = (700-2*5)/2 = 345 (brez reže med kriloma)
"""
from __future__ import annotations

import pytest

import vrata


# ---------------------------------------------------------------------------
# Geometrija — ročno preverjene vrednosti
# ---------------------------------------------------------------------------

def test_enokrilna_geometrija():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 1000, "visina": 2000},
                              1000, 2100)
    assert g["n_kril"] == 1
    assert g["sirine_kril"] == [990.0]           # (1000 - 2*5) / 1
    assert g["h_k"] == 2045.0                     # 2100 - 50 - 5
    # Invariant verige: 5 + 990 + 5 = 1000
    r = g["reze"]
    assert r["bok"] + g["sirine_kril"][0] + r["bok"] == 1000.0


def test_dvokrilna_geometrija():
    g = vrata.geometrija_vrat({"tip": "dvokrilna", "sirina": 3000, "visina": 2100},
                              3000, 2155)
    assert g["n_kril"] == 2
    assert g["sirine_kril"] == [1490.0, 1490.0]  # (3000 - 10 - 10) / 2
    assert g["h_k"] == 2100.0
    r = g["reze"]
    assert (r["bok"] + g["sirine_kril"][0] + r["med"]
            + g["sirine_kril"][1] + r["bok"]) == 3000.0


def test_pasja_geometrija():
    g = vrata.geometrija_vrat({"tip": "pasja", "sirina": 700, "visina": 600},
                              700, 655)
    assert g["n_kril"] == 2
    assert g["sirine_kril"] == [345.0, 345.0]     # ni reže med kriloma
    assert g["h_k"] == 600.0
    r = g["reze"]
    assert (r["bok"] + g["sirine_kril"][0] + g["sirine_kril"][1] + r["bok"]) == 700.0


def test_prehodna_geometrija():
    g = vrata.geometrija_vrat({"tip": "prehodna", "sirina": 1000, "visina": 2100},
                              1000, 2100)
    assert g["n_kril"] == 0
    assert g["odprtina"] == {"sirina": 1000.0, "visina": 2100.0}
    assert g["st_tecajev"] == 0


# ---------------------------------------------------------------------------
# Tečaji (pravilo P1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("h_k,pricakovano", [(1200, 2), (1201, 3), (2100, 3),
                                             (2101, 4), (2500, 4), (2501, 5)])
def test_pravilo_p1_tecaji(h_k, pricakovano):
    # Odprtina: h_k = H_o - 55 -> H_o = h_k + 55
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 900},
                              900, h_k + 55)
    assert g["st_tecajev"] == pricakovano


def test_tecaj_dodatek_za_siroko_krilo():
    # Krilo širše od 1200 mm -> +1 tečaj (dvokrilna 3000: krilo 1490 mm)
    g = vrata.geometrija_vrat({"tip": "dvokrilna", "sirina": 3000},
                              3000, 2155)
    assert g["st_tecajev"] == 4                   # 3 (h_k=2100) + 1 (w>1200)


def test_tecaji_skriti_minimalno_tri():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 900,
                               "tecaji": "skriti"}, 900, 1000)
    assert g["st_tecajev"] >= 3


# ---------------------------------------------------------------------------
# Prečke (P5), diagonala (P6), vijaki (P2)
# ---------------------------------------------------------------------------

def test_precke_p5():
    assert vrata._st_preck(1800, "enokrilna") == 2
    assert vrata._st_preck(2100, "enokrilna") == 3
    assert vrata._st_preck(2900, "enokrilna") == 4


def test_diagonala_je_hipotenuza_zaokrozjena():
    # w_k=990, h_k=2045 -> sqrt(990^2+2045^2)=2272.8 -> ceil na 5 mm = 2275
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 1000,
                               "diagonala": True}, 1000, 2100)
    assert g["diagonala_dolzina"] == 2275.0


def test_vijaki_na_tecaj_p2():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 900}, 900, 2155)
    assert g["vijaki_na_tecaj"] == 6               # 3 peresi


# ---------------------------------------------------------------------------
# Kosovnica (P3/P4)
# ---------------------------------------------------------------------------

def test_kosovnica_vrat_tecaji_in_vijaki():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 900}, 900, 2155)
    k = vrata.kosovnica_vrat(g)
    kup = {ozn: (kol, enota) for ozn, kol, enota, _kljuc, _opis in k["kupljeni"]}
    assert kup["TEČ-STD"][0] == 3                  # 3 tečaji na krilo
    assert kup["M8x40"][0] == 18                   # 3 tečaji * 6 vijakov
    assert kup["MAT-M8"][0] == 18
    assert kup["POD-M8"][0] == 18


def test_kosovnica_precke_in_plosce():
    # h_k = 2100 -> 3 prečke na krilu; okvir ima 2 prečki -> skupaj 5 prečk.
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 900}, 900, 2155)
    k = vrata.kosovnica_vrat(g)
    izd = {o: (d, s, kol, op) for o, d, s, kol, op, _ in k["izdelani"]}
    # 2 stojali okvirja + 2 prečki okvirja + 2 stojali krila + 2 letvi + 3 prečke krila
    assert izd["V1-1"][2] == 2                     # stojala okvirja
    assert sum(kol for (_d, _s, kol, op) in izd.values() if "prečka" in op) == 5


def test_kosovnica_prehoda_p7():
    g = vrata.geometrija_prehoda({"x": 100}, 1000, 2100)
    k = vrata.kosovnica_prehoda(g)
    kup = {ozn: kol for ozn, kol, _e, _kl, _op in k["kupljeni"]}
    assert kup["ZAK-STE"] == 2
    assert kup["ZAK-PRO"] == 2
    assert kup["SID-M10"] == 4                     # 2 sidri na steber


def test_kupljene_vrstice_za_kolicine():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 900}, 900, 2155)
    k = vrata.kosovnica_vrat(g)
    vrstice = vrata.kupljene_vrstice(k)
    assert all(len(v) == 4 for v in vrstice)       # (naziv, kol, enota, kljuc_cene)
    kljuci = [v[3] for v in vrstice]
    assert "tecaj_kos" in kljuci
    assert "vijak_vrata_kos" in kljuci


# ---------------------------------------------------------------------------
# Validacija odprtin
# ---------------------------------------------------------------------------

def test_preveri_odprtine_pravilno():
    assert vrata.preveri_odprtine(
        [(0, 1000, 2100, "V1"), (2000, 1000, 2100, "V2")], 3000, 2155) == []


def test_preveri_odprtine_prekrivanje():
    napake = vrata.preveri_odprtine(
        [(0, 1000, 2100, "V1"), (500, 1000, 2100, "V2")], 3000, 2155)
    assert any("prekrivata" in n for n in napake)


def test_preveri_odprtine_cez_rob():
    napake = vrata.preveri_odprtine([(2900, 1000, 2100, "V1")], 3000, 2155)
    assert any("čez rob" in n for n in napake)


def test_preveri_odprtine_visina():
    napake = vrata.preveri_odprtine([(0, 1000, 3000, "V1")], 3000, 2155)
    assert any("presega višino" in n for n in napake)


# ---------------------------------------------------------------------------
# Robni primeri / napake
# ---------------------------------------------------------------------------

def test_neznan_tip_zavrnjen():
    with pytest.raises(ValueError):
        vrata.geometrija_vrat({"tip": "drsna"}, 1000, 2000)


def test_premajhna_odprtina_zavrnjena():
    with pytest.raises(ValueError):
        vrata.geometrija_vrat({"tip": "dvokrilna"}, 20, 2000)


def test_normalizacija_s_presledki_in_vejicami():
    v = vrata.normaliziraj_vrata({"x": " 120,5 ", "sirina": " 900 "})
    assert v["x"] == 120.5
    assert v["sirina"] == 900.0


def test_normalizacija_napacna_vrednost():
    with pytest.raises(ValueError, match="število"):
        vrata.normaliziraj_vrata({"x": "abc"})


def test_razrezne_skupine_vsebujejo_izdelane_kose():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 900}, 900, 2155)
    k = vrata.kosovnica_vrat(g)
    skupine = vrata.razrezne_skupine(k)
    assert skupine
    skupaj = sum(len(kosi) for _v, kosi in skupine)
    assert skupaj == sum(int(kol) for _o, _d, _s, kol, _op, _kl in k["izdelani"])