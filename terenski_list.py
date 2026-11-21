"""Prazen terenski list — prostoročna skica, ročno sestavljanje elementov in tisk A4/A3.

Ločen dokumentni tip (issue #9/#10): začne se s popolnoma praznim listom in NIMA
noble zveze s parametričnim modelom ograje, kosovnicami ali razrezom.

Trda pravila:
- ročno vpisane mere so ANOTACIJE skice (označene "(ročno)"), nikoli potrjene
  proizvodne mere — modul ne uvaža risba/vrata/razrez in ne izvaža količin;
- dokument je ločen tip ("tip": "skica") z lastno verzijo in migracijo;
- PDF se zapiše v ENEM krogu PdfPages (zaščita pred matplotlib pastjo ≥ 3.10.7).

Koordinate elementov so v milimetrih sveta skice (y navzgor). Prikaz na stran
določita "merilo": "prilagodi" (celotna skica na eno stran) ali "dejansko"
(1:1, večje skice se razporedijo na več strani).
"""
from __future__ import annotations

import copy
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import yaml

TIP_DOKUMENTA = "skica"
TRENUTNA_VERZIJA = 1

STRANI = {"A4": (210.0, 297.0), "A3": (297.0, 420.0)}  # mm (pokončno)
ORIENTACIJE = ("pokoncno", "lezece")
MERILA = ("prilagodi", "dejansko")
ROB_MM = 10.0          # tiskovni rob
NOTRANJI_ROB_MM = 0.25  # varnostni rob znotraj tiskovnega polja: poteza na
                        # skrajnem robu skice (npr. tlorisna črta pri ymin)
                        # sicer ob rezanju na rob ostane prepolovljena
MREZA_MM = 10.0        # korak mreže
BARVE = ("crna", "siva", "rdeca", "modra", "zelena")
TOLERANCA_ZADETKA = 6.0  # mm — občutljivost izbire v urejevalniku

# Oznaka, ki mora biti na vsaki ročno vpisani meri (sprejemni kriterij 8).
OZNAKA_ROCNO = "(ročno)"


# ---------------------------------------------------------------------------
# Gradniki elementov (tovarne vratniških slovarjev — enoten zapis v YAML)
# ---------------------------------------------------------------------------

def _preveri_barvo(barva):
    if barva not in BARVE:
        raise ValueError(f"Neznana barva {barva!r} — dovoljene: {', '.join(BARVE)}")
    return barva


def poteza(tocke, barva="crna", sirina=0.5):
    """Prostoročna poteza — polilinija točk [(x, y), ...] v mm."""
    tocke = [(float(x), float(y)) for x, y in tocke]
    if len(tocke) < 2:
        raise ValueError("Poteza potrebuje vsaj 2 točki")
    return {"tip": "poteza", "tocke": tocke,
            "barva": _preveri_barvo(barva), "sirina": float(sirina)}


def crta(a, b, barva="crna", sirina=0.5):
    return {"tip": "crta", "a": (float(a[0]), float(a[1])),
            "b": (float(b[0]), float(b[1])),
            "barva": _preveri_barvo(barva), "sirina": float(sirina)}


def puscica(a, b, barva="crna", sirina=0.5):
    return {"tip": "puscica", "a": (float(a[0]), float(a[1])),
            "b": (float(b[0]), float(b[1])),
            "barva": _preveri_barvo(barva), "sirina": float(sirina)}


def pravokotnik(x, y, sirina, visina, rotacija=0.0, barva="crna", sirina_crte=0.5):
    if sirina <= 0 or visina <= 0:
        raise ValueError("Pravokotnik potrebuje pozitivni širini in višini")
    return {"tip": "pravokotnik", "x": float(x), "y": float(y),
            "sirina": float(sirina), "visina": float(visina),
            "rotacija": float(rotacija),
            "barva": _preveri_barvo(barva), "sirina_crte": float(sirina_crte)}


def elipsa(x, y, sirina, visina, rotacija=0.0, barva="crna", sirina_crte=0.5):
    if sirina <= 0 or visina <= 0:
        raise ValueError("Elipsa potrebuje pozitivni širini in višini")
    return {"tip": "elipsa", "x": float(x), "y": float(y),
            "sirina": float(sirina), "visina": float(visina),
            "rotacija": float(rotacija),
            "barva": _preveri_barvo(barva), "sirina_crte": float(sirina_crte)}


def besedilo(x, y, vsebina, visina=3.5, rotacija=0.0, barva="crna"):
    if not str(vsebina).strip():
        raise ValueError("Besedilo ne sme biti prazno")
    return {"tip": "besedilo", "x": float(x), "y": float(y),
            "vsebina": str(vsebina), "visina": float(visina),
            "rotacija": float(rotacija), "barva": _preveri_barvo(barva)}


def mera(a, b, vsebina=None, visina=3.0, barva="crna"):
    """Ročno vpisana mera — anotacija skice, NE potrjena proizvodna mera.

    Če vsebine ni, se vpiše dolžina odseka, a je vedno označena z OZNAKA_ROCNO.
    """
    dolzina = math.dist(a, b)
    if vsebina is None:
        vsebina = f"{dolzina:.0f} mm"
    return {"tip": "mera", "a": (float(a[0]), float(a[1])),
            "b": (float(b[0]), float(b[1])), "vsebina": str(vsebina),
            "visina": float(visina), "barva": _preveri_barvo(barva)}


