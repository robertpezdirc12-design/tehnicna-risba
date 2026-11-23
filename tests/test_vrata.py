"""Testi geometrije in količin za vrata/prehode (issue #3, popravljeno v #6).

Ročno izračunane pričakovane vrednosti (invariant verige — issue #6:
veriga vključuje profile okvirja, ki stojijo znotraj odprtine:
2·60 + r_bok + w_1 + r_med + ... + r_bok = S_o):
- enokrilna 1000x2100: w_k = (1000-2*60-2*5)/1 = 870; h_k = 2100-50-5 = 2045
- dvokrilna 3000x2155: w_k = (3000-2*60-2*5-10)/2 = 1430; h_k = 2155-50-5 = 2100
- pasja 700x655: w_k = (700-2*60-2*5)/2 = 285 (brez reže med kriloma)
- diagonala (P6): hipotenuza NOTRANJIH mer krila, ceil5 (npr. 790x1965 -> 2120)
"""
from __future__ import annotations

import pytest

import vrata


# ---------------------------------------------------------------------------
# Geometrija — ročno preverjene vrednosti
# ---------------------------------------------------------------------------

def test_enokrilna_geometrija():
    # Issue #6: veriga vključuje tudi profile okvirja (stojala 60 mm so
    # znotraj odprtine): 60 + 5 + 870 + 5 + 60 = 1000.
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 1000, "visina": 2000},
                              1000, 2100)
    assert g["n_kril"] == 1
    assert g["sirine_kril"] == [870.0]            # (1000 - 2*60 - 2*5) / 1
    assert g["h_k"] == 2045.0                     # 2100 - 50 - 5
    r = g["reze"]
    assert (2 * vrata.SIRINA_OKVIRJA + r["bok"] + g["sirine_kril"][0]
            + r["bok"]) == 1000.0


def test_dvokrilna_geometrija():
    # 60 + 5 + 1430 + 10 + 1430 + 5 + 60 = 3000
    g = vrata.geometrija_vrat({"tip": "dvokrilna", "sirina": 3000, "visina": 2100},
                              3000, 2155)
    assert g["n_kril"] == 2
    assert g["sirine_kril"] == [1430.0, 1430.0]  # (3000 - 120 - 10 - 10) / 2
    assert g["h_k"] == 2100.0
    r = g["reze"]
    assert (2 * vrata.SIRINA_OKVIRJA + r["bok"] + g["sirine_kril"][0] + r["med"]
            + g["sirine_kril"][1] + r["bok"]) == 3000.0


def test_pasja_geometrija():
    # 60 + 5 + 285 + 285 + 5 + 60 = 700 (ni reže med kriloma)
    g = vrata.geometrija_vrat({"tip": "pasja", "sirina": 700, "visina": 600},
                              700, 655)
    assert g["n_kril"] == 2
    assert g["sirine_kril"] == [285.0, 285.0]
    assert g["h_k"] == 600.0
    r = g["reze"]
    assert (2 * vrata.SIRINA_OKVIRJA + r["bok"] + g["sirine_kril"][0]
            + g["sirine_kril"][1] + r["bok"]) == 700.0


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
    # Issue #6 (P6): diagonala je hipotenuza NOTRANJIH mer krila
    # (specifikacija docs/issue-3-vrata-dxf.md): w_k=870, h_k=2045,
    # notranje 790×1965 -> sqrt(790^2+1965^2)=2118.85 -> ceil na 5 mm = 2120
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 1000,
                               "diagonala": True}, 1000, 2100)
    assert g["diagonala_dolzina"] == 2120.0
    # skladnost: kosovnica uporablja isto vrednost
    kos = vrata.kosovnica_vrat(g)
    diag = [k for k in kos["izdelani"] if "diagonala" in k[4]]
    assert diag and diag[0][1] == 2120.0


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

# ---------------------------------------------------------------------------
# F1 (issue #5): zavrnitev negativnih rež/prečk, uskladitev elementov s
# kosovnico, enoten profil prečke in ključi cenika
# ---------------------------------------------------------------------------

def test_negativne_reze_zavrnjene():
    with pytest.raises(ValueError, match="negativna"):
        vrata.normaliziraj_vrata({"tip": "enokrilna", "sirina": 1000,
                                  "visina": 2000, "reze": {"tla": -100}})


def test_negativne_precke_zavrnjene():
    with pytest.raises(ValueError, match="negativno"):
        vrata.normaliziraj_vrata({"tip": "enokrilna", "sirina": 1000,
                                  "visina": 2000, "precke": -2})


def test_elementi_vrat_krilo_visoce_kot_kosovnica():
    g = vrata.geometrija_vrat({"tip": "dvokrilna", "sirina": 3000,
                               "visina": 2100}, 3000, 2155)
    el = vrata.elementi_vrat(g)
    krila = [(p, pl) for t, p, pl in el if t == "kvadrat" and pl == "OUTLINE"]
    assert len(krila) == 2
    for (x, y, w, h), _plast in krila:
        assert y == g["reze"]["tla"]           # krilo od tal (kot kosovnica)
        assert h == g["h_k"]                   # višina h_k (kot stojalo krila)


