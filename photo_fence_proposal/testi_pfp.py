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
        print("=== (kalibracija na razmak: dolžina (n−1)×razmak je po konstrukciji "
              "natančna; višina je odvisna od zaznave letvi ===")


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
# Regresija merjenja (PODAGENT A): meritve iz zanesljivih referenc, ne bbox-a
# ---------------------------------------------------------------------------

def _zaznava_iz_elementov(elementi, sirina=1280, visina=860, obmocje=None):
    from model import Slika, Zaznava
    z = Zaznava(slika=Slika(pot="test", sirina_px=sirina, visina_px=visina))
    z.elementi = elementi
    z.obmocje_ograje_px = obmocje or []
    return z


def test_dolzina_iz_sredisc_stebrov_ne_iz_bbox():
    """Hough daljice segajo prek ograje — bbox bi PREVELIČAL dolžino."""
    from model import Element
    z = _zaznava_iz_elementov([
        Element("steber", [(100.0, 50.0), (100.0, 400.0)], 0.7),
        Element("steber", [(700.0, 50.0), (700.0, 400.0)], 0.7),
        Element("precka", [(80.0, 100.0), (720.0, 100.0)], 0.5),
        Element("precka", [(0.0, 380.0), (1000.0, 380.0)], 0.5),  # odvečna daljica
    ], obmocje=[(0.0, 50.0), (1000.0, 50.0), (1000.0, 400.0), (0.0, 400.0)])
    assert kalibracija.dolzina_ograje_px(z) == 600.0
    assert kalibracija.visina_ograje_px(z) == 280.0  # središči letvi 100 in 380


def test_visina_iz_letvi_uposteva_sredisca_ne_robov():
    """Zgornja in spodnja letva sta zaznani kot par robnih črt (±4 px) —
    meriti je treba središči gruč, ne najbolj oddaljenih robov (ta bi bila
    296 namesto 288)."""
    from model import Element
    z = _zaznava_iz_elementov([
        Element("steber", [(100.0, 30.0), (100.0, 420.0)], 0.7),
        Element("steber", [(700.0, 30.0), (700.0, 420.0)], 0.7),
        Element("precka", [(80.0, 327.0), (720.0, 327.0)], 0.5),
        Element("precka", [(80.0, 335.0), (720.0, 335.0)], 0.5),
        Element("precka", [(80.0, 615.0), (720.0, 615.0)], 0.5),
        Element("precka", [(80.0, 623.0), (720.0, 623.0)], 0.5),
    ], obmocje=[(80.0, 30.0), (720.0, 30.0), (720.0, 420.0), (80.0, 420.0)])
    assert abs(kalibracija.visina_ograje_px(z) - 288.0) < 1.0


def test_dolzina_in_visina_fallback_na_obmocje():
    """Brez dveh stebrov/letvi meritve fallbackajo na bbox (in so negotove)."""
    from model import Element
    z = _zaznava_iz_elementov([
        Element("steber", [(100.0, 50.0), (100.0, 400.0)], 0.7),
    ], obmocje=[(30.0, 40.0), (1200.0, 40.0), (1200.0, 500.0), (30.0, 500.0)])
    assert kalibracija.dolzina_ograje_px(z) == 1170.0
    assert kalibracija.visina_ograje_px(z) == 460.0
    z2 = _zaznava_iz_elementov([], obmocje=[])
    assert kalibracija.dolzina_ograje_px(z2) is None
    assert kalibracija.visina_ograje_px(z2) is None


def test_napaka_mer_regresija(testni_prizori, capsys):
    """Regresija: sistematični odmik bbox-a mora ostati odstranjen.

    Kalibracija na razmak: dolžina je (n−1)×razmak po konstrukciji (0 mm);
    neodvisen preizkus: kalibracija na višino → napaka dolžine < 5 %.
    """
    from model import ParametriNove
    for ime, pot, resni in testni_prizori:
        z = zaznavanje.zaznaj(pot)
        kal = kalibracija.kalibriraj_referenca(
            z, "razmak_stebrov", resni["dolzina_ograje"] / resni["stevilo_polj"])
        mere = kalibracija.izpelji_mere(z, ParametriNove(), kal)
        nd = abs(mere["dolzina_ograje"].vrednost_mm - resni["dolzina_ograje"])
        nv = abs(mere["visina_ograje"].vrednost_mm - resni["visina_ograje"])
        assert nd < 0.01 * resni["dolzina_ograje"], f"{ime}: dolzina ±{nd:.0f} mm"
        assert nv < 0.05 * resni["visina_ograje"], f"{ime}: visina ±{nv:.0f} mm"
        # neodvisna pot: kalibracija na višino → napaka dolžine
        kal_v = kalibracija.kalibriraj_referenca(
            z, "visina_ograje", resni["visina_ograje"])
        mere_v = kalibracija.izpelji_mere(z, ParametriNove(), kal_v)
        nd_v = abs(mere_v["dolzina_ograje"].vrednost_mm
                   - resni["dolzina_ograje"])
        assert nd_v < 0.05 * resni["dolzina_ograje"], f"{ime}: navzkrižno ±{nd_v:.0f} mm"
        with capsys.disabled():
            print(f"  regresija {ime}: dolzina ±{nd:.0f} mm, visina ±{nv:.0f} mm, "
                  f"navzkrižno (kal. višina→dolžina) ±{nd_v:.0f} mm")


