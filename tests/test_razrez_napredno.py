# -*- coding: utf-8 -*-
"""Issue #14: napredni razrez — testna matrika (zahteva F).

Pokriva: omejeno zalogo (tudi nezadostno), mešane/enake dolžine, kerf +
odreze + flush/ostanek, prag ostanka, združljivost lastnosti, dvojno
porabo ostanka, determinizem, veljavnost spodnje meje (noben načrt pod
mejo), vrzel do optimuma, neizvedljive primere in FIZIČNO bilanco
vsakega traku.
"""
import pytest

from razrez import (
    Kos, Nacrt, OmejitveReza, ZalogovnaPostavka,
    ekstaktni_nacrt, primerjaj_nacrte, razrez_nacrt, spodnja_meja,
    STRATEGIJE,
)


def _bilanca(nacrt):
    nacrt.preveri_bilanco()


# ---------------- A: dejanska zaloga (bounded stock) ----------------

def test_kolicine_zaloge_se_upostevajo():
    """Iz 2 × 2000 mm se ne porabi 3. palica — količina je omejitev."""
    zaloga = [ZalogovnaPostavka(2000, kolicina=2)]
    n = razrez_nacrt([("K1", 900), ("K2", 900), ("K3", 900)], zaloga,
                     OmejitveReza(kerf=3))
    _bilanca(n)
    assert len(n.traki) == 2                      # 2 palici, tretje ni


def test_nezadostna_zaloga_javi_in_ne_odpre_palice():
    zaloga = [ZalogovnaPostavka(2000, kolicina=1)]
    with pytest.raises(ValueError, match="ne zadošča"):
        razrez_nacrt([("K1", 900), ("K2", 900), ("K3", 900)], zaloga,
                     OmejitveReza(kerf=3))


def test_sledljivost_vira_trakov():
    zaloga = [ZalogovnaPostavka(2000, kolicina=1, oznaka="Z-1"),
              ZalogovnaPostavka(6000, kolicina=1, oznaka="Z-2")]
    n = razrez_nacrt([("K1", 1500), ("K2", 5000)], zaloga,
                     OmejitveReza(kerf=3), "ffd")
    _bilanca(n)
    oznake = sorted(t.zaloga.oznaka for t in n.traki)
    assert oznake == ["Z-1", "Z-2"]               # vsak trak ve, od kod je


def test_neomejena_zaloga_nazaj_zdruzljiva():
    n = razrez_nacrt([("K1", 700), ("K2", 700)], [2000, 6000],
                     OmejitveReza(kerf=3))
    _bilanca(n)


# ---------------- B: omejitve, kerf, odrezi, flush/ostanek ----------------

def test_flush_primer_rezi_n_minus_1():
    """Kos natanko do roba: rezi = n−1 (dokaz fizičnega modela)."""
    o = OmejitveReza(kerf=0, zacetni_odrez=0, koncni_odrez=0)
    n = razrez_nacrt([("K1", 1000)], [1000], o)
    t = n.traki[0]
    assert t.rezi == 0                            # 1 kos flush → 0 rezov
    assert t.ostanek_mm == 0 and t.odpad_mm == 0
    _bilanca(n)


def test_ločen_ostanek_rezi_n():
    o = OmejitveReza(kerf=3)
    n = razrez_nacrt([("K1", 500)], [2000], o)
    t = n.traki[0]
    assert t.rezi == 1                            # zadnji rez loči ostanek
    assert t.ostanek_mm == pytest.approx(2000 - 500 - 3)
    _bilanca(n)


def test_odrezi_in_bilanca():
    o = OmejitveReza(kerf=4, zacetni_odrez=10, koncni_odrez=20, min_ostanek=50)
    n = razrez_nacrt([("K1", 400), ("K2", 300)], [2000], o)
    _bilanca(n)
    t = n.traki[0]
    assert t.zacetni_odrez == 10 and t.koncni_odrez == 20
    # B = odrezi + kosi + rezi·kerf + ostanek + odpad (natanko)
    assert (10 + 20 + 700 + t.rezi * 4 + t.ostanek_mm + t.odpad_mm
            == pytest.approx(2000))


