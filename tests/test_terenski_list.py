"""Testi za terenski list (issue #9/#10) — model, shranjevanje, PDF/tisk.

Preverjajo se sprejemni kriteriji iz issue #9/#10:
- prazen list brez privzete mreže/okvirja (kriterij 1),
- prostoročne poteze in elementi (kriteriji 2-4),
- round-trip shranjevanja z verzijo/migracijo (kriterij 5),
- PDF A4/A3 v obeh orientacijah, več strani, čitljivost (kriteriji 6-7),
- ročne mere ostanejo označene anotacije (kriterij 8),
- popolna ločenost od proizvodnih izračunov (kriterija 9 in 10).
"""
import os

import pytest
from pypdf import PdfReader

import terenski_list as tl


def _mm(meritev_pts):
    return float(meritev_pts) * 25.4 / 72.0


def _besedilo_strani(pot, indeks=0):
    r = PdfReader(pot)
    return r.pages[indeks].extract_text(), len(r.pages)


# ---------------------------------------------------------------------------
# 1. Prazen list in nastavitve (sprejemni kriterij 1)
# ---------------------------------------------------------------------------

def test_prazen_list_brez_privzetih_okraskov():
    dok = tl.nov_dokument()
    assert dok["elementi"] == []
    nast = dok["nastavitve"]
    assert nast["mreza"] is False
    assert nast["vodila"] is False
    assert nast["okvir"] is False
    assert nast["merilo"] == "prilagodi"
    assert dok["tip"] == "skica"


@pytest.mark.parametrize("stran,orientacija,pričakovano", [
    ("A4", "pokoncno", (210.0, 297.0)),
    ("A4", "lezece", (297.0, 210.0)),
    ("A3", "pokoncno", (297.0, 420.0)),
    ("A3", "lezece", (420.0, 297.0)),
])
def test_dimenzije_strani(stran, orientacija, pričakovano):
    assert tl.dimenzije_strani(stran, orientacija) == pričakovano


def test_neveljavna_stran_ali_orientacija():
    with pytest.raises(ValueError):
        tl.nov_dokument("A5", "pokoncno")
    with pytest.raises(ValueError):
        tl.nov_dokument("A4", "narobe")


# ---------------------------------------------------------------------------
# 2. Elementi in validacija (kriteriji 2-4)
# ---------------------------------------------------------------------------

def test_gradniki_in_validacija():
    dok = tl.nov_dokument()
    dok["elementi"] = [
        tl.poteza([(0, 0), (10, 10), (20, 5)]),
        tl.crta((0, 0), (100, 0)),
        tl.puscica((0, 0), (50, 50)),
        tl.pravokotnik(10, 10, 40, 20),
        tl.elipsa(60, 10, 30, 20),
        tl.besedilo(10, 60, "opomba"),
        tl.mera((0, 80), (120, 80), "120"),
        tl.kocka(150, 10, 25),
        tl.kvader(150, 60, 30, 20, 40),
    ]
    assert tl.preveri_dokument(dok)


def test_poteza_potrebuje_dve_tocki():
    with pytest.raises(ValueError):
        tl.poteza([(0, 0)])


def test_neznana_barva_zavrnjena():
    with pytest.raises(ValueError):
        tl.crta((0, 0), (1, 1), barva="vijolicna")


def test_negativne_dimenzije_zavrnjene():
    with pytest.raises(ValueError):
        tl.pravokotnik(0, 0, -5, 10)
    with pytest.raises(ValueError):
        tl.kvader(0, 0, 10, -1, 10)
    with pytest.raises(ValueError):
        tl.kocka(0, 0, 0)


def test_neznana_vrsta_elementa_zavrnjena():
    """Past iz issue #6: neznana vrsta mora biti napaka, ne tiha veja."""
    dok = tl.nov_dokument()
    dok["elementi"] = [{"tip": "zmaj", "x": 0}]
    with pytest.raises(ValueError, match="neznana vrsta"):
        tl.preveri_dokument(dok)


def test_elementu_manjkajoča_polja():
    dok = tl.nov_dokument()
    dok["elementi"] = [{"tip": "crta", "a": (0, 0)}]
    with pytest.raises(ValueError, match="manjkajo polja"):
        tl.preveri_dokument(dok)


def test_dokument_ni_tipa_skica_zavrnjen():
    with pytest.raises(ValueError):
        tl.preveri_dokument({"tip": "projekt", "verzija": 1})


# ---------------------------------------------------------------------------
# 3. Shranjevanje in migracija (kriterij 5)
# ---------------------------------------------------------------------------

