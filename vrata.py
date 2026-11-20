"""Geometrija in količine za vrata in prehode (issue #3).

Edini vir resnice za geometrijo vrat/prehodov (funkcija ``geometrija_vrat``) —
risba, količine, kosovnica in DXF izvoz porabljajo isti rezultat.

Enote: milimetri. Konvencija koordinat: x od levega roba odprtine, y od tal.

Odločitve (dokumentirane v docs/issue-3-*.md):
- reže: tla = 50, bok = 5 (vsaka stran), med kriloma = 10, nad = 5
- tečaji (P1): h_k <= 1200 -> 2; <= 2100 -> 3; <= 2500 -> 4; sicer 5;
  +1 tečaj, če je krilo širše od 1200 mm; ``skriti`` -> max(3, izračun)
- vijaki (P2): 4/6/8 na tečaj (2/3/4 peresi)
- diagonala (P6): notranje mere, zaokroženo navzgor na 5 mm (``ceil5``)
- ročaj/ključavnica: višina 1050 mm (za krila z višino < 1000 mm: sredina)
- prehod (P7): 2 zaključna stebra + 2 zaključna profila + sidranje M10
"""
from __future__ import annotations

import math
import os

import yaml

# ---------------------------------------------------------------------------
# Katalog sestavnih delov (razširljiv prek ``nalozi_katalog``)
# ---------------------------------------------------------------------------

KATALOG = {
    "tecaj_standard": {"vrsta": "tecaj", "oznaka": "TEČ-STD",
                       "opis": "tečaj s peresom, jeklo, cinkano", "enota": "kos"},
    "tecaj_skrit": {"vrsta": "tecaj", "oznaka": "TEČ-SKR",
                    "opis": "skriti tečaj", "enota": "kos"},
    "zapah": {"vrsta": "zaklep", "oznaka": "ZAP-1", "opis": "zapah", "enota": "kos"},
    "kljucavnica": {"vrsta": "zaklep", "oznaka": "KLJ-1",
                    "opis": "ključavnica z ročajem", "enota": "kos"},
    "cilinder": {"vrsta": "zaklep", "oznaka": "CIL-1", "opis": "cilinder", "enota": "kos"},
    "roc_standard": {"vrsta": "roc", "oznaka": "ROČ-STD", "opis": "standardni ročaj",
                     "enota": "par"},
    "roc_palica": {"vrsta": "roc", "oznaka": "ROČ-PAL", "opis": "palični ročaj",
                   "enota": "par"},
    "talni_zatic": {"vrsta": "pritrdilo", "oznaka": "TAL-ZAT", "opis": "talni zatič",
                    "enota": "kos"},
    "zapiralo": {"vrsta": "okovje", "oznaka": "ZAP-VR", "opis": "zapiralo vrat",
                 "enota": "kos"},
    "povezovalna_plosca": {"vrsta": "pritrjevanje", "oznaka": "PLO-1",
                           "opis": "povezovalna plošča", "enota": "kos"},
    "kotnik": {"vrsta": "pritrjevanje", "oznaka": "KOT-1", "opis": "kotnik",
               "enota": "kos"},
    "vijak_m8x40": {"vrsta": "pritrdilo", "oznaka": "M8x40", "opis": "vijak M8x40",
                    "enota": "kos"},
    "matica_m8": {"vrsta": "pritrdilo", "oznaka": "MAT-M8", "opis": "matica M8",
                  "enota": "kos"},
    "podlozka_m8": {"vrsta": "pritrdilo", "oznaka": "POD-M8", "opis": "podložka M8",
                    "enota": "kos"},
    "zakljucni_steber": {"vrsta": "steber", "oznaka": "ZAK-STE",
                         "opis": "zaključni steber prehoda", "enota": "kos"},
    "zakljucni_profil": {"vrsta": "profil", "oznaka": "ZAK-PRO",
                         "opis": "zaključni profil prehoda", "enota": "kos"},
    "sidro_m10": {"vrsta": "pritrdilo", "oznaka": "SID-M10", "opis": "sidro M10",
                  "enota": "kos"},
}

VRSTE_VRAT = ("enokrilna", "dvokrilna", "pasja", "prehodna")
SMERI = ("levo-navzven", "desno-navzven", "levo-navznoter", "desno-navznoter")