def kocka(x, y, a, barva="crna", sirina_crte=0.5):
    """Izometrična kocka z robov a (wireframe)."""
    if a <= 0:
        raise ValueError("Rob kocke mora biti pozitiven")
    return {"tip": "kocka", "x": float(x), "y": float(y), "a": float(a),
            "barva": _preveri_barvo(barva), "sirina_crte": float(sirina_crte)}


def kvader(x, y, a, b, c, barva="crna", sirina_crte=0.5):
    """Izometrični kvader (wireframe) — a širina, b globina, c višina."""
    if a <= 0 or b <= 0 or c <= 0:
        raise ValueError("Dimenzije kvadra morajo biti pozitivne")
    return {"tip": "kvader", "x": float(x), "y": float(y),
            "a": float(a), "b": float(b), "c": float(c),
            "barva": _preveri_barvo(barva), "sirina_crte": float(sirina_crte)}


VRSTE = {
    "poteza": ("tocke", "barva", "sirina"),
    "crta": ("a", "b", "barva", "sirina"),
    "puscica": ("a", "b", "barva", "sirina"),
    "pravokotnik": ("x", "y", "sirina", "visina", "rotacija", "barva", "sirina_crte"),
    "elipsa": ("x", "y", "sirina", "visina", "rotacija", "barva", "sirina_crte"),
    "besedilo": ("x", "y", "vsebina", "visina", "rotacija", "barva"),
    "mera": ("a", "b", "vsebina", "visina", "barva"),
    "kocka": ("x", "y", "a", "barva", "sirina_crte"),
    "kvader": ("x", "y", "a", "b", "c", "barva", "sirina_crte"),
}


# ---------------------------------------------------------------------------
# Dokument
# ---------------------------------------------------------------------------

def nov_dokument(stran="A4", orientacija="pokoncno"):
    """Popolnoma prazen list — brez mreže, okvirja, merila ali predloge."""
    _preveri_stran(stran, orientacija)
    return {
        "tip": TIP_DOKUMENTA,
        "verzija": TRENUTNA_VERZIJA,
        "nastavitve": {
            "stran": stran,
            "orientacija": orientacija,
            "merilo": "prilagodi",
            "mreza": False,
            "vodila": False,
            "okvir": False,
        },
        "elementi": [],
    }


def _preveri_stran(stran, orientacija):
    if stran not in STRANI:
        raise ValueError(f"Neznana stran {stran!r} — dovoljene: {', '.join(STRANI)}")
    if orientacija not in ORIENTACIJE:
        raise ValueError(f"Neznana orientacija {orientacija!r} — dovoljene: "
                         f"{', '.join(ORIENTACIJE)}")


def dimenzije_strani(stran, orientacija):
    """(širina, višina) strani v mm po orientaciji."""
    _preveri_stran(stran, orientacija)
    s, v = STRANI[stran]
    return (v, s) if orientacija == "lezece" else (s, v)


def preveri_dokument(dok):
    """Validacija dokumenta skice — javi ValueError z jasnim sporočilom.

    Neznane vrste elementov so napaka (ne tiho spregledane) — isti vzorec
    zaščite kot pri predlogah iz issue #6.
    """
    if not isinstance(dok, dict):
        raise ValueError("Dokument mora biti slovar")
    if dok.get("tip") != TIP_DOKUMENTA:
        raise ValueError(f"Dokument ni tipa {TIP_DOKUMENTA!r} (tip={dok.get('tip')!r})")
    verzija = dok.get("verzija")
    if not isinstance(verzija, int) or verzija < 1:
        raise ValueError(f"Neveljavna verzija dokumenta: {verzija!r}")
    if verzija > TRENUTNA_VERZIJA:
        raise ValueError(f"Dokument je verzije {verzija}, program podpira do "
                         f"{TRENUTNA_VERZIJA} — posodobi program")
    nast = dok.get("nastavitve")
    if not isinstance(nast, dict):
        raise ValueError("Manjkajo nastavitve dokumenta")
    _preveri_stran(nast.get("stran"), nast.get("orientacija"))
    if nast.get("merilo") not in MERILA:
        raise ValueError(f"Neznano merilo {nast.get('merilo')!r} — dovoljena: "
                         f"{', '.join(MERILA)}")
    elementi = dok.get("elementi")
    if not isinstance(elementi, list):
        raise ValueError("Elementi morajo biti seznam")
    for i, el in enumerate(elementi):
        if not isinstance(el, dict) or "tip" not in el:
            raise ValueError(f"Element {i} nima vrste (tip)")
        if el["tip"] not in VRSTE:
            raise ValueError(f"Element {i}: neznana vrsta {el['tip']!r} — "
                             f"dovoljene: {', '.join(sorted(VRSTE))}")
        manjkajo = [k for k in VRSTE[el["tip"]] if k not in el]
        if manjkajo:
            raise ValueError(f"Element {i} ({el['tip']}): manjkajo polja "
                             f"{', '.join(manjkajo)}")
        if el["tip"] == "poteza" and len(el["tocke"]) < 2:
            raise ValueError(f"Element {i} (poteza): premalo točk")
    return True