def test_prag_ostanka_kratek_rep_je_odpad():
    o = OmejitveReza(kerf=3, min_ostanek=100)
    # 2000 − 1500 = 500; po zadnjem rezu rep 497 ≥ 100 → ostanek
    n1 = razrez_nacrt([("K1", 1500)], [2000], o)
    assert n1.traki[0].ostanek_mm == pytest.approx(497)
    # rep 50 − 3 = 47 < 100 → odpad
    n2 = razrez_nacrt([("K1", 1950)], [2000], o)
    assert n2.traki[0].ostanek_mm == 0
    assert n2.traki[0].odpad_mm == pytest.approx(47)
    _bilanca(n1)
    _bilanca(n2)


def test_omejitvi_dolzine_kosa():
    o = OmejitveReza(kerf=3, min_dolzina_kosa=100, max_dolzina_kosa=1500)
    with pytest.raises(ValueError, match="krajši"):
        razrez_nacrt([("K1", 50)], [2000], o)
    with pytest.raises(ValueError, match="presega"):
        razrez_nacrt([("K1", 1600)], [2000], o)


def test_neveljavne_omejitve():
    with pytest.raises(ValueError):
        razrez_nacrt([("K1", 100)], [2000], OmejitveReza(kerf=-1))
    with pytest.raises(ValueError, match="cene"):
        razrez_nacrt([("K1", 100)], [2000], OmejitveReza(politika="cena"))


# ---------------- združljivost lastnosti ----------------

def test_prepoved_mesanja_lastnosti():
    zaloga = [ZalogovnaPostavka(2000, kolicina=2, barva="antracit"),
              ZalogovnaPostavka(2000, kolicina=1, barva="rjava")]
    n = razrez_nacrt(
        [Kos("K1", 500, barva="antracit"), Kos("K2", 500, barva="antracit"),
         Kos("K3", 500, barva="rjava")],
        zaloga, OmejitveReza(kerf=3))
    _bilanca(n)
    barve_kosov = {"K1": "antracit", "K2": "antracit", "K3": "rjava"}
    for t in n.traki:
        barve = {barve_kosov[k[0]] for k in t.kosi}
        assert len(barve) == 1                    # brez mešanja barv
    assert len(n.traki) == 2


def test_kos_brez_lastnosti_gre_kamorkoli():
    n = razrez_nacrt([Kos("K1", 500), Kos("K2", 400, barva="rjava")],
                     [ZalogovnaPostavka(2000, barva="rjava")],
                     OmejitveReza(kerf=3))
    _bilanca(n)
    assert len(n.traki) == 1


def test_nezdruzljiv_kos_javi():
    with pytest.raises(ValueError, match="ne gre v noben"):
        razrez_nacrt([Kos("K1", 500, profil="ROMB 67")],
                     [ZalogovnaPostavka(2000, profil="ROMB 90")],
                     OmejitveReza(kerf=3))


# ---------------- E: skladišče ostankov ----------------

def test_ostanek_se_porabi_najvec_enkrat():
    zaloga = [ZalogovnaPostavka(800, kolicina=1, vir="ostanek", oznaka="O-7"),
              ZalogovnaPostavka(6000, kolicina=1)]
    n = razrez_nacrt([("K1", 700), ("K2", 700)], zaloga,
                     OmejitveReza(kerf=3), "ffd")
    _bilanca(n)
    uporabljeni = [t.zaloga.oznaka for t in n.traki]
    assert uporabljeni.count("O-7") <= 1          # brez dvojne porabe


def test_ostanek_je_sledljiv_in_locen_od_novega():
    zaloga = [ZalogovnaPostavka(2000, kolicina=1, vir="ostanek", oznaka="O-1")]
    n = razrez_nacrt([("K1", 500)], zaloga, OmejitveReza(kerf=3))
    m = n.metrike()
    assert n.traki[0].zaloga.vir == "ostanek"     # izvor ohranjen
    # novonastali ostanek NI vpisan v skladišče — le naveden
    assert m["novi_ostanki"] == [("O-1", m["ostanek_mm"])]


# ---------------- C: spodnja meja in optimalnost ----------------

