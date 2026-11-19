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
        "Vse mere v mm; pred izdelavo preveri dejanske mere na objektu.",
        "Splošne tolerance: ISO 2768-m (razen drugače navedeno).",
        f"Lamele: {profil} — WPC (bambus + HDPE), 15 let garancije, brez barvanja.",
        "Profili/nosilci: aluminij, prašno barvano (RAL po dogovoru, privzeto RAL 7016).",
        "Pritrditev: bočno v fasado ali z vrha v ploščo; predrtje Ø + 1 mm (ekspanzija).",
        f"Razmak nosilcev največ {fmt(m.get('razmak_nosilcev', 1000))} mm; "
        "količine pritrdilnih elementov orientacijske.",
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


PREDLOGE["ograda"] = narisi_ogrado


# ---------------------------------------------------------------- konfiguracija
PRIVZETO = {
    "predloga": "ograda",
    "ime": "BALKONSKA OGRAJA",
    "risba_st": "BO-001",
    "izdelal": "R. Pezdirc",
    "stranka": "",            # naročnik (glava + montażni list)
    "objekt": "",             # lokacija objekta (glava + montażni list)
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
             "debelina": 20, "lamele": 13, "razmak_nosilcev": 1000},
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
    print(" GENERATOR TEHNIČNE RISBE — balkonska ograja")
    print("=" * 52)
    print("(Pritisni Enter za privzeto vrednost v oglatih oklepajih.)\n")
    c = {}
    c["ime"] = vprasanje("Ime projekta", PRIVZETO["ime"])
    c["risba_st"] = vprasanje("Številka risbe", PRIVZETO["risba_st"])
    c["izdelal"] = vprasanje("Izdelal", PRIVZETO["izdelal"])
    c["podjetje"] = vprasanje("Podjetje (Enter = brez)", PRIVZETO["podjetje"])
    m = {}
    m["sirina"] = vprasanje("Širina ograje (mm)", 3000, float)
    m["visina"] = vprasanje("Višina od tal do vrha (mm)", 1200, float)
    m["globina"] = vprasanje("Globina / stranska dolžina (mm)", 1200, float)
    m["lamele"] = vprasanje("Število lamel", 13, int)
    m["lamela_v"] = vprasanje("Višina lamel (mm)", 60, float)
    m["debelina"] = vprasanje("Debelina lamel (mm)", 20, float)
    m["odcep"] = vprasanje("Odcep od tal (mm)", 60, float)
    m["razmak_nosilcev"] = vprasanje("Razmak nosilcev (mm)", 1000, float)
    c["material"] = vprasanje("Material profilov", PRIVZETO["material"])
    c["profil"] = vprasanje("Profil / model deske", PRIVZETO["profil"])
    c["foto"] = vprasanje("Pot do fotografije (Enter = brez)", "")
    c["izhod"] = vprasanje("Ime izhodne datoteke", PRIVZETO["izhod"])
    c["mere"] = m
    return zdruzi(c)


def nalozi_konf(pot):
    with open(pot, "r", encoding="utf-8") as f:
        podatki = yaml.safe_load(f) or {}
    return zdruzi(podatki)