def migriraj(dok):
    """Migracijska strategija dokumentov skice (verzija → TRENUTNA_VERZIJA).

    Za zdaj obstaja samo verzija 1; funkcija ostaja razširitvena točka in
    zavrne neznane prihodnje verzije (ne tiho predela). Hkrati normalizira
    obliko koordinat (YAML sezname → pare), da je round-trip zanesljiv.
    """
    if not isinstance(dok, dict):
        raise ValueError("Dokument mora biti slovar")
    verzija = dok.get("verzija")
    if verzija is None:
        raise ValueError("Dokument nima verzije — ni veljaven dokument skice")
    if not isinstance(verzija, int) or verzija < 1:
        raise ValueError(f"Neveljavna verzija dokumenta: {verzija!r}")
    if verzija > TRENUTNA_VERZIJA:
        raise ValueError(f"Dokument je verzije {verzija}, program podpira do "
                         f"{TRENUTNA_VERZIJA} — posodobi program")
    for i, el in enumerate(dok.get("elementi", [])):
        if not isinstance(el, dict):
            continue
        tip = el.get("tip")
        # Normalizacija PO VRSTI elementa in ne po ključih: pri crta/puscica/mera
        # sta "a"/"b" koordinatni par, pri kocka/kvader pa sta "a"/"b" SKALARNE
        # mere (rob/širina) — po ključih bi round-trip kocke/kvadra padel.
        if tip in ("crta", "puscica", "mera"):
            for k in ("a", "b"):
                if k in el:
                    el[k] = _par_tocek(el[k], f"Element {i} ({tip}).{k}")
        elif tip == "poteza" and "tocke" in el:
            try:
                el["tocke"] = [_par_tocek(t, f"Element {i} (poteza).tocke[{j}]")
                               for j, t in enumerate(el["tocke"])]
            except TypeError:   # "tocke" ni ponovljiv (npr. število)
                raise ValueError(f"Element {i} (poteza): tocke morajo biti seznam parov")
    return dok  # verzija 1 je trenutna


def _par_tocek(vrednost, kje):
    """Normaliziraj koordinatni par v (float, float) — sicer jasna ValueError.

    Pri okrnjenem/poškodovanem dokumentu mora biti napaka razumljiva
    (ValueError), ne surovi TypeError/IndexError iz notranjosti.
    """
    try:
        x, y = vrednost
        return (float(x), float(y))
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"{kje}: koordinati morata biti par števil (prejeli: {vrednost!r})") from e


# ---------------------------------------------------------------------------
# Shranjevanje (YAML, varno)
# ---------------------------------------------------------------------------

def shrani(dok, pot):
    preveri_dokument(dok)
    with open(pot, "w", encoding="utf-8") as f:
        yaml.safe_dump(dok, f, allow_unicode=True, sort_keys=False)
    return pot


def nalozi(pot):
    with open(pot, "r", encoding="utf-8") as f:
        dok = yaml.safe_load(f)
    dok = migriraj(dok)
    preveri_dokument(dok)
    return dok


# ---------------------------------------------------------------------------
# Geometrija elementov (za izbiro/premikanje v urejevalniku)
# ---------------------------------------------------------------------------

def _tocke_elementa(el):
    tip = el["tip"]
    if tip == "poteza":
        return list(el["tocke"])
    if tip in ("crta", "puscica", "mera"):
        return [el["a"], el["b"]]
    if tip in ("pravokotnik", "elipsa"):
        x, y, s, v = el["x"], el["y"], el["sirina"], el["visina"]
        kot = math.radians(el.get("rotacija", 0.0))
        cx, cy = x + s / 2.0, y + v / 2.0
        vogali = [(x, y), (x + s, y), (x + s, y + v), (x, y + v)]
        return [(cx + (px - cx) * math.cos(kot) - (py - cy) * math.sin(kot),
                 cy + (px - cx) * math.sin(kot) + (py - cy) * math.cos(kot))
                for px, py in vogali]
    if tip == "besedilo":
        return [(el["x"], el["y"])]
    if tip == "kocka":
        return [(el["x"], el["y"])]
    if tip == "kvader":
        return [(el["x"], el["y"])]
    raise ValueError(f"Neznana vrsta elementa {tip!r}")


def tocke_elipse(el, koraki=64):
    """Točke obrobe elipse (upošteva rotacijo) — za izris kot zasukan poligon.

    Tkinter canvas nima zasukanih ovalov, zato urejevalnik riše elipso prek
    teh točk; matplotlib elipso nariše neposredno. Točke so v mm sveta skice.
    """
    cx = el["x"] + el["sirina"] / 2.0
    cy = el["y"] + el["visina"] / 2.0
    kot = math.radians(el.get("rotacija", 0.0))
    rx, ry = el["sirina"] / 2.0, el["visina"] / 2.0
    tocke = []
    for i in range(koraki):
        t = 2.0 * math.pi * i / koraki
        px, py = rx * math.cos(t), ry * math.sin(t)
        tocke.append((cx + px * math.cos(kot) - py * math.sin(kot),
                      cy + px * math.sin(kot) + py * math.cos(kot)))
    return tocke


