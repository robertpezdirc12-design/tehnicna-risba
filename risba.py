#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
risba.py — generator profesionalnih tehničnih risb (PDF A3) iz mer.

Uporaba:
    python risba.py                  -> vprašanja v terminalu
    python risba.py projekt.yaml     -> iz konfiguracijske datoteke
    python risba.py projekt.yaml -o BO-002.pdf

Predloge: "ograda" (balkonska ograja iz lamel). Nove predloge se dodajo
v slovar PREDLOGE spodaj.
"""

import argparse
import datetime
import math
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import yaml
from matplotlib.patches import Circle, Polygon, Rectangle

# ---------------------------------------------------------------- konstante
A3_W, A3_H = 420.0, 297.0
CRNA = "#000000"
BARVA_OZN = "#1f2a3a"   # temne oznake pogledov / naslovi tabel
BARVA_LAMEL = "#3e4a5e"  # privzeta barva lamel (temen antracit z modrim tonom)
LW_THICK = 1.4          # debele črte (robovi, zgradba)
LW_THIN = 0.7           # tanke črte (kote, šrafura)
FS_DIM = 9              # besedilo kot

C30 = math.cos(math.radians(30))


def odsteni(hexbarva, faktor):
    """Osvetli (faktor > 1) ali potemni (faktor < 1) barvo v zapisu #rrggbb."""
    h = hexbarva.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    f = lambda c: max(0, min(255, int(c * faktor)))
    return f"#{f(r):02x}{f(g):02x}{f(b):02x}"


# Poimenovane barve desek (približki — natančni odtenek vedno po vzorcu
# proizvajalca, WoodCore WPC ne deluje po sistemu RAL)
WPC_BARVE = {
    "Antracit": "#3e4a5e",
    "RAL 7016 (prašno barvanje)": "#383e42",
    "Siva": "#8d939c",
    "Teak": "#a9764f",
    "Rustic Oak": "#9c6b43",
    "Rustic Walnut": "#6e4a33",
    "Kava": "#5d4433",
    "Bež": "#c3b394",
}


def barva_hex(vrednost):
    """Prevede ime barve (WPC_BARVE) ali #hex v #rrggbb."""
    if not vrednost:
        return BARVA_LAMEL
    vrednost = str(vrednost).strip()
    if vrednost.startswith("#"):
        return vrednost
    return WPC_BARVE.get(vrednost, BARVA_LAMEL)

PREDLOGE = {}  # izpolnjeno spodaj


def fmt(v):
    """Število brez odvečnih decimalk (2500.0 -> 2500, 47.5 -> 47.5)."""
    return f"{v:g}"


# ---------------------------------------------------------------- risalni motor
def nov_list():
    """Prazna A3 krajinska stran; koordinate v mm (izvor spodaj levo)."""
    fig = plt.figure(figsize=(A3_W / 25.4, A3_H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A3_W)
    ax.set_ylim(0, A3_H)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def crta(ax, x0, y0, x1, y1, lw=LW_THIN, z=4, stil="-"):
    ax.plot([x0, x1], [y0, y1], color=CRNA, lw=lw, zorder=z, linestyle=stil)


def pravokotnik(ax, x, y, w, h, fill=None, lw=LW_THICK, z=3, ec=CRNA):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=ec,
                           lw=lw, zorder=z))


def sachiranje(ax, x0, y0, x1, y1, razmak=2.6):
    """Šrafiranje zidu (diagonale 45°)."""
    w, h = x1 - x0, y1 - y0
    rect = Rectangle((x0, y0), w, h, facecolor="none", edgecolor="none")
    ax.add_patch(rect)
    for i in range(int((w + h) / razmak) + 2):
        xs = x0 + i * razmak - h
        ln, = ax.plot([xs, xs + h], [y0, y1], color=CRNA, lw=0.55, zorder=1)
        ln.set_clip_path(rect)


def puscica(ax, x, y, dx, dy, vel=2.4):
    """Polna puščica; konica v (x, y), smer (dx, dy)."""
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    w = 0.75
    ax.add_patch(Polygon(
        [(x, y),
         (x - ux * vel + px * w, y - uy * vel + py * w),
         (x - ux * vel - px * w, y - uy * vel - py * w)],
        closed=True, facecolor=CRNA, edgecolor="none", zorder=5))


def dim_h(ax, x0, x1, y, e0=None, e1=None, besedilo=None, fs=FS_DIM):
    """Horizontalna kotirna črta na višini y; e0/e1 = robovi geometrije."""
    if x0 > x1:
        x0, x1, e0, e1 = x1, x0, e1, e0
    for xe, e in ((x0, e0), (x1, e1)):
        if e is not None:
            d = 1 if y > e else -1
            crta(ax, xe, e + 0.8 * d, xe, y + 1.2 * d, lw=0.6)
    crta(ax, x0, y, x1, y, lw=0.6)
    raz = abs(x1 - x0)
    if raz < 6:  # kratka kota — puščici od zunaj
        crta(ax, x0 - 5, y, x1 + 5, y, lw=0.6)
        puscica(ax, x0, y, 1, 0)
        puscica(ax, x1, y, -1, 0)
        ax.text(x1 + 1.6, y, besedilo, ha="left", va="center", fontsize=fs)
    else:
        puscica(ax, x0, y, -1, 0)
        puscica(ax, x1, y, 1, 0)
        ax.text((x0 + x1) / 2, y + 0.8, besedilo, ha="center", va="bottom",
                fontsize=fs)


def dim_v(ax, y0, y1, x, e0=None, e1=None, besedilo=None, fs=FS_DIM):
    """Vertikalna kotirna črta na x; besedilo se bere od spodaj navzgor."""
    if y0 > y1:
        y0, y1, e0, e1 = y1, y0, e1, e0
    for ye, e in ((y0, e0), (y1, e1)):
        if e is not None:
            d = 1 if x > e else -1
            crta(ax, e + 0.8 * d, ye, x + 1.2 * d, ye, lw=0.6)
    crta(ax, x, y0, x, y1, lw=0.6)
    raz = abs(y1 - y0)
    if raz < 6:  # kratka kota — puščici od zunaj, besedilo horizontalno
        crta(ax, x, y0 - 5, x, y1 + 5, lw=0.6)
        puscica(ax, x, y0, 0, 1)
        puscica(ax, x, y1, 0, -1)
        ax.text(x + 1.6, (y0 + y1) / 2, besedilo, ha="left", va="center",
                fontsize=fs)
    else:
        puscica(ax, x, y0, 0, -1)
        puscica(ax, x, y1, 0, 1)
        ax.text(x - 0.9, (y0 + y1) / 2, besedilo, rotation=90, ha="center",
                va="center", fontsize=fs)


def ozna_st(ax, px, py, tx, ty, stevilka, r=4.0):
    """Balonč s številko kosa (px,py = točka na kosu, tx,ty = balonč)."""
    crta(ax, px, py, tx, ty, lw=0.65)
    ax.plot([px], [py], marker="o", ms=1.8, color=CRNA, zorder=5)
    ax.add_patch(Circle((tx, ty), r, facecolor="white", edgecolor=CRNA,
                        lw=1.0, zorder=6))
    ax.text(tx, ty, str(stevilka), ha="center", va="center", fontsize=9.5,
            zorder=7)


def oznaka(ax, x, y, besedilo):
    """Temna oznaka pogleda z belim besedilom (y = zgornji rob)."""
    w = 6 + len(besedilo) * 2.3
    pravokotnik(ax, x, y - 6, w, 6, fill=BARVA_OZN, lw=0, z=4)
    ax.text(x + w / 2, y - 3, besedilo, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color="white", zorder=5)
    return w


def tla(ax, x0, x1, y):
    """Talna črta s šrafiranimi crtami pod njo."""
    crta(ax, x0, y, x1, y, lw=1.0)
    for x in np.arange(x0, x1, 2.2):
        crta(ax, x, y, x - 1.5, y - 1.5, lw=0.5)


class Pogled:
    """Pretvorba realnih mm v mm papirja. x desno, z NAVZGOR od tal."""

    def __init__(self, ax, x0, y_tla, s):
        self.ax, self.x0, self.y_tla, self.s = ax, x0, y_tla, s

    def X(self, xr):
        return self.x0 + xr * self.s

    def Y(self, zr):
        return self.y_tla + zr * self.s

    def kocka(self, x0r, z0r, x1r, z1r, fill=None, lw=LW_THICK):
        pravokotnik(self.ax, self.X(x0r), self.Y(z0r),
                    (x1r - x0r) * self.s, (z1r - z0r) * self.s,
                    fill=fill, lw=lw)


# ---------------------------------------------------------------- izometrija
def izo_tocka(x, y, z, f):
    return ((x - y) * C30 * f, ((x + y) * 0.5 + z) * f)


def izo_kocka(ax, x, y, z, dx, dy, dz, f, ox, oy, barve):
    def P(xr, yr, zr):
        px, py = izo_tocka(xr, yr, zr, f)
        return (ox + px, oy + py)

    zgornja = [P(x, y, z + dz), P(x + dx, y, z + dz),
               P(x + dx, y + dy, z + dz), P(x, y + dy, z + dz)]
    sprednja = [P(x, y, z), P(x + dx, y, z),
                P(x + dx, y, z + dz), P(x, y, z + dz)]
    leva = [P(x, y, z), P(x, y + dy, z),
            P(x, y + dy, z + dz), P(x, y, z + dz)]
    for pts, barva in zip((sprednja, leva, zgornja), barve):
        ax.add_patch(Polygon(pts, closed=True, facecolor=barva,
                             edgecolor=CRNA, lw=0.6, zorder=3))


# ---------------------------------------------------------------- tabele/blokovi
def tabela(ax, x0, y_top, sirine, vh, vrste, naslov=None, fs=8.5):
    y = y_top
    skupna = sum(sirine)
    if naslov:
        pravokotnik(ax, x0, y - (vh + 1.5), skupna, vh + 1.5,
                    fill=BARVA_OZN, lw=0)
        ax.text(x0 + skupna / 2, y - (vh + 1.5) / 2, naslov, ha="center",
                va="center", fontsize=fs + 2, fontweight="bold", color="white")
        y -= vh + 1.5
    for ri, vrsta in enumerate(vrste):
        bold = ri == 0
        fill = "#e6e6e6" if bold else ("white" if ri % 2 else "#f4f4f4")
        x = x0
        for ci, celica in enumerate(vrsta):
            w = sirine[ci]
            pravokotnik(ax, x, y - vh, w, vh, fill=fill, lw=0.7)
            ax.text(x + w / 2, y - vh / 2, str(celica), ha="center",
                    va="center", fontsize=fs,
                    fontweight="bold" if bold else "normal")
            x += w
        y -= vh
    return y


