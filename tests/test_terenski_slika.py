# -*- coding: utf-8 -*-
"""Vstavljanje slik v terenski list (odziv uporabnika: 'slik ne morem vložiti').

Element 'slika' je VGRAJEN v dokument (base64) — YAML je samozadosten.
"""
import base64
import os

import pytest

import terenski_list as tl


@pytest.fixture()
def slika_pot(tmp_path):
    from PIL import Image
    pot = tmp_path / "foto.jpg"
    im = Image.new("RGB", (320, 200), (200, 60, 60))
    im.save(pot, format="JPEG")
    return str(pot)


def test_slika_iz_datoteke_in_nalozi(slika_pot):
    el = tl.slika_iz_datoteke(slika_pot, 10.0, 20.0, sirina=60.0)
    assert el["tip"] == "slika"
    assert el["ime"] == "foto.jpg"
    # razmerje 320:200 -> visina 60 * 200/320 = 37.5
    assert abs(el["visina"] - 37.5) < 1e-9
    img = tl.nalozi_sliko(el)
    assert img is not None and img.size[0] > 0
    # dokument je samozadosten: podatki so base64 v YAML-u
    assert base64.b64decode(el["podatki"])


def test_slika_yaml_roundtrip(slika_pot, tmp_path):
    el = tl.slika_iz_datoteke(slika_pot, 0.0, 0.0, sirina=50.0)
    d = tl.nov_dokument()
    d["elementi"].append(el)
    pot = str(tmp_path / "s.yaml")
    tl.shrani(d, pot)
    d2 = tl.nalozi(pot)
    assert d2["elementi"][0]["tip"] == "slika"
    assert d2["elementi"][0]["podatki"] == el["podatki"]
    assert tl.nalozi_sliko(d2["elementi"][0]) is not None


def test_slika_pdf_izvoz(slika_pot, tmp_path):
    el = tl.slika_iz_datoteke(slika_pot, 20.0, 30.0, sirina=80.0)
    d = tl.nov_dokument()
    d["elementi"].append(el)
    pot = str(tmp_path / "s.pdf")
    tl.izvozi_pdf(d, pot)
    assert os.path.getsize(pot) > 1000
    from pypdf import PdfReader
    r = PdfReader(pot)
    assert len(r.pages) == 1
    # slika je vgrajena kot slikovni objekt XObject
    res = r.pages[0].get("/Resources", {})
    xobj = res.get("/XObject", {})
    assert xobj, "PDF mora vsebovati vgrajeno sliko (Image XObject)"


def test_slika_transformacije_in_zadetek(slika_pot):
    el = tl.slika_iz_datoteke(slika_pot, 0.0, 0.0, sirina=40.0)
    d = tl.nov_dokument()
    d["elementi"].append(el)
    # zadetek znotraj pravokotnika slike
    assert tl.zadetek(d, 20.0, el["visina"] / 2) == 0
    prem = tl.premakni(el, 10.0, 5.0)
    assert prem["x"] == 10.0 and prem["y"] == 5.0
    vel = tl.povecaj(el, 2.0)
    assert abs(vel["sirina"] - 80.0) < 1e-9
    mn = tl.element_meje(el)
    assert mn[2] == pytest.approx(40.0)
    # vrtenje slike DELUJE (odziv uporabnika: zasuk potrebujemo)
    obrn = tl.zavrti(el, 90.0)
    assert abs(obrn["rotacija"] - 90.0) < 1e-9
    # pri 90° se ohišje zavrti — mere se zamenjajo
    mn2 = tl.element_meje(obrn)
    assert mn2[2] - mn2[0] == pytest.approx(el["visina"], abs=0.5)
    assert mn2[3] - mn2[1] == pytest.approx(el["sirina"], abs=0.5)
    # pri 45° je ohišje večje (diag. vsote)
    obrn45 = tl.zavrti(el, 45.0)
    mn3 = tl.element_meje(obrn45)
    assert mn3[2] - mn3[0] > 40.0
    # zasukana slika se pravilno izriše v PDF (brez izjeme, XObject ostane)
    d2 = tl.nov_dokument()
    d2["elementi"].append(obrn45)
    import os as _os
    import tempfile
    from pypdf import PdfReader
    with tempfile.TemporaryDirectory() as td:
        pot = str(_os.path.join(td, "rot.pdf"))
        tl.izvozi_pdf(d2, pot)
        r = PdfReader(pot)
        assert r.pages[0].get("/Resources", {}).get("/XObject", {})