def _visina_elementa(el):
    """Približna višina elementa (mm) — za mere/besedila upošteva velikost."""
    tip = el["tip"]
    if tip == "kocka":
        return el["a"] * 1.5
    if tip == "kvader":
        return el["c"] + (el["a"] + el["b"]) * 0.5
    if tip in ("besedilo", "mera"):
        return el["visina"] * 2.0
    return 0.0


def element_meje(el):
    """(xmin, ymin, xmax, ymax) elementa v mm."""
    tocke = _tocke_elementa(el)
    xs = [t[0] for t in tocke]
    ys = [t[1] for t in tocke]
    dod = _visina_elementa(el)
    return (min(xs) - dod, min(ys) - dod, max(xs) + dod, max(ys) + dod)


def meje(dok):
    """Obseg vseh elementov (xmin, ymin, xmax, ymax); None za prazen dokument."""
    if not dok["elementi"]:
        return None
    meje_vseh = [element_meje(el) for el in dok["elementi"]]
    return (min(m[0] for m in meje_vseh), min(m[1] for m in meje_vseh),
            max(m[2] for m in meje_vseh), max(m[3] for m in meje_vseh))


def _oddaljenost_tocke_od_odseka(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    dolzina2 = dx * dx + dy * dy
    if dolzina2 == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / dolzina2))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def zadetek(dok, x, y, toleranca=TOLERANCA_ZADETKA):
    """Indeks elementa pod točko (x, y) ali None — najprej zadnji narisani."""
    najblizji = None
    naj_razdalja = toleranca
    for i, el in enumerate(dok["elementi"]):
        tip = el["tip"]
        if tip == "poteza":
            tocke = el["tocke"]
            razdalje = [_oddaljenost_tocke_od_odseka((x, y), tocke[j], tocke[j + 1])
                        for j in range(len(tocke) - 1)]
            razdalja = min(razdalje)
        elif tip in ("crta", "puscica", "mera"):
            razdalja = _oddaljenost_tocke_od_odseka((x, y), el["a"], el["b"])
        else:
            xmn, ymn, xmx, ymx = element_meje(el)
            if xmn <= x <= xmx and ymn <= y <= ymx:
                razdalja = 0.0
            else:
                razdalja = min(abs(x - xmn), abs(x - xmx), abs(y - ymn), abs(y - ymx))
                if not (xmn - toleranca <= x <= xmx + toleranca
                        and ymn - toleranca <= y <= ymx + toleranca):
                    razdalja = toleranca + 1.0
        if razdalja <= naj_razdalja:
            naj_razdalja = razdalja
            najblizji = i
    return najblizji


# ---------------------------------------------------------------------------
# Transformacije (operacije nad elementi — testne brez GUI)
# ---------------------------------------------------------------------------

def premakni(el, dx, dy):
    """Premakni element za (dx, dy) — vrne NOV element (nepromenjen vnos)."""
    nov = copy.deepcopy(el)
    tip = nov["tip"]
    if tip == "poteza":
        nov["tocke"] = [(x + dx, y + dy) for x, y in nov["tocke"]]
    elif tip in ("crta", "puscica", "mera"):
        nov["a"] = (nov["a"][0] + dx, nov["a"][1] + dy)
        nov["b"] = (nov["b"][0] + dx, nov["b"][1] + dy)
    else:
        nov["x"] += dx
        nov["y"] += dy
    return nov


def _zavrti_tocko(p, srediste, kot):
    cx, cy = srediste
    px, py = p
    return (cx + (px - cx) * math.cos(kot) - (py - cy) * math.sin(kot),
            cy + (px - cx) * math.sin(kot) + (py - cy) * math.cos(kot))


def zavrti(el, kot_stopinje, srediste=None):
    """Zavrti element okoli središča (privzeto središča ohišja)."""
    kot = math.radians(kot_stopinje)
    if srediste is None:
        xmn, ymn, xmx, ymx = element_meje(el)
        srediste = ((xmn + xmx) / 2.0, (ymn + ymx) / 2.0)
    nov = copy.deepcopy(el)
    tip = nov["tip"]
    if tip == "poteza":
        nov["tocke"] = [_zavrti_tocko(t, srediste, kot) for t in nov["tocke"]]
    elif tip in ("crta", "puscica", "mera"):
        nov["a"] = _zavrti_tocko(nov["a"], srediste, kot)
        nov["b"] = _zavrti_tocko(nov["b"], srediste, kot)
    elif tip in ("pravokotnik", "elipsa"):
        # zavrti SREDIŠČE okoli dane točke in dodaj kot — čista rotacija lika
        sredina = (nov["x"] + nov["sirina"] / 2.0, nov["y"] + nov["visina"] / 2.0)
        nova_sredina = _zavrti_tocko(sredina, srediste, kot)
        nov["x"] = nova_sredina[0] - nov["sirina"] / 2.0
        nov["y"] = nova_sredina[1] - nov["visina"] / 2.0
        nov["rotacija"] = nov.get("rotacija", 0.0) + kot_stopinje
    else:
        nov["x"], nov["y"] = _zavrti_tocko((nov["x"], nov["y"]), srediste, kot)
        nov["rotacija"] = nov.get("rotacija", 0.0) + kot_stopinje
    return nov


