# -*- coding: utf-8 -*-
"""Testi urejevalnika terenske skice (Tk) — brez modalnih dialogov.

Urejevalnik je doslej pokrival le meni; tu preizkusimo dejansko vedenje:
risanje vseh orodij, izbiro/premik/radirko, razveljavitev, shranjevanje,
PDF/predogled in pan/zoom. Dialogi so nadomeščeni, dogodki pa so
preprosti objekti z ``x``, ``y``, ``delta`` — tako test ne visi na
uporabnikovem kliku.
"""

from __future__ import annotations

import pathlib
import sys
import tkinter as tk
from types import SimpleNamespace

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import terenski_gui as tg  # noqa: E402
import terenski_list as tl  # noqa: E402


def dogodek(x=0, y=0, delta=0):
    return SimpleNamespace(x=x, y=y, delta=delta)


@pytest.fixture
def urejevalnik():
    zadnja = None
    for _ in range(3):
        try:
            app = tg.Urejevalnik()
            break
        except tk.TclError as e:            # pragma: no cover — okolje
            zadnja = e
    else:                                    # pragma: no cover — okolje
        pytest.skip(f"Tk okolje ni na voljo: {zadnja}")
    app.withdraw()
    app.update_idletasks()
    yield app
    try:
        app.destroy()
    except tk.TclError:
        pass


def _narisi_lik(app, orodje, a=(60, 60), b=(220, 160)):
    app.orodje.set(orodje)
    app._na_pritisk(dogodek(*a))
    app._na_premik(dogodek(*b))
    app._na_oddajo(dogodek(*b))
    return app.dok["elementi"][-1]


def test_zacetno_stanje_in_koordinate(urejevalnik):
    app = urejevalnik
    assert app.dok["elementi"] == []
    assert app.umazano is False
    svet = app._v_svet(100, 200)
    assert app._v_platno(*svet) == pytest.approx((100, 200))
    app._narisi()
    assert len(app.platno.find_all()) > 0


@pytest.mark.parametrize("orodje, tip", [
    ("crta", "crta"), ("puscica", "puscica"), ("pravokotnik", "pravokotnik"),
    ("elipsa", "elipsa"), ("kocka", "kocka"), ("kvader", "kvader"),
])
def test_risanje_likov(urejevalnik, orodje, tip):
    app = urejevalnik
    el = _narisi_lik(app, orodje)
    assert el["tip"] == tip
    assert app.umazano is True
    assert el["barva"] == "crna"


def test_premajhen_premik_ne_ustvari_lika(urejevalnik):
    app = urejevalnik
    app.orodje.set("crta")
    app._na_pritisk(dogodek(100, 100))
    app._na_oddajo(dogodek(100.2, 100.2))
    assert app.dok["elementi"] == []


def test_prostorocna_poteza(urejevalnik):
    app = urejevalnik
    app.orodje.set("prostorocno")
    app._na_pritisk(dogodek(50, 50))
    app._na_premik(dogodek(80, 90))
    app._na_premik(dogodek(120, 140))
    app._na_oddajo(dogodek(120, 140))
    el = app.dok["elementi"][-1]
    assert el["tip"] == "poteza"
    assert len(el["tocke"]) >= 2


def test_besedilo_in_rocna_mera(urejevalnik, monkeypatch):
    app = urejevalnik
    monkeypatch.setattr(tg.simpledialog, "askstring",
                        lambda *a, **k: "nosilec 40×40")
    el = _narisi_lik(app, "besedilo", (40, 40), (45, 45))
    assert el["tip"] == "besedilo" and el["vsebina"] == "nosilec 40×40"

    el = _narisi_lik(app, "mera")
    assert el["tip"] == "mera" and el["vsebina"] == "nosilec 40×40"


def test_izberi_skozi_klik_in_izbris(urejevalnik, monkeypatch):
    app = urejevalnik
    el = _narisi_lik(app, "pravokotnik", (60, 60), (220, 160))
    app.orodje.set("izberi")
    ax, ay = app._v_platno(el["x"] + el["sirina"] / 2,
                           el["y"] + el["visina"] / 2)
    app._na_pritisk(dogodek(ax, ay))
    assert app.izbran == 0
    app._na_oddajo(dogodek(ax, ay))

    app._podvoji()
    assert len(app.dok["elementi"]) == 2
    app._spremeni(1.25)
    assert app.dok["elementi"][app.izbran]["sirina"] > el["sirina"]
    app._izbrisi()
    assert len(app.dok["elementi"]) == 1

    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showinfo",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    app.izbran = None
    app._izbrisi()
    assert sporocila


def test_premik_izbranega(urejevalnik):
    app = urejevalnik
    el = _narisi_lik(app, "pravokotnik", (60, 60), (220, 160))
    app.orodje.set("izberi")
    ax, ay = app._v_platno(el["x"] + 10, el["y"] + 10)
    app._na_pritisk(dogodek(ax, ay))
    assert app.izbran == 0
    app._na_premik(dogodek(ax + 30, ay + 20))
    app._na_oddajo(dogodek(ax + 30, ay + 20))
    premaknjen = app.dok["elementi"][0]
    assert premaknjen["x"] != el["x"]