def test_tecaji_na_obeh_krilih_pri_dvokrilnih():
    g = vrata.geometrija_vrat({"tip": "dvokrilna", "sirina": 3000,
                               "visina": 2100}, 3000, 2155)
    el = vrata.elementi_vrat(g)
    krogi = [p for t, p, _plast in el if t == "krog"]
    assert len(krogi) == 2 * g["st_tecajev"]    # tečaji na OBEH krilih
    xs = {round(p[0]) for p in krogi}
    assert len(xs) >= 2                        # ločeni x za levo/desno krilo


def test_precka_in_diagonala_enoten_profil_40():
    g = vrata.geometrija_vrat({"tip": "enokrilna", "sirina": 1000, "visina": 2000,
                               "precke": 2, "diagonala": True}, 1000, 2100)
    k = vrata.kosovnica_vrat(g)
    precke = [r for r in k["izdelani"] if "prečka krila" in r[4]]
    diag = [r for r in k["izdelani"] if "diagonala" in r[4]]
    assert precke and all(r[2] == vrata.VISINA_LETE for r in precke)
    assert diag and all(r[2] == vrata.VISINA_LETE for r in diag)


def test_cenik_vsebuje_vse_kljuce_okovja_vrat():
    # F1: ključi vrata.CENE_KLJUCI morajo obstajati v cene.yaml, sicer so
    # postavke vrat TIHO izpuščene iz predračuna.
    import os
    import yaml
    pot = os.path.join(os.path.dirname(__file__), "..", "cene.yaml")
    with open(pot, encoding="utf-8") as f:
        cene = yaml.safe_load(f)
    for kljuc in vrata.CENE_KLJUCI.values():
        assert kljuc in cene, f"v cene.yaml manjka ključ {kljuc!r}"


# ---------------------------------------------------------------------------
# Drsná vrata (preklop je obvezen vhod — "brez ugibanja")
# ---------------------------------------------------------------------------

def test_drsna_geometrija_preklop_in_teka():
    g = vrata.geometrija_vrat({"tip": "drsna", "preklop": 150, "smer": "levo"},
                              2000, 1800)
    assert g["n_kril"] == 1
    assert g["sirine_kril"] == [2150.0]      # odprtina + preklop
    assert g["preklop"] == 150.0
    assert g["teka"] == 2150.0               # umik = širina krila
    assert g["st_tecajev"] == 0              # drsna vrata nimajo tečajev
    assert g["h_k"] == 1800 - 50 - 5


def test_drsna_brez_preklopa_je_eksplicitna_napaka():
    with pytest.raises(ValueError, match="preklop"):
        vrata.geometrija_vrat({"tip": "drsna", "smer": "levo"}, 2000, 1800)


def test_drsna_negativen_preklop_je_napaka():
    with pytest.raises(ValueError, match="Preklop"):
        vrata.geometrija_vrat({"tip": "drsna", "preklop": -10, "smer": "levo"},
                              2000, 1800)


def test_drsna_zahteva_smer_parkiranja():
    with pytest.raises(ValueError, match="smer parkiranja"):
        vrata.geometrija_vrat({"tip": "drsna", "preklop": 100,
                               "smer": "desno-navzven"}, 2000, 1800)
    with pytest.raises(ValueError, match="smer parkiranja"):
        vrata.geometrija_vrat({"tip": "drsna", "preklop": 100}, 2000, 1800)
    g = vrata.geometrija_vrat({"tip": "drsna", "preklop": 100, "smer": "desno"},
                              2000, 1800)
    assert g["smer"] == "desno"


def test_drsna_kosovnica_brez_okvirja_in_tecajev():
    g = vrata.geometrija_vrat({"tip": "drsna", "preklop": 150, "smer": "levo"},
                              2000, 1800)
    k = vrata.kosovnica_vrat(g)
    opisi = " ".join(vr[4] for vr in k["izdelani"])
    assert "okvirja" not in opisi             # drsna nimajo okvirja v odprtini
    assert "krila" in opisi                   # krilo je izdelano
    oznake = [vr[0] for vr in k["kupljeni"]]
    assert not any(o.startswith("TEČ") for o in oznake)   # brez tečajev
    letev = next(vr for vr in k["izdelani"] if "letev" in vr[4])
    assert letev[1] == 2150.0 - 2 * vrata.SIRINA_STOJALA


def test_drsna_elementi_zrcaljenje_preklopa():
    g_l = vrata.geometrija_vrat({"tip": "drsna", "preklop": 150, "smer": "levo"},
                                2000, 1800)
    g_d = vrata.geometrija_vrat({"tip": "drsna", "preklop": 150, "smer": "desno"},
                                2000, 1800)

    def krilo(g):
        return [p for v, p, plast in vrata.elementi_vrat(g)
                if v == "kvadrat" and plast == "OUTLINE"][0]

    # levo: krilo [0, S_o + preklop]; desno zrcalno: [-preklop, S_o]
    k_l, k_d = krilo(g_l), krilo(g_d)
    assert (k_l[0], k_l[2]) == (0.0, 2150.0)
    assert (k_d[0], k_d[2]) == (-150.0, 2150.0)
    # brez tečajev (krogov) in brez okvirnih stojal v odprtini
    for g in (g_l, g_d):
        el = vrata.elementi_vrat(g)
        assert not any(v == "krog" for v, _p, _plast in el)