def povecaj(el, faktor, srediste=None):
    """Povečaj/pomanjšaj element okoli središča (privzeto središče ohišja)."""
    if faktor <= 0:
        raise ValueError("Faktor mora biti pozitiven")
    if srediste is None:
        xmn, ymn, xmx, ymx = element_meje(el)
        srediste = ((xmn + xmx) / 2.0, (ymn + ymx) / 2.0)

    def skaliraj(p):
        return (srediste[0] + (p[0] - srediste[0]) * faktor,
                srediste[1] + (p[1] - srediste[1]) * faktor)

    nov = copy.deepcopy(el)
    tip = nov["tip"]
    if tip == "poteza":
        nov["tocke"] = [skaliraj(t) for t in nov["tocke"]]
        nov["sirina"] *= faktor
    elif tip in ("crta", "puscica"):
        nov["a"] = skaliraj(nov["a"])
        nov["b"] = skaliraj(nov["b"])
        nov["sirina"] *= faktor
    elif tip == "mera":
        nov["a"] = skaliraj(nov["a"])
        nov["b"] = skaliraj(nov["b"])
        nov["visina"] *= faktor
    elif tip in ("pravokotnik", "elipsa"):
        nov["x"], nov["y"] = skaliraj((nov["x"], nov["y"]))
        nov["sirina"] *= faktor
        nov["visina"] *= faktor
    elif tip == "besedilo":
        nov["x"], nov["y"] = skaliraj((nov["x"], nov["y"]))
        nov["visina"] *= faktor
    elif tip == "kocka":
        nov["x"], nov["y"] = skaliraj((nov["x"], nov["y"]))
        nov["a"] *= faktor
    elif tip == "kvader":
        nov["x"], nov["y"] = skaliraj((nov["x"], nov["y"]))
        nov["a"] *= faktor
        nov["b"] *= faktor
        nov["c"] *= faktor
    else:
        raise ValueError(f"Neznana vrsta elementa {tip!r}")
    return nov


def podvoji(el, odmik=10.0):
    """Podvoji element z zamikom (odmik, odmik)."""
    return premakni(el, odmik, odmik)


class Zgodovina:
    """Undo/redo z zgodovino stanj dokumenta (snapshots) — preprosto in zanesljivo."""

    def __init__(self, dok):
        self._stanja = [copy.deepcopy(dok)]
        self._polozaj = 0

    @property
    def trenutno(self):
        return copy.deepcopy(self._stanja[self._polozaj])

    def zapomni(self, dok):
        """Zapomni si novo stanje (po izvedeni spremembi)."""
        self._stanja = self._stanja[:self._polozaj + 1]
        self._stanja.append(copy.deepcopy(dok))
        self._polozaj += 1

    def razveljavi(self):
        if self._polozaj <= 0:
            return None
        self._polozaj -= 1
        return self.trenutno

    def ponovi(self):
        if self._polozaj >= len(self._stanja) - 1:
            return None
        self._polozaj += 1
        return self.trenutno

    @property
    def lahko_razveljavi(self):
        return self._polozaj > 0

    @property
    def lahko_ponovi(self):
        return self._polozaj < len(self._stanja) - 1


# ---------------------------------------------------------------------------
# Risanje / PDF
# ---------------------------------------------------------------------------

BARVE_HEX = {
    "crna": "#000000",
    "siva": "#777777",
    "rdeca": "#b22222",
    "modra": "#1f4e9c",
    "zelena": "#1e7a1e",
}