def test_radirka_odstrani_element(urejevalnik):
    app = urejevalnik
    el = _narisi_lik(app, "elipsa", (60, 60), (200, 160))
    app.orodje.set("radirka")
    ax, ay = app._v_platno(el["x"] + el["sirina"] / 2,
                           el["y"] + el["visina"] / 2)
    app._na_pritisk(dogodek(ax, ay))
    assert app.dok["elementi"] == []


def test_razveljavi_in_ponovi(urejevalnik):
    app = urejevalnik
    _narisi_lik(app, "crta")
    assert len(app.dok["elementi"]) == 1
    app._razveljavi()
    assert app.dok["elementi"] == []
    app._ponovi()
    assert len(app.dok["elementi"]) == 1


def test_zavrti_sliko_opozori(urejevalnik, monkeypatch):
    app = urejevalnik
    el = _narisi_lik(app, "pravokotnik", (60, 60), (200, 160))
    app.izbran = 0
    assert el["tip"] == "pravokotnik"

    def zavrni(*_a, **_k):
        raise ValueError("vrtenje slik ni podprto")

    monkeypatch.setattr(tg.tl, "zavrti", zavrni)
    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showinfo",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    app._zavrti()
    assert sporocila and "slik" in sporocila[0]


def test_nastavitve_se_zapisejo_le_ob_spremembi(urejevalnik):
    app = urejevalnik
    app._nastavitve()
    assert app.umazano is False           # ni spremembe
    app.stran.set("A3")
    app._nastavitve()
    assert app.dok["nastavitve"]["stran"] == "A3"
    assert app.umazano is True
    assert app.zgodovina.razveljavi() is not None


def test_mreza_vodila_okvir_se_izrisejo(urejevalnik):
    app = urejevalnik
    app.dok["nastavitve"].update({"mreza": True, "vodila": True,
                                  "okvir": True})
    app._narisi()
    assert len(app.platno.find_all()) > 10


def test_zoom_in_pan(urejevalnik):
    app = urejevalnik
    zacetna = app.lestvica
    app._na_kolesce(dogodek(delta=120))
    assert app.lestvica > zacetna
    app._na_kolesce(dogodek(delta=-120))
    assert app.lestvica == pytest.approx(zacetna)

    ox, oy = app.ox, app.oy
    app._na_pritisk_premik(dogodek(100, 100))
    app._na_premik_premik(dogodek(140, 130))
    assert app.ox != ox and app.oy != oy


def test_vstavi_sliko_iz_datoteke(urejevalnik, monkeypatch, tmp_path):
    from PIL import Image

    app = urejevalnik
    pot = tmp_path / "foto.png"
    Image.new("RGB", (40, 30), (200, 120, 40)).save(pot)
    monkeypatch.setattr(tg.filedialog, "askopenfilename",
                        lambda **k: str(pot))
    app._vstavi_sliko()
    el = app.dok["elementi"][-1]
    assert el["tip"] == "slika"
    assert app.orodje.get() == "izberi"
    app._narisi()                          # naloži sliko na platno

    monkeypatch.setattr(tg.filedialog, "askopenfilename", lambda **k: "")
    app._vstavi_sliko()
    assert len(app.dok["elementi"]) == 1   # preklic ne doda ničesar


def test_vstavi_napacno_sliko_opozori(urejevalnik, monkeypatch, tmp_path):
    app = urejevalnik
    pot = tmp_path / "ni_slika.png"
    pot.write_text("to ni slika", encoding="utf-8")
    monkeypatch.setattr(tg.filedialog, "askopenfilename",
                        lambda **k: str(pot))
    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showerror",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    app._vstavi_sliko()
    assert sporocila
    assert app.dok["elementi"] == []


def test_shrani_in_odpri(urejevalnik, monkeypatch, tmp_path):
    app = urejevalnik
    _narisi_lik(app, "crta")
    pot = tmp_path / "skica.yaml"
    monkeypatch.setattr(tg.filedialog, "asksaveasfilename",
                        lambda **k: str(pot))
    assert app._shrani() is True           # brez poti -> shrani kot
    assert pot.is_file()
    assert app.umazano is False

    app._nova()
    assert app.dok["elementi"] == []
    monkeypatch.setattr(tg.filedialog, "askopenfilename",
                        lambda **k: str(pot))
    app._odpri()
    assert len(app.dok["elementi"]) == 1
    assert app.pot == str(pot)


def test_odpri_pokvarjeno_datoteko(urejevalnik, monkeypatch, tmp_path):
    app = urejevalnik
    pot = tmp_path / "slabo.yaml"
    pot.write_text("ni: [veljavno", encoding="utf-8")
    monkeypatch.setattr(tg.filedialog, "askopenfilename",
                        lambda **k: str(pot))
    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showerror",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    app.umazano = False
    app._odpri()
    assert sporocila and "odpreti" in sporocila[0]