def naslovni_blok(ax, polja):
    x0, y0, x1, y1 = 6, 7, 414, 25
    pravokotnik(ax, x0, y0, x1 - x0, y1 - y0, fill="white", lw=1.4)
    delitve = [
        ("PROJEKT", polja["ime"], 0.36, 14),
        ("MERILO", polja["merilo"], 0.12, 10.5),
        ("FORMAT", polja["format"], 0.10, 10.5),
        ("DATUM", polja["datum"], 0.13, 10.5),
        ("IZDELAL", polja["izdelal"], 0.15, 10.5),
        ("RISBA ŠT.", polja["risba_st"], 0.14, 13),
    ]
    x = x0
    for i, (ozn, vred, frak, fs) in enumerate(delitve):
        w = (x1 - x0) * frak
        if i > 0:
            crta(ax, x, y0, x, y1, lw=0.9)
        ax.text(x + 2, y1 - 4.2, ozn, fontsize=6.5, color="#555555",
                ha="left", va="center")
        ax.text(x + 2, y0 + (y1 - y0) / 2 - 2.2, vred, fontsize=fs,
                fontweight="bold", ha="left", va="center")
        x += w


def opombe_blok(ax, x0, y_top, sirina, opombe,
                naslov_t="TEHNIČNI PODATKI IN OPOMBE"):
    vrstice = []
    for i, o in enumerate(opombe, 1):
        vrstice.extend(textwrap.wrap(f"{i}. {o}", width=86) or [f"{i}."])
    visina = 8.5 + len(vrstice) * 3.9 + 2
    pravokotnik(ax, x0, y_top - visina, sirina, visina, fill="white", lw=0.8)
    pravokotnik(ax, x0, y_top - 8.5, sirina, 8.5, fill=BARVA_OZN, lw=0)
    ax.text(x0 + sirina / 2, y_top - 4.25, naslov_t,
            ha="center", va="center", fontsize=9.5, fontweight="bold",
            color="white")
    y = y_top - 12
    for vrsta in vrstice:
        ax.text(x0 + 2.5, y, vrsta, ha="left", va="center", fontsize=8.5)
        y -= 3.9
    return y_top - visina


def iso_okvir(ax):
    """Okvir + conatna mreža po vzoru ISO 5457 (A3 krajinski).

    Številke con 1..8 (zgoraj/spodaj), črke A..F (levo/desno, A spodaj).
    """
    pravokotnik(ax, 5, 5, A3_W - 10, A3_H - 10, fill="none", lw=0.5, z=1)
    pravokotnik(ax, 10, 10, A3_W - 20, A3_H - 20, fill="none", lw=0.9, z=1)
    n_z, w_z = 8, (A3_W - 20) / 8
    n_v, h_v = 6, (A3_H - 20) / 6
    for i in range(1, n_z):
        x = 10 + i * w_z
        crta(ax, x, 5, x, 10, lw=0.4, z=1)
        crta(ax, x, A3_H - 10, x, A3_H - 5, lw=0.4, z=1)
    for i in range(n_z):
        ax.text(10 + w_z * (i + 0.5), 7.5, str(i + 1), ha="center", va="center",
                fontsize=7, zorder=1)
        ax.text(10 + w_z * (i + 0.5), A3_H - 7.5, str(i + 1), ha="center",
                va="center", fontsize=7, zorder=1)
    for i in range(1, n_v):
        y = 10 + i * h_v
        crta(ax, 5, y, 10, y, lw=0.4, z=1)
        crta(ax, A3_W - 10, y, A3_W - 5, y, lw=0.4, z=1)
    for i in range(n_v):
        y = 10 + h_v * (i + 0.5)
        ax.text(7.5, y, chr(65 + i), ha="center", va="center", fontsize=7, zorder=1)
        ax.text(A3_W - 7.5, y, chr(65 + i), ha="center", va="center",
                fontsize=7, zorder=1)


def simbol_projekcije(ax, x, y):
    """Simbol prvega kota projekcije (zrezek) — evropska praksa."""
    ax.plot([x - 3, x + 3], [y, y], lw=0.4, color="#555555", zorder=6)
    ax.plot([x - 2.6, x - 0.9, x - 0.9, x - 2.6, x - 2.6],
            [y - 1.9, y - 1.0, y + 1.0, y + 1.9, y - 1.9], lw=0.5,
            color="#555555", zorder=6)
    ax.add_patch(Circle((x + 1.7, y), 1.1, fill=False, edgecolor="#555555",
                        lw=0.5, zorder=6))
    ax.add_patch(Circle((x + 1.7, y), 0.55, fill=False, edgecolor="#555555",
                        lw=0.5, zorder=6))


def _iso_cel(ax, x, y, w, h, oznaka, vrednost, fs=8.5):
    ax.text(x + 1.5, y + h - 2.0, oznaka, fontsize=5.5, color="#555555",
            ha="left", va="center", zorder=6)
    ax.text(x + 1.5, y + (h - 2.0) / 2, vrednost, fontsize=fs,
            fontweight="bold", ha="left", va="center", zorder=6)


def naslovni_blok(ax, p):
    """Glava risbe po vzoru ISO 7200 (desni spodnji kot)."""
    x0, x1 = 250, 410
    pravokotnik(ax, x0, 10, x1 - x0, 28, fill="white", lw=1.2)
    # vrstica 4: podjetje | risba št. + revizija
    crta(ax, x0, 29, x1, 29, lw=0.7)
    crta(ax, 355, 29, 355, 38, lw=0.7)
    ax.text(x0 + 2, 33.5, p["podjetje"], fontsize=11, fontweight="bold",
            ha="left", va="center")
    ax.text(357, 36.2, "RISBA ŠT. / REV.", fontsize=5.5, color="#555555",
            ha="left", va="center")
    ax.text(357, 31.8, f"{p['risba_st']}  •  REV. {p['rev']}", fontsize=10.5,
            fontweight="bold", ha="left", va="center")
    # vrstica 3: naziv | naročnik / objekt
    crta(ax, x0, 21.5, x1, 21.5, lw=0.7)
    crta(ax, 352, 21.5, 352, 29, lw=0.7)
    ax.text(x0 + 2, 27, "NAZIV:", fontsize=5.5, color="#555555", ha="left",
            va="center")
    ax.text(x0 + 2, 24, p["ime"][:28], fontsize=11.5, fontweight="bold",
            ha="left", va="center")
    ax.text(354, 27, "NAROČNIK / OBJEKT:", fontsize=5.5, color="#555555",
            ha="left", va="center")
    ax.text(354, 24.7, (p["stranka"] or "—")[:30], fontsize=7,
            fontweight="bold", ha="left", va="center")
    ax.text(354, 22.6, (p["objekt"] or "—")[:34], fontsize=6,
            ha="left", va="center")
    # vrstica 2: izdelal / pregledal / odobril
    crta(ax, x0, 15.5, x1, 15.5, lw=0.7)
    crta(ax, 303.3, 15.5, 303.3, 21.5, lw=0.7)
    crta(ax, 356.6, 15.5, 356.6, 21.5, lw=0.7)
    _iso_cel(ax, x0, 15.5, 53.3, 6, "IZDELAL:", p["izdelal"] or "—", fs=8)
    _iso_cel(ax, 303.3, 15.5, 53.3, 6, "PREGLEDAL:", p["pregledal"], fs=8)
    _iso_cel(ax, 356.6, 15.5, 53.4, 6, "ODOBRIL:", p["odobril"], fs=8)
    # vrstica 1: material | merilo | datum | format/list | simbol
    crta(ax, 300, 10, 300, 15.5, lw=0.7)
    crta(ax, 325, 10, 325, 15.5, lw=0.7)
    crta(ax, 355, 10, 355, 15.5, lw=0.7)
    crta(ax, 380, 10, 380, 15.5, lw=0.7)
    _iso_cel(ax, x0, 10, 50, 5.5, "MATERIAL:", p["material"][:26], fs=6.5)
    _iso_cel(ax, 300, 10, 25, 5.5, "MERILO:", p["merilo"], fs=8)
    _iso_cel(ax, 325, 10, 30, 5.5, "DATUM:", p["datum"], fs=8)
    _iso_cel(ax, 355, 10, 25, 5.5, "FORMAT/LIST:",
             f"A3 • {p['list']}", fs=7)
    simbol_projekcije(ax, 395, 12.75)


def tabela_revizij(ax, x0, y0, sirine, vrste):
    """Tabela revizij (spodaj levo): [[rev, datum, opis, izdelal], ...]."""
    glava = ["REV.", "DATUM", "OPIS SPREMEMBE", "IZDELAL"]
    h = 6
    y = y0
    x = x0
    for ci, g in enumerate(glava):
        w = sirine[ci]
        pravokotnik(ax, x, y, w, h, fill="#e6e6e6", lw=0.7)
        ax.text(x + w / 2, y + h / 2, g, ha="center", va="center",
                fontsize=6.5, fontweight="bold")
        x += w
    y += h
    for vrsta in vrste:
        x = x0
        for ci, celica in enumerate(vrsta):
            w = sirine[ci]
            pravokotnik(ax, x, y, w, h, fill="white", lw=0.7)
            tx = x + 1.5 if ci == 2 else x + w / 2
            ax.text(tx, y + h / 2, str(celica), ha="left" if ci == 2 else
                    "center", va="center", fontsize=6.5)
            x += w
        y += h