def _narisi_element(ax, el, merilo_osa):
    barva = BARVE_HEX.get(el.get("barva", "crna"), "#000000")
    tip = el["tip"]
    if tip == "poteza":
        xs = [t[0] for t in el["tocke"]]
        ys = [t[1] for t in el["tocke"]]
        ax.plot(xs, ys, color=barva, linewidth=el["sirina"], solid_joinstyle="round")
    elif tip in ("crta", "puscica"):
        ax.plot([el["a"][0], el["b"][0]], [el["a"][1], el["b"][1]],
                color=barva, linewidth=el["sirina"])
        if tip == "puscica":
            _glava_puscice(ax, el["a"], el["b"], barva, el["sirina"])
    elif tip == "pravokotnik":
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle((el["x"], el["y"]), el["sirina"], el["visina"],
                               angle=el.get("rotacija", 0.0),
                               rotation_point="center",
                               fill=False, edgecolor=barva,
                               linewidth=el["sirina_crte"]))
    elif tip == "elipsa":
        from matplotlib.patches import Ellipse
        ax.add_patch(Ellipse((el["x"] + el["sirina"] / 2.0,
                              el["y"] + el["visina"] / 2.0),
                             el["sirina"], el["visina"],
                             angle=el.get("rotacija", 0.0),
                             fill=False, edgecolor=barva,
                             linewidth=el["sirina_crte"]))
    elif tip == "besedilo":
        ax.text(el["x"], el["y"], el["vsebina"], color=barva,
                fontsize=el["visina"] * merilo_osa * 72.0 / 25.4,
                rotation=el.get("rotacija", 0.0),
                ha="left", va="bottom")
    elif tip == "mera":
        # visina je v mm SVETA — na strani velja visina * merilo_osa (kot pri
        # besedilu); sicer napis pri merilu < 1 odstopa od črte in lahko
        # seže čez rob tiskovnega polja.
        ax.plot([el["a"][0], el["b"][0]], [el["a"][1], el["b"][1]],
                color=barva, linewidth=max(0.15, el["visina"] * merilo_osa / 8.0))
        _glava_puscice(ax, el["b"], el["a"], barva, 0.4)
        _glava_puscice(ax, el["a"], el["b"], barva, 0.4)
        mx = (el["a"][0] + el["b"][0]) / 2.0
        my = (el["a"][1] + el["b"][1]) / 2.0
        ax.text(mx, my + el["visina"] * merilo_osa * 0.8,
                f"{el['vsebina']} {OZNAKA_ROCNO}", color=barva,
                fontsize=el["visina"] * merilo_osa * 72.0 / 25.4,
                ha="center", va="bottom")
    elif tip == "kocka":
        _narisi_kvader(ax, el["x"], el["y"], el["a"], el["a"], el["a"],
                       barva, el["sirina_crte"])
    elif tip == "kvader":
        _narisi_kvader(ax, el["x"], el["y"], el["a"], el["b"], el["c"],
                       barva, el["sirina_crte"])
    else:
        raise ValueError(f"Neznana vrsta elementa {tip!r} — ne morem narisati")


def _glava_puscice(ax, od, proti, barva, sirina):
    dx = proti[0] - od[0]
    dy = proti[1] - od[1]
    dolzina = math.hypot(dx, dy)
    if dolzina == 0:
        return
    velikost = max(1.5, min(6.0, dolzina * 0.12))
    ux, uy = dx / dolzina, dy / dolzina
    px, py = -uy, ux
    ax.fill([od[0], od[0] + ux * velikost + px * velikost / 2.5,
             od[0] + ux * velikost - px * velikost / 2.5],
            [od[1], od[1] + uy * velikost + py * velikost / 2.5,
             od[1] + uy * velikost - py * velikost / 2.5],
            color=barva, linewidth=0)


def tocke_kvader_odseki(x, y, a, b, c):
    """Robovi izometričnega kvadra kot seznam odsekov ((x1, y1), (x2, y2))."""
    kx, ky = 0.866, 0.5  # izometrična projekcija
    vx = (a * kx, a * ky)
    vy = (-b * kx, b * ky)
    p0 = (x, y)
    p1 = (p0[0] + vx[0], p0[1] + vx[1])
    p2 = (p1[0] + vy[0], p1[1] + vy[1])
    p3 = (p0[0] + vy[0], p0[1] + vy[1])
    spodaj = [p0, p1, p2, p3]
    zgoraj = [(px, py + c) for px, py in spodaj]
    odseki = []
    for i in range(4):
        j = (i + 1) % 4
        odseki.append((spodaj[i], spodaj[j]))
        odseki.append((zgoraj[i], zgoraj[j]))
        odseki.append((spodaj[i], zgoraj[i]))
    return odseki


def _narisi_kvader(ax, x, y, a, b, c, barva, sirina_crte):
    """Wireframe izometrični kvader (kocka = a=b=c)."""
    for (p, q) in tocke_kvader_odseki(x, y, a, b, c):
        ax.plot([p[0], q[0]], [p[1], q[1]],
                color=barva, linewidth=sirina_crte)


def _sredisce_strani(nast):
    s, v = dimenzije_strani(nast["stran"], nast["orientacija"])
    return s, v


def _sheme_strani(dok):
    """Seznam (odmik_x, odmik_y, sirina_strani, visina_strani, merilo_osa).

    "prilagodi": ena stran, vsebina raztegnjena/zmanjšana v rob.
    "dejansko": 1:1, vsebina razrezana na ploščice (več strani).
    """
    nast = dok["nastavitve"]
    s, v = _sredisce_strani(nast)
    uporabno = (s - 2 * ROB_MM - 2 * NOTRANJI_ROB_MM,
                v - 2 * ROB_MM - 2 * NOTRANJI_ROB_MM)
    zacetek = ROB_MM + NOTRANJI_ROB_MM
    obseg = meje(dok)
    if obseg is None:
        return [(0.0, 0.0, s, v, 1.0)]
    xmin, ymin, xmax, ymax = obseg
    sirina_vsebine = max(xmax - xmin, 1e-6)
    visina_vsebine = max(ymax - ymin, 1e-6)

    if nast["merilo"] == "prilagodi":
        merilo = min(uporabno[0] / sirina_vsebine, uporabno[1] / visina_vsebine)
        # postavi središče vsebine v središče uporabnega polja
        odmik_x = zacetek + uporabno[0] / 2.0 - (xmin + xmax) / 2.0 * merilo
        odmik_y = zacetek + uporabno[1] / 2.0 - (ymin + ymax) / 2.0 * merilo
        return [(odmik_x, odmik_y, s, v, merilo)]

    # dejansko: 1:1, ploščice čez obseg
    stolpci = max(1, math.ceil(sirina_vsebine / uporabno[0]))
    vrstice = max(1, math.ceil(visina_vsebine / uporabno[1]))
    sheme = []
    for j in range(vrstice):
        for i in range(stolpci):
            odmik_x = zacetek - xmin - i * uporabno[0]
            odmik_y = zacetek - ymin - j * uporabno[1]
            sheme.append((odmik_x, odmik_y, s, v, 1.0))
    return sheme