def test_noben_nacrt_pod_mejo():
    """Ključni dokaz: vsak načrt ≥ veljavna spodnja meja."""
    kosi = [("K1", 700), ("K2", 650), ("K3", 400), ("K4", 380),
            ("K5", 350), ("K6", 200)]
    zaloga = [ZalogovnaPostavka(2000, kolicina=4),
              ZalogovnaPostavka(4000, kolicina=2)]
    o = OmejitveReza(kerf=3, zacetni_odrez=5, koncni_odrez=5, min_ostanek=100)
    meja = spodnja_meja(kosi, zaloga, o)["spodnja_meja_mm"]
    assert meja > 0
    for strategija in STRATEGIJE:
        n = razrez_nacrt(kosi, zaloga, o, strategija)
        _bilanca(n)
        m = n.metrike()
        assert m["poraba_mm"] + 1e-6 >= meja, \
            f"{strategija} pod mejo: {m['poraba_mm']} < {meja}"


def test_protiprimer_meje_f_zvezdica():
    """Kerf > odrez se f(k) ZMANJŠA s k — stara meja f(k*) bi bila
    neveljavna; nova min-max meja mora sprejeti dosegljiv načrt."""
    o = OmejitveReza(kerf=100, min_ostanek=0)
    kosi = [("K1", 500), ("K2", 500)]
    zaloga = [ZalogovnaPostavka(500, kolicina=None),
              ZalogovnaPostavka(1100, kolicina=None)]
    meja = spodnja_meja(kosi, zaloga, o)["spodnja_meja_mm"]
    n = razrez_nacrt(kosi, zaloga, o, "ffd")
    _bilanca(n)
    assert n.metrike()["poraba_mm"] + 1e-6 >= meja
    # in meja ne sme presegati dosegljivega načrta (veljavnost obeh strani)
    assert meja <= n.metrike()["poraba_mm"] + 1e-6


def test_ekstaktno_dokazano_optimalno():
    kosi = [("K1", 700), ("K2", 650), ("K3", 400)]
    zaloga = [ZalogovnaPostavka(2000, kolicina=3)]
    o = OmejitveReza(kerf=3)
    e = ekstaktni_nacrt(kosi, zaloga, o)
    assert e is not None
    assert e.status == "dokazano optimalno"
    _bilanca(e)
    # nobena hevristika ne more biti boljša od dokazanega optimuma
    for strategija in STRATEGIJE:
        n = razrez_nacrt(kosi, zaloga, o, strategija)
        m, me = n.metrike(), e.metrike()
        assert (m["st_trakov"], m["poraba_mm"]) >= \
               (me["st_trakov"], me["poraba_mm"])


def test_ekstaktno_omejeno_stanje():
    kosi = [(f"K{i}", 100 + i) for i in range(10)]
    zaloga = [ZalogovnaPostavka(300, kolicina=8)]
    e = ekstaktni_nacrt(kosi, zaloga, OmejitveReza(kerf=1), max_stanj=50)
    # ali vrne omejen izračun ali (če hitro konča) dokazano optimalno
    if e is not None:
        assert e.status in ("omejen izračun", "dokazano optimalno")


def test_vrzel_do_meje_pravilna():
    kosi = [("K1", 700), ("K2", 650), ("K3", 400)]
    zaloga = [ZalogovnaPostavka(2000, kolicina=3)]
    o = OmejitveReza(kerf=3)
    pr = primerjaj_nacrte(kosi, zaloga, o)
    for vrstica in pr["tabela"]:
        if vrstica["vrzel_mm"] is not None:
            assert vrstica["vrzel_mm"] + 1e-6 >= 0
            assert vrstica["poraba_mm"] == pytest.approx(
                vrstica["spodnja_meja_mm"] + vrstica["vrzel_mm"])


# ---------------- D: primerjava načrtov ----------------

def test_primerjava_vsebuje_konkretne_razporeditve():
    kosi = [("K1", 700), ("K2", 650), ("K3", 400), ("K4", 380)]
    zaloga = [ZalogovnaPostavka(2000, kolicina=3)]
    pr = primerjaj_nacrte(kosi, zaloga, OmejitveReza(kerf=3))
    assert len(pr["nacrti"]) >= len(STRATEGIJE)
    for n in pr["nacrti"]:
        assert isinstance(n, Nacrt)
        assert all(t.kosi for t in n.traki)       # vsak trak ima kose
        _bilanca(n)
    # tabela ni le agregat: vsebuje število trakov in porabo
    for vrstica in pr["tabela"]:
        assert vrstica["st_trakov"] >= 1
        assert vrstica["poraba_mm"] > 0