def test_risba_namesto_fotografije_ne_izmisli_mer(tmp_path):
    """Tehnična risba (bel okvir) ni fotografija ograje — program MORA
    javiti šibko/lažno zaznavo in NE sme izmišljati mer v mm."""
    import cv2
    import numpy as np
    from model import ParametriNove
    slika = np.full((860, 1280, 3), 245, dtype=np.uint8)
    cv2.rectangle(slika, (40, 40), (1240, 820), (0, 0, 0), 6)
    cv2.line(slika, (40, 430), (1240, 430), (0, 0, 0), 4)
    pot = str(tmp_path / "risba.png")
    cv2.imwrite(pot, slika)
    z = zaznavanje.zaznaj(pot)
    mere = kalibracija.izpelji_mere(z, ParametriNove(), None)
    for kljuc in ("dolzina_ograje", "visina_ograje", "razmak_stebrov"):
        m = mere[kljuc]
        assert m.status == NEZNANO and m.vrednost_mm is None, (
            f"{kljuc}: {m.oznaka} — izmišljena mera na sliki brez ograje!")
    assert any("šibka" in o.lower() or "lažn" in o.lower() or "manj kot" in o
               for o in z.opozorila), "brez opozorila o negotovi zaznavi"


def test_neverodostojna_mera_je_zavrzena_ne_izmisljena():
    """Izračunana vrednost zunaj fizičnih mej (tu: višina 8,2 m) se JAVNO
    zavrže (NEZNANO + opozorilo) — nikoli se ne izpiše kot 'izmerjeno'."""
    from model import Element, Slika, Zaznava, ParametriNove
    z = Zaznava(slika=Slika(pot="test", sirina_px=1280, visina_px=860))
    z.elementi = [
        Element("steber", [(100.0, 20.0), (100.0, 840.0)], 0.7),
        Element("steber", [(300.0, 20.0), (300.0, 840.0)], 0.7),
        Element("precka", [(90.0, 20.0), (310.0, 20.0)], 0.5),
        Element("precka", [(90.0, 840.0), (310.0, 840.0)], 0.5),
    ]
    z.obmocje_ograje_px = [(90.0, 20.0), (310.0, 20.0),
                           (310.0, 840.0), (90.0, 840.0)]
    # 200 px = 2000 mm → 10 mm/px; višina 820 px → 8200 mm (neverodostojno)
    kal = kalibracija.kalibriraj_referenca(z, "razmak_stebrov", 2000.0)
    mere = kalibracija.izpelji_mere(z, ParametriNove(), kal)
    assert mere["visina_ograje"].status == NEZNANO
    assert mere["visina_ograje"].vrednost_mm is None
    assert "8200" in mere["visina_ograje"].opis  # zavržena vrednost ostane vidna
    assert mere["dolzina_ograje"].status == IZMERJENO  # 2000 mm je v mejah
    assert any("verodostojna" in o or "zavržena" in o.lower()
               for o in z.opozorila), "brez opozorila o zavrženi meritvi"


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
    zazeni.pozeni(pot, izhod, ParametriNove(),
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


# ---------------------------------------------------------------------------
# Regresija: material/razrez/kosovnica, risba, predlog in CLI (PODAGENT B)
# ---------------------------------------------------------------------------

def _rezultat_z_merami(dolzina=None, visina=None, n_polj=None, razmak=None):
    rez = Rezultat(zaznava=None, parametri=ParametriNove())
    mere = {}
    if dolzina is not None:
        mere["dolzina_ograje"] = Mera(dolzina, IZMERJENO, "x")
    else:
        mere["dolzina_ograje"] = Mera(None, NEZNANO, "x")
    if visina is not None:
        mere["visina_ograje"] = Mera(visina, IZMERJENO, "x")
    else:
        mere["visina_ograje"] = Mera(None, NEZNANO, "x")
    if n_polj is not None:
        mere["stevilo_polj"] = Mera(float(n_polj), IZRACUNANO, "x")
    if razmak is not None:
        mere["razmak_stebrov"] = Mera(razmak, IZRACUNANO, "x")
    rez.mere = mere
    return rez


def test_razrez_rocni_primer_6x2500():
    """Ročni preverjen primer: 6 kosov × 2500 mm iz 6000 mm palic (kerf 3).

    Po 2 kosa na palico (2×2500 + 3 = 5003 ≤ 6000): 3 palice;
    poraba 3×5003 = 15009 → odpad 18000 − 15009 = 2991 mm (3×997)."""
    palice, odpad = material._razrez_palic(6, 2500.0)
    assert palice == [2, 2, 2]
    assert len(palice) == 3
    assert odpad == pytest.approx(2991.0)
    assert sum(palice) == 6  # vsi kosi izdelani


def test_razrez_kos_daljsi_od_palice_ne_negativen_odpad():
    """Regresija: kos > 6000 mm NE sme dati negativnega odpada."""
    with pytest.raises(ValueError):
        material._razrez_palic(4, 7000.0)
    with pytest.raises(ValueError):
        material._razrez_palic(2, 6001.0)
    # prek kosovnice: pošteno opozorilo, brez izmišljenega razreza
    rez = _rezultat_z_merami(dolzina=7000.0, visina=1800.0, n_polj=3)
    material.izracunaj_material(rez)
    assert rez.razrez == []
    assert rez.odpad_mm is None
    assert any("spajanje" in o for o in rez.opozorila)


def test_vijaki_stevilo_iz_lamel_ne_iz_vrstic_kosovnice():
    """Regresija: vijaki = 2 × n_polj × št. lamel (ne × št. vrstic kosovnice)."""
    rez = _rezultat_z_merami(dolzina=6000.0, visina=1800.0, n_polj=3,
                            razmak=2000.0)
    material.izracunaj_material(rez)
    lamela = next(p for p in rez.kosovnica if p.naziv == "WPC lamela/deska")
    vijaki = next(p for p in rez.kosovnica if p.naziv == "Vijaki M8×70")
    assert lamela.kolicina > 0
    assert vijaki.kolicina == 2 * 3 * lamela.kolicina


def test_kosovnica_najseibkejsi_status_mer():
    """Regresija: status kosovnice = najšibkejši status vpletenih mer.

    Brez znane višine ni ne lamel ne višine stebra — vrstice NE smejo
    trditi 'izracunano', če je ključna vpletena mera NEZNANA."""
    rez = _rezultat_z_merami(dolzina=6000.0, visina=None, n_polj=3,
                            razmak=2000.0)
    material.izracunaj_material(rez)
    steber = next(p for p in rez.kosovnica if p.naziv == "Steber")
    assert steber.dimenzija == "??"
    assert steber.status_mer == NEZNANO
    vijaki = next(p for p in rez.kosovnica if p.naziv == "Vijaki M8×70")
    assert vijaki.kolicina == 0
    assert vijaki.status_mer == NEZNANO
    # če je višina znana, je status največ ocenjeno (širina lamele/+200 mm)
    rez2 = _rezultat_z_merami(dolzina=6000.0, visina=1800.0, n_polj=3,
                             razmak=2000.0)
    material.izracunaj_material(rez2)
    for p in rez2.kosovnica:
        assert p.status_mer in (OCENJENO, NEZNANO), p.naziv


def test_mera_ne_more_biti_negativna():
    """Regresija: negativna vrednost ne sme biti označena kot izmerjena."""
    with pytest.raises(ValueError):
        Mera(-100.0, IZMERJENO, "napačen ročni vnos")


def test_predlog_korak_desk_ni_degeneriran():
    """Regresija: korak risanja desk je bil za pokončne deske vedno 3.0 px
    (sto črt namesto desk). Korak naj sledi merilu ali px ≈ mm."""
    import predlog
    rez = _rezultat_z_merami(dolzina=6000.0, visina=1800.0)
    # kalibrirano: 500 px za 6000 mm → korak 180 mm ≈ 15 px
    korak = predlog._korak_px(rez, "dolzina_ograje", 500.0, 180.0)
    assert korak == pytest.approx(15.0)
    # brez kalibracije: informativni prikaz px ≈ mm (kot doslej)
    rez2 = _rezultat_z_merami(dolzina=None, visina=None)
    assert predlog._korak_px(rez2, "dolzina_ograje", 500.0, 180.0) == 180.0


def test_tehniska_risba_shematska_ko_mere_neznane(testni_prizori, tmp_path):
    from pypdf import PdfReader
    import tehniska_risba
    rez = _rezultat_z_merami(dolzina=None, visina=None)
    import material as mat
    mat.izracunaj_material(rez)
    pot = tehniska_risba.narisi_tehnisko_risbo(
        rez, str(tmp_path / "shema.pdf"))
    besedilo = PdfReader(pot).pages[0].extract_text()
    assert "INFORMATIVNI" in besedilo
    assert "shematski" in besedilo  # placeholder L/H mora biti označen
    assert "neznano" in besedilo


def test_cli_neobstojoca_fotografija_jasna_napaka(tmp_path, capsys):
    import zazeni
    kod = zazeni.main(["--fotografija", str(tmp_path / "manjka.jpg"),
                       "--izhod", str(tmp_path / "izhod")])
    assert kod == 1
    err = capsys.readouterr().err
    assert "NAPAKA" in err and "manjka.jpg" in err  # brez zrušitve/tracebacka


def test_cli_napacna_referenca_jasna_napaka(testni_prizori, tmp_path, capsys):
    import zazeni
    ime, pot, resni = testni_prizori[0]
    for referenca, pricakovano in (("razmak", 2),              # brez '='
                                   ("razmak_stebrov=abc", 2),  # ni številka
                                   ("sirina=100", 1),          # neznano ime
                                   ("razmak_stebrov=-5", 1)):  # negativno
        kod = zazeni.main(["--fotografija", pot,
                           "--izhod", str(tmp_path / "izhod"),
                           "--referenca", referenca])
        assert kod == pricakovano, referenca
        err = capsys.readouterr().err
        assert "NAPAKA" in err, referenca


def test_cli_negativna_rocna_mera_zavrnjena(tmp_path, capsys):
    """Regresija: --visina -100 ne sme dati 'PRIPRAVLJENO ZA IZDELAVO'."""
    import zazeni
    for argumenti in (["--visina", "-100"], ["--dolzina", "0"]):
        kod = zazeni.main(["--fotografija", "ne_obstaja.jpg",
                           "--izhod", str(tmp_path / "izhod"),
                           *argumenti])
        assert kod == 2, argumenti
        err = capsys.readouterr().err
        assert "NAPAKA" in err and "pozitivna" in err, argumenti

def test_negotova_zaznava_demove_mere_in_dokument():
    """Realni balkonski test: zgrešena zaznava ne sme dajati 'izmerjeno'
    in 'PRIPRAVLJENO ZA IZDELAVO' (dolžina 17329 mm namesto ~6200 mm)."""
    from model import Zaznava, Slika, Element, ParametriNove
    import kalibracija
    slika = Slika("x.png", 1024, 768)
    el = [Element("steber", [(10, 0), (10, 100)], 0.5),
          Element("steber", [(900, 0), (900, 100)], 0.5),
          Element("letv", [(0, 50), (1024, 50)], 0.5),
          Element("letv", [(0, 95), (1024, 95)], 0.5)]
    z = Zaznava(slika, el, [(0, 0), (1024, 0), (1024, 768), (0, 768)],
                ["Razmaki med zaznanimi stebri so zelo neenakomerni — "
                 "zaznava stebrov je negotova."])
    k = kalibracija.kalibriraj_referenca(z, "visina_ograje", 1050.0)
    mere = kalibracija.izpelji_mere(z, ParametriNove(), k)
    # dolžina iz negotove zaznave NI 'izmerjeno'
    assert mere["dolzina_ograje"].status in ("ocenjeno", "neznano")
    # referenčna višina (uporabnik potrdil) ostane izmerjeno
    assert mere["visina_ograje"].status == "izmerjeno"
    # dokument NI 'PRIPRAVLJENO ZA IZDELAVO'
    from model import Rezultat
    r = Rezultat(z, ParametriNove(), mere=mere, opozorila=list(z.opozorila))
    assert "PRIPRAVLJENO" not in r.oznaka_dokumenta


# ---------------------------------------------------------------------------
# Avtomatska skica (slika -> profesionalni A3 list): rektifikacija, ritem
# ---------------------------------------------------------------------------

def test_lamelni_ritem_na_sinteticni_sliki():
    import numpy as np
    import rektifikacija
    slika = np.full((400, 600), 220, dtype=np.uint8)
    for y in range(40, 360, 30):          # deske 20 px, fuge 10 px
        slika[y:y + 20, :] = 40
    ritem = rektifikacija.lamelni_ritem(slika)
    assert ritem["n_lamel"] >= 5
    assert abs(ritem["pitch_px"] - 30.0) < 4.0
    assert ritem["vrzel_px"] < ritem["debelina_px"]   # fuga tanjša od deske


def test_pas_ograje_zazna_pas():
    import numpy as np
    import rektifikacija
    slika = np.full((400, 600), 230, dtype=np.uint8)
    for y in range(100, 300, 30):         # pas samo med 100..300
        slika[y:y + 20, 50:550] = 40
    pas = rektifikacija.pas_ograje(slika, 30.0)
    assert pas is not None
    y0, y1, x0, x1 = pas
    assert 60 <= y0 <= 140 and 260 <= y1 <= 340, pas    # pas ograje, ne cela slika


def test_avtomatska_skica_pdf_vsebina(tmp_path):
    import os
    import napravi_testne_slike
    import avtomatska_skica
    from pypdf import PdfReader
    scena = str(tmp_path / "prizor.png")
    napravi_testne_slike.narisi_prizor(scena, 6000.0, 1800.0, nagib=0)
    pot = str(tmp_path / "skica.pdf")
    pot2, pod = avtomatska_skica.generiraj(
        scena, pot, lokacija="TEST", referenca=("visina_ograje", 1800.0))
    assert pot2 == pot and os.path.getsize(pot) > 5000
    t = PdfReader(pot).pages[0].extract_text()
    for kljuc in ("SPREDNJI POGLLED", "PRESEZ A-A", "DETAJL",
                  "NASLOVNI BLOK", "KOSOVNICA", "izmerjeno", "izracunano",
                  "NASLOV", "LOKACIJA: TEST", "LEGENDA"):
        assert kljuc in t, kljuc
    # referenčna višina je potrjena
    assert pod["mere"]["visina_ograje"].status == "izmerjeno"


def test_avtomatska_skica_brez_reference_ne_izmisljuje(tmp_path):
    import napravi_testne_slike
    import avtomatska_skica
    scena = str(tmp_path / "prizor2.png")
    napravi_testne_slike.narisi_prizor(scena, 6000.0, 1800.0, nagib=4)
    pot, pod = avtomatska_skica.generiraj(scena, str(tmp_path / "s2.pdf"))
    for ime, m in pod["mere"].items():
        # brez reference NIČ ni 'izmerjeno' — samo ocenjeno/izracunano/neznano
        assert m.status != "izmerjeno", (ime, m.status)
    assert any("Brez referenčne mere" in o for o in pod["opombe"])


def test_vp_ransac_z_outlierji():
    """RANSAC najde točko izginjanja tudi ob 40 % motnjah."""
    import numpy as np
    import rektifikacija
    rng = np.random.default_rng(7)
    resnica = np.array([900.0, 300.0])       # prava točka izginjanja
    linije = []
    for _ in range(25):                      # prave premice skozi resnico
        p = np.array([rng.uniform(0, 600), rng.uniform(0, 400)])
        d = resnica - p
        d /= np.linalg.norm(d)
        linije.append((p, d))
    for _ in range(18):                      # motnje (naključne smeri)
        p = np.array([rng.uniform(0, 600), rng.uniform(0, 400)])
        k = rng.uniform(0, np.pi)
        linije.append((p, np.array([np.cos(k), np.sin(k)])))
    v = rektifikacija.vp_ransac(linije, prag=2.0)
    assert v is not None
    assert np.linalg.norm(v - resnica) < 30.0, v


def test_vogali_in_referenca_natančno_izmerita(tmp_path):
    """P1: klikani vogali + 1 referenca -> mere iz trdne geometrije.

    Sintetični prizor: plošča 2400x1200 mm zavita v perspektivo (trapez),
    znani vogali. Referenca visina=1200 -> dolžina mora biti ~2400 mm.
    """
    import numpy as np
    import cv2
    import avtomatska_skica

    # izvorna plošča (2 mm/px): lamele
    Wp, Hp = 1200, 600
    plosca = np.full((Hp, Wp), 235, dtype=np.uint8)
    for y in range(30, Hp - 30, 58):
        plosca[y:y + 44, :] = 55
    # zavij v perspektivo (trapez) na 1200x900 platno
    platno = np.full((900, 1200), 250, dtype=np.uint8)
    cilj = np.float32([[120, 260], [1080, 160], [1120, 660], [80, 760]])
    H = cv2.getPerspectiveTransform(
        np.float32([[0, 0], [Wp, 0], [Wp, Hp], [0, Hp]]), cilj)
    zavito = cv2.warpPerspective(plosca, H, (1200, 900))
    maska = cv2.warpPerspective(np.full((Hp, Wp), 255, np.uint8), H, (1200, 900))
    platno[maska > 0] = zavito[maska > 0]
    pot_slike = str(tmp_path / "persp.png")
    cv2.imwrite(pot_slike, platno)

    pot_pdf = str(tmp_path / "skica.pdf")
    pot2, pod = avtomatska_skica.generiraj(
        pot_slike, pot_pdf,
        referenca=("visina_ograje", 1200.0),
        vogali=[tuple(map(float, t)) for t in cilj])
    m = pod["mere"]
    assert m["visina_ograje"].status == "izmerjeno"
    assert m["dolzina_ograje"].status == "izracunano"   # klikani vogali
    assert abs(m["visina_ograje"].vrednost_mm - 1200.0) < 3.0
    assert abs(m["dolzina_ograje"].vrednost_mm - 2400.0) / 2400.0 < 0.05, \
        m["dolzina_ograje"].oznaka


def test_povecava_lupe():
    """Plan B: lupa vrne povečan izrez s središčem na kliku."""
    import numpy as np
    import avtomatska_skica as ask
    rgb = np.zeros((200, 300, 3), dtype=np.uint8)
    rgb[78:83, 98:103] = 255          # svetla pika okoli (100, 80)
    izrez, (cx, cy) = ask._povecava(rgb, 100, 80, polmer=50)
    assert izrez.shape[0] == 100 and izrez.shape[1] == 100
    assert (cx, cy) == (50, 50)       # center izreza = klik
    assert izrez[cy, cx].max() > 200  # pika je v središču


def test_povecava_na_robu_slike():
    """Lupa deluje tudi ob robu (brez napake, crop ni prazen)."""
    import numpy as np
    import avtomatska_skica as ask
    rgb = np.full((50, 60, 3), 128, dtype=np.uint8)
    izrez, (cx, cy) = ask._povecava(rgb, 0, 0, polmer=40)
    assert izrez.size > 0
    assert cx == 0 and cy == 0


def test_izberi_vogale_programski_vnos():
    """Plan B: programski vnos 4 točk deluje, 3 točke -> jasna napaka."""
    import avtomatska_skica as ask
    tocke = ask.izberi_vogale(
        "ne-obstaja.png", vnosi=[(0, 0), (10, 0), (10, 5), (0, 5)])
    assert tocke == [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
    with pytest.raises(ValueError):
        ask.izberi_vogale("ne-obstaja.png", vnosi=[(0, 0), (1, 0), (1, 1)])


def test_izberi_vogale_interaktivni_tok_z_lupo():
    """Plan B: logika klika (klik/tipka/premik) + lupa.

    4 kliki -> 4 točke; tipka 'u' razveljavi zadnji klik."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import avtomatska_skica as ask

    rgb = np.full((120, 160, 3), 200, dtype=np.uint8)
    fig, ax = plt.subplots()
    lupa_ax = fig.add_axes((0.72, 0.72, 0.26, 0.26))
    inter = ask._KlikVogalov(rgb, ax, lupa_ax, fig)

    for x, y in ((10, 10), (150, 10), (150, 110), (10, 110)):
        inter.premik(x, y)                       # lupa sledi kurzorju
        inter.klik(x, y, button=1)
    assert inter.tocke == [(10.0, 10.0), (150.0, 10.0),
                           (150.0, 110.0), (10.0, 110.0)]
    # 5. klik se NE zabeleži
    inter.klik(50, 50, button=1)
    assert len(inter.tocke) == 4
    # desni klik = razveljavitev
    inter.klik(0, 0, button=3)
    assert len(inter.tocke) == 3
    # tipka 'u' = razveljavitev
    inter.tipka("u")
    assert len(inter.tocke) == 2
    # dopolnitev in Enter zapre figuro
    inter.klik(150, 110, button=1)
    inter.klik(10, 110, button=1)
    inter.tipka("enter")
    assert not plt.fignum_exists(fig.number)
    assert len(inter.tocke) == 4