# ---------------------------------------------------------------- geometrija ograje
def razpored(m):
    """Vrne (zgornji_profil, spodnji_profil, lamele od spodaj, vrzel, n).

    Profili: (z0, z1) v mm od tal; lamele: seznam (z0, z1).
    Če se lamele ne prilegajo v cono, se število samodejno prilagodi.
    """
    cona = m["visina"] - m["odcep"] - 2 * m["profil_v"]
    n, lv = m["lamele"], m["lamela_v"]
    if n * lv > cona:
        n_nova = max(1, int((cona - 8) // (lv + 8)))
        print(f"[OPOZORILO] {n} lamel × {lv} mm se ne prilega v cono "
              f"{cona:.0f} mm — prilagojeno na {n_nova} lamel.")
        n = n_nova
    if n * lv > cona:
        raise ValueError("Lamele se ne prilegajo v cono — zmanjšaj število "
                         "ali višino lamel.")
    vrzel = (cona - n * lv) / (n - 1) if n > 1 else 0
    zg = (m["visina"] - m["profil_v"], m["visina"])
    sp = (m["odcep"], m["odcep"] + m["profil_v"])
    lamele = []
    z = zg[0]                      # od zgoraj navzdol
    for _ in range(n):
        lamele.append((z - lv, z))
        z -= lv + vrzel
    lamele.reverse()
    return zg, sp, lamele, vrzel, n


def narisi_zgradbo(v, zg, sp, lamele, x0r, x1r, b_lam, b_pro, cut=False):
    """Profila + lamele med x0r..x1r (realni mm). cut=True -> prerezi."""
    v.kocka(x0r, zg[0], x1r, zg[1], fill=b_pro)
    v.kocka(x0r, sp[0], x1r, sp[1], fill=b_pro)
    for z0, z1 in lamele:
        v.kocka(x0r, z0, x1r, z1, fill=b_lam)


# ---------------------------------------------------------------- predloga: pokončna
def razpored_pokoncna(m):
    """Razpored pokončne ograje: stebri (lego), deske (x0), višine.

    Stebri po krajih in z največjim razmakom; deske med stebri z enakomerno
    vrzeljo; če se ne prilegajo, se število samodejno prilagodi.
    """
    sir, vis = m["sirina"], m["visina"]
    odcep, rv = m["odcep"], m["rocaj_v"]
    ss, sd = m["steber_sirina"], m["steber_debelina"]
    ds, dd = m["deska_sirina"], m["deska_debelina"]
    vrzel, n = m["vrzel"], m["lamele"]
    raz = m["razmak_stebrov"]

    n_stebrov = max(2, math.ceil((sir - ss) / raz) + 1)
    centri = [ss / 2 + i * (sir - ss) / (n_stebrov - 1) for i in range(n_stebrov)]

    cona = sir - n_stebrov * ss               # za deske (med stebri)
    n_max = max(1, int((cona + vrzel) // (ds + vrzel)))
    if n > n_max:
        print(f"[OPOZORILO] {n} desk × {ds} mm se ne prilega v cono "
              f"{cona:.0f} mm — prilagojeno na {n_max} desk.")
        n = n_max
    if n * ds > cona:
        raise ValueError("Deske se ne prilegajo — zmanjšaj število ali "
                         "širino desk.")
    vrzel_r = (cona - n * ds) / (n - 1) if n > 1 else 0
    x0_prva = ss / 2 + (cona - n * ds - (n - 1) * vrzel_r) / 2
    deske_x = [x0_prva + i * (ds + vrzel_r) for i in range(n)]
    deske_h = vis - rv - odcep
    return {"centri": centri, "deske_x": deske_x, "deske_h": deske_h,
            "vrzel": vrzel_r, "n_stebrov": n_stebrov, "n_desk": n,
            "rocaj": (vis - rv, vis), "deske_z": (odcep, odcep + deske_h)}


def narisi_pokoncna(ax, c):
    m = c["mere"]
    sir, vis = m["sirina"], m["visina"]
    odcep, rv = m["odcep"], m["rocaj_v"]
    ss, sd = m["steber_sirina"], m["steber_debelina"]
    ds, dd = m["deska_sirina"], m["deska_debelina"]
    p = razpored_pokoncna(m)
    cona_z = p["deske_z"][1] - p["deske_z"][0]

    b_lam = barva_hex(c.get("barva"))
    b_pro = odsteni(b_lam, 0.72)

    if str(c["merilo"]).lower() == "auto":
        d = next((q for q in (2, 5, 10, 20, 25, 50, 100)
                  if sir / q <= 150 and vis / q <= 72), 100)
    else:
        d = int(str(c["merilo"]).split(":")[-1])
    s = 1.0 / d
    merilo_niz = f"1:{d}"

    iso_okvir(ax)

    # ==================== SPREDNJI POGLLED ====================
    oznaka(ax, 30, 286, "SPREDNJI POGLLED")
    v = Pogled(ax, 35, 206, s)
    for xr in p["deske_x"]:                    # deske (za stebri)
        v.kocka(xr, p["deske_z"][0], xr + ds, p["deske_z"][1], fill=b_lam)
    for xc in p["centri"]:                     # stebri (pred deskami)
        v.kocka(xc - ss / 2, 0, xc + ss / 2, vis, fill=b_pro)
        v.kocka(xc - ss / 2 - 15, 0, xc + ss / 2 + 15, 6, fill=b_pro)  # osnova
    v.kocka(0, vis - rv, sir, vis, fill=b_pro)  # ročaj
    tla(ax, v.X(-3), v.X(sir + 3), v.Y(0))
    # vijaki (pika = priključek deska↔steber, 2 vijaka)
    for xc in p["centri"]:
        for xr in p["deske_x"]:
            for fz in (0.25, 0.75):
                z = p["deske_z"][0] + cona_z * fz
                ax.add_patch(Circle((v.X(xc), v.Y(z)), 0.55,
                                    facecolor="#e8e8e8", edgecolor="none",
                                    zorder=4))
    dim_h(ax, v.X(0), v.X(sir), v.Y(vis) + 8, v.Y(vis), v.Y(vis),
          f"{fmt(sir)} mm")
    dim_v(ax, v.Y(0), v.Y(vis), v.X(0) - 3, v.X(-3), v.X(0), f"{fmt(vis)} mm")
    xk = v.X(sir) + 8
    dim_v(ax, v.Y(vis - rv), v.Y(vis), xk, v.X(sir), v.X(sir),
          f"{fmt(rv)} mm")
    dim_v(ax, v.Y(p["deske_z"][0]), v.Y(p["deske_z"][1]), xk, v.X(sir),
          v.X(sir), f"{fmt(cona_z)} mm")
    dim_v(ax, v.Y(0), v.Y(odcep), xk, v.X(sir), v.X(sir), f"{fmt(odcep)} mm")
    if len(p["centri"]) >= 2:
        dim_h(ax, v.X(p["centri"][0]), v.X(p["centri"][1]), v.Y(0) - 5,
              None, None, f"{fmt(p['centri'][1] - p['centri'][0])} mm")
    # širina deske + vrzel (kota na prvih dveh deskah, zgoraj)
    if len(p["deske_x"]) >= 2:
        pass  # širina deske se kotira na DETAJL DESKE

    # ==================== STRANSKI POGLLED ====================
    oznaka(ax, 268, 286, "STRANSKI POGLLED")
    v2 = Pogled(ax, 276, 206, s)
    skupna_d = sd + dd                         # steber + deska pred njim
    v2.kocka(0, 0, sd, vis, fill=b_pro)        # steber (prerez)
    v2.kocka(sd, p["deske_z"][0], skupna_d, p["deske_z"][1], fill=b_lam)
    v2.kocka(0, vis - rv, skupna_d, vis, fill=b_pro)   # ročaj
    pravokotnik(ax, v2.X(0) - 4.5, v2.Y(0) - 2, (skupna_d + 4.5) * s,
                6 * s + 2, fill=b_pro, lw=0.5)          # osnova
    tla(ax, v2.X(0) - 4.5, v2.X(skupna_d + 3), v2.Y(0))
    dim_h(ax, v2.X(0), v2.X(skupna_d), v2.Y(vis) + 8, v2.Y(vis), v2.Y(vis),
          f"{fmt(skupna_d)} mm")
    dim_v(ax, v2.Y(0), v2.Y(vis), v2.X(skupna_d) + 8, v2.X(skupna_d),
          v2.X(skupna_d), f"{fmt(vis)} mm")

    # ==================== TLORIS ====================
    oznaka(ax, 30, 130, "TLORIS")
    v3 = Pogled(ax, 35, 120, s)                # y = globina (od tal)
    pravokotnik(ax, v3.X(0), v3.Y(0), sir * s, skupna_d * s, fill="none",
                lw=LW_THICK)
    for xc in p["centri"]:                     # stebri v tlorisu
        pravokotnik(ax, v3.X(xc - ss / 2), v3.Y(0) + 1,
                    ss * s, (skupna_d - 2) * s, fill=b_pro, lw=0.5)
    xa = v3.X(sir - 100)
    crta(ax, xa, v3.Y(0) - 3, xa, v3.Y(0) + skupna_d * s + 3, lw=1.1,
         stil=(0, (6, 2, 1, 2)))
    puscica(ax, xa + 3, v3.Y(0) - 3, 1, 0, vel=2.2)
    puscica(ax, xa + 3, v3.Y(0) + skupna_d * s + 3, 1, 0, vel=2.2)
    ax.text(xa + 7, v3.Y(0) - 3, "A", ha="left", va="center", fontsize=10.5,
            fontweight="bold")
    ax.text(xa + 7, v3.Y(0) + skupna_d * s + 3, "A", ha="left", va="center",
            fontsize=10.5, fontweight="bold")
    dim_h(ax, v3.X(0), v3.X(sir), v3.Y(0) + skupna_d * s + 10,
          v3.Y(0) + skupna_d * s + 6, v3.Y(0) + skupna_d * s + 6, f"{fmt(sir)} mm")
    dim_v(ax, v3.Y(0), v3.Y(0) + skupna_d * s, v3.X(sir) + 8, v3.X(sir),
          v3.X(sir), f"{fmt(skupna_d)} mm")

    # ==================== PREREZ A - A (1:5, prekinjen) ====================
    oznaka(ax, 20, 39, "PREREZ A - A")
    s2 = 1.0 / 5
    px0 = 30                                   # levi rob (steber) na papirju
    pw_s, pw_d = ss * s2, dd * s2              # širini na papirju
    y_tla = 45
    # spodnji del: plošča + osnova + ankerja + steber + deska
    sachiranje(ax, px0 - 8, y_tla - 2, px0 + pw_s + pw_d + 8, y_tla + 3)
    pravokotnik(ax, px0 - 3, y_tla + 3, pw_s + pw_d + 6, 4, fill=b_pro,
                lw=0.5)                        # osnova
    pravokotnik(ax, px0 + 2, y_tla + 5, 3, 5, fill="white", lw=0.4)   # anker
    pravokotnik(ax, px0 + pw_s + pw_d - 5, y_tla + 5, 3, 5, fill="white",
                lw=0.4)                        # anker
    h_b = 14
    y_b0 = y_tla + 7
    pravokotnik(ax, px0, y_b0, pw_s, h_b, fill=b_pro, lw=LW_THICK)
    pravokotnik(ax, px0 + pw_s, y_b0, pw_d, h_b, fill=b_lam, lw=LW_THICK)
    for xx in (px0, px0 + pw_s, px0 + pw_s + pw_d):
        crta(ax, xx - 1.5, y_b0 + h_b - 2, xx + 1.5, y_b0 + h_b + 3, lw=0.7)
    # zgornji del: steber + deska + ročaj
    y_top_top = 101
    h_t = 16
    pravokotnik(ax, px0, y_top_top - h_t, pw_s, h_t - 8, fill=b_pro,
                lw=LW_THICK)
    pravokotnik(ax, px0 + pw_s, y_top_top - h_t, pw_d, h_t - 8, fill=b_lam,
                lw=LW_THICK)
    pravokotnik(ax, px0 - 2, y_top_top - 8, pw_s + pw_d + 4, 8, fill=b_pro,
                lw=LW_THICK)                   # ročaj
    for xx in (px0, px0 + pw_s, px0 + pw_s + pw_d):
        crta(ax, xx - 1.5, y_top_top - h_t - 3, xx + 1.5, y_top_top - h_t - 8,
             lw=0.7)
    dim_h(ax, px0 - 2, px0 + pw_s + pw_d + 2, y_top_top + 4, y_top_top,
          y_top_top, f"{fmt(skupna_d)} mm")
    dim_h(ax, px0, px0 + pw_s, y_tla - 7, None, None, f"{fmt(ss)} mm")
    dim_h(ax, px0 + pw_s, px0 + pw_s + pw_d, y_tla - 14, None, None,
          f"{fmt(dd)} mm")
    ax.text(px0 + pw_s + pw_d + 10, y_tla + 10, "M10 × 2", fontsize=7,
            ha="left", va="center")
    ax.text(px0 + pw_s + pw_d + 10, y_tla + 22, "(prekinjeno)", fontsize=6,
            color="#555555", ha="left", va="center")
    ozna_st(ax, px0 - 2, y_top_top - 4, 106, y_top_top - 4, 1)
    ozna_st(ax, px0 + pw_s + pw_d, y_top_top - 12, 106, y_top_top - 12, 2)
    ozna_st(ax, px0 + pw_s + pw_d, y_b0 + h_b - 6, 106, y_b0 + h_b - 14, 3)
    ozna_st(ax, px0 - 3, y_tla + 5, 16, 30, 4)

    # ==================== DETAJL PRITRJEVANJA ====================
    oznaka(ax, 106, 121, "DETAJL PRITRJEVANJA")
    cx, cy, r = 138, 74, 23
    sachiranje(ax, cx - r, cy - r, cx + r, cy - r + 7)      # plošča (spodaj)
    pravokotnik(ax, cx - 15, cy - 7, 30, 5, fill=b_pro, lw=0.5)  # osnova
    pravokotnik(ax, cx - 9, cy - 16, 4, 9, fill="white", lw=0.4)  # anker L
    pravokotnik(ax, cx + 5, cy - 16, 4, 9, fill="white", lw=0.4)  # anker D
    pravokotnik(ax, cx - 7.5, cy - 2, 15, 20, fill=b_pro, lw=0.5)  # steber
    pravokotnik(ax, cx + 7.5, cy + 2, 8, 15, fill=b_lam, lw=0.5)   # deska
    ax.add_patch(Circle((cx + 11.5, cy + 6), 1.2, facecolor="#e8e8e8",
                        edgecolor="none", zorder=4))
    ax.add_patch(Circle((cx + 11.5, cy + 13), 1.2, facecolor="#e8e8e8",
                        edgecolor="none", zorder=4))
    dim_h(ax, cx - 7.5, cx + 7.5, cy + 21, None, None, "60 mm")
    ax.add_patch(Circle((cx, cy), r, facecolor="none", edgecolor=CRNA,
                        lw=LW_THICK, zorder=8))
    ax.text(cx, cy - r - 3, "NERAZMERJENO", ha="center", va="center",
            fontsize=7, color="#555555")
    ax.text(cx, cy - r - 7, "anker M10 × 2 • predrtje Ø + 1 mm", ha="center",
            va="center", fontsize=7, color="#555555")

    # ==================== DETAJL DESKE ====================
    oznaka(ax, 172, 121, "DETAJL DESKE")
    cx2, cy2, r2 = 192, 74, 20
    sl = min(0.4, 36 / ds, 14 / dd)
    lw_, hh_ = ds * sl, dd * sl
    pravokotnik(ax, cx2 - lw_ / 2, cy2 - hh_ / 2, lw_, hh_, fill=b_lam,
                lw=0.5)
    ax.add_patch(Circle((cx2, cy2), r2, facecolor="none", edgecolor=CRNA,
                        lw=LW_THICK, zorder=8))
    dim_h(ax, cx2 - lw_ / 2, cx2 + lw_ / 2, cy2 + hh_ / 2 + 4, None, None,
          f"{fmt(ds)} mm")
    dim_v(ax, cy2 - hh_ / 2, cy2 + hh_ / 2, cx2 + r2 + 4, cx2 + lw_ / 2,
          cx2 + lw_ / 2, f"{fmt(dd)} mm")

    # ==================== IZOMETRIČNI POGLLED / FOTO ====================
    foto = c.get("foto") or ""
    if foto and os.path.isfile(foto):
        oznaka(ax, 256, 200, "POGLED IZVEDBE")
        img = plt.imread(foto)
        h_px, w_px = img.shape[0], img.shape[1]
        rx0, ry0, rw, rh = 258, 132, 148, 58
        f_fit = min(rw / w_px, rh / h_px)
        w_mm, h_mm = w_px * f_fit, h_px * f_fit
        ax.imshow(img, extent=[rx0 + (rw - w_mm) / 2, rx0 + (rw + w_mm) / 2,
                               ry0 + (rh - h_mm) / 2, ry0 + (rh + h_mm) / 2],
                  zorder=2, interpolation="bilinear")
        pravokotnik(ax, rx0 + (rw - w_mm) / 2, ry0 + (rh - h_mm) / 2,
                    w_mm, h_mm, fill="none", lw=0.6)
    else:
        oznaka(ax, 256, 200, "IZOMETRIČNI POGLLED")
        D = skupna_d
        f = min(148 / ((sir + D) * C30), 58 / ((sir + D) * 0.5 + vis))
        gap_iso = 4.0 / f
        xs = [izo_tocka(x, y, 0, f)[0] for x, y in ((0, D), (sir, 0))]
        ys = [izo_tocka(x, y, z, f)[1] for x, y, z in
              ((0, 0, 0), (sir, D, vis))]
        ox = 331 - (min(xs) + max(xs)) / 2
        oy = 162 - (min(ys) + max(ys)) / 2
        barve_izo = (b_lam, odsteni(b_lam, 0.72), odsteni(b_lam, 1.55))
        for xr in p["deske_x"]:                # deske (navpične)
            izo_kocka(ax, xr, 0, odcep, ds, dd, cona_z, f, ox, oy, barve_izo)
        for xc in p["centri"]:                 # stebri (pred deskami)
            izo_kocka(ax, xc - ss / 2, 0, 0, ss, sd, vis, f, ox, oy,
                      (b_pro, odsteni(b_pro, 0.75), odsteni(b_pro, 1.4)))
        izo_kocka(ax, 0, 0, vis - rv, sir, D, rv, f, ox, oy,
                  (b_pro, odsteni(b_pro, 0.72), odsteni(b_pro, 1.5)))

    # ==================== SEZNAM SESTAVNIH DELOV ====================
    deli = c.get("deli")
    if not deli:
        mat = c["material"]
        profil = c.get("profil") or "POLNA DESKA 100"
        ml = c.get("material_lamel") or "WPC lesni kompozit"
        n_vij = p["n_desk"] * p["n_stebrov"] * 2
        deli = [
            ["Ročaj", mat, f"{fmt(sir)} mm", "1 kos"],
            [f"WPC deska {profil}", ml, f"{fmt(ds)}×{fmt(dd)}",
             f"{p['n_desk']} kos"],
            ["Alu steber 60×40", "Aluminij", "60×40",
             f"{p['n_stebrov']} kos"],
            ["Osnova za steber (vrh)", "Jeklo", "90×90×6",
             f"{p['n_stebrov']} kos"],
            ["Vijaki M8×70 (deska↔steber)", "Inox A2", "M8×70",
             f"{n_vij} kos"],
            ["Anker M10 (osnova)", "Inox", "M10", f"{p['n_stebrov'] * 2} kos"],
        ]
    vrste = [["Št.", "Naziv dela", "Material", "Dimenzije (mm)", "Količina"]]
    vrste += [[i] + list(d) for i, d in enumerate(deli, 1)]
    tabela(ax, 246, 131, [10, 58, 44, 30, 20], 6.5, vrste,
           naslov="SEZNAM SESTAVNIH DELOV")

    # ==================== OPOMBE ====================
    opombe = c.get("opombe") or [
        "Vse mere v mm (tolerance ISO 2768-m); pred izdelavo preveri "
        "dejanske mere na objektu.",
        f"Deske: {profil} — WPC (bambus + HDPE), pritrditev z 2 vijaki na "
        "desko na vsak steber; predrtje Ø + 1 mm.",
        "Stebri: aluminij, na osnove z anker M10 (vrh v ploščo).",
        f"Razmak stebrov največ {fmt(m['razmak_stebrov'])} mm.",
        "Količine pritrdilnih elementov so orientacijske.",
        "Risba NI statični izračun — nosilnost, sidranje in veterno breme "
        "preveri usposobljen strokovnjak.",
    ]
    opombe_blok(ax, 246, 74, 162, opombe)

    # ==================== ISO NASLOVNI BLOK + REVIZIJE ====================
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    revizije = c.get("revizije") or [
        ["A", datum, "Prva izdaja", c["izdelal"] or "—"]]
    tabela_revizij(ax, 10, 10, [15, 35, 150, 30], revizije)
    mat_cel = ("ALU stebri + WPC deske"
               if "WPC" in (c.get("material_lamel") or "").upper()
               else c["material"])[:26]
    naslovni_blok(ax, {
        "podjetje": c.get("podjetje") or "—",
        "ime": c["ime"], "risba_st": c["risba_st"],
        "rev": revizije[-1][0], "merilo": merilo_niz,
        "datum": datum, "izdelal": c["izdelal"],
        "pregledal": c.get("pregledal") or "—",
        "odobril": c.get("odobril") or "—",
        "material": mat_cel, "list": "1 od 1",
        "stranka": c.get("stranka") or "—", "objekt": c.get("objekt") or "—",
    })


# ---------------------------------------------------------------- predloga: ograda
def narisi_ogrado(ax, c):
    m = c["mere"]
    sir, vis, glob = m["sirina"], m["visina"], m["globina"]
    zg, sp, lamele, vrzel, n_lamel = razpored(m)
    cona = zg[0] - sp[1]
    b_lam = barva_hex(c.get("barva"))         # barva lamel (izdelek)
    b_pro = odsteni(b_lam, 0.72)              # profili nekoliko temnejši

    # merilo (avtomatsko ali vpisano, npr. "1:20")
    if str(c["merilo"]).lower() == "auto":
        d = next((q for q in (2, 5, 10, 20, 25, 50, 100)
                  if sir / q <= 150 and vis / q <= 72), 100)
    else:
        d = int(str(c["merilo"]).split(":")[-1])
    s = 1.0 / d
    merilo_niz = f"1:{d}"

    iso_okvir(ax)

    # ==================== SPREDNJI POGLLED ====================
    oznaka(ax, 30, 286, "SPREDNJI POGLLED")
    v = Pogled(ax, 35, 206, s)
    narisi_zgradbo(v, zg, sp, lamele, 0, sir, b_lam, b_pro)
    tla(ax, v.X(-3), v.X(sir + 3), v.Y(0))
    # lega pritrdilnih nosilcev (kos 4): črtkane linije + puščice na tleh,
    # vijaki/piščavniki na vsaki lameli; razmak nosilcev se izpiše kot kota
    raz = m.get("razmak_nosilcev", 1000)
    n_nos = max(2, math.ceil(sir / raz) + 1)
    xs_nos = [100 + i * (sir - 200) / (n_nos - 1) for i in range(n_nos)]
    for xn in xs_nos:
        ax.plot([v.X(xn)] * 2, [v.Y(0) - 2, v.Y(sp[1])], color=CRNA, lw=0.5,
                zorder=2, linestyle=(0, (4, 2, 1, 2)))
        ax.add_patch(Polygon(
            [(v.X(xn), v.Y(0) + 1.3), (v.X(xn) - 1.0, v.Y(0)),
             (v.X(xn) + 1.0, v.Y(0))], closed=True, facecolor=CRNA,
            edgecolor="none", zorder=5))
        for z0, z1 in lamele:
            ax.add_patch(Circle((v.X(xn), v.Y((z0 + z1) / 2)), 0.55,
                                facecolor="#e8e8e8", edgecolor="none",
                                zorder=4))
    if n_nos >= 2:
        dim_h(ax, v.X(xs_nos[0]), v.X(xs_nos[1]), v.Y(0) - 5, None, None,
              f"{fmt(raz)} mm")
    ozna_st(ax, v.X(xs_nos[-1]), v.Y(0), v.X(xs_nos[-1]), v.Y(0) - 10, 4)
    dim_h(ax, v.X(0), v.X(sir), v.Y(vis) + 8, v.Y(vis), v.Y(vis),
          f"{fmt(sir)} mm")
    dim_v(ax, v.Y(0), v.Y(vis), v.X(0) - 3, v.X(-3), v.X(0), f"{fmt(vis)} mm")
    xk = v.X(sir) + 8
    dim_v(ax, v.Y(zg[0]), v.Y(zg[1]), xk, v.X(sir), v.X(sir),
          f"{fmt(m['profil_v'])} mm")
    dim_v(ax, v.Y(sp[1]), v.Y(zg[0]), xk, v.X(sir), v.X(sir), f"{fmt(cona)} mm")
    dim_v(ax, v.Y(sp[0]), v.Y(sp[1]), xk, v.X(sir), v.X(sir),
          f"{fmt(m['profil_v'])} mm")
    dim_v(ax, v.Y(0), v.Y(sp[0]), xk, v.X(sir), v.X(sir),
          f"{fmt(m['odcep'])} mm")

    # ==================== STRANSKI POGLLED ====================
    oznaka(ax, 268, 286, "STRANSKI POGLLED")
    v2 = Pogled(ax, 276, 202, s)
    sachiranje(ax, v2.X(0) - 8, v2.Y(0) - 2, v2.X(0), v2.Y(vis) + 4)
    narisi_zgradbo(v2, zg, sp, lamele, 0, glob, b_lam, b_pro)
    tla(ax, v2.X(0) - 8, v2.X(glob + 3), v2.Y(0))
    dim_h(ax, v2.X(0), v2.X(glob), v2.Y(vis) + 8, v2.Y(vis), v2.Y(vis),
          f"{fmt(glob)} mm")
    dim_v(ax, v2.Y(0), v2.Y(vis), v2.X(glob) + 8, v2.X(glob), v2.X(glob),
          f"{fmt(vis)} mm")

    # ==================== TLORIS ====================
    oznaka(ax, 30, 200, "TLORIS")
    v3 = Pogled(ax, 35, 120, s)         # y = globina (0 = sprednji rob)
    pravokotnik(ax, v3.X(0), v3.Y(0), sir * s, glob * s, fill="none",
                lw=LW_THICK)
    sachiranje(ax, v3.X(-3), v3.Y(glob), v3.X(sir + 3), v3.Y(glob) + 6)  # zid
    for cxr in (8, sir - 8):            # pritrdilni nosilci po vogalih (kos 4)
        for cyr in (8, glob - 8):
            x, y = v3.X(cxr), v3.Y(cyr)
            pravokotnik(ax, x - 1.25, y - 1.25, 2.5, 2.5, fill="white", lw=0.5)
            crta(ax, x - 1.25, y - 1.25, x + 1.25, y + 1.25, lw=0.3)
            crta(ax, x - 1.25, y + 1.25, x + 1.25, y - 1.25, lw=0.3)
    # rez A-A pri desnem robu
    xa = v3.X(sir - 100)
    crta(ax, xa, v3.Y(0) - 3, xa, v3.Y(glob) + 3, lw=1.1,
         stil=(0, (6, 2, 1, 2)))
    puscica(ax, xa + 3, v3.Y(0) - 3, 1, 0, vel=2.2)
    puscica(ax, xa + 3, v3.Y(glob) + 3, 1, 0, vel=2.2)
    ax.text(xa + 7, v3.Y(0) - 3, "A", ha="left", va="center", fontsize=10.5,
            fontweight="bold")
    ax.text(xa + 7, v3.Y(glob) + 3, "A", ha="left", va="center", fontsize=10.5,
            fontweight="bold")
    dim_h(ax, v3.X(0), v3.X(sir), v3.Y(glob) + 10, v3.Y(glob) + 6,
          v3.Y(glob) + 6, f"{fmt(sir)} mm")
    dim_v(ax, v3.Y(0), v3.Y(glob), v3.X(sir) + 8, v3.X(sir), v3.X(sir),
          f"{fmt(glob)} mm")

    # ==================== PREREZ A - A ====================
    oznaka(ax, 20, 115, "PREREZ A - A")
    v4 = Pogled(ax, 32, 42, s)          # x = od zida navzven
    sachiranje(ax, 24, v4.Y(0) - 2, v4.X(0), v4.Y(vis) + 4)
    narisi_zgradbo(v4, zg, sp, lamele, 0, glob, b_lam, b_pro, cut=True)
    tla(ax, 24, v4.X(glob) + 3, v4.Y(0))
    # nosilec ob zidu (kos 4) z oznako detajla
    pravokotnik(ax, v4.X(0), v4.Y(0) + 0.8, 3, 5, fill=b_pro, lw=0.5)
    ax.add_patch(Circle((v4.X(0) + 1.5, v4.Y(0) + 3.3), 6, facecolor="none",
                        edgecolor=CRNA, lw=0.4, zorder=6))
    ozna_st(ax, v4.X(0) + 1.5, v4.Y(0) + 1.5, 16, 34, 4)
    dim_h(ax, v4.X(0), v4.X(glob), v4.Y(vis) + 6, v4.Y(vis), v4.Y(vis),
          f"{fmt(glob)} mm")
    dim_v(ax, v4.Y(0), v4.Y(vis), 17, 24, v4.X(0), f"{fmt(vis)} mm")
    ozna_st(ax, v4.X(glob), v4.Y(vis - m["profil_v"] / 2),
            v4.X(glob) + 16, v4.Y(vis - m["profil_v"] / 2), 1)
    ozna_st(ax, v4.X(glob), v4.Y(lamele[len(lamele) // 2][1] - m["lamela_v"] / 2),
            v4.X(glob) + 16, v4.Y(lamele[len(lamele) // 2][1] - m["lamela_v"] / 2), 2)
    ozna_st(ax, v4.X(glob), v4.Y(sp[0] + m["profil_v"] / 2),
            v4.X(glob) + 16, v4.Y(sp[0] + m["profil_v"] / 2), 3)

    # ==================== DETAJL PRITRJEVANJA ====================
    oznaka(ax, 118, 104, "DETAJL PRITRJEVANJA")
    cx, cy, r = 142, 74, 23
    sachiranje(ax, cx - r, cy - r, cx - 15, cy + r)
    pravokotnik(ax, cx - 15, cy - 20, 5, 40, fill=b_pro, lw=0.5)     # nosilec
    pravokotnik(ax, cx - 10, cy - 8, 16, 16, fill=b_lam, lw=0.5)     # profil
    pravokotnik(ax, cx - 10, cy - 5, 12, 10, fill="white", lw=0.4)   # kanal
    for by in (cy + 14, cy - 14):                                     # vijaki M8
        pravokotnik(ax, cx - 22, by - 0.8, 12, 1.6, fill="white", lw=0.4)
        ax.add_patch(Circle((cx - 11.5, by), 1.5, facecolor="white",
                            edgecolor=CRNA, lw=0.5, zorder=4))
    ax.text(cx - 11.5, cy + 17.2, "M8", ha="center", va="center", fontsize=7.5)
    dim_v(ax, cy + 14, cy - 14, cx + 20, None, None, "800 mm")
    ax.add_patch(Circle((cx, cy), r, facecolor="none", edgecolor=CRNA,
                        lw=LW_THICK, zorder=8))
    ax.text(cx, cy - r - 3, "NERAZMERJENO", ha="center", va="center",
            fontsize=7, color="#555555")
    ax.text(cx, cy - r - 7, "predrtje Ø + 1 mm (ekspanzija)", ha="center",
            va="center", fontsize=7, color="#555555")

    # ==================== DETAJL LAMELE ====================
    oznaka(ax, 172, 104, "DETAJL LAMELE")
    cx2, cy2, r2 = 192, 74, 20
    sl = min(0.4, 30 / m["lamela_v"], 14 / m["debelina"])
    lw_, hh_ = m["debelina"] * sl, m["lamela_v"] * sl
    pravokotnik(ax, cx2 - lw_ / 2, cy2 - hh_ / 2, lw_, hh_, fill=b_lam,
                lw=0.5)
    ax.add_patch(Circle((cx2, cy2), r2, facecolor="none", edgecolor=CRNA,
                        lw=LW_THICK, zorder=8))
    dim_v(ax, cy2 - hh_ / 2, cy2 + hh_ / 2, cx2 + r2 + 4, cx2 + lw_ / 2,
          cx2 + lw_ / 2, f"{fmt(m['lamela_v'])} mm")
    dim_h(ax, cx2 - lw_ / 2, cx2 + lw_ / 2, cy2 - r2 - 4, None, None,
          f"{fmt(m['debelina'])} mm")

    # ==================== IZOMETRIČNI POGLLED / FOTO ====================
    foto = c.get("foto") or ""
    if foto and os.path.isfile(foto):
        oznaka(ax, 256, 200, "POGLED IZVEDBE")
        img = plt.imread(foto)
        h_px, w_px = img.shape[0], img.shape[1]
        rx0, ry0, rw, rh = 258, 132, 148, 58
        f_fit = min(rw / w_px, rh / h_px)
        w_mm, h_mm = w_px * f_fit, h_px * f_fit
        ax.imshow(img, extent=[rx0 + (rw - w_mm) / 2, rx0 + (rw + w_mm) / 2,
                               ry0 + (rh - h_mm) / 2, ry0 + (rh + h_mm) / 2],
                  zorder=2, interpolation="bilinear")
        pravokotnik(ax, rx0 + (rw - w_mm) / 2, ry0 + (rh - h_mm) / 2,
                    w_mm, h_mm, fill="none", lw=0.6)
    else:
        oznaka(ax, 256, 200, "IZOMETRIČNI POGLLED")
        # merilo izometrije; vrzeli med lamelami se po potrebi rahlo
        # povečajo, da je slojastost berljiva (slikovna poučnost)
        f = 58 / ((sir + glob) * 0.5 + vis)
        gap_iso = vrzel
        for _ in range(4):
            gap_iso = max(vrzel, 0.7 / f)
            vis_iso = 2 * m["profil_v"] + n_lamel * m["lamela_v"] \
                + (n_lamel + 1) * gap_iso
            f = 58 / ((sir + glob) * 0.5 + vis_iso)
        nivoji = []
        z = 0.0
        nivoji.append((z, z + m["profil_v"])); z += m["profil_v"] + gap_iso
        for _ in range(n_lamel):
            nivoji.append((z, z + m["lamela_v"])); z += m["lamela_v"] + gap_iso
        nivoji.append((z, z + m["profil_v"]))
        xs = [izo_tocka(x, y, 0, f)[0] for x, y in ((0, glob), (sir, 0))]
        ys = [izo_tocka(x, y, z, f)[1] for x, y, z in
              ((0, 0, 0), (sir, glob, nivoji[-1][1]))]
        ox = 331 - (min(xs) + max(xs)) / 2
        oy = 162 - (min(ys) + max(ys)) / 2
        t = m["debelina"]
        barve_izo = (b_lam, odsteni(b_lam, 0.72), odsteni(b_lam, 1.55))
        for z0, z1 in nivoji:
            izo_kocka(ax, sir - t, 0, z0, t, glob, z1 - z0, f, ox, oy, barve_izo)
            izo_kocka(ax, 0, 0, z0, sir, t, z1 - z0, f, ox, oy, barve_izo)

    # ==================== SEZNAM SESTAVNIH DELOV ====================
    deli = c.get("deli")
    if not deli:
        mat = c["material"]
        profil = c.get("profil") or "ROMB 67"
        ml = c.get("material_lamel") or "WPC lesni kompozit"
        deli = [
            ["Zgornji profil", mat, "80×40×3", "1 kos"],
            [f"WPC deska {profil}", ml,
             f"{fmt(m['lamela_v'])}×{fmt(m['debelina'])}", f"{n_lamel} kos"],
            ["Spodnji profil", mat, "60×40×3", "1 kos"],
            ["Nosilni nosilec 50×50×5", "Jeklo", "50×50×5", f"{n_nos} kos"],
            ["RF vijaki M8×70 (lamela↔profil)", "Inox A2", "M8×70",
             f"{n_lamel * n_nos * 2} kos"],
            ["Fasadni vijaki Ø8×80 + tipli", "Inox", "Ø8×80",
             f"{n_nos * 2} kos"],
        ]
    vrste = [["Št.", "Naziv dela", "Material", "Dimenzije (mm)", "Količina"]]
    vrste += [[i] + list(d) for i, d in enumerate(deli, 1)]
    tabela(ax, 246, 131, [10, 58, 44, 30, 20], 6.5, vrste,
           naslov="SEZNAM SESTAVNIH DELOV")

    # ==================== OPOMBE ====================
    opombe = c.get("opombe") or [
        "Vse mere v mm (tolerance ISO 2768-m); pred izdelavo preveri "
        "dejanske mere na objektu.",
        f"Lamele: {profil} — WPC (bambus + HDPE), 15 let garancije, brez barvanja.",
        "Profili/nosilci: aluminij, prašno barvano (RAL po dogovoru, privzeto RAL 7016).",
        "Pritrditev: bočno v fasado ali z vrha v ploščo; predrtje Ø + 1 mm (ekspanzija).",
        f"Razmak nosilcev največ {fmt(m.get('razmak_nosilcev', 1000))} mm; "
        "količine pritrdilnih elementov orientacijske.",
        "Risba NI statični izračun — nosilnost, sidranje in veterno breme "
        "preveri usposobljen strokovnjak.",
    ]
    opombe_blok(ax, 246, 74, 162, opombe)

    # ==================== ISO NASLOVNI BLOK + REVIZIJE ====================
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    revizije = c.get("revizije") or [
        ["A", datum, "Prva izdaja", c["izdelal"] or "—"]]
    tabela_revizij(ax, 10, 10, [15, 35, 150, 30], revizije)
    mat_cel = ("ALU okvir + WPC lamele"
               if "WPC" in (c.get("material_lamel") or "").upper()
               else c["material"])[:26]
    naslovni_blok(ax, {
        "podjetje": c.get("podjetje") or "—",
        "ime": c["ime"], "risba_st": c["risba_st"],
        "rev": revizije[-1][0], "merilo": merilo_niz,
        "datum": datum, "izdelal": c["izdelal"],
        "pregledal": c.get("pregledal") or "—",
        "odobril": c.get("odobril") or "—",
        "material": mat_cel, "list": "1 od 1",
        "stranka": c.get("stranka") or "—", "objekt": c.get("objekt") or "—",
    })


PREDLOGE["ograda"] = narisi_ogrado      # star ključ (združljivost)
PREDLOGE["ograja"] = narisi_ogrado      # pravilno slovensko ime
PREDLOGE["pokončna"] = narisi_pokoncna


# ---------------------------------------------------------------- konfiguracija
PRIVZETO = {
    "predloga": "ograja",
    "ime": "BALKONSKA OGRAJA",
    "risba_st": "BO-001",
    "izdelal": "R. Pezdirc",
    "stranka": "",            # naročnik (glava + montažni list)
    "objekt": "",             # lokacija objekta (glava + montažni list)
    "dolzina_deske": 5800,    # tovarniška dolžina WPC deske (WoodCore 5,8 m)
    "dolzina_palice": 6000,   # tovarniška dolžina alu profila
    "kerf": 3.0,              # širina rezila (mm) — upoštevana v rezalnem načrtu
    "podjetje": "",           # ime podjetja v naslovnem bloku (neobvezno)
    "pregledal": "",          # neobvezno
    "odobril": "",            # neobvezno
    "revizije": None,         # ali [[rev, datum, opis, izdelal], ...]
    "datum": "",
    "merilo": "auto",
    "format": "A3",
    "izhod": "BO-001.pdf",
    "foto": "",
    "barva": "Antracit",      # ime iz WPC_BARVE ali #hex
    "profil": "ROMB 67",      # ime/dimenzija WPC deske (WoodCore)
    "material": "Aluminij (prašno barvano)",
    "material_lamel": "WPC lesni kompozit",
    "deli": None,
    "opombe": None,
    "mere": {"sirina": 3000, "visina": 1200, "globina": 1200,
             "odcep": 60, "profil_v": 40, "lamela_v": 60,
             "debelina": 20, "lamele": 13, "razmak_nosilcev": 1000,
             # predloga "pokončna":
             "deska_sirina": 100, "deska_debelina": 20, "vrzel": 20,
             "rocaj_v": 40, "razmak_stebrov": 1500,
             "steber_sirina": 60, "steber_debelina": 40},
}


def zdruzi(cfg):
    izhod = dict(PRIVZETO)
    izhod.update(cfg or {})
    izhod["mere"] = {**PRIVZETO["mere"], **(cfg or {}).get("mere", {})}
    return izhod


def vprasanje(besedilo, privzeto, tip=str):
    while True:
        odg = input(f"{besedilo} [{privzeto}]: ").strip()
        if not odg:
            return privzeto
        try:
            return tip(odg)
        except ValueError:
            print("  Neveljaven vnos, poskusi znova.")


def interaktivno():
    print("=" * 52)
    print(" GENERATOR TEHNIČNE RISBE — ograje")
    print("=" * 52)
    print("(Pritisni Enter za privzeto vrednost v oglatih oklepajih.)\n")
    c = {}
    c["predloga"] = vprasanje("Predloga (ograja / pokončna)", "ograja")
    pok = c["predloga"].strip().lower() == "pokončna"
    c["ime"] = vprasanje("Ime projekta", "BALKONSKA OGRAJA" if not pok
                         else "POKONČNA OGRAJA")
    c["risba_st"] = vprasanje("Številka risbe", PRIVZETO["risba_st"])
    c["izdelal"] = vprasanje("Izdelal", PRIVZETO["izdelal"])
    c["podjetje"] = vprasanje("Podjetje (Enter = brez)", PRIVZETO["podjetje"])
    c["stranka"] = vprasanje("Naročnik / stranka (Enter = brez)", "")
    c["objekt"] = vprasanje("Objekt / lokacija (Enter = brez)", "")
    m = {}
    m["sirina"] = vprasanje("Širina ograje (mm)", 3000, float)
    m["visina"] = vprasanje("Višina od tal do vrha (mm)", 1200, float)
    m["odcep"] = vprasanje("Odcep od tal (mm)", 60, float)
    if pok:
        m["lamele"] = vprasanje("Število desk", 20, int)
        m["deska_sirina"] = vprasanje("Širina desk (mm)", 100, float)
        m["deska_debelina"] = vprasanje("Debelina desk (mm)", 20, float)
        m["vrzel"] = vprasanje("Vrzel med deskami (mm)", 20, float)
        m["razmak_stebrov"] = vprasanje("Razmak stebrov (mm)", 1500, float)
        c["profil"] = vprasanje("Model deske", "POLNA DESKA 100")
    else:
        m["globina"] = vprasanje("Globina / stranska dolžina (mm)", 1200,
                                 float)
        m["lamele"] = vprasanje("Število lamel", 13, int)
        m["lamela_v"] = vprasanje("Višina lamel (mm)", 60, float)
        m["debelina"] = vprasanje("Debelina lamel (mm)", 20, float)
        m["razmak_nosilcev"] = vprasanje("Razmak nosilcev (mm)", 1000, float)
        c["profil"] = vprasanje("Profil / model deske", "ROMB 67")
    c["material"] = vprasanje("Material profilov", PRIVZETO["material"])
    c["material_lamel"] = vprasanje("Material lamel/desk",
                                    PRIVZETO["material_lamel"])
    c["foto"] = vprasanje("Pot do fotografije (Enter = brez)", "")
    c["izhod"] = vprasanje("Ime izhodne datoteke", PRIVZETO["izhod"])
    c["mere"] = m
    return zdruzi(c)


def nalozi_konf(pot):
    with open(pot, "r", encoding="utf-8") as f:
        podatki = yaml.safe_load(f) or {}
    return zdruzi(podatki)


def montazni_osnova(ax, c, pot_rows, rez_rows, viz_traki, koraki):
    """Skupni izgled montažnega lista (stran 2) za vse predloge."""
    iso_okvir(ax)
    oznaka(ax, 20, 286, "MONTAŽNI LIST — POTREBŠČINE")
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    ax.text(20, 278, f"Naloga: {c['risba_st']}   •   Datum: {datum}",
            fontsize=9, ha="left", va="center")
    ax.text(20, 272, f"Stranka: {c.get('stranka') or '—'}   •   Objekt: "
            f"{c.get('objekt') or '—'}", fontsize=9, ha="left", va="center")

    tabela(ax, 20, 256, [90, 60, 35, 75], 7.0,
           [["NAZIV", "SPECIFIKACIJA", "KOLIČINA", "OPOMBA"], *pot_rows],
           naslov="POTREBŠČINE")

    if rez_rows:
        tabela(ax, 20, 197, [45, 55, 75, 45, 40], 7.0, rez_rows,
               naslov="REZALNI NAČRT")
    else:
        opombe_blok(ax, 20, 197, 260,
                    ["Deska je krajša od enega kosa — spoj/rez po dogovoru "
                     "s proizvajalcem."], naslov_t="REZALNI NAČRT")

    kerf = c.get("kerf", 3.0)
    b_lam = barva_hex(c.get("barva"))
    y = 130
    if viz_traki:
        maxdl = max(dl for dl, _ in viz_traki)
        sk = 260.0 / maxdl
        prikaz_b = min(len(viz_traki), 5)
        n_vrst_r = (len(rez_rows) - 1) if rez_rows else 1
        y = 197 - (8.5 + 7 + n_vrst_r * 7) - 8
        skup_k = sum(ln for _, kosi in viz_traki for _, ln in kosi)
        skup_d = sum(dl for dl, _ in viz_traki)
        izk = skup_k / skup_d * 100 if skup_d else 0
        ax.text(20, y + 2, f"VIZUALNI REZ • kerf {fmt(kerf)} mm • "
                f"izkoristek {izk:.0f} % • ostanek = trak − kosi − rez",
                fontsize=7, color="#555555", ha="left", va="center")
        for ti, (dl, kosi) in enumerate(viz_traki[:prikaz_b]):
            y -= 10
            x = 20
            for lab, ln in kosi:
                w = max(2.0, ln * sk)
                pravokotnik(ax, x, y, w, 7, fill=b_lam, lw=0.5)
                if w > 14:
                    ax.text(x + w / 2, y + 3.5, lab, ha="center",
                            va="center", fontsize=6, color="white")
                x += w
            ost = dl - sum(ln for _, ln in kosi) - kerf * len(kosi)
            w_ost = max(2.0, ost * sk)
            pravokotnik(ax, x, y, w_ost, 7, fill="#e9e9e9", lw=0.5)
            if w_ost > 16:
                ax.text(x + w_ost / 2, y + 3.5, f"ostanek {fmt(ost)}",
                        ha="center", va="center", fontsize=6)
            ax.text(18, y + 3.5, f"{ti + 1}", ha="right", va="center",
                    fontsize=6.5, fontweight="bold")
        if len(viz_traki) > prikaz_b:
            y -= 8
            ax.text(20, y, f"… ostali traki po istem vzorcu "
                    f"(skupaj {len(viz_traki)})", fontsize=6.5,
                    color="#555555", ha="left", va="center")

    opombe_blok(ax, 20, y - 6, 260, koraki, naslov_t="MONTAŽNI KORAKI")

    kontrola = [
        "□ preveri dejanske mere objekta",
        "□ označi lege pritrditve (razmak)",
        "□ preveri razvod inštalacij",
        "□ sidranje po nosilnosti stene/plošče",
        "□ statiko potrdil usposobljen strokovnjak",
        "□ kontrola višine in ravni",
        "□ slika končno izvedbo",
    ]
    opombe_blok(ax, 288, 256, 120, kontrola, naslov_t="KONTROLA NA TERENU")

    for x0, w, ime in ((20, 126, "IZDELAL (podpis)"),
                       (148, 126, "STRANKA (prejem dela)"),
                       (276, 132, "DATUM MONTAŽE")):
        pravokotnik(ax, x0, 12, w, 16, fill="none", lw=0.7)
        ax.text(x0 + 2, 24.5, ime, fontsize=6.5, color="#555555",
                ha="left", va="center")
        crta(ax, x0 + 6, 18, x0 + w - 6, 18, lw=0.5)


def narisi_montazni_list(ax, c):
    """Stran 2 za predlogo "ograda" (prečna)."""
    m = c["mere"]
    sir = m["sirina"]
    zg, sp, lamele, vrzel, n = razpored(m)
    raz = m.get("razmak_nosilcev", 1000)
    n_nos = max(2, math.ceil(sir / raz) + 1)
    vijaki = n * n_nos * 2
    profil = c.get("profil") or "ROMB 67"
    dl_deske = c.get("dolzina_deske", 5800)
    dl_palice = c.get("dolzina_palice", 6000)
    kerf = c.get("kerf", 3.0)
    na_desko = (max(1, int((dl_deske + kerf) // (sir + kerf)))
                if dl_deske >= sir else 0)
    deske = (math.ceil(n / na_desko) if na_desko
             else math.ceil(n * sir / dl_deske))
    palice = math.ceil((2 * sir + 2 * kerf) / dl_palice)
    pot = [
        [f"WPC deska {profil}", f"{fmt(dl_deske)} mm", f"{deske} kos",
         f"skupaj {fmt(n * sir / 1000)} m lamel"],
        ["Alu profili 80×40 (zg.) + 60×40 (sp.)", f"{fmt(dl_palice)} mm",
         f"{palice} kos", f"obe sta dolgi {fmt(sir)} mm"],
        ["Nosilni nosilec 50×50×5", "—", f"{n_nos} kos",
         f"razmak ≤ {fmt(raz)} mm"],
        ["RF vijaki M8×70 (lamela↔profil)", "—", f"{vijaki} kos",
         f"2 na priključek ({n * n_nos}) • Ø+1 mm"],
        ["Fasadni vijaki Ø8×80 + tipli", "—", f"{n_nos * 2} kos",
         "2 na nosilec"],
    ]
    rez_rows = None
    viz_traki = []
    if na_desko:
        rez_rows = [["DESKA", "KOSOV NA DESKI", "LAMELE ŠT.",
                     "DOLŽINA (mm)", "OSTANEK (mm)"]]
        prikaz = min(deske, 6)
        for i in range(prikaz):
            zac = min(na_desko, n - i * na_desko)
            prva = i * na_desko + 1
            ost = dl_deske - zac * sir - zac * kerf
            rez_rows.append([str(i + 1), str(zac), f"{prva}–{prva + zac - 1}",
                             fmt(sir), fmt(ost)])
        if deske > prikaz:
            rez_rows.append(["…", "", f"skupaj {deske} desk", "", ""])
        for i in range(deske):
            zac = min(na_desko, n - i * na_desko)
            prva = i * na_desko + 1
            viz_traki.append((dl_deske,
                              [(f"L{prva + j}", sir) for j in range(zac)]))
    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lego nosilcev (razmak največ {fmt(raz)} mm); "
        "preveri razvod inštalacij pred vrtanjem.",
        "Pritrdi nosilce (bočno/vrh po dogovoru — glej DETAJL "
        "PRITRJEVANJA); za WPC vedno predrtje Ø + 1 mm.",
        "Vgradi zgornji in spodnji alu profil; kontroliraj višino "
        "in ravnost.",
        "Vgradi lamele (RF vijaki skozi notranjo alu cev; brez "
        "predrtja ne vrtaj!).",
        "Kontrola ravni in višine, slika izvedbo, pridobi podpis "
        "stranke.",
    ]
    montazni_osnova(ax, c, pot, rez_rows, viz_traki, koraki)

    # izračun višine + poraba/odpad (viden na montažnem listu)
    cona_z = zg[0] - sp[1]
    n_vrst_r = (len(rez_rows) - 1) if rez_rows else 0
    y_iz = 197 - (8.5 + 7 + n_vrst_r * 7) - 22
    ax.text(20, y_iz, f"IZRAČUN VIŠINE: {fmt(m['visina'])} = "
            f"{fmt(m['profil_v'])} (zgornji profil) + {fmt(cona_z)} "
            f"(lamele: {n} × {fmt(m['lamela_v'])} + {n - 1} × vrzel "
            f"{vrzel:.1f} mm) + {fmt(m['profil_v'])} (spodnji profil) + "
            f"{fmt(m['odcep'])} (odcep)", fontsize=6.5, color="#555555",
            ha="left", va="center")
    por_m = deske * dl_deske / 1000
    odp_m = por_m - n * sir / 1000
    ax.text(20, y_iz - 5, f"PORABA: deske {deske} kos = {por_m:.2f} m • "
            f"odpad {odp_m:.2f} m ({odp_m / por_m * 100:.0f} %) • alu "
            f"palice {palice} kos = {palice * dl_palice / 1000:.1f} m",
            fontsize=6.5, color="#555555", ha="left", va="center")
    por_m = deske * dl_deske / 1000
    por_alu = palice * dl_palice / 1000
    kolicine = {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{deske} kos = {fmt(por_m)}",
         "m", "wpc_deska_m", por_m),
        ("Alu profili (nabava)", f"{palice} kos = {fmt(por_alu)}", "m",
         "alu_m", por_alu),
        ("Nosilni nosilci 50×50×5", f"{n_nos}", "kos", "nosilec_kos", n_nos),
        ("RF vijaki M8×70", f"{vijaki}", "kos", "vijak_kos", vijaki),
        ("Fasadni vijaki Ø8×80 + tipli", f"{n_nos * 2}", "kos",
         "fasadni_kos", n_nos * 2),
    ]}
    return {"postavke": kolicine["postavke"]}


def narisi_montazni_pokoncna(ax, c):
    """Stran 2 za predlogo "pokončna" (stebri + navpične deske)."""
    m = c["mere"]
    sir, vis = m["sirina"], m["visina"]
    odcep = m["odcep"]
    p = razpored_pokoncna(m)
    n_d, n_s = p["n_desk"], p["n_stebrov"]
    deska_h = p["deske_h"]
    profil = c.get("profil") or "POLNA DESKA 100"
    dl_deske = c.get("dolzina_deske", 5800)
    dl_palice = c.get("dolzina_palice", 6000)
    kerf = c.get("kerf", 3.0)
    na_desko = (max(1, int((dl_deske + kerf) // (deska_h + kerf)))
                if dl_deske >= deska_h else 0)
    deske = (math.ceil(n_d / na_desko) if na_desko
             else math.ceil(n_d * deska_h / dl_deske))
    palice_s = math.ceil(n_s * (vis + kerf) / dl_palice)
    vijaki = n_d * n_s * 2
    pot = [
        [f"WPC deska {profil}", f"{fmt(dl_deske)} mm", f"{deske} kos",
         f"skupaj {fmt(n_d * deska_h / 1000)} m desek"],
        ["Alu steber 60×40", f"{fmt(dl_palice)} mm", f"{palice_s} kos",
         f"{n_s} stebrov (L = {fmt(vis)} mm)"],
        ["Ročaj (WPC/alu)", f"{fmt(sir)} mm", "1 kos",
         "pritrjen na steber"],
        ["Osnova za steber (vrh)", "90×90×6", f"{n_s} kos",
         "anker M10 × 2 na osnovo"],
        ["Vijaki M8×70 (deska↔steber)", "—", f"{vijaki} kos",
         f"2 na desko na steber • Ø+1 mm"],
        ["Anker M10", "—", f"{n_s * 2} kos",
         "2 na osnovo • sidranje ≥ 60 mm (beton C20/25)"],
    ]
    rez_rows = None
    viz_traki = []
    if na_desko:
        rez_rows = [["DESKA", "KOSOV NA DESKI", "DESKE ŠT.",
                     "DOLŽINA (mm)", "OSTANEK (mm)"]]
        prikaz = min(deske, 6)
        for i in range(prikaz):
            zac = min(na_desko, n_d - i * na_desko)
            prva = i * na_desko + 1
            ost = dl_deske - zac * deska_h - zac * kerf
            rez_rows.append([str(i + 1), str(zac), f"{prva}–{prva + zac - 1}",
                             fmt(deska_h), fmt(ost)])
        if deske > prikaz:
            rez_rows.append(["…", "", f"skupaj {deske} desk", "", ""])
        for i in range(deske):
            zac = min(na_desko, n_d - i * na_desko)
            prva = i * na_desko + 1
            viz_traki.append((dl_deske,
                              [(f"D{prva + j}", deska_h)
                               for j in range(zac)]))
    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lege stebrov (razmak največ {fmt(m['razmak_stebrov'])} mm); "
        "preveri razvod inštalacij pred vrtanjem.",
        "Pritrdi osnove z anker M10 (vrh v ploščo — glej DETAJL "
        "PRITRJEVANJA); kontroliraj ravnost.",
        "Postavi stebre; kontroliraj navpičnost.",
        "Vgradi deske (2 vijaka M8×70 na desko na steber; predrtje "
        "Ø + 1 mm).",
        "Vgradi ročaj, kontrola ravni in višine, slika izvedbo, podpis "
        "stranke.",
    ]
    montazni_osnova(ax, c, pot, rez_rows, viz_traki, koraki)

    cona_z = p["deske_z"][1] - p["deske_z"][0]
    n_vrst_r = (len(rez_rows) - 1) if rez_rows else 0
    y_iz = 197 - (8.5 + 7 + n_vrst_r * 7) - 22
    ax.text(20, y_iz, f"IZRAČUN VIŠINE: {fmt(vis)} = {fmt(m['rocaj_v'])} "
            f"(ročaj) + {fmt(deska_h)} (deske) + {fmt(odcep)} (odcep) • "
            f"ŠIRINA: {fmt(sir)} = {n_d} × {fmt(m['deska_sirina'])} + "
            f"{n_d - 1} × vrzel {p['vrzel']:.1f} mm",
            fontsize=6.5, color="#555555", ha="left", va="center")
    por_s = deske * dl_deske / 1000
    odp_s = por_s - n_d * deska_h / 1000
    ax.text(20, y_iz - 5, f"PORABA: deske {deske} kos = {por_s:.2f} m • "
            f"odpad {odp_s:.2f} m ({odp_s / por_s * 100:.0f} %) • alu "
            f"palice {palice_s} kos = {palice_s * dl_palice / 1000:.1f} m",
            fontsize=6.5, color="#555555", ha="left", va="center")
    por_s = deske * dl_deske / 1000
    por_st = palice_s * dl_palice / 1000
    return {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{deske} kos = {fmt(por_s)}",
         "m", "wpc_deska_m", por_s),
        ("Alu stebri (nabava)", f"{palice_s} kos = {fmt(por_st)}", "m",
         "alu_m", por_st),
        ("Ročaj", "1", "kos", "rocaj_kos", 1),
        ("Osnove za steber", f"{n_s}", "kos", "osnova_kos", n_s),
        ("Vijaki M8×70", f"{vijaki}", "kos", "vijak_kos", vijaki),
        ("Anker M10", f"{n_s * 2}", "kos", "anker_kos", n_s * 2),
    ]}


def preveri_cfg(cfg):
    """Kontrola pravilnosti PRED izvozom. Vrne seznam napak (prazno = OK)."""
    nap = []
    m = cfg.get("mere", {})
    for k in ("sirina", "visina"):
        v = m.get(k)
        if not isinstance(v, (int, float)) or v <= 0:
            nap.append(f"Mera '{k}' mora biti pozitivno število.")
    odcep = m.get("odcep", 0)
    if not isinstance(odcep, (int, float)) or odcep < 0:
        nap.append("Mera 'odcep' ne sme biti negativna.")
    if cfg.get("predloga") == "pokončna":
        rv = m.get("rocaj_v", 40)
        cona = m.get("visina", 0) - odcep - rv
        if cona <= 0:
            nap.append("Višina ročaja in odcepa presega skupno višino.")
        ds = m.get("deska_sirina", 0)
        if ds > m.get("sirina", 0) - m.get("steber_sirina", 60):
            nap.append(f"Deska ({ds:.0f} mm) je širša kot razpon ograje "
                       "med stebroma.")
        if m.get("razmak_stebrov", 0) <= m.get("steber_sirina", 60):
            nap.append("Razmak stebrov mora biti večji od širine stebra.")
        if m.get("lamele", 0) < 1:
            nap.append("Število desk mora biti vsaj 1.")
    else:
        cona = m.get("visina", 0) - odcep - 2 * m.get("profil_v", 40)
        if cona <= 0:
            nap.append("Višina profilov in odcepa presega skupno višino.")
        elif m.get("lamele", 0) * m.get("lamela_v", 0) > cona:
            nap.append(f"Lamele se ne prilegajo: {m.get('lamele')} × "
                       f"{m.get('lamela_v')} mm > cona {cona:.0f} mm.")
    kerf = cfg.get("kerf", 3.0)
    if not isinstance(kerf, (int, float)) or kerf < 0:
        nap.append("Kerf (širina rezila) ne sme biti negativen.")
    dl = cfg.get("dolzina_deske", 5800)
    if not isinstance(dl, (int, float)) or dl <= 0:
        nap.append("Dolžina deske mora biti pozitivna.")
    if cfg.get("foto") and not os.path.isfile(cfg["foto"]):
        nap.append(f"Fotografija ne obstaja: {cfg['foto']}")
    return nap


def narisi_predracun(ax, c, postavke):
    """Stran 3: orientacijski predračun (samo če so cene v konfiguraciji)."""
    cene = c.get("cene") or {}
    iso_okvir(ax)
    oznaka(ax, 20, 286, "PREDRAČUN (ORIENTACIJSKI)")
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    ax.text(20, 278, f"Naloga: {c['risba_st']}   •   Datum: {datum}   •   "
            f"Veljavnost: 30 dni", fontsize=9, ha="left", va="center")
    ax.text(20, 272, f"Stranka: {c.get('stranka') or '—'}   •   Objekt: "
            f"{c.get('objekt') or '—'}", fontsize=9, ha="left", va="center")

    skup = 0.0
    vrste = [["POSTAVKA", "KOLIČINA", "CENA ENOTE", "SKUPAJ"]]
    for (naziv, kol_str, enota, kljuc, num) in postavke:
        cena = cene.get(kljuc)
        if cena is None or not num:
            continue
        sk = num * cena
        vrste.append([naziv, f"{kol_str} {enota}",
                      f"{cena:.2f} EUR/{enota}", f"{sk:.2f} EUR"])
        skup += sk
    ur, ur_c = cene.get("dela_ure"), cene.get("dela_ur_cena")
    if ur and ur_c:
        vrste.append(["Delo (izdelava + montaža)", f"{fmt(ur)} h",
                      f"{ur_c:.2f} EUR/h", f"{ur * ur_c:.2f} EUR"])
        skup += ur * ur_c
    vrste.append(["SKUPAJ (brez DDV)", "", "", f"{skup:.2f} EUR"])
    tabela(ax, 20, 256, [110, 55, 60, 45], 7.5, vrste, naslov="PREDRAČUN")

    opombe_blok(ax, 20, 185, 260, [
        "Predračun je ORIENTACIJSKI in brez DDV; veljavnost 30 dni.",
        "Cene materialov so nastavljene v konfiguraciji ('cene'); "
        "količine po dejanski porabi, odpad je prikazan posebej.",
        "Konstrukcijsko ustreznost (nosilnost, sidranje, veterno breme) "
        "preveri usposobljen strokovnjak — risba ni statični izračun.",
        "Montaža po dogovoru; končno poravnanje po prevzemu dela.",
    ], naslov_t="OPOMBE K PREDRAČUNU")


# ---------------------------------------------------------------- glavno
def generiraj(cfg, dpi_png=200):
    """Iz konfiguracije nariše risbo in vrne (pot_pdf, pot_png)."""
    pred_norm = ("pokončna" if str(cfg.get("predloga", "")).strip().lower()
                 == "pokončna" else "ograja")
    predloga = PREDLOGE.get(pred_norm) or PREDLOGE.get("ograja")
    if predloga is None:
        raise ValueError(f"Neznana predloga: {cfg.get('predloga')} "
                         f"(na voljo: {', '.join(PREDLOGE)})")
    napake = preveri_cfg(cfg)
    if napake:
        raise ValueError("Kontrola pravilnosti ni uspela — PDF ni bil "
                         "izdelan:\n- " + "\n- ".join(napake))

    fig, ax = nov_list()
    predloga(ax, cfg)
    fig2 = None
    kolicine = None
    ml_fn = {"ograja": narisi_montazni_list,
             "ograda": narisi_montazni_list,
             "pokončna": narisi_montazni_pokoncna}.get(pred_norm)
    if ml_fn:
        try:
            fig2, ax2 = nov_list()
            kolicine = ml_fn(ax2, cfg)
        except Exception:
            if fig2 is not None:
                plt.close(fig2)
            fig2 = None
    izhod = os.path.abspath(cfg["izhod"])
    with PdfPages(izhod) as pdf:
        pdf.savefig(fig)
        if fig2 is not None:
            pdf.savefig(fig2)
        fig3 = None
        if kolicine and (cfg.get("cene") or {}):
            try:
                fig3, ax3 = nov_list()
                narisi_predracun(ax3, cfg, kolicine["postavke"])
                pdf.savefig(fig3)
            except Exception:
                if fig3 is not None:
                    plt.close(fig3)
                fig3 = None
    png = os.path.splitext(izhod)[0] + ".png"
    fig.savefig(png, dpi=dpi_png)
    dodatni = []
    if fig2 is not None:
        p2 = os.path.splitext(izhod)[0] + "-montazni-list.png"
        fig2.savefig(p2, dpi=dpi_png)
        dodatni.append(p2)
        plt.close(fig2)
    if fig3 is not None:
        p3 = os.path.splitext(izhod)[0] + "-predracun.png"
        fig3.savefig(p3, dpi=dpi_png)
        dodatni.append(p3)
        plt.close(fig3)
    plt.close(fig)
    return izhod, png, dodatni


def main():
    ap = argparse.ArgumentParser(description="Generator tehničnih risb (PDF A3).")
    ap.add_argument("konf", nargs="?",
                    help="pot do projekt.yaml (brez: vprašanja v terminalu)")
    ap.add_argument("-o", "--izhod", help="ime izhodne PDF datoteke")
    a = ap.parse_args()

    cfg = nalozi_konf(a.konf) if a.konf else interaktivno()
    if a.izhod:
        cfg["izhod"] = a.izhod

    try:
        izhod, png, dodatni = generiraj(cfg)
    except ValueError as e:
        sys.exit(str(e))

    print(f"[OK] Risba:    {izhod}")
    print(f"[OK] Predogled: {png}")
    for p in dodatni:
        print(f"[OK] Dodatno: {p}")


if __name__ == "__main__":
    main()