def _seka_okno(el, okno_x, okno_y):
    """Ali element seka tiskovno polje strani (svetovne meje okna)?"""
    xmn, ymn, xmx, ymx = element_meje(el)
    if el["tip"] == "besedilo":
        # groba ocena širine niza — da besedila po pomoti ne izpustimo,
        # če je sidro zunaj okna, niz pa sega vanj
        w = max(2 * el["visina"], 0.8 * el["visina"] * len(el["vsebina"]))
        xmn, xmx = xmn - w, xmx + w
        ymn, ymx = ymn - w, ymx + w
    return not (xmx < okno_x[0] or xmn > okno_x[1]
                or ymx < okno_y[0] or ymn > okno_y[1])


def narisi_stran(dok, ax, shema):
    """Nariše eno stran skice v dane matplotlib osi."""
    odmik_x, odmik_y, s, v, merilo_osa = shema
    ax.set_xlim(0, s)
    ax.set_ylim(0, v)
    ax.set_aspect("equal")
    ax.axis("off")

    nast = dok["nastavitve"]
    from matplotlib.patches import Rectangle
    if nast.get("okvir"):
        ax.add_patch(Rectangle((5.0, 5.0), s - 10.0, v - 10.0,
                               fill=False, edgecolor="#000000", linewidth=0.7))
    if nast.get("mreza"):
        xs = [x for x in frange(0, s, MREZA_MM)]
        ys = [y for y in frange(0, v, MREZA_MM)]
        for x in xs:
            ax.plot([x, x], [0, v], color="#dddddd", linewidth=0.2)
        for y in ys:
            ax.plot([0, s], [y, y], color="#dddddd", linewidth=0.2)
    if nast.get("vodila"):
        ax.plot([s / 2, s / 2], [0, v], color="#99bbdd", linewidth=0.3,
                linestyle="--")
        ax.plot([0, s], [v / 2, v / 2], color="#99bbdd", linewidth=0.3,
                linestyle="--")

    # vsebina: svetovne koordinate → stran prek odmika in merila.
    # Tiskovno polje (rob ROB_MM) je MEJA risanja: brez rezanja pri merilu
    # "dejansko" vsebina sosednjih ploščic uhaja v 10 mm rob in se med
    # stranmi podvaja. Elementi, ki polja sploh ne sekajo, se ne rišejo.
    # okno preskoka je za 1 mm večje od tiskovnega polja: element, ki le
    # rahlo seka rob, naj bo vseeno narisani (prerez naredi rob_izreza)
    okno_x = ((ROB_MM - 1.0 - odmik_x) / merilo_osa,
              (s - ROB_MM + 1.0 - odmik_x) / merilo_osa)
    okno_y = ((ROB_MM - 1.0 - odmik_y) / merilo_osa,
              (v - ROB_MM + 1.0 - odmik_y) / merilo_osa)
    rob_izreza = Rectangle((ROB_MM, ROB_MM), s - 2 * ROB_MM, v - 2 * ROB_MM,
                           transform=ax.transData, fill=False)
    for el in dok["elementi"]:
        if not _seka_okno(el, okno_x, okno_y):
            continue
        preslikan = _preslikaj(el, odmik_x, odmik_y, merilo_osa)
        prej = set(ax.get_children())
        _narisi_element(ax, preslikan, merilo_osa)
        for umetnik in ax.get_children():
            if umetnik not in prej:
                umetnik.set_clip_path(rob_izreza)


def frange(zacetek, konec, korak):
    n = int((konec - zacetek) / korak) + 1
    for i in range(n):
        yield zacetek + i * korak