# Privzete reže (mm) — odločitev O-4/O-7 iz poročila pod-agenta.
PRIVZETE_REZE = {"tla": 50.0, "bok": 5.0, "med": 10.0, "zgoraj": 5.0}

# Profilne dimenzije (mm) — okvir vrat in krilo (issue #6, uskladitev
# kosovnice z geometrijo). Model: okvirna stojala stojijo ZNOTRAJ odprtine
# S_o, zato vodoravna veriga vključuje tudi profila okvirja:
#   2·SIRINA_OKVIRJA + r_bok + Σw_k + (n_kril−1)·r_med + r_bok = S_o
# (prej je geometrija štela le 5 mm reže, kosovnica pa je rezala 60 mm
# široka stojala — deli se fizično niso mogli zložiti: 60+990+60 > 1000).
SIRINA_OKVIRJA = 60.0    # širina stojala okvirja (profil 60×40)
SIRINA_STOJALA = 40.0    # širina navpičnega stojala krila
VISINA_LETE = 40.0       # višina vodoravne letve krila

PRIVZETA_VRATA = {
    "tip": "enokrilna",
    "x": 0.0,
    "sirina": 900.0,
    "visina": 2000.0,
    "smer": "desno-navzven",
    "polnilo": "lamelno",
    "tecaji": "avtomatsko",
    "zaklep": "kljuc",
    "roc": "standardni",
    "precke": 0,
    "diagonala": False,
    "reze": None,
}

PRIVZET_PREHOD = {
    "x": 0.0,
    "sirina": 1000.0,
    "visina": 2100.0,
    "zaporni_element": False,
}

CENE_KLJUCI = {
    "tecaj": "tecaj_kos",
    "zapah": "zapah_kos",
    "kljucavnica": "kljucavnica_kos",
    "cilinder": "cilinder_kos",
    "roc": "rocaj_vrata_par",
    "talni_zatic": "talni_zatic_kos",
    "zapiralo": "zapiralo_kos",
    "povezovalna_plosca": "povezovalna_plosca_kos",
    "kotnik": "kotnik_kos",
    "vijak": "vijak_vrata_kos",
    "matica": "matica_kos",
    "podlozka": "podlozka_kos",
    "zakljucni_steber": "zakljucni_steber_kos",
    "zakljucni_profil": "zakljucni_profil_kos",
    "sidro": "sidro_m10_kos",
}


def nalozi_katalog(pot):
    """Naloži razširitev kataloga iz datoteke YAML (varno — brez izvrševanja).

    Oblika datoteke: ``ime: {vrsta, oznaka, opis, enota}``. Vrnjen je nov slovar
    (vhodni ``KATALOG`` se ne spreminja).
    """
    katalog = {k: dict(v) for k, v in KATALOG.items()}
    if pot and os.path.exists(pot):
        with open(pot, "r", encoding="utf-8") as f:
            podatki = yaml.safe_load(f) or {}
        if not isinstance(podatki, dict):
            raise ValueError("katalog mora biti slika (ime -> podatki)")
        for ime, vrednost in podatki.items():
            if not isinstance(vrednost, dict):
                raise ValueError(f"postavka kataloga '{ime}' mora biti slika")
            katalog[str(ime)] = dict(vrednost)
    return katalog


# ---------------------------------------------------------------------------
# Normalizacija
# ---------------------------------------------------------------------------

def _stevilo(vrednost, ime):
    """Pretvori vrednost v float z jasno napako (slog risba.py)."""
    if isinstance(vrednost, bool):
        raise ValueError(f"Polje »{ime}« mora biti število (vpisano: {vrednost!r})")
    if isinstance(vrednost, (int, float)):
        return float(vrednost)
    try:
        return float(str(vrednost).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"Polje »{ime}« mora biti število (vpisano: {vrednost!r})")


