# -*- coding: utf-8 -*-
"""Popolnost opravilne vrstice: vsaka funkcija je dosegljiva iz menijev.

Statično križanje: vsak gumb na ekranu/dialogu mora imeti svojo pot tudi
v meniju (razen čistih nastavitev obrazca in notranjih gumbov dialogov).
Realni preizkus: menijsko drevo obeh vmesnikov vsebuje vse funkcije.
"""
import re
import tkinter as tk

import pytest

import terenski_gui

# akcije, ki so po naravi notranje (dialogi) ali nastavitve obrazca
DOVOLJENO_BREZ_MENIJA = {
    "destroy",            # zapiranje oken/dialogov
    "_naprej", "_nazaj",  # koraki čarovnika (korak ima lastne gumbe)
    "_pokazi_kolicine",   # gumb v dialogu Nova vrsta
    "_predogled",         # gumb v dialogu Nova vrsta
    "_zivi_sprememba",    # handler checkbutton nastavitve (obrazec)
}


def _telo_metode(src, ime):
    zac = src.index(f"def {ime}")
    konec = src.index("\n    def ", zac + 10)
    return src[zac:konec]


def test_vse_akcije_imajo_pot_v_meniju():
    """Vsak command=self.X zunaj menija mora biti vezan tudi v meniju."""
    src = open("vmesnik.py", encoding="utf-8").read()
    telo = _telo_metode(src, "_zgradi_meni")
    v_meniju = set(re.findall(r"self(?:\.app)?\.(\w+)", telo))
    zunaj = src.replace(telo, "")
    ukazi = set(re.findall(r"command=self(?:\.app)?\.(\w+)", zunaj))
    manjkajo = ukazi - v_meniju - DOVOLJENO_BREZ_MENIJA
    assert not manjkajo, f"funkcije brez poti v meniju: {sorted(manjkajo)}"


PRICAKOVANO = {
    "Datoteka": ["Odpri projekt…", "Shrani projekt (.yaml)", "Nova revizija…",
                 "NARIŠI RISBO", "Odpri PDF", "Izvozi DXF",
                 "CNC (CSV + G-code)", "Naročilo (kopiraj)", "Ponudba (PDF)",
                 "Izhod"],
    "Urejanje": ["Podatki projekta…", "Razveljavi", "Ponovi",
                 "Dodaj vrata/prehod…", "Uredi izbrana vrata…",
                 "Odstrani izbrana vrata"],
    "Vstavi": ["Sliko v prostor…", "Sliko iz odložišča",
               "Nastavi merilo (2 točki)", "Izmeri v prostoru (2 točki)",
               "Meri s slike", "Predlog mer iz fotografije…",
               "Avtomatska skica", "Fotografija v projekt",
               "Obrni sliko levo", "Obrni sliko desno",
               "Odstrani sliko iz prostora"],
    "Pogled": ["Cel zaslon", "3D predogled", "Osveži živ povzetek",
               "Živo osveževanje povzetka", "Klik na risbo odpre cel zaslon",
               "Vrstica stanja", "Preprosti način", "Preklopi temo"],
    "Orodja": ["Izberi fotografijo…", "Meri s slike (pomožno merjenje)",
               "Avtomatska skica (iz foto)", "Predlog mer (iz foto)",
               "Statični pregled",
               "Statična priloga (PDF)",
               "Nova vrsta (pilot)…", "Primerjaj načrte razreza…",
               "Odpiši ostanke"],
    "Pomoč": ["Čarovnik (voden vnos)", "Preveri posodobitev", "O programu"],
}


def _meni_drevo(u):
    meni = u.nametowidget(u.cget("menu"))
    drevo = {}
    for i in range(meni.index("end") + 1):
        if meni.type(i) != "cascade":
            continue
        pod = meni.nametowidget(meni.entrycget(i, "menu"))
        oznake = [pod.entrycget(j, "label")
                  for j in range(pod.index("end") + 1)
                  if pod.type(j) in ("command", "radiobutton", "checkbutton")]
        drevo[meni.entrycget(i, "label")] = oznake
    return drevo


def test_glavni_meni_je_popoln():
    import vmesnik
    try:
        u = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        drevo = _meni_drevo(u)
        for meni, pricakovane in PRICAKOVANO.items():
            assert meni in drevo, f"manjka meni {meni}"
            for lbl in pricakovane:
                assert lbl in drevo[meni], f"manjka: {meni} → {lbl}"
    finally:
        u.destroy()


def test_terenski_meni_ima_orodja():
    """Vseh 12 orodij tudi v meniju Vstavi — vezana na isti self.orodje."""
    try:
        u = terenski_gui.Urejevalnik()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        u.withdraw()
        u.update_idletasks()
        meni = u.nametowidget(u.cget("menu"))
        v = None
        for i in range(meni.index("end") + 1):
            if meni.type(i) == "cascade" and meni.entrycget(i, "label") == "Vstavi":
                v = meni.nametowidget(meni.entrycget(i, "menu"))
        assert v is not None
        radii = [(v.entrycget(j, "label"), v.entrycget(j, "value"))
                 for j in range(v.index("end") + 1)
                 if v.type(j) == "radiobutton"]
        for oznaka, opis in terenski_gui.ORODJA:
            assert (opis, oznaka) in radii, f"manjka orodje v meniju: {opis}"
        # meniški radiobutton upravlja ISTI vir kot orodna vrstica
        ime_orodja = str(u.orodje)          # Tcl ime spremenljivke
        assert all(str(v.entrycget(j, "variable")) == ime_orodja
                   for j in range(v.index("end") + 1)
                   if v.type(j) == "radiobutton")
        u.orodje.set("crta")               # izbira prek menija = izbira orodja
        assert u.orodje.get() == "crta"
    finally:
        u.destroy()