def _preslikaj(el, odmik_x, odmik_y, merilo_osa):
    """Linearna preslikava sveta na stran: p → p*merilo + odmik."""
    nov = copy.deepcopy(el)
    tip = nov["tip"]

    def t(p):
        return (p[0] * merilo_osa + odmik_x, p[1] * merilo_osa + odmik_y)

    if tip == "poteza":
        nov["tocke"] = [t(p) for p in nov["tocke"]]
        nov["sirina"] = max(0.15, nov["sirina"] * merilo_osa)
    elif tip in ("crta", "puscica"):
        nov["a"] = t(nov["a"])
        nov["b"] = t(nov["b"])
        nov["sirina"] = max(0.15, nov["sirina"] * merilo_osa)
    elif tip == "mera":
        nov["a"] = t(nov["a"])
        nov["b"] = t(nov["b"])
    elif tip in ("pravokotnik", "elipsa"):
        nov["x"], nov["y"] = t((nov["x"], nov["y"]))
        nov["sirina"] *= merilo_osa
        nov["visina"] *= merilo_osa
        nov["sirina_crte"] = max(0.15, nov["sirina_crte"] * merilo_osa)
    elif tip == "besedilo":
        nov["x"], nov["y"] = t((nov["x"], nov["y"]))
    elif tip == "kocka":
        nov["x"], nov["y"] = t((nov["x"], nov["y"]))
        nov["a"] *= merilo_osa
        nov["sirina_crte"] = max(0.15, nov["sirina_crte"] * merilo_osa)
    elif tip == "kvader":
        nov["x"], nov["y"] = t((nov["x"], nov["y"]))
        nov["a"] *= merilo_osa
        nov["b"] *= merilo_osa
        nov["c"] *= merilo_osa
        nov["sirina_crte"] = max(0.15, nov["sirina_crte"] * merilo_osa)
    else:
        raise ValueError(f"Neznana vrsta elementa {tip!r}")
    return nov


def izvozi_pdf(dok, pot):
    """Izvozi skico v PDF (A4/A3, obe orientaciji, več strani po potrebi).

    Vse strani se zapišejo v ENEM krogu PdfPages — brez savefig po zaprtju
    (matplotlib ≥ 3.10.7 bi sicer datoteko tiho prepisal v 0 B).
    Vrne število strani.
    """
    preveri_dokument(dok)
    nast = dok["nastavitve"]
    s, v = _sredisce_strani(nast)
    sheme = _sheme_strani(dok)
    figsize = (s / 25.4, v / 25.4)
    with PdfPages(pot) as pdf:
        for shema in sheme:
            fig = plt.figure(figsize=figsize)
            ax = fig.add_axes([0, 0, 1, 1])
            narisi_stran(dok, ax, shema)
            pdf.savefig(fig)
            plt.close(fig)
        metapodatki = pdf.infodict()
        metapodatki["Title"] = "Terenski list — skica"
        metapodatki["Creator"] = "tehnicna-risba (terenski_list)"
    return len(sheme)


def predogled_png(dok, pot, stran_indeks=0):
    """PNG predogled strani (isti izris kot PDF — predogled ustreza izpisu)."""
    preveri_dokument(dok)
    nast = dok["nastavitve"]
    s, v = _sredisce_strani(nast)
    sheme = _sheme_strani(dok)
    if not 0 <= stran_indeks < len(sheme):
        raise ValueError(f"Stran {stran_indeks} ne obstaja (skica ima {len(sheme)} strani)")
    fig = plt.figure(figsize=(s / 25.4, v / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    narisi_stran(dok, ax, sheme[stran_indeks])
    fig.savefig(pot, dpi=150)
    plt.close(fig)
    return pot


def tiskaj_pdf(pot):
    """Sistemski tisk PDF (Windows: os.startfile(..., "print")).

    Vrne True ob oddaji v sistemski tiskalniški red. Dejanski fizični izpis
    je odvisen od tiskalnika — preveriti ročno (testni fizični izpis).
    """
    if not os.path.exists(pot):
        raise ValueError(f"PDF ne obstaja: {pot}")
    if os.name != "nt":
        raise ValueError("Sistemski tisk je podprt samo na Windows; "
                         "uporabi izvoz PDF in tisk iz bralnika")
    os.startfile(pot, "print")
    return True


# ---------------------------------------------------------------------------
# CLI (demo/smoke — tudi za preverjanje paketa Windows)
# ---------------------------------------------------------------------------

def _demo_dokument():
    dok = nov_dokument("A4", "lezece")
    dok["elementi"] = [
        poteza([(20, 20), (40, 45), (55, 30), (80, 60), (100, 40)], sirina=0.7),
        crta((20, 100), (180, 100)),
        puscica((20, 120), (180, 130)),
        pravokotnik(30, 150, 60, 40),
        elipsa(110, 150, 60, 40),
        besedilo(30, 210, "Terenski list — demo"),
        mera((30, 235), (150, 235), "120"),
        kocka(200, 30, 30),
        kvader(200, 100, 40, 25, 35),
    ]
    return dok


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="terenski_list",
                                description="Prazen terenski list — skica in tisk")
    p.add_argument("--smoke", metavar="PDF",
                   help="iz demo skice izvozi PDF in preveri strani (smoke)")
    p.add_argument("--gui", action="store_true", help="odpri urejevalnik skice")
    args = p.parse_args(argv)
    if args.smoke:
        dok = _demo_dokument()
        st = izvozi_pdf(dok, args.smoke)
        print(f"OK: {args.smoke} ({st} strani)")
        return 0
    if args.gui:
        import terenski_gui
        terenski_gui.zazeni()
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())