def normaliziraj_vrata(vnos):
    """Normalizira slovar vrat; manjkajoča polja dobijo privzete vrednosti."""
    v = dict(PRIVZETA_VRATA)
    if vnos:
        v.update(vnos)
    izhod = dict(v)
    izhod["tip"] = str(v.get("tip") or "").strip().lower()
    izhod["x"] = _stevilo(v["x"], "x (vrata)")
    izhod["sirina"] = _stevilo(v["sirina"], "širina vrat")
    izhod["visina"] = _stevilo(v["visina"], "višina vrat")
    izhod["smer"] = str(v.get("smer") or "").strip().lower()
    izhod["polnilo"] = str(v.get("polnilo") or "").strip().lower()
    izhod["tecaji"] = str(v.get("tecaji") or "avtomatsko").strip().lower()
    izhod["zaklep"] = str(v.get("zaklep") or "kljuc").strip().lower()
    izhod["roc"] = str(v.get("roc") or "standardni").strip().lower()
    izhod["precke"] = int(_stevilo(v.get("precke") or 0, "prečke"))
    izhod["diagonala"] = bool(v.get("diagonala"))
    reze = dict(PRIVZETE_REZE)
    if isinstance(v.get("reze"), dict):
        for k in PRIVZETE_REZE:
            if k in v["reze"] and v["reze"][k] is not None:
                reze[k] = _stevilo(v["reze"][k], f"reža {k}")
    izhod["reze"] = reze
    return izhod


def normaliziraj_prehod(vnos):
    """Normalizira slovar prehoda; manjkajoča polja dobijo privzete vrednosti."""
    v = dict(PRIVZET_PREHOD)
    if vnos:
        v.update(vnos)
    izhod = dict(v)
    izhod["x"] = _stevilo(v["x"], "x (prehod)")
    izhod["sirina"] = _stevilo(v["sirina"], "širina prehoda")
    izhod["visina"] = _stevilo(v["visina"], "višina prehoda")
    izhod["zaporni_element"] = bool(v.get("zaporni_element"))
    return izhod


# ---------------------------------------------------------------------------
# Geometrija — EDINI vir resnice
# ---------------------------------------------------------------------------

def geometrija_vrat(vnos, sirina_odprtine, visina_odprtine):
    """Izračuna celotno geometrijo vrat iz odprtine.

    ``vnos``: slovar (glej ``PRIVZETA_VRATA``), ``sirina_odprtine``/``visina_odprtine``:
    zunanje mere odprtine S_o x H_o (mm). Vrne slovar z vsemi izpeljanimi merami —
    edini vir za risbo, količine, kosovnico in DXF.
    """
    v = normaliziraj_vrata(vnos)
    S_o = float(sirina_odprtine)
    H_o = float(visina_odprtine)
    if S_o <= 0 or H_o <= 0:
        raise ValueError("Mere odprtine morajo biti pozitivne.")

    tip = v["tip"]
    if tip not in VRSTE_VRAT:
        raise ValueError(f"Neznan tip vrat: {tip!r} (dovoljeno: {', '.join(VRSTE_VRAT)})")
    if v["smer"] and v["smer"] not in SMERI:
        raise ValueError(f"Neznana smer odpiranja: {v['smer']!r}")

    r = v["reze"]
    if tip == "prehodna":
        # Prehod brez kril: odprtina = S_o x H_o, zgoraj do polne višine ograje.
        w = S_o
        h = H_o
        n_kril = 0
        sirine_kril = []
        h_k = 0.0
    elif tip == "pasja":
        # Pasja vrata: ničelna reža med kriloma, obe polovici enaki.
        r_med = 0.0
        w = (S_o - 2 * SIRINA_OKVIRJA - 2 * r["bok"] - r_med) / 2.0
        sirine_kril = [w, w]
        n_kril = 2
        h_k = H_o - r["tla"] - r["zgoraj"]
        h = h_k
    else:
        n_kril = 2 if tip == "dvokrilna" else 1
        r_med = r["med"] if n_kril == 2 else 0.0
        # Veriga: 2·okvir + r_bok + w_1 + r_med + w_2 + ... + r_bok = S_o
        w = (S_o - 2 * SIRINA_OKVIRJA - 2 * r["bok"]
             - (n_kril - 1) * r_med) / n_kril
        sirine_kril = [w] * n_kril
        h_k = H_o - r["tla"] - r["zgoraj"]
        h = h_k

    if w <= 0:
        raise ValueError(f"Širina odprtine {S_o} je premajhna za reže in profile okvirja.")
    if tip != "prehodna" and h_k <= 0:
        raise ValueError(f"Višina odprtine {H_o} je premajhna za reže.")
    if tip != "prehodna" and (w <= 2 * SIRINA_STOJALA or h_k <= 2 * VISINA_LETE):
        raise ValueError(
            f"Krilo {w:g}×{h_k:g} mm je premajhno za stojala/letve "
            f"({SIRINA_STOJALA:g}/{VISINA_LETE:g} mm).")

    if tip == "prehodna":
        st_tec = 0
    elif v["tecaji"] in ("0", "brez", "none"):
        st_tec = 0
    else:
        st_tec = _st_tecajev(h_k, w, skriti=(v["tecaji"] == "skriti"))
        if v["tecaji"] not in ("avtomatsko", "skriti"):
            st_tec = int(_stevilo(v["tecaji"], "tečaji"))

    precke = _st_preck(h_k if tip != "prehodna" else H_o, tip)
    vijaki_na_tecaj = {2: 4, 3: 6, 4: 8}.get(st_tec, 8)
    # P6 (issue #6, uskladitev s specifikacijo): diagonala je hipotenuza
    # NOTRANJIH mer krila (med stojali in letvami), zaokrožena na 5 mm.
    diagonala = (math.ceil(math.hypot(w - 2 * SIRINA_STOJALA,
                                      h_k - 2 * VISINA_LETE) / 5.0) * 5.0
                 if v["diagonala"] else 0.0)
    visina_rocaj = 1050.0 if h_k >= 1000.0 else h_k / 2.0
    visina_zaklep = 1050.0 if h_k >= 1000.0 else h_k / 2.0
    if tip == "pasja":
        visina_rocaj = visina_zaklep = h_k / 2.0

    return {
        "tip": tip,
        "odprtina": {"sirina": S_o, "visina": H_o},
        "sirina": v["sirina"],
        "visina": v["visina"],
        "x": v["x"],
        "smer": v["smer"],
        "polnilo": v["polnilo"],
        "n_kril": n_kril,
        "sirine_kril": sirine_kril,
        "h_k": h_k if n_kril else H_o,
        "h": h if n_kril else H_o,
        "reze": dict(r),
        "st_tecajev": st_tec,
        "vijaki_na_tecaj": vijaki_na_tecaj if st_tec else 0,
        "precke": precke,
        "diagonala_dolzina": diagonala,
        "visina_rocaj": visina_rocaj,
        "visina_zaklep": visina_zaklep,
        "zaklep": v["zaklep"],
        "roc": v["roc"],
        "tecaji_skriti": v["tecaji"] == "skriti",
        "sirina_okvirja": SIRINA_OKVIRJA,
    }