def test_neshranjene_spremembe_tri_odgovori(urejevalnik, monkeypatch,
                                            tmp_path):
    app = urejevalnik
    assert app._preveri_neshranjeno() is True   # ni umazan

    app.umazano = True
    monkeypatch.setattr(tg.messagebox, "askyesnocancel",
                        lambda *a, **k: None)
    assert app._preveri_neshranjeno() is False  # preklic

    monkeypatch.setattr(tg.messagebox, "askyesnocancel",
                        lambda *a, **k: False)
    assert app._preveri_neshranjeno() is True   # ne shrani

    pot = tmp_path / "shrani.yaml"
    monkeypatch.setattr(tg.filedialog, "asksaveasfilename",
                        lambda **k: str(pot))
    monkeypatch.setattr(tg.messagebox, "askyesnocancel",
                        lambda *a, **k: True)
    assert app._preveri_neshranjeno() is True
    assert pot.is_file()


def test_shranjevanje_napake(urejevalnik, monkeypatch):
    app = urejevalnik
    app.pot = "C:/ne-obstaja/skica.yaml"
    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showerror",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    assert app._shrani() is False
    assert sporocila


def test_pdf_predogled_in_tiskanje(urejevalnik, monkeypatch, tmp_path):
    from PIL import Image

    app = urejevalnik
    _narisi_lik(app, "crta")
    pdf_pot = tmp_path / "skica.pdf"
    monkeypatch.setattr(tg.filedialog, "asksaveasfilename",
                        lambda **k: str(pdf_pot))
    monkeypatch.setattr(tg.tl, "izvozi_pdf", lambda dok, pot: 2)
    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showinfo",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    app._pdf()
    assert sporocila and "2 strani" in sporocila[0]
    assert "PDF:" in app.status.cget("text")

    def naredi_png(_dok, pot):
        Image.new("RGB", (30, 20), (10, 10, 10)).save(pot)
        return pot

    monkeypatch.setattr(tg.tl, "predogled_png", naredi_png)
    app._predogled()

    monkeypatch.setattr(tg.tl, "tiskaj_pdf", lambda pot: None)
    app._tiskaj()
    assert "tisk" in app.status.cget("text")


def test_napake_pri_pdf_in_tiskanju(urejevalnik, monkeypatch, tmp_path):
    app = urejevalnik
    monkeypatch.setattr(tg.filedialog, "asksaveasfilename",
                        lambda **k: str(tmp_path / "x.pdf"))

    def pokvari(*_a, **_k):
        raise OSError("ni pisalnika")

    monkeypatch.setattr(tg.tl, "izvozi_pdf", pokvari)
    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showerror",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    app._pdf()
    app._tiskaj()
    assert len(sporocila) == 2


def test_predogled_napaka(urejevalnik, monkeypatch):
    app = urejevalnik

    def pokvari(*_a, **_k):
        raise RuntimeError("brez risalnika")

    monkeypatch.setattr(tg.tl, "predogled_png", pokvari)
    sporocila = []
    monkeypatch.setattr(tg.messagebox, "showerror",
                        lambda naslov, besedilo, **k: sporocila.append(besedilo))
    app._predogled()
    assert sporocila


def test_narisi_vse_tipe_elementov(urejevalnik):
    app = urejevalnik
    el = tl.pravokotnik(10, 10, 50, 40)
    el["rotacija"] = 30
    app.dok["elementi"] = [
        tl.crta((0, 0), (10, 10)), tl.puscica((0, 0), (10, 10)),
        tl.mera((0, 0), (10, 10), "1200"),
        tl.pravokotnik(10, 10, 50, 40), tl.pravokotnik(10, 10, 50, 40),
        el, tl.elipsa(10, 10, 50, 40),
        tl.besedilo(10, 10, "opomba"),
        tl.kocka(10, 10, 20), tl.kvader(10, 10, 20, 10, 30),
    ]
    app.dok["elementi"][5]["rotacija"] = 45
    app.izbran = 3
    app._narisi()
    assert len(app.platno.find_all()) > 5


def test_narisi_sliko_brez_datoteke(urejevalnik, tmp_path):
    app = urejevalnik
    app.dok["elementi"] = [{"tip": "slika", "x": 10, "y": 10,
                            "sirina": 40, "visina": 30, "rotacija": 0,
                            "pot": str(tmp_path / "ni.png")}]
    app._narisi()
    besedila = [app.platno.itemcget(i, "text")
                for i in app.platno.find_all()
                if app.platno.type(i) == "text"]
    assert any("ni mogoče naložiti" in b for b in besedila)


def test_zapri_brez_sprememb(urejevalnik):
    app = urejevalnik
    app.umazano = False
    app._zapri()
    # po uničenju Tk ne odgovarja več — to je dokaz, da je okno res zaprto
    with pytest.raises(tk.TclError, match="destroyed"):
        app.winfo_exists()