def test_slika_napake(slika_pot, tmp_path):
    with pytest.raises(ValueError):
        tl.slika(0, 0, -5, 10, "abc")          # negativne mere
    with pytest.raises(ValueError):
        tl.slika(0, 0, 5, 10, "")              # brez podatkov
    with pytest.raises(ValueError):
        tl.slika_iz_datoteke(str(tmp_path / "ni.jpg"), 0, 0)   # ne obstaja
    # okvarjeni podatki -> nalozi_sliko vrne None (brez izjeme)
    el = tl.slika(0, 0, 10, 10, "ni-base64!!!")
    assert tl.nalozi_sliko(el) is None
    # PDF z okvarjeno sliko NE pade — nariše nadomestni okvir
    d = tl.nov_dokument()
    d["elementi"].append(el)
    tl.izvozi_pdf(d, str(tmp_path / "napaka.pdf"))
    assert os.path.getsize(str(tmp_path / "napaka.pdf")) > 1000


def test_slika_pomanjsanje_omejeno(slika_pot):
    """Dolga rob slike se zmanjša (YAML ne sme rasti v MB-e)."""
    el = tl.slika_iz_datoteke(slika_pot, 0, 0, sirina=60.0, najvecja_roba=100)
    img = tl.nalozi_sliko(el)
    assert max(img.size) <= 100


def test_slika_v_urejevalniku(slika_pot):
    """Izris slike na platnu urejevalnika (brez Tk -> preskočeno)."""
    import tkinter as tk
    try:
        import terenski_gui as tg
        u = tg.Urejevalnik()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        el = tl.slika_iz_datoteke(slika_pot, 20.0, 20.0, sirina=60.0)
        u.dok["elementi"].append(el)
        u._narisi()                        # brez izjeme, slika narisana
        assert u._tk_slike, "PhotoImage referenca mora obstajati (GC zaščita)"
        # zasukana slika — prav tako brez izjeme, referenca ostane
        u.dok["elementi"][0] = tl.zavrti(el, 30.0)
        u._narisi()
        assert u._tk_slike
    finally:
        u.destroy()


def test_vstavljanje_klik_s_tresljajem(tmp_path):
    """Pravi klik miške ima 2–3 px tresljaja — prej je bil TIHO zavrgel
    (odziv uporabnika: 'se vedno ne morem slik naložiti')."""
    import tkinter as tk
    import tkinter.filedialog as fd
    try:
        import terenski_gui as tg
        u = tg.Urejevalnik()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    from PIL import Image
    pot = str(tmp_path / "s.jpg")
    Image.new("RGB", (100, 80), (10, 10, 10)).save(pot, format="JPEG")
    stara = fd.askopenfilename
    fd.askopenfilename = lambda *a, **k: pot
    try:
        u.update_idletasks()          # okno mora biti izrisano, sicer se
        u.update()                    # vezani dogodki ne sprožijo
        u.orodje.set("slika")
        cx, cy = u._v_platno(100.0, 200.0)
        u.platno.event_generate("<ButtonPress-1>", x=int(cx), y=int(cy))
        u.platno.event_generate("<ButtonRelease-1>", x=int(cx) + 3, y=int(cy) + 2)
        u.update()
        assert len(u.dok["elementi"]) == 1, "klik s tresljajem mora vstaviti sliko"
    finally:
        fd.askopenfilename = stara
        u.destroy()


def test_orodje_slika_takoj_odpre_dialog(tmp_path):
    """Izbira orodja 'Slika' takoj ponudi izbiro datoteke (ne ugibanje klika)."""
    import tkinter as tk
    import tkinter.filedialog as fd
    try:
        import terenski_gui as tg
        u = tg.Urejevalnik()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    from PIL import Image
    pot = str(tmp_path / "s.jpg")
    Image.new("RGB", (60, 40), (10, 10, 10)).save(pot, format="JPEG")
    stara = fd.askopenfilename
    fd.askopenfilename = lambda *a, **k: pot
    try:
        u.orodje.set("slika")
        u._zamenjaj_orodje()
        u.update()
        assert len(u.dok["elementi"]) == 1
        assert u.orodje.get() == "izberi", "po vstavitvi takoj v načinu premikanja"
    finally:
        fd.askopenfilename = stara
        u.destroy()


def test_gumb_vstavi_sliko(tmp_path):
    """Gumb 'Vstavi sliko…' deluje neodvisno od izbranega orodja."""
    import tkinter as tk
    import tkinter.filedialog as fd
    try:
        import terenski_gui as tg
        u = tg.Urejevalnik()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    from PIL import Image
    pot = str(tmp_path / "s.jpg")
    Image.new("RGB", (60, 40), (10, 10, 10)).save(pot, format="JPEG")
    stara = fd.askopenfilename
    fd.askopenfilename = lambda *a, **k: pot
    try:
        u._vstavi_sliko()          # brez koordinat -> sredina strani
        u.update()
        assert len(u.dok["elementi"]) == 1
        import terenski_list as tl2
        s, v = tl2.dimenzije_strani(u.dok["nastavitve"]["stran"],
                                    u.dok["nastavitve"]["orientacija"])
        el = u.dok["elementi"][0]
        sredina_x = el["x"] + el["sirina"] / 2.0
        assert abs(sredina_x - s / 2.0) < 1.0, "slika naj bo sredinjena na strani"
    finally:
        fd.askopenfilename = stara
        u.destroy()
