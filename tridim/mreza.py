# -*- coding: utf-8 -*-
"""Tridimenzionalna mreža — čista Python geometrija, brez zunanjih knjižnic.

Zakaj brez cadquery/OCP: OCCT je LGPL-2.1 (z izjemo ``OCCT-exception-1.0``),
zato bi bila vgradnja v izvršilno datoteko distribucija LGPL knjižnice;
``casadi`` v cadqueryjevih odvisnostih je LGPL-3.0. Politika projekta
(MIT, samostojni EXE) copyleft komponent ne vgrajuje — glej
``docs/odlocitev-3d-in-ocr.md``.

Zato je 3D sloj sestavljen iz:
- tega modula (mreža, prizme, kontrola zaprtosti),
- ``tridim/izvoz.py`` (STL / OBJ / GLB — sami pisalniki, brez odvisnosti),
- ``tridim/sestav.py`` (sestav ograje iz obstoječih mer ``jedro``),
- ``tridim/step.py`` (neobvezni most do cadqueryja — NI vgrajen v EXE).

Mreža je zaprta (vsak rob pripada natanko dvema trikotnikoma), zato je
prostornino mogoče izračunati z izrekom o divergenci in jo preveriti v
testih namesto zaupanja risalniku.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Trikotnik = tuple[int, int, int]
Tocka = tuple[float, float, float]


def _povrsina2d(poligon: Sequence[tuple[float, float]]) -> float:
    """Predznačena ploščina (pozitivna = nasprotna smer urinega kazalca)."""
    vsota = 0.0
    for i, (x0, y0) in enumerate(poligon):
        x1, y1 = poligon[(i + 1) % len(poligon)]
        vsota += x0 * y1 - x1 * y0
    return vsota / 2.0


def _v_trikotniku(p: tuple[float, float], a: tuple[float, float],
                  b: tuple[float, float], c: tuple[float, float]) -> bool:
    def stran(p0, p1, p2):
        return ((p1[0] - p0[0]) * (p2[1] - p0[1])
                - (p1[1] - p0[1]) * (p2[0] - p0[0]))

    d1, d2, d3 = stran(a, b, p), stran(b, c, p), stran(c, a, p)
    neg = d1 < -1e-12 or d2 < -1e-12 or d3 < -1e-12
    poz = d1 > 1e-12 or d2 > 1e-12 or d3 > 1e-12
    return not (neg and poz)


def trianguliraj(poligon: Sequence[tuple[float, float]]) -> list[Trikotnik]:
    """Triangulacija enostavnega poligona z rezanjem ušes.

    Vrne indekse v podan seznam. Robni primer (vse točke kolinearne ali
    premalo točk) vrne pahljačo — nikoli ne vrne nesmisla tiho.
    """
    n = len(poligon)
    if n < 3:
        return []
    indeksi = list(range(n))
    if _povrsina2d(poligon) < 0:          # normaliziraj na CCW
        indeksi.reverse()

    trikotniki: list[Trikotnik] = []
    zascita = 0
    while len(indeksi) > 3 and zascita < 10 * n:
        zascita += 1
        nasel = False
        for k in range(len(indeksi)):
            i0 = indeksi[k - 1]
            i1 = indeksi[k]
            i2 = indeksi[(k + 1) % len(indeksi)]
            a, b, c = poligon[i0], poligon[i1], poligon[i2]
            kriz = ((b[0] - a[0]) * (c[1] - a[1])
                    - (b[1] - a[1]) * (c[0] - a[0]))
            if kriz <= 1e-12:             # ni konveksen (ali kolinearen)
                continue
            if any(_v_trikotniku(poligon[j], a, b, c)
                   for j in indeksi if j not in (i0, i1, i2)):
                continue
            trikotniki.append((i0, i1, i2))
            indeksi.pop(k)
            nasel = True
            break
        if not nasel:                     # degeneriran poligon — pahljača
            trikotniki = [(indeksi[0], indeksi[i], indeksi[i + 1])
                          for i in range(1, len(indeksi) - 1)]
            indeksi = []
            break
    if len(indeksi) == 3:
        trikotniki.append((indeksi[0], indeksi[1], indeksi[2]))
    return trikotniki


@dataclass(frozen=True)
class Mreza:
    """Zaprta trikotniška mreža v milimetrih (x, y globina, z navzgor)."""

    tocke: tuple[Tocka, ...]
    trikotniki: tuple[Trikotnik, ...]

    # ------------------------------------------------------------ sestavljanje
    def zdruzi(self, *druge: Mreza) -> Mreza:
        tocke = list(self.tocke)
        trikotniki = list(self.trikotniki)
        for druga in druge:
            odmik = len(tocke)
            tocke.extend(druga.tocke)
            trikotniki.extend((a + odmik, b + odmik, c + odmik)
                              for a, b, c in druga.trikotniki)
        return Mreza(tuple(tocke), tuple(trikotniki))

    def premakni(self, dx: float = 0.0, dy: float = 0.0,
                 dz: float = 0.0) -> Mreza:
        return Mreza(tuple((x + dx, y + dy, z + dz) for x, y, z in self.tocke),
                     self.trikotniki)

    # ------------------------------------------------------------- merjenje
    def meje(self) -> tuple[Tocka, Tocka]:
        if not self.tocke:
            raise ValueError("prazna mreža")
        xs = [t[0] for t in self.tocke]
        ys = [t[1] for t in self.tocke]
        zs = [t[2] for t in self.tocke]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def prostornina(self) -> float:
        """Prostornina zaprte mreže (izrek o divergenci); znak = orientacija."""
        vsota = 0.0
        for a, b, c in self.trikotniki:
            p, q, r = self.tocke[a], self.tocke[b], self.tocke[c]
            vsota += (p[0] * (q[1] * r[2] - q[2] * r[1])
                      - p[1] * (q[0] * r[2] - q[2] * r[0])
                      + p[2] * (q[0] * r[1] - q[1] * r[0]))
        return vsota / 6.0

    def povrsina(self) -> float:
        vsota = 0.0
        for a, b, c in self.trikotniki:
            p, q, r = self.tocke[a], self.tocke[b], self.tocke[c]
            u = (q[0] - p[0], q[1] - p[1], q[2] - p[2])
            v = (r[0] - p[0], r[1] - p[1], r[2] - p[2])
            kriz = (u[1] * v[2] - u[2] * v[1],
                    u[2] * v[0] - u[0] * v[2],
                    u[0] * v[1] - u[1] * v[0])
            vsota += math.sqrt(sum(k * k for k in kriz)) / 2.0
        return vsota

    def normale(self) -> list[Tocka]:
        """Enotske normale trikotnikov (ničelna normala = degeneriran trikotnik)."""
        izhod: list[Tocka] = []
        for a, b, c in self.trikotniki:
            p, q, r = self.tocke[a], self.tocke[b], self.tocke[c]
            u = (q[0] - p[0], q[1] - p[1], q[2] - p[2])
            v = (r[0] - p[0], r[1] - p[1], r[2] - p[2])
            kriz = (u[1] * v[2] - u[2] * v[1],
                    u[2] * v[0] - u[0] * v[2],
                    u[0] * v[1] - u[1] * v[0])
            d = math.sqrt(sum(k * k for k in kriz))
            izhod.append((0.0, 0.0, 0.0) if d < 1e-12
                         else (kriz[0] / d, kriz[1] / d, kriz[2] / d))
        return izhod

    def je_zaprta(self) -> bool:
        """Vsak neusmerjeni rob mora imeti natanko dva trikotnika."""
        robovi: dict[tuple[int, int], int] = {}
        for a, b, c in self.trikotniki:
            for i, j in ((a, b), (b, c), (c, a)):
                kljuc = (i, j) if i < j else (j, i)
                robovi[kljuc] = robovi.get(kljuc, 0) + 1
        return all(stevilo == 2 for stevilo in robovi.values())

    def preveri(self) -> list[str]:
        """Vrne seznam težav (prazen seznam = mreža je uporabna)."""
        tezave: list[str] = []
        n = len(self.tocke)
        for tri in self.trikotniki:
            if len(set(tri)) != 3:
                tezave.append(f"degeneriran trikotnik (ponovljena točka): {tri}")
                continue
            if not all(0 <= i < n for i in tri):
                tezave.append(f"indeks zunaj obsega: {tri}")
        if not self.je_zaprta():
            tezave.append("mreža ni zaprta (rob brez para ali z več kot dvema)")
        if self.prostornina() <= 0:
            tezave.append("prostornina ni pozitivna (orientacija navznoter?)")
        return tezave


# ---------------------------------------------------------------- gradniki


def kvader(x0: float, y0: float, z0: float, dx: float, dy: float,
           dz: float) -> Mreza:
    """Zaprt kvader (12 trikotnikov) z izhodiščem v kotu."""
    if dx <= 0 or dy <= 0 or dz <= 0:
        raise ValueError("kvader potrebuje pozitivne dimenzije")
    profil = [(0.0, 0.0), (dx, 0.0), (dx, dy), (0.0, dy)]
    return prizma(profil, dz, os="z", zacetek=0.0).premakni(x0, y0, z0)


def prizma(profil: Sequence[tuple[float, float]], dolzina: float,
           os: str = "z", zacetek: float = 0.0) -> Mreza:
    """Izstisni 2D profil vzdolž osi.

    ``profil`` je v ravnini, pravokotni na os:
    - ``os="z"``: profil (x, y), izstisk navzgor,
    - ``os="x"``: profil (y, z), izstisk po dolžini,
    - ``os="y"``: profil (x, z), izstisk v globino.
    """
    if dolzina <= 0:
        raise ValueError("dolžina prizme mora biti pozitivna")
    if os not in ("x", "y", "z"):
        raise ValueError(f"neznana os: {os!r}")
    poligon = list(profil)
    if _povrsina2d(poligon) < 0:
        poligon.reverse()
    n = len(poligon)

    def tocka(u: float, v: float, w: float) -> Tocka:
        if os == "z":
            return (u, v, w)
        if os == "x":
            return (w, u, v)
        return (u, w, v)

    tocke: list[Tocka] = ([tocka(u, v, zacetek) for u, v in poligon]
                          + [tocka(u, v, zacetek + dolzina) for u, v in poligon])
    trikotniki: list[Trikotnik] = []
    for a, b, c in trianguliraj(poligon):
        trikotniki.append((c, b, a))                       # dno navzven
        trikotniki.append((n + a, n + b, n + c))           # vrh navzven
    for i in range(n):
        j = (i + 1) % n
        trikotniki.append((i, j, n + j))
        trikotniki.append((i, n + j, n + i))

    mreza = Mreza(tuple(tocke), tuple(trikotniki))
    if mreza.prostornina() < 0:
        # Preslikava osi z determinanto -1 (npr. os="y") obrne orientacijo;
        # normala mora gledati navzven, zato trikotnike obrnemo.
        mreza = Mreza(mreza.tocke, tuple((a, c, b)
                                        for a, b, c in mreza.trikotniki))
    return mreza