def test_round_trip_shranjevanja(tmp_path):
    dok = tl.nov_dokument("A3", "lezece")
    dok["elementi"] = [tl.poteza([(0, 0), (10, 10)]), tl.mera((0, 0), (50, 0), "50")]
    pot = tmp_path / "skica.yaml"
    tl.shrani(dok, str(pot))
    nalozen = tl.nalozi(str(pot))
    assert nalozen == dok


def test_migracija_manjkajoča_verzija_zavrnjena():
    with pytest.raises(ValueError, match="verzij"):
        tl.migriraj({"tip": "skica", "elementi": []})


def test_migracija_prihodnja_verzija_zavrnjena():
    with pytest.raises(ValueError, match="posodobi program"):
        tl.migriraj({"tip": "skica", "verzija": 99})


def test_nalozi_neveljaven_dokument(tmp_path):
    pot = tmp_path / "slab.yaml"
    pot.write_text("tip: skica\nverzija: 1\nelementi:\n  - tip: zmaj\n",
                   encoding="utf-8")
    with pytest.raises(ValueError):
        tl.nalozi(str(pot))


# ---------------------------------------------------------------------------
# 4. Transformacije in zgodovina (kriteriji 2-4: premikanje, vrtenje, ...)
# ---------------------------------------------------------------------------

def test_premik_elementa():
    el = tl.crta((0, 0), (10, 0))
    premaknjen = tl.premakni(el, 5, -3)
    assert premaknjen["a"] == (5.0, -3.0)
    assert premaknjen["b"] == (15.0, -3.0)
    assert el["a"] == (0.0, 0.0)  # vhod ni spremenjen


def test_vrtenje_pravokotnika_za_90():
    el = tl.pravokotnik(0, 0, 20, 10)
    zavrtet = tl.zavrti(el, 90.0, srediste=(0, 0))
    # vogal (20, 0) po 90° okoli izhodišča → (0, 20)
    tocke = tl._tocke_elementa(zavrtet)
    assert any(abs(x - 0) < 1e-6 and abs(y - 20) < 1e-6 for x, y in tocke)


def test_povecavanje_kvadra():
    el = tl.kvader(0, 0, 10, 20, 30)
    vecji = tl.povecaj(el, 2.0, srediste=(0, 0))
    assert vecji["a"] == 20.0 and vecji["b"] == 40.0 and vecji["c"] == 60.0


def test_povecavanje_negativni_faktor_zavrnjen():
    with pytest.raises(ValueError):
        tl.povecaj(tl.crta((0, 0), (1, 1)), -1.0)


def test_podvoji_zamakne():
    el = tl.besedilo(10, 10, "x")
    dvojnik = tl.podvoji(el, odmik=5.0)
    assert dvojnik["x"] == 15.0 and dvojnik["y"] == 15.0


def test_zgodovina_undo_redo():
    dok = tl.nov_dokument()
    z = tl.Zgodovina(dok)
    dok["elementi"].append(tl.crta((0, 0), (1, 1)))
    z.zapomni(dok)
    dok["elementi"].append(tl.crta((0, 0), (2, 2)))
    z.zapomni(dok)
    assert len(z.trenutno["elementi"]) == 2
    prejsnje = z.razveljavi()
    assert len(prejsnje["elementi"]) == 1
    naslednje = z.ponovi()
    assert len(naslednje["elementi"]) == 2
    assert z.razveljavi() is not None
    assert z.razveljavi() is not None  # nazaj do začetka
    assert z.razveljavi() is None      # več ni zgodovine
    assert z.ponovi() is not None


def test_zadetek_pod_elementom():
    dok = tl.nov_dokument()
    dok["elementi"] = [tl.crta((0, 0), (100, 0)), tl.pravokotnik(200, 200, 50, 50)]
    assert tl.zadetek(dok, 50, 1) == 0
    assert tl.zadetek(dok, 225, 225) == 1
    assert tl.zadetek(dok, 1000, 1000) is None


# ---------------------------------------------------------------------------
# 5. PDF / tisk (kriteriji 6-7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stran,orientacija", [
    ("A4", "pokoncno"), ("A4", "lezece"),
    ("A3", "pokoncno"), ("A3", "lezece"),
])
def test_pdf_mere_strani(tmp_path, stran, orientacija):
    dok = tl.nov_dokument(stran, orientacija)
    dok["elementi"] = [tl.crta((0, 0), (100, 100))]
    pot = str(tmp_path / "stran.pdf")
    st = tl.izvozi_pdf(dok, pot)
    assert st == 1
    r = PdfReader(pot)
    sirina, visina = tl.dimenzije_strani(stran, orientacija)
    assert abs(_mm(r.pages[0].mediabox.width) - sirina) < 1.0
    assert abs(_mm(r.pages[0].mediabox.height) - visina) < 1.0


def test_pdf_prazen_dokument_je_ena_stran(tmp_path):
    pot = str(tmp_path / "prazen.pdf")
    assert tl.izvozi_pdf(tl.nov_dokument(), pot) == 1


