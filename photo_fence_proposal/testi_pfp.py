"""photo_fence_proposal — samostojni testi (ne vplivajo na obstoječo tests/).

Zagon: python -m pytest photo_fence_proposal/testi_pfp.py
ali iz mape: python -m pytest testi_pfp.py

Testi Faze 4 merijo NAPAKO kalibriranih mer na sintetičnih prizorih z
znanimi resničnimi merami — poročajo dejanske vrednosti, ne le "zeleno".
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model import (Mera, ParametriNove, Rezultat, NEZNANO, OCENJENO,
                   IZMERJENO, IZRACUNANO)
import zaznavanje
import kalibracija
import material
import napravi_testne_slike

MAPA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testni_primeri")


@pytest.fixture(scope="session")
def testni_prizori():
    """Generiraj 5 sintetičnih prizorov z znanimi merami (enkrat)."""
    os.makedirs(MAPA, exist_ok=True)
    primeri = [
        ("prizor_cel", dict(dolzina_mm=6000, visina_mm=1800, st_polj=3,
                            nagib=0.0, sem=1)),
        ("prizor_nagib", dict(dolzina_mm=5000, visina_mm=1700, st_polj=2,
                              nagib=8.0, sem=2)),
        ("prizor_ozek", dict(dolzina_mm=3000, visina_mm=1500, st_polj=1,
                             nagib=3.0, sem=3)),
        ("prizor_dolg", dict(dolzina_mm=9000, visina_mm=1800, st_polj=5,
                             nagib=5.0, sem=4)),
        ("prizor_nizek", dict(dolzina_mm=4000, visina_mm=1000, st_polj=2,
                              nagib=0.0, sem=5)),
    ]
    izhod = []
    for ime, parametri in primeri:
        pot = os.path.join(MAPA, ime + ".png")
        resni = napravi_testne_slike.narisi_prizor(pot, **parametri)
        izhod.append((ime, pot, resni))
    return izhod


# ---------------------------------------------------------------------------
# Model: poštenost mer (jedro zahteve "ne sme si izmišljati mer")
# ---------------------------------------------------------------------------

def test_neznana_mera_nima_izmisljene_vrednosti():
    with pytest.raises(ValueError):
        Mera(1200.0, NEZNANO, "neznano ne sme imeti številke")
    with pytest.raises(ValueError):
        Mera(None, IZMERJENO, "potrjena brez vrednosti")


def test_neznan_status_zavrnjen():
    with pytest.raises(ValueError):
        Mera(100.0, "verjetno", "izmišljen status")


def test_oznaka_mere_vedno_vsebuje_status():
    assert "izmerjeno" in Mera(100.0, IZMERJENO, "x").oznaka
    assert "neznano" in Mera(None, NEZNANO, "x").oznaka
    assert "ocenjeno" in Mera(100.0, OCENJENO, "x").oznaka


def test_dokument_informativen_dokler_mere_niso_potrjene():
    rez = Rezultat(zaznava=None, parametri=ParametriNove())
    rez.mere = {"dolzina_ograje": Mera(None, NEZNANO, "x"),
                "visina_ograje": Mera(1800.0, IZMERJENO, "x")}
    assert not rez.vse_kljucne_mere_potrjene
    assert "INFORMATIVNI" in rez.oznaka_dokumenta
    rez.mere["dolzina_ograje"] = Mera(6000.0, IZMERJENO, "x")
    assert rez.vse_kljucne_mere_potrjene
    assert "IZDELAVO" in rez.oznaka_dokumenta


def test_neveljaven_tip_ograje_zavrnjen():
    with pytest.raises(ValueError):
        ParametriNove(tip="zid")


# ---------------------------------------------------------------------------
# Zaznavanje (klasični algoritmi) + napaka mer na testnih prizorih
# ---------------------------------------------------------------------------

def test_zaznava_na_prizoru(testni_prizori):
    ime, pot, resni = testni_prizori[0]
    z = zaznavanje.zaznaj(pot)
    stebri = len({round(t[0], 1) for e in z.elementi if e.vrsta == "steber"
                  for t in e.tocke_px[:1]})
    assert stebri >= 2, f"{ime}: zaznanih {stebri} stebrov (pričakovano >= 2)"
    assert z.opozorila, "zaznavanje mora poročati omejitve"


def test_napaka_mer_na_prizorih(testni_prizori, capsys):
    """Faza 4: merjenje napake kalibriranih mer proti znanim resničnim."""
    porocilo = []
    for ime, pot, resni in testni_prizori:
        z = zaznavanje.zaznaj(pot)
        kal = kalibracija.kalibriraj_referenca(
            z, "razmak_stebrov", resni["dolzina_ograje"] / resni["stevilo_polj"])
        mere = kalibracija.izpelji_mere(z, ParametriNove(), kal)
        napake = kalibracija.napaka_na_testni_sliki(
            mere, {"dolzina_ograje": resni["dolzina_ograje"],
                   "visina_ograje": resni["visina_ograje"]})
        porocilo.append((ime, resni["nagib_stopinj"], napake))
        # ključne mere so s kalibracijo IZMERJENE (ne izmišljene)
        assert mere["dolzina_ograje"].status == IZMERJENO
        assert mere["visina_ograje"].status == IZMERJENO
    with capsys.disabled():
        print("\n=== NAPAKA MER (sintetični prizori, kalibracija na razmak stebrov) ===")
        for ime, nagib, napake in porocilo:
            niz = ", ".join(f"{k}: ±{v:.0f} mm" for k, v in napake.items())
            print(f"  {ime} (nagib {nagib}°): {niz}")
        print("=== (manjši nagib → manjša napaka; pri nagibu so mere slabše ===")


def test_brez_kalibracije_mere_ostanejo_neznane(testni_prizori):
    ime, pot, resni = testni_prizori[0]
    z = zaznavanje.zaznaj(pot)
    mere = kalibracija.izpelji_mere(z, ParametriNove(), None)
    assert mere["dolzina_ograje"].status == NEZNANO
    assert mere["dolzina_ograje"].vrednost_mm is None
    # štetje stebrov je zanesljivo tudi brez kalibracije
    assert mere["stevilo_stebrov"].status == IZMERJENO


def test_kalibracija_z_visino(testni_prizori):
    ime, pot, resni = testni_prizori[0]
    z = zaznavanje.zaznaj(pot)
    kal = kalibracija.kalibriraj_referenca(z, "visina_ograje", resni["visina_ograje"])
    mere = kalibracija.izpelji_mere(z, ParametriNove(), kal)
    napaka = abs(mere["visina_ograje"].vrednost_mm - resni["visina_ograje"])
    assert napaka < resni["visina_ograje"] * 0.15, f"napaka {napaka:.0f} mm"


def test_neveljavna_referenca_zavrnjena(testni_prizori):
    ime, pot, resni = testni_prizori[0]
    z = zaznavanje.zaznaj(pot)
    with pytest.raises(ValueError):
        kalibracija.kalibriraj_referenca(z, "razmak_stebrov", -5)
    with pytest.raises(ValueError):
        kalibracija.kalibriraj_referenca(z, "neki", 1000)


# ---------------------------------------------------------------------------
# Material / razrez
# ---------------------------------------------------------------------------

def test_material_informativen_brez_mer():
    rez = Rezultat(zaznava=None, parametri=ParametriNove())
    rez.mere = {"dolzina_ograje": Mera(None, NEZNANO, "x"),
                "visina_ograje": Mera(None, NEZNANO, "x")}
    material.izracunaj_material(rez)
    assert all(p.status_mer == NEZNANO or p.kolicina == 0
               for p in rez.kosovnica)
    assert any("informativne" in o.lower() or "ni izračunana" in o.lower()
               for o in rez.opozorila)


def test_material_s_potrjenimi_merami():
    rez = Rezultat(zaznava=None, parametri=ParametriNove())
    rez.mere = {
        "dolzina_ograje": Mera(6000.0, IZMERJENO, "x"),
        "visina_ograje": Mera(1800.0, IZMERJENO, "x"),
        "stevilo_polj": Mera(3.0, IZRACUNANO, "x"),
        "stevilo_stebrov": Mera(4.0, IZMERJENO, "x"),
        "razmak_stebrov": Mera(2000.0, IZRACUNANO, "x"),
    }
    material.izracunaj_material(rez)
    lamela = next(p for p in rez.kosovnica if p.naziv == "WPC lamela/deska")
    assert lamela.kolicina > 0
    steber = next(p for p in rez.kosovnica if p.naziv == "Steber")
    assert steber.kolicina == 4
    assert rez.razrez and rez.odpad_mm is not None


def test_razrez_ne_prelazi_palice():
    palice, odpad = material._razrez_palic(10, 6000.0)
    # 6000 mm kos = 1 kos na palico (tlačni rez ni potreben)
    assert palice == [1] * 10
    palice, odpad = material._razrez_palic(3, 1000.0)
    assert sum(palice) == 3
    assert odpad >= 0


# ---------------------------------------------------------------------------
# Celoten tok (CLI pozeni)
# ---------------------------------------------------------------------------

def test_celoten_tok(testni_prizori, tmp_path):
    import zazeni
    ime, pot, resni = testni_prizori[0]
    izhod = str(tmp_path / "izhod")
    rez = zazeni.pozeni(pot, izhod, ParametriNove(),
                        referenca=("razmak_stebrov",
                                   resni["dolzina_ograje"] / resni["stevilo_polj"]))
    for ime_datoteke in ("01-zaznava.png", "02-vizualni-predlog.png",
                         "03-tehniska-risba.pdf", "04-kosovnica.csv",
                         "05-povzetek.json", "06-povzetek.txt"):
        pot_d = os.path.join(izhod, ime_datoteke)
        assert os.path.isfile(pot_d) and os.path.getsize(pot_d) > 0, ime_datoteke
    # JSON vsebuje statuse mer (strojno preverljiva poštenost)
    with open(os.path.join(izhod, "05-povzetek.json"), encoding="utf-8") as f:
        podatki = json.load(f)
    assert podatki["mere"]["dolzina_ograje"]["status"] == "izmerjeno"
    assert podatki["mere"]["sirina_lamele"]["status"] == "ocenjeno"


def test_tehniska_risba_vsebuje_statuse(testni_prizori, tmp_path):
    from pypdf import PdfReader
    import zazeni
    ime, pot, resni = testni_prizori[0]
    izhod = str(tmp_path / "izhod2")
    zazeni.pozeni(pot, izhod, ParametriNove(),
                  referenca=("razmak_stebrov",
                             resni["dolzina_ograje"] / resni["stevilo_polj"]))
    r = PdfReader(os.path.join(izhod, "03-tehniska-risba.pdf"))
    besedilo = r.pages[0].extract_text()
    assert "izmerjeno" in besedilo or "ocenjeno" in besedilo
    assert "VIZUAL" not in besedilo  # risba ni vizualizacija


# ---------------------------------------------------------------------------
# Brez AI / lokalno (dokazilo z AST pregledom uvozov)
# ---------------------------------------------------------------------------

def test_brez_ai_in_omreznih_odvisnosti():
    import ast
    prepovedani = {"torch", "tensorflow", "keras", "onnx", "ultralytics",
                   "requests", "urllib", "httpx", "openai", "anthropic"}
    mapa = os.path.dirname(os.path.abspath(__file__))
    for ime in os.listdir(mapa):
        if not ime.endswith(".py"):
            continue
        with open(os.path.join(mapa, ime), encoding="utf-8") as f:
            drevo = ast.parse(f.read())
        for vozlisce in ast.walk(drevo):
            if isinstance(vozlisce, ast.Import):
                imena = {a.name.split(".")[0] for a in vozlisce.names}
            elif isinstance(vozlisce, ast.ImportFrom) and vozlisce.module:
                imena = {vozlisce.module.split(".")[0]}
            else:
                continue
            assert not (imena & prepovedani), f"{ime}: prepovedan uvoz {imena & prepovedani}"


def test_dodatek_ne_uvaza_obstojecega_programa():
    """Issue #8: dodatek je samostojen — ne uvaža risba/razrez/vrata/vmesnik."""
    import ast
    prepovedani = {"risba", "razrez", "vrata", "vmesnik", "dxf_izvoz",
                   "merjenje", "migracija", "terenski_list", "terenski_gui"}
    mapa = os.path.dirname(os.path.abspath(__file__))
    for ime in os.listdir(mapa):
        if not ime.endswith(".py"):
            continue
        with open(os.path.join(mapa, ime), encoding="utf-8") as f:
            drevo = ast.parse(f.read())
        for vozlisce in ast.walk(drevo):
            if isinstance(vozlisce, ast.Import):
                imena = {a.name.split(".")[0] for a in vozlisce.names}
            elif isinstance(vozlisce, ast.ImportFrom) and vozlisce.module:
                imena = {vozlisce.module.split(".")[0]}
            else:
                continue
            assert not (imena & prepovedani), f"{ime}: uvaža obstoječi program"