def narisi_montazni_list(ax, c):
    """Stran 2: potrebščine, rezalni načrt, montażni koraki, podpisi."""
    m = c["mere"]
    sir = m["sirina"]
    zg, sp, lamele, vrzel, n = razpored(m)
    raz = m.get("razmak_nosilcev", 1000)
    n_nos = max(2, math.ceil(sir / raz) + 1)
    vijaki = n * n_nos * 2
    profil = c.get("profil") or "ROMB 67"
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")

    iso_okvir(ax)
    oznaka(ax, 20, 286, "MONTAŽNI LIST — POTREBŠČINE")
    ax.text(20, 278, f"Nalog: {c['risba_st']}   •   Datum: {datum}",
            fontsize=9, ha="left", va="center")
    ax.text(20, 272, f"Stranka: {c.get('stranka') or '—'}   •   Objekt: "
            f"{c.get('objekt') or '—'}", fontsize=9, ha="left", va="center")

    dl_deske = c.get("dolzina_deske", 5800)
    dl_palice = c.get("dolzina_palice", 6000)
    kerf = c.get("kerf", 3.0)
    na_desko = (max(1, int((dl_deske + kerf) // (sir + kerf)))
                if dl_deske >= sir else 0)
    deske = (math.ceil(n / na_desko) if na_desko
             else math.ceil(n * sir / dl_deske))
    palice = math.ceil((2 * sir + 2 * kerf) / dl_palice)
    b_lam = barva_hex(c.get("barva"))
    pot = [
        [f"WPC deska {profil}", f"{fmt(dl_deske)} mm", f"{deske} kos",
         f"skupaj {fmt(n * sir / 1000)} m lamel"],
        ["Alu profil 80×40×3", f"{fmt(dl_palice)} mm", f"{palice} kos",
         "zgornji profil"],
        ["Alu profil 60×40×3", f"{fmt(dl_palice)} mm", "1 kos",
         "spodnji profil"],
        ["Nosilni nosilec 50×50×5", "—", f"{n_nos} kos",
         f"razmak ≤ {fmt(raz)} mm"],
        ["RF vijaki M8×70 (lamela↔profil)", "—", f"{vijaki} kos",
         f"2 na priključek ({n * n_nos}) • Ø+1 mm"],
        ["Fasadni vijaki Ø8×80 + tipli", "—", f"{n_nos * 2} kos",
         "2 na nosilec"],
    ]
    tabela(ax, 20, 256, [90, 60, 35, 75], 7.0,
           [["NAZIV", "SPECIFIKACIJA", "KOLIČINA", "OPOMBA"], *pot],
           naslov="POTREBŠČINE")

    if na_desko:
        vrste = [["DESKA", "KOSOV NA DESKI", "LAMELE ŠT.",
                  "DOLŽINA (mm)", "OSTANEK (mm)"]]
        prikaz = min(deske, 6)
        for i in range(prikaz):
            zac = min(na_desko, n - i * na_desko)
            prva = i * na_desko + 1
            ost = dl_deske - zac * sir - zac * kerf
            vrste.append([str(i + 1), str(zac), f"{prva}–{prva + zac - 1}",
                          fmt(sir), fmt(ost)])
        if deske > prikaz:
            vrste.append(["…", "", f"skupaj {deske} desk", "", ""])
        tabela(ax, 20, 197, [45, 55, 75, 45, 40], 7.0, vrste,
               naslov="REZALNI NAČRT — LAMELE")
    else:
        opombe_blok(ax, 20, 197, 260,
                    ["Deska je krajša od lamele — spoj/rez po dogovoru "
                     "s proizvajalcem."], naslov_t="REZALNI NAČRT — LAMELE")

    # vizualni rezalni načrt (po vzoru rezalnih optimizatorjev):
    # vsaka deska = trak s segmenti lamel + ostanek (kerf upoštevan)
    y = 140
    if na_desko and deske:
        sk = 260.0 / dl_deske
        prikaz_b = min(deske, 5)
        y = 197 - (8.5 + 7 + (min(deske, 6) + (1 if deske > 6 else 0)) * 7) - 8
        izkoristek = n * sir / (deske * dl_deske) * 100
        ax.text(20, y + 2, f"VIZUALNI REZ • kerf {fmt(kerf)} mm • "
                f"izkoristek {izkoristek:.0f} % • ostanek = deska − kosi − "
                "rez", fontsize=7, color="#555555", ha="left", va="center")
        for i in range(prikaz_b):
            y -= 10
            zac = min(na_desko, n - i * na_desko)
            x = 20
            for j in range(zac):
                w_seg = sir * sk
                pravokotnik(ax, x, y, w_seg, 7, fill=b_lam, lw=0.5)
                ax.text(x + w_seg / 2, y + 3.5, f"L{i * na_desko + j + 1}",
                        ha="center", va="center", fontsize=6, color="white")
                x += w_seg
            ost = dl_deske - zac * sir - zac * kerf
            w_ost = max(2.0, ost * sk)
            pravokotnik(ax, x, y, w_ost, 7, fill="#e9e9e9", lw=0.5)
            ax.text(x + w_ost / 2, y + 3.5, f"ostanek {fmt(ost)}",
                    ha="center", va="center", fontsize=6)
            ax.text(18, y + 3.5, f"D{i + 1}", ha="right", va="center",
                    fontsize=6.5, fontweight="bold")
        if deske > prikaz_b:
            y -= 8
            ax.text(20, y, f"… ostale deske po istem vzorcu "
                    f"(skupaj {deske} desk)", fontsize=6.5, color="#555555",
                    ha="left", va="center")

    opombe_blok(ax, 20, y - 6, 260, [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lego nosilcev (razmak največ {fmt(raz)} mm); "
        "preveri razvod inštalacij pred vrtanjem.",
        "Pritrdi nosilce (bočno/vrh po dogovoru); za WPC vedno "
        "predrtje Ø + 1 mm.",
        "Vgradi zgornji in spodnji alu profil; kontroliraj višino "
        "in ravnost.",
        "Vgradi lamele (RF vijaki skozi notranjo alu cev; brez "
        "predrtja ne vrtaj!).",
        "Kontrola ravni in višine, slika izvedbo, pridobi podpis "
        "stranke.",
    ], naslov_t="MONTAŽNI KORAKI")

    kontrola = [
        "□ preveri dejanske mere objekta",
        "□ označi lego nosilcev (razmak)",
        "□ preveri razvod inštalacij",
        "□ sidranje po nosilnosti stene/plošče",
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


# ---------------------------------------------------------------- glavno
def generiraj(cfg, dpi_png=200):
    """Iz konfiguracije nariše risbo in vrne (pot_pdf, pot_png)."""
    predloga = PREDLOGE.get(cfg.get("predloga"))
    if predloga is None:
        raise ValueError(f"Neznana predloga: {cfg.get('predloga')} "
                         f"(na voljo: {', '.join(PREDLOGE)})")
    fig, ax = nov_list()
    predloga(ax, cfg)
    fig2 = None
    if cfg.get("predloga") == "ograda":
        try:
            fig2, ax2 = nov_list()
            narisi_montazni_list(ax2, cfg)
        except Exception:
            if fig2 is not None:
                plt.close(fig2)
            fig2 = None
    izhod = os.path.abspath(cfg["izhod"])
    with PdfPages(izhod) as pdf:
        pdf.savefig(fig)
        if fig2 is not None:
            pdf.savefig(fig2)
    png = os.path.splitext(izhod)[0] + ".png"
    fig.savefig(png, dpi=dpi_png)
    png2 = None
    if fig2 is not None:
        png2 = os.path.splitext(izhod)[0] + "-montazni-list.png"
        fig2.savefig(png2, dpi=dpi_png)
        plt.close(fig2)
    plt.close(fig)
    return izhod, png, png2


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
        izhod, png, png2 = generiraj(cfg)
    except ValueError as e:
        sys.exit(str(e))

    print(f"[OK] Risba:    {izhod}")
    print(f"[OK] Predogled: {png}")
    if png2:
        print(f"[OK] Montažni list: {png2}")


if __name__ == "__main__":
    main()