def _st_tecajev(h_k, w_k, skriti=False):
    """Pravilo P1 za število tečajev glede na višino krila."""
    if h_k <= 1200:
        n = 2
    elif h_k <= 2100:
        n = 3
    elif h_k <= 2500:
        n = 4
    else:
        n = 5
    if w_k > 1200:
        n += 1
    if skriti:
        n = max(3, n)
    return n


def _st_preck(visina_vrat, tip):
    """Pravilo P5 za število prečk."""
    if tip in ("prehodna",):
        return 0
    n = 2
    if visina_vrat > 2000:
        n += 1
    if visina_vrat > 2800:
        n += 1
    return n


def ceil5(x):
    """Zaokroži navzgor na 5 mm (proizvodni odrez)."""
    return int(math.ceil(float(x) / 5.0) * 5)


def geometrija_prehoda(vnos, sirina_odprtine, visina_odprtine):
    """Geometrija prehoda (odprtina brez kril)."""
    p = normaliziraj_prehod(vnos)
    S_o = float(sirina_odprtine)
    H_o = float(visina_odprtine)
    if S_o <= 0 or H_o <= 0:
        raise ValueError("Mere odprtine morajo biti pozitivne.")
    return {
        "tip": "prehod",
        "x": p["x"],
        "odprtina": {"sirina": S_o, "visina": H_o},
        "sirina": p["sirina"],
        "visina": p["visina"],
        "zaporni_element": p["zaporni_element"],
        "st_zakljucnih_stebrov": 2,
        "st_zakljucnih_profilov": 2,
        "sidro_na_stebro": 2,
    }