def test_determinizem():
    kosi = [("K1", 700), ("K2", 650), ("K3", 400), ("K4", 380)]
    zaloga = [ZalogovnaPostavka(2000, kolicina=3)]
    o = OmejitveReza(kerf=3)
    for strategija in STRATEGIJE:
        a = razrez_nacrt(kosi, zaloga, o, strategija).metrike()
        b = razrez_nacrt(kosi, zaloga, o, strategija).metrike()
        assert a == b


def test_politike_spremenijo_razvrstitev():
    kosi = [("K1", 700), ("K2", 650), ("K3", 400)]
    zaloga = [ZalogovnaPostavka(2000, kolicina=3),
              ZalogovnaPostavka(1000, kolicina=3)]
    pr_palice = primerjaj_nacrte(kosi, zaloga,
                                 OmejitveReza(kerf=3, politika="palice"))
    pr_odpad = primerjaj_nacrte(kosi, zaloga,
                                OmejitveReza(kerf=3, politika="odpad"))
    assert pr_palice["kriterij"] == "palice"
    assert pr_odpad["kriterij"] == "odpad"
    # pri politiki 'palice' je prvi načrt z najmanj trakovi
    prvi = pr_palice["tabela"][0]
    assert prvi["st_trakov"] == min(v["st_trakov"]
                                    for v in pr_palice["tabela"])


def test_cenovna_politika():
    kosi = [("K1", 700), ("K2", 650)]
    zaloga = [ZalogovnaPostavka(1000, kolicina=2),
              ZalogovnaPostavka(2000, kolicina=2)]
    o = OmejitveReza(kerf=3, politika="cena",
                     cene_palice={1000.0: 10.0, 2000.0: 30.0})
    pr = primerjaj_nacrte(kosi, zaloga, o)
    # cenejša 2 × 1000 (20) kot 1 × 2000 (30) — politika 'cena' izbere prvo
    assert pr["tabela"][0]["poraba_mm"] <= 2000


# ---------------- neizvedljivo in napake ----------------

def test_neizvedljivo_jasno_sporocilo():
    zaloga = [ZalogovnaPostavka(1000, kolicina=1)]
    with pytest.raises(ValueError, match="ne zadošča|ne gre"):
        razrez_nacrt([("K1", 2000)], zaloga, OmejitveReza(kerf=3))


def test_prazen_seznam_kosov():
    n = razrez_nacrt([], [2000], OmejitveReza(kerf=3))
    assert n.traki == []
    assert n.metrike()["poraba_mm"] == 0


# ---------------- F: bilanca VSAKEGA traku ----------------

def test_bilanca_vseh_strategij():
    kosi = [(f"K{i}", 100 * i + 37) for i in range(1, 8)]
    zaloga = [ZalogovnaPostavka(1200, kolicina=5),
              ZalogovnaPostavka(3000, kolicina=2)]
    o = OmejitveReza(kerf=3, zacetni_odrez=8, koncni_odrez=12, min_ostanek=150)
    for strategija in STRATEGIJE:
        n = razrez_nacrt(kosi, zaloga, o, strategija)
        n.preveri_bilanco()                       # AssertionError = kršitev
        for t in n.traki:
            assert abs(t.bilanca_napaka()) < 1e-6

def test_strojna_omejitev_rezov():
    """max_rezov: konservativno — n kosov na trak ≤ max_rezov (B)."""
    o = OmejitveReza(kerf=3, max_rezov=2)
    n = razrez_nacrt([("K1", 400), ("K2", 400), ("K3", 400), ("K4", 400),
                      ("K5", 400)], [2000], o)
    _bilanca(n)
    for t in n.traki:
        assert len(t.kosi) <= 2
        assert t.rezi <= 2
    o1 = OmejitveReza(kerf=3, max_rezov=1)
    n1 = razrez_nacrt([("K1", 400), ("K2", 400)], [2000], o1)
    for t in n1.traki:
        assert len(t.kosi) == 1             # vsak kos svoj trak
    with pytest.raises(ValueError, match="max_rezov"):
        razrez_nacrt([("K1", 100)], [2000], OmejitveReza(max_rezov=0))