def test_pdf_rocna_mera_je_oznacena(tmp_path):
    """Sprejemni kriterij 8: ročna mera mora biti označena kot ročni vnos."""
    dok = tl.nov_dokument()
    dok["elementi"] = [tl.mera((0, 0), (120, 0), "120")]
    pot = str(tmp_path / "mera.pdf")
    tl.izvozi_pdf(dok, pot)
    besedilo, _ = _besedilo_strani(pot)
    # font subset v PDF-ju nadomesti 'č' — preverimo robustno
    assert "(ro" in besedilo and "no)" in besedilo
    assert "120" in besedilo


def test_pdf_vecje_skice_vec_strani(tmp_path):
    """'dejansko' merilo: večja skica se razporedi na več strani (kriterij 6)."""
    dok = tl.nov_dokument("A4", "lezece")
    dok["nastavitve"]["merilo"] = "dejansko"
    dok["elementi"] = [tl.crta((0, 0), (600, 400)),
                       tl.besedilo(300, 200, "sredina")]
    pot = str(tmp_path / "vecje.pdf")
    st = tl.izvozi_pdf(dok, pot)
    assert st > 1
    r = PdfReader(pot)
    assert len(r.pages) == st
    # prilagodi pa spravi isto skico na eno stran
    dok["nastavitve"]["merilo"] = "prilagodi"
    pot2 = str(tmp_path / "prilagojeno.pdf")
    assert tl.izvozi_pdf(dok, pot2) == 1


def test_pdf_vsebina_izpisana(tmp_path):
    """Vsebinsko preverjanje (ne le obstoj datoteke): besedilo je v PDF-ju."""
    dok = tl.nov_dokument()
    dok["elementi"] = [tl.besedilo(20, 20, "Terenski list"), tl.kvader(50, 50, 30, 20, 40)]
    pot = str(tmp_path / "vsebina.pdf")
    tl.izvozi_pdf(dok, pot)
    besedilo, strani = _besedilo_strani(pot)
    assert strani == 1
    norm = "".join(besedilo.split()).lower()
    assert "terenski" in norm and "list" in norm


def test_predogled_enak_izpisu(tmp_path):
    """Predogled uporablja isti izris kot PDF (kriterij 7)."""
    dok = tl.nov_dokument()
    dok["elementi"] = [tl.mera((0, 0), (80, 0), "80")]
    pot_png = str(tmp_path / "predogled.png")
    tl.predogled_png(dok, pot_png)
    assert os.path.getsize(pot_png) > 1000
    # ista shema strani kot za PDF
    sheme = tl._sheme_strani(dok)
    assert len(sheme) == 1


def test_tiskanje_brez_pdf_zavrnjeno():
    with pytest.raises(ValueError):
        tl.tiskaj_pdf("neobstojajoca_pot.pdf")


def test_tiskanje_izven_windows_iskreno_zavrnjeno():
    if os.name == "nt":
        pytest.skip("Windows: sistemski tisk je na voljo (preveri fizično ročno)")
    with pytest.raises(ValueError, match="samo na Windows"):
        tl.tiskaj_pdf(__file__)


# ---------------------------------------------------------------------------
# 6. Ločenost od proizvodnje (kriterija 9 in 10)
# ---------------------------------------------------------------------------

def test_modul_ne_uvaža_proizvodnih_modulov():
    """Ročne mere so anotacije — modul ne sme uvažati risba/vrata/razrez."""
    import ast
    with open(tl.__file__, encoding="utf-8") as f:
        drevo = ast.parse(f.read())
    uvozi = set()
    for vozlisce in ast.walk(drevo):
        if isinstance(vozlisce, ast.Import):
            uvozi.update(a.name.split(".")[0] for a in vozlisce.names)
        elif isinstance(vozlisce, ast.ImportFrom) and vozlisce.module:
            uvozi.add(vozlisce.module.split(".")[0])
    prepovedani = {"risba", "vrata", "razrez", "dxf_izvoz", "merjenje"}
    assert uvozi & prepovedani == set()


def test_rocna_mera_nima_proizvodnih_podatkov():
    """Element mera vsebuje le anotacijo — brez količin/razreza/kosov."""
    el = tl.mera((0, 0), (100, 0))
    assert set(el) == {"tip", "a", "b", "vsebina", "visina", "barva"}
    assert tl.OZNAKA_ROCNO == "(ročno)"


def test_demo_smoke_pdf(tmp_path):
    """CLI --smoke naredi veljaven PDF (uporablja se tudi pri Windows buildu)."""
    pot = str(tmp_path / "smoke.pdf")
    assert tl.main(["--smoke", pot]) == 0
    r = PdfReader(pot)
    assert len(r.pages) >= 1