def preveri_odprtine(odprtine, sirina_segmenta, visina_ograje):
    """Preveri lege odprtin v segmentu.

    ``odprtine``: [(x, sirina, visina_odprtine, oznaka)]. Vrne seznam napak
    (prazen seznam = veljavno). Pravila: znotraj segmenta, brez prekrivanja.
    """
    napake = []
    prejsnji = None
    for x, w, h_o, oznaka in sorted(odprtine, key=lambda t: t[0]):
        if x < 0:
            napake.append(f"{oznaka}: leva lega {x} je negativna.")
        if x + w > sirina_segmenta + 1e-9:
            napake.append(
                f"{oznaka} sega čez rob segmenta ({x} + {w} > {sirina_segmenta}).")
        if h_o > visina_ograje + 1e-9:
            napake.append(
                f"{oznaka}: višina odprtine {h_o} presega višino ograje {visina_ograje}.")
        if prejsnji is not None:
            px, pw, _, po = prejsnji
            if x < px + pw - 1e-9:
                napake.append(f"{po} in {oznaka} se prekrivata "
                              f"({px}-{px + pw} / {x}-{x + w}).")
        prejsnji = (x, w, h_o, oznaka)
    return napake


# ---------------------------------------------------------------------------
# Količine / kosovnica
# ---------------------------------------------------------------------------

def kosovnica_vrat(g, oznaka="V1"):
    """Kosovnica vrat iz geometrije ``g`` (iz ``geometrija_vrat``).

    Vrne slovar s ključi:
    - ``izdelani``: [(oznaka, dolzina_mm, sirina_mm, kolicina, opis, kljuc_cene)]
    - ``kupljeni``: [(oznaka, kolicina, enota, kljuc_cene, opis)]
    Izdelani kosi gredo v rezalni načrt (``razrezne_skupine``), kupljeni ne.
    """
    tip = g["tip"]
    izdelani = []
    kupljeni = []

    if tip == "prehodna":
        # P7: le zaključni kosi prehoda (prehod brez kril).
        kupljeni.append(("ZAK-STE", 2, "kos", CENE_KLJUCI["zakljucni_steber"],
                         "zaključni steber prehoda"))
        kupljeni.append(("ZAK-PRO", 2, "kos", CENE_KLJUCI["zakljucni_profil"],
                         "zaključni profil prehoda"))
        kupljeni.append(("SID-M10", 4, "kos", CENE_KLJUCI["sidro"],
                         "sidro M10 (2 na steber)"))
        return {"izdelani": izdelani, "kupljeni": kupljeni}

    sirina = g["odprtina"]["sirina"]
    h_k = g["h_k"]
    r = g["reze"]

    # Okvir vrat: 2 stojali + prečke (P5) — mere iz konstant profila.
    stojalo = h_k + r["tla"]
    izdelani.append((f"{oznaka}-1", stojalo, SIRINA_OKVIRJA, 2, "stojalo okvirja", None))
    dolzina_precke_okvir = sirina - 2 * SIRINA_OKVIRJA
    izdelani.append((f"{oznaka}-2", dolzina_precke_okvir, SIRINA_OKVIRJA, 2,
                     "prečka okvirja", None))

    for i, w_k in enumerate(g["sirine_kril"], start=1):
        # Krilo: 2 stojali + 2 vodoravni letvi.
        izdelani.append((f"{oznaka}-{2 + i}", h_k, SIRINA_STOJALA, 2, f"stojalo krila {i}", None))
        letev = w_k - 2 * SIRINA_STOJALA
        izdelani.append((f"{oznaka}-{2 + len(g['sirine_kril']) + i}", letev, VISINA_LETE, 2,
                         f"vodoravna letev krila {i}", None))
        # Prečke krila (P5) in diagonala (P6).
        if g["precke"]:
            izdelani.append((f"{oznaka}-P{i}", letev, 60.0, g["precke"],
                             f"prečka krila {i}", None))
        if g["diagonala_dolzina"]:
            izdelani.append((f"{oznaka}-D{i}", g["diagonala_dolzina"], 60.0, 1,
                             f"diagonala krila {i}", None))

    # Okovje (kupljeno).
    if g["st_tecajev"]:
        ozn_tec = "TEČ-SKR" if g.get("tecaji_skriti") else "TEČ-STD"
        kupljeni.append((ozn_tec, g["st_tecajev"] * max(1, g["n_kril"]), "kos",
                         CENE_KLJUCI["tecaj"], "tečaj"))
        kupljeni.append(("M8x40", g["st_tecajev"] * max(1, g["n_kril"])
                         * g["vijaki_na_tecaj"], "kos", CENE_KLJUCI["vijak"],
                         "vijak M8x40"))
        kupljeni.append(("MAT-M8", g["st_tecajev"] * max(1, g["n_kril"])
                         * g["vijaki_na_tecaj"], "kos", CENE_KLJUCI["matica"],
                         "matica M8"))
        kupljeni.append(("POD-M8", g["st_tecajev"] * max(1, g["n_kril"])
                         * g["vijaki_na_tecaj"], "kos", CENE_KLJUCI["podlozka"],
                         "podložka M8"))
    if g["zaklep"] == "kljuc":
        kupljeni.append(("KLJ-1", 1, "kos", CENE_KLJUCI["kljucavnica"], "ključavnica"))
        kupljeni.append(("CIL-1", 1, "kos", CENE_KLJUCI["cilinder"], "cilinder"))
    elif g["zaklep"] == "brava":
        kupljeni.append(("KLJ-1", 1, "kos", CENE_KLJUCI["kljucavnica"], "ključavnica"))
    elif g["zaklep"] == "zapah":
        kupljeni.append(("ZAP-1", 1, "kos", CENE_KLJUCI["zapah"], "zapah"))
    if g["roc"] != "brez":
        kljuc_roc = (CENE_KLJUCI["roc"] if g["roc"] == "standardni"
                     else CENE_KLJUCI["roc"])
        kupljeni.append(("ROČ-STD" if g["roc"] == "standardni" else "ROČ-PAL",
                         1, "par", kljuc_roc, "ročaj"))
    if tip in ("enokrilna", "dvokrilna"):
        kupljeni.append(("TAL-ZAT", g["n_kril"], "kos", CENE_KLJUCI["talni_zatic"],
                         "talni zatič"))
    return {"izdelani": izdelani, "kupljeni": kupljeni}


def kosovnica_prehoda(g):
    """Kosovnica prehoda (iz ``geometrija_prehoda``)."""
    return {
        "izdelani": [],
        "kupljeni": [
            ("ZAK-STE", g["st_zakljucnih_stebrov"], "kos",
             CENE_KLJUCI["zakljucni_steber"], "zaključni steber prehoda"),
            ("ZAK-PRO", g["st_zakljucnih_profilov"], "kos",
             CENE_KLJUCI["zakljucni_profil"], "zaključni profil prehoda"),
            ("SID-M10", g["st_zakljucnih_stebrov"] * g["sidro_na_stebro"], "kos",
             CENE_KLJUCI["sidro"], "sidro M10"),
        ],
    }


def kosovnica_vrstice(kosovnica):
    """Pretvori kosovnico v ``postavke`` za ``razrez.razrez_podatki`` (5-tuple)."""
    vrstice = []
    for oznaka, dolzina, sirina, kol, opis, _kljuc in kosovnica["izdelani"]:
        vrstice.append((f"Vrata {oznaka} {opis}", float(kol), "mm", None,
                        float(dolzina)))
    return vrstice


def kupljene_vrstice(kosovnica):
    """Kupljene komponente kot ``(naziv, kol, enota, kljuc_cene)`` za količine."""
    return [(f"{opis} ({oznaka})", float(kol), enota, kljuc)
            for oznaka, kol, enota, kljuc, opis in kosovnica["kupljeni"]]


def razrezne_skupine(kosovnica):
    """Izdelane kose razdeli v razrezne skupine za ``razrez.razrez_podatki``.

    Vrne [(oznaka_vira, [(oznaka, dolzina, sirina, barva)])]; debelina kosov je
    enaka debelini profilov (iz cfg), zato se skupine imenujejo po vrstah kosov.
    """
    skupine = {}
    for oznaka, dolzina, sirina, kol, opis, _kljuc in kosovnica["izdelani"]:
        kljuc = f"profil {int(sirina)}x40"
        for _ in range(int(kol)):
            skupine.setdefault(kljuc, []).append(
                (f"{oznaka} {opis}", float(dolzina), float(sirina), "#4a90d9"))
    return list(skupine.items())


def razrezne_skupine_prehoda(kosovnica, visina=2100.0):
    """Razrezne skupine prehoda (P7: zaključni profili se režejo na višino odprtine)."""
    skupine = {}
    for oznaka, kol, enota, _kljuc, opis in kosovnica["kupljeni"]:
        if oznaka == "ZAK-PRO":
            kljuc = "zakljucni profil"
            for _ in range(int(kol)):
                skupine.setdefault(kljuc, []).append(
                    (f"{oznaka} {opis}", float(visina), 60.0, "#7bb369"))
    return list(skupine.items())


# ---------------------------------------------------------------------------
# 2D elementi za risbo in DXF (izpeljani iz iste geometrije)
# ---------------------------------------------------------------------------

def elementi_vrat(g):
    """2D elementi vrat v koordinah odprtine (x od levega roba, y od tal).

    Vrne [(vrsta, podatki, plast)] — risba in DXF izvoz porabljata isti seznam;
    ``plast`` je ciljna DXF plast (POSTS/FRAME/FILL/HARDWARE/OUTLINE/DIMENSIONS).
    """
    el = []
    sirina = g["odprtina"]["sirina"]
    H_o = g["odprtina"]["visina"]
    r = g["reze"]
    if g["tip"] == "prehodna":
        el.append(("kvadrat", (0.0, 0.0, sirina, H_o), "DIMENSIONS"))
        return el

    w = g["sirine_kril"][0]
    ok = g.get("sirina_okvirja", 60.0)
    # Okvir: levo in desno stojalo (znotraj odprtine), spodnja in zgornja prečka.
    el.append(("kvadrat", (0.0, r["tla"], ok, H_o - r["zgoraj"]), "POSTS"))
    el.append(("kvadrat", (sirina - ok, r["tla"], ok,
                           H_o - r["zgoraj"]), "POSTS"))
    el.append(("kvadrat", (ok, r["tla"], sirina - 2 * ok, 40.0), "FRAME"))
    el.append(("kvadrat", (ok, H_o - r["zgoraj"] - 40.0, sirina - 2 * ok,
                           40.0), "FRAME"))
    # Krila: med okvirnimi stojali z režo r_bok.
    x0 = ok + r["bok"]
    for i, w_k in enumerate(g["sirine_kril"]):
        el.append(("kvadrat", (x0, r["tla"] + 20.0, w_k, g["h_k"] - 40.0), "OUTLINE"))
        x0 += w_k + (r["med"] if g["n_kril"] == 2 and i == 0 else 0.0)
    # Prečke in diagonala (P6: diagonala čez NOTRANJE mere krila).
    for i, w_k in enumerate(g["sirine_kril"]):
        xr = ok + r["bok"] + (w_k + r["med"]) * i
        for j in range(g["precke"]):
            y = r["tla"] + g["h_k"] * (j + 1) / (g["precke"] + 1)
            el.append(("kvadrat", (xr + 10.0, y - 20.0, w_k - 20.0, 40.0), "FILL"))
        if g["diagonala_dolzina"]:
            el.append(("crta", (xr + 40.0, r["tla"] + 40.0,
                                xr + w_k - 40.0, r["tla"] + g["h_k"] - 40.0), "FILL"))
    # Tečaji (P1) na levi strani krila.
    n = g["st_tecajev"]
    if n:
        w_k = g["sirine_kril"][0]
        for j in range(n):
            y = r["tla"] + g["h_k"] * (j + 0.5) / n
            el.append(("krog", (ok + r["bok"] + 20.0, y, 12.0), "HARDWARE"))
    # Ročaj in ključavnica (odločitev: višina 1050 mm ali sredina krila).
    el.append(("kvadrat", (sirina - ok - 80.0, g["visina_rocaj"] - 25.0,
                           60.0, 50.0), "HARDWARE"))
    if g["zaklep"] != "brez":
        el.append(("kvadrat", (sirina - ok - 60.0, g["visina_zaklep"] - 150.0,
                               30.0, 100.0), "HARDWARE"))
    return el


def elementi_prehoda(g):
    """2D elementi prehoda (odprtina brez kril)."""
    sirina = g["odprtina"]["sirina"]
    H_o = g["odprtina"]["visina"]
    el = [("kvadrat", (0.0, 0.0, sirina, H_o), "DIMENSIONS")]
    el.append(("kvadrat", (0.0, 0.0, 60.0, H_o), "POSTS"))
    el.append(("kvadrat", (sirina - 60.0, 0.0, 60.0, H_o), "POSTS"))
    return el


# ---------------------------------------------------------------------------
# Pomožno: formatiranje
# ---------------------------------------------------------------------------

def fmt_mm(vrednost):
    """Zapiše mm vrednost kot cele mm (slog risba.fmt)."""
    return f"{int(round(float(vrednost)))}"