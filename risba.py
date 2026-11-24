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

from razrez import (shrani_ostanke,
                     razrez_podatki,
                     razrez_kosov_podatki,
                     stevilo_palic,
                     metrika_reza,
                     # F2 fasada — javni re-exporti (as zapis = namerni):
                     nalozi_ostanke as nalozi_ostanke,
                     pot_ostanki as pot_ostanki,
                     kos_iz_vira as kos_iz_vira)
from jedro import (odsteni, barva_hex, fmt, traki_nabava,
                   pritrdilo_material, vijak_dim, razpored,
                   pozicije_nosilcev, razdeli_po_odprtinah,
                   razpored_pokoncna, vrata_podatki, zdruzi,
                   nalozi_konf, preveri_cfg, PRIVZETO,
                   priporoceno_sidranje, SIDRANJA_PODLAGE,
                   BARVA_OKOVJA,
                   BARVA_LAMEL as BARVA_LAMEL,
                   WPC_BARVE as WPC_BARVE,
                   privzeto_stevilo_lamel as privzeto_stevilo_lamel)
from proizvodnja import (izracunaj_kolicine, predracun_znesek,
                         vrata_vrstice_potrebscine,
                         vrata_vrstice_kolicin as vrata_vrstice_kolicin,
                         proizvodni_model,
                         rezni_nacrt as rezni_nacrt_izracun)
import vrata as vrata
from matplotlib.patches import Circle, Polygon, Rectangle

# ---------------------------------------------------------------- konstante
A3_W, A3_H = 420.0, 297.0
CRNA = "#000000"
BARVA_OZN = "#1f2a3a"   # temne oznake pogledov / naslovi tabel
LW_THICK = 1.4          # debele črte (robovi, zgradba)
LW_THIN = 0.7           # tanke črte (kote, šrafura)
FS_DIM = 9              # besedilo kot

C30 = math.cos(math.radians(30))


# ---------------------------------------------------------------- risalni motor
def nov_list():
    """Prazna A3 krajinska stran; koordinate v mm (izvor spodaj levo)."""
    fig = plt.figure(figsize=(A3_W / 25.4, A3_H / 25.4))
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
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


def sachiranje(ax, x0, y0, x1, y1, razmak=2.6, lw=0.55, barva=None, z=1):
    """Šrafura z diagonali 45° (ISO 128-50) — zid, tla ali PREREZANI MATERIAL.

    Privzete vrednosti so za zid/tla (z=1, zadaj); prerezi kosov gredo
    PREKO barvnega polnila (z=4) s tanjšo črto (lw≈0,2).
    Vzorec je konvencija CAD sveta (ANSI31), implementirana samostojno.
    """
    w, h = x1 - x0, y1 - y0
    rect = Rectangle((x0, y0), w, h, facecolor="none", edgecolor="none")
    ax.add_patch(rect)
    barva = barva or CRNA
    for i in range(int((w + h) / razmak) + 2):
        xs = x0 + i * razmak - h
        ln, = ax.plot([xs, xs + h], [y0, y1], color=barva, lw=lw, zorder=z)
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


# Splošne tolerance — vrednosti ISO 2768-1, razred m (srednji).
# JAVNO OBJAVLJENE vrednosti standarda (vir naveden na listu),
# ne naše meritve — nič se ne izmišlja.
TOL_LINE = (
    ("0.5–3", "±0.1", "120–400", "±0.5"),
    ("3–6", "±0.1", "400–1000", "±0.8"),
    ("6–30", "±0.2", "1000–2000", "±1.2"),
    ("30–120", "±0.3", "2000–4000", "±2"),
)
TOL_KOTI = ("Koti (kratka stranica): ≤10 ±1° | 10–50 ±0°30′ | "
            "50–120 ±0°20′ | 120–400 ±0°10′ | >400 ±5′")


def blok_toleranc(ax, x0, y_top, sirina=128):
    """Blok splošnih toleranc (načrt 9) — kota brez ± ni določena.

    Vrednosti: ISO 2768-1, razred m (srednji) — objavljene vrednosti
    standarda. Kote brez oznake tolerance veljajo po tem bloku.
    """
    stolpci = [sirina * 0.34, sirina * 0.16, sirina * 0.34, sirina * 0.16]
    vrste = [("Mere (mm)", "±", "Mere (mm)", "±")] + list(TOL_LINE)
    y = tabela(ax, x0, y_top, stolpci, 4.8, vrste,
               naslov="SPLOŠNE TOLERANCE (ISO 2768-m)", fs=7.5)
    ax.text(x0 + 1, y - 3.4, TOL_KOTI, fontsize=6.5, ha="left", va="center")
    ax.text(x0 + 1, y - 7.6,
            "Kote brez oznake tolerance veljajo po tem bloku "
            "(vir: ISO 2768-1).",
            fontsize=6.5, ha="left", va="center", color="#555555")
    return y - 10.5


def opombe_blok(ax, x0, y_top, sirina, opombe,
                naslov_t="TEHNIČNI PODATKI IN OPOMBE",
                velikost=8.5, wrap=None, dno=None):
    """Blok opomb. Če je podan ``dno`` (npr. vrh naslovnega bloka), se
    besedilo SAMODEJNO skrči (manjša pisava), da ne zaide pod oviro —
    prej so bile zadnje opombe tiho SKRITE za naslovnim blokom.
    Če tudi pri najmanjši pisavi ne gre, je odvečni del odrezan z
    ISKRENIM opozorilom (nikoli tiho izpuščen).
    """
    if wrap is None:
        wrap = 86
    fs = float(velikost)
    while True:
        w = wrap if fs >= velikost else max(
            40, int(round(wrap * velikost / fs)))
        vrstice = []
        for i, o in enumerate(opombe, 1):
            vrstice.extend(textwrap.wrap(f"{i}. {o}", width=w) or [f"{i}."])
        raz = fs * 0.459
        visina = 8.5 + len(vrstice) * raz + 2
        if dno is None or y_top - visina >= dno - 1e-9 or fs <= 5.5:
            break
        fs = max(5.5, fs - 0.5)
    odrezano = False
    if dno is not None and y_top - visina < dno - 1e-9:
        prostor = y_top - dno - 10.5
        max_vrstic = max(1, int(prostor / raz))
        if len(vrstice) > max_vrstic:
            vrstice = vrstice[:max_vrstic]
            vrstice[-1] = vrstice[-1].rsplit(" ", 1)[0] + " …"
            visina = 8.5 + len(vrstice) * raz + 2
            odrezano = True
    pravokotnik(ax, x0, y_top - visina, sirina, visina, fill="white", lw=0.8)
    pravokotnik(ax, x0, y_top - 8.5, sirina, 8.5, fill=BARVA_OZN, lw=0)
    ax.text(x0 + sirina / 2, y_top - 4.25, naslov_t,
            ha="center", va="center", fontsize=9.5, fontweight="bold",
            color="white")
    y = y_top - 12
    for vrsta in vrstice:
        ax.text(x0 + 2.5, y, vrsta, ha="left", va="center", fontsize=fs)
        y -= raz
    if odrezano:
        ax.text(x0 + sirina / 2, y_top - visina + 1.2,
                "OPOMBE PRESEGAJO PROSTOR — celotno besedilo je v PDF "
                "(izvleci besedilo)",
                ha="center", va="bottom", fontsize=4.5,
                color="#b00020")
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


def status_vodni_zig(ax, status):
    """Statusni žig čez list (načrt 11) — loči osnutek/potrditev od izvedbe.

    Profesionalni listi nosijo žig stanja (FOR APPROVAL / NOT FOR
    CONSTRUCTION), da se osnutek ne zamenja za izvedbeno risbo.
    Žig je prosojen (alpha 0.12) in ne moti branja risbe.
    """
    zigi = {
        "V DELU": ("V DELU — OSNUTEK", "#555555", 40),
        "ZA POTRDITEV": ("ZA POTRDITEV — NI ZA IZDELAVO", "#b00020", 30),
    }
    if status in zigi:
        besedilo, barva, fs = zigi[status]
        ax.text(210, 148, besedilo, fontsize=fs, color=barva, alpha=0.12,
                ha="center", va="center", rotation=18, fontweight="bold",
                zorder=20)


def naslovni_blok(ax, p):
    """Glava risbe po vzoru ISO 7200 (desni spodnji kot)."""
    status_vodni_zig(ax, (p.get("status") or "V DELU").upper())
    x0, x1 = 250, 410
    pravokotnik(ax, x0, 10, x1 - x0, 28, fill="white", lw=1.2)
    # vrstica 4: podjetje | risba št. + revizija
    crta(ax, x0, 29, x1, 29, lw=0.7)
    crta(ax, 355, 29, 355, 38, lw=0.7)
    ax.text(x0 + 2, 33.5, p["podjetje"], fontsize=11, fontweight="bold",
            ha="left", va="center")
    # ISO 7200 (Plan 2): STATUS dokumenta (V DELU / ZA POTRDITEV / IZVEDENO)
    status = (p.get("status") or "V DELU").upper()
    ax.text(x0 + 2, 30.6, f"STATUS: {status}", fontsize=6.5,
            color="#555555", ha="left", va="center")
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


def narisi_zgradbo(v, zg, sp, lamele, x0r, x1r, b_lam, b_pro, cut=False):
    """Profila + lamele med x0r..x1r (realni mm). cut=True -> prerezi."""
    v.kocka(x0r, zg[0], x1r, zg[1], fill=b_pro)
    v.kocka(x0r, sp[0], x1r, sp[1], fill=b_pro)
    for z0, z1 in lamele:
        v.kocka(x0r, z0, x1r, z1, fill=b_lam)


def narisi_odprtine_in_vrata(ax, v, vp, b_lam, b_pro, merilo_s):
    """Nariše vrate/prehode v sprednji pogled (iz iste geometrije kot DXF)."""
    for vr, pod, plast, ozn in vp["elementi"]:
        if vr == "kvadrat" and plast != "DIMENSIONS":
            px, py, pw, ph = pod
            barva = (b_pro if plast in ("POSTS", "FRAME") else
                     BARVA_OKOVJA if plast == "HARDWARE" else b_lam)
            v.kocka(px, py, px + pw, py + ph, fill=barva)
        elif vr == "crta" and plast != "DIMENSIONS":
            x1, y1, x2, y2 = pod
            ax.plot([v.X(x1), v.X(x2)], [v.Y(y1), v.Y(y2)], color="white",
                    lw=0.5, zorder=5)
        elif vr == "krog":
            cx, cy, dd = pod
            ax.add_patch(Circle((v.X(cx), v.Y(cy)), max(0.4, dd * merilo_s / 2),
                                facecolor=BARVA_OKOVJA, edgecolor="none",
                                zorder=5))
    # oznake in kota širine odprtine
    for enota in vp["vrata"] + vp["prehodi"]:
        g = enota["g"]
        x = g["x"]
        w = g["odprtina"]["sirina"]
        ozn = enota["oznaka"]
        tip = g["tip"]
        ax.text(v.X(x + w / 2), v.Y(g.get("h", g["odprtina"]["visina"])) + 5,
                f"{ozn} ({tip})", ha="center", va="bottom", fontsize=6.5,
                fontweight="bold", color=CRNA)
        dim_h(ax, v.X(x), v.X(x + w), v.Y(0) - 8, v.Y(0), v.Y(0),
              f"{fmt(w)} mm")


def narisi_pokoncna(ax, c):
    m = c["mere"]
    sir, vis = m["sirina"], m["visina"]
    odcep, rv = m["odcep"], m["rocaj_v"]
    ss, sd = m["steber_sirina"], m["steber_debelina"]
    ds, dd = m["deska_sirina"], m["deska_debelina"]
    p = razpored_pokoncna(m)
    cona_z = p["deske_z"][1] - p["deske_z"][0]
    pritrditev = c.get("pritrditev") or "vrh"
    vijak_lamela_naziv = c.get("vijak_lamela") or "Vijak M8×70 (deska↔steber)"
    vijak_nosilec_naziv = c.get("vijak_nosilec") or "Anker M10"
    anker_dim = vijak_dim(vijak_nosilec_naziv, "M10")

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

    # vrata/prehodi (issue #3) — ista geometrija kot količine in DXF
    vp = vrata_podatki(c)
    for op in vp["opozorila"]:
        _opozori(op)

    # ==================== SPREDNJI POGLLED ====================
    oznaka(ax, 30, 286, "SPREDNJI POGLLED")
    v = Pogled(ax, 35, 206, s)
    for xr in p["deske_x"]:                    # deske (za stebri), brez odprtin
        for xa, xb in razdeli_po_odprtinah(xr, xr + ds, vp["odprtine"]):
            v.kocka(xa, p["deske_z"][0], xb, p["deske_z"][1], fill=b_lam)
    for xc in p["centri"]:                     # stebri (pred deskami)
        v.kocka(xc - ss / 2, 0, xc + ss / 2, vis, fill=b_pro)
        v.kocka(xc - ss / 2 - 15, 0, xc + ss / 2 + 15, 6, fill=b_pro)  # osnova
    v.kocka(0, vis - rv, sir, vis, fill=b_pro)  # ročaj
    narisi_odprtine_in_vrata(ax, v, vp, b_lam, b_pro, s)
    tla(ax, v.X(-3), v.X(sir + 3), v.Y(0))
    # vijaki (pika = priključek deska↔nosilna konstrukcija; 2 vijaka na stik).
    # F1 (issue #5, O3) — konstrukcijska odločitev A1/C: deske so v poljih
    # (ne prekrivajo stebrov) in so pritrjene na MONTAŽNE LETVE za deskami,
    # ki so na koncih prišraufane na stebre. Zato so vijaki na ROBOVIH desk
    # (kot jih šteje model stikov), NE na sredini stebrov.
    for polje in p["polja"]:
        for xr in polje["deske_x"]:
            for xk in (xr + 8.0, xr + ds - 8.0):
                for fz in (0.25, 0.75):
                    z = p["deske_z"][0] + cona_z * fz
                    ax.add_patch(Circle((v.X(xk), v.Y(z)), 0.55,
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
              None, None, f"{fmt(round(p['centri'][1] - p['centri'][0]))} mm")
    # načrt 12: delovne točke — mere/kote od T točk (ne verižno)
    delovne_tocke(ax, [v.X(xc) for xc in p["centri"]], v.Y(0))
    ax.text(35, v.Y(0) - 16,
            "T1…Tn = delovne točke (osi stebrov): mere in kote se "
            "vodijo od delovnih točk — brez verižnega seštevanja.",
            fontsize=5.5, color="#555555", ha="left", va="center")
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
    # ISO 128-50: beton je drobci + trikotniki
    srafura_betona(ax, px0 - 3, y_tla + 3, pw_s + pw_d + 6, 4)
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
    ax.text(px0 + pw_s + pw_d + 10, y_tla + 10, f"{anker_dim} × 2",
            fontsize=7, ha="left", va="center")
    _g_glob, _r_glob = napisi_sidranja(c.get("podlaga"))
    ax.text(px0 + pw_s + pw_d + 10, y_tla + 4, _g_glob.replace(
        " — priporočeno, potrdi strokovnjak", " (≈ priporočeno)"),
            fontsize=5.5, ha="left", va="center")
    ax.text(px0 + pw_s + pw_d + 10, y_tla + 22, "(prekinjeno)", fontsize=6,
            color="#555555", ha="left", va="center")
    ozna_st(ax, px0 - 2, y_top_top - 4, 106, y_top_top - 4, 1)
    ozna_st(ax, px0 + pw_s + pw_d, y_top_top - 12, 106, y_top_top - 12, 2)
    ozna_st(ax, px0 + pw_s + pw_d, y_b0 + h_b - 6, 106, y_b0 + h_b - 14, 3)
    ozna_st(ax, px0 - 3, y_tla + 5, 16, 30, 4)

    # ==================== DETAJL 1 — SIDRANJE ====================
    oznaka(ax, 106, 121, "DETAJL 1 — SIDRANJE")
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
    dim_h(ax, cx - 7.5, cx + 7.5, cy + 21, None, None, f"{fmt(ss)} mm")
    ax.add_patch(Circle((cx, cy), r, facecolor="none", edgecolor=CRNA,
                        lw=LW_THICK, zorder=8))
    ax.text(cx, cy - r - 3, "NERAZMERJENO", ha="center", va="center",
            fontsize=7, color="#555555")
    ax.text(cx, cy - r - 7,
            f"{vijak_nosilec_naziv} × 2 • predrtje Ø + 1 mm", ha="center",
            va="center", fontsize=7, color="#555555")
    # načrt 8: dimenziji sidranja (≈ priporočeno ali iskren ?? — brez izmišljanja)
    g_napis, r_napis = napisi_sidranja(c.get("podlaga"))
    ax.text(cx, cy - r - 11, g_napis, ha="center", va="center",
            fontsize=5.5, color="#555555")
    ax.text(cx, cy - r - 15, r_napis, ha="center", va="center",
            fontsize=5.5, color="#555555")

    # ==================== DETAJL 2 — DESKE ====================
    oznaka(ax, 172, 121, "DETAJL 2 — DESKE")
    cx2, cy2, r2 = 192, 74, 20
    sl = min(0.4, 36 / ds, 14 / dd)
    lw_, hh_ = ds * sl, dd * sl
    pravokotnik(ax, cx2 - lw_ / 2, cy2 - hh_ / 2, lw_, hh_, fill=b_lam,
                lw=0.5)
    # ISO 128-50: prerezana površina je šrafirana (45° tanke črte, PREKO polnila)
    sachiranje(ax, cx2 - lw_ / 2, cy2 - hh_ / 2,
               cx2 + lw_ / 2, cy2 + hh_ / 2, razmak=1.6, lw=0.2, z=4)
    ax.add_patch(Circle((cx2, cy2), r2, facecolor="none", edgecolor=CRNA,
                        lw=LW_THICK, zorder=8))
    # načrt 12: simbol usmerjenosti kos (▲ VRH) + iskrena opomba
    oznaka_usmerjenosti(ax, cx2 - lw_ / 2 - 6, cy2, visina=11)
    ax.text(cx2, cy2 - r2 - 3, "▲ VRH — usmerjenost po risbi",
            fontsize=6, ha="center", va="center", color=CRNA)
    ax.text(cx2, cy2 - r2 - 7,
            "vidno stran profila preveri pri proizvajalcu — NI izmerjeno",
            fontsize=5, ha="center", va="center", color="#555555")
    ax.text(cx2, cy2 - r2 - 11,
            "šrafura 45° = prerezani material (ISO 128-50)",
            fontsize=5, ha="center", va="center", color="#555555")
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
        model = proizvodni_model(c)          # kanonični izračun (issue #6)
        steber_dim = f"{fmt(m['steber_sirina'])}×{fmt(m['steber_debelina'])}"
        deli = [
            ["Ročaj", mat, f"{fmt(sir)} mm", "1 kos"],
            [f"WPC deska {profil}", ml, f"{fmt(ds)}×{fmt(dd)}",
             f"{model['n_kosov']} kos"],
            [f"Alu steber {steber_dim}", "Aluminij", steber_dim,
             f"{model['n_nosilcev']} kos"],
            ["Osnova za steber (vrh)", "Jeklo", c.get("osnova_dim") or "90×90×6",
             f"{model['n_nosilcev']} kos"],
            [vijak_lamela_naziv,
             pritrdilo_material(c.get("vijak_lamela")),
             vijak_dim(c.get("vijak_lamela")), f"{model['vijaki_element']} kos"],
            [vijak_nosilec_naziv, pritrdilo_material(vijak_nosilec_naziv),
             anker_dim, f"{model['pritrdila_nosilec']} kos"],
        ]
        # F1 (issue #5, O3): montažne letve (pokončna) — fizični nosilec desk,
        # prej manjkajoč v kosovnici.
        if (c.get("predloga") or "ograja") == "pokončna" and model.get("montazne_letve"):
            deli.append(["Montažna letev (za deskami)", "Aluminij", "40×30",
                         f"{model['montazne_letve']} kos"])
    vrste = [["Št.", "Naziv dela", "Material", "Dimenzije (mm)", "Količina"]]
    vrste += [[i] + list(d) for i, d in enumerate(deli, 1)]
    tabela(ax, 246, 131, [10, 58, 44, 30, 20], 6.5, vrste,
           naslov="SEZNAM SESTAVNIH DELOV")

    # ==================== OPOMBE ====================
    opombe = c.get("opombe") or [
        "Vse mere v mm (tolerance ISO 2768-m — glej blok SPLOŠNE "
        "TOLERANCE); pred izdelavo preveri dejanske mere na objektu.",
        f"Deske: {profil} — WPC (bambus + HDPE), pritrditev z 2 vijaki na "
        "rob deske na nosilno konstrukcijo (pokončna: montažne letve za "
        "deskami); predrtje Ø + 1 mm.",
        f"Stebri: aluminij, na osnove z {vijak_nosilec_naziv} "
        f"(vrh v ploščo). Pritrditev: {pritrditev} — pritrdilni material "
        "prilagodi podlagi.",
        f"Razmak stebrov največ {fmt(m['razmak_stebrov'])} mm.",
        "Količine pritrdilnih elementov so orientacijske.",
        "Risba NI statični izračun — nosilnost, sidranje in veterno breme "
        "preveri usposobljen strokovnjak.",
    ]
    opombe_blok(ax, 246, 74, 162, opombe, dno=40)  # dno = vrh naslovnega bloka
    blok_toleranc(ax, 120, 172)          # načrt 9: kota brez ± ni določena

    # ==================== ISO NASLOVNI BLOK + REVIZIJE ====================
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    revizije = c.get("revizije") or [
        ["A", datum, "Prva izdaja", c["izdelal"] or "—"]]
    tabela_revizij(ax, 10, 10, [15, 35, 150, 30], revizije)
    mat_cel = ("ALU stebri + WPC deske"
               if "WPC" in (c.get("material_lamel") or "").upper()
               else c["material"])[:26]
    naslovni_blok(ax, {
        "status": (c.get("status_dokumenta") or "V DELU").upper(),
        "podjetje": c.get("podjetje") or "—",
        "ime": c["ime"], "risba_st": c["risba_st"],
        "rev": revizije[-1][0], "merilo": merilo_niz,
        "datum": datum, "izdelal": c["izdelal"],
        "pregledal": c.get("pregledal") or "—",
        "odobril": c.get("odobril") or "—",
        "material": mat_cel, "list": "1 od 2",
        "stranka": c.get("stranka") or "—", "objekt": c.get("objekt") or "—",
    })


# ---------------------------------------------------------------- predloga: ograda
def narisi_ogrado(ax, c):
    m = c["mere"]
    sir, vis, glob = m["sirina"], m["visina"], m["globina"]
    vijak_lamela_naziv = c.get("vijak_lamela") or "RF vijak M8×70 (lamela↔profil)"
    vijak_nosilec_naziv = c.get("vijak_nosilec") or         f"Pritrdilni vijaki za {c.get('podlaga') or 'podlago'}"
    pritrditev = c.get("pritrditev") or "bočno"
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

    # vrata/prehodi (issue #3) — ista geometrija kot količine in DXF
    vp = vrata_podatki(c)
    for op in vp["opozorila"]:
        _opozori(op)

    # ==================== SPREDNJI POGLLED ====================
    oznaka(ax, 30, 286, "SPREDNJI POGLLED")
    v = Pogled(ax, 35, 206, s)
    for xa, xb in razdeli_po_odprtinah(0, sir, vp["odprtine"]):
        narisi_zgradbo(v, zg, sp, lamele, xa, xb, b_lam, b_pro)
    narisi_odprtine_in_vrata(ax, v, vp, b_lam, b_pro, s)
    tla(ax, v.X(-3), v.X(sir + 3), v.Y(0))
    # lega pritrdilnih nosilcev (kos 4): črtkane linije + puščice na tleh,
    # vijaki/piščavniki na vsaki lameli; kotira se DEJANSKI razmak (A4)
    raz = m.get("razmak_nosilcev", 1000)
    xs_nos, razmak_dejanski = pozicije_nosilcev(sir, raz)
    n_nos = len(xs_nos)
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
              f"{fmt(round(razmak_dejanski))} mm")
    # načrt 12: delovne točke — mere/kote od T točk (ne verižno)
    delovne_tocke(ax, [v.X(xn) for xn in xs_nos], v.Y(0))
    ax.text(35, v.Y(0) - 16,
            "T1…Tn = delovne točke (presečišča osi nosilcev s tlemi): "
            "mere in kote se vodijo od delovnih točk — brez verižnega "
            "seštevanja.",
            fontsize=5.5, color="#555555", ha="left", va="center")
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

    # ==================== DETAJL 1 — SIDRANJE ====================
    oznaka(ax, 118, 104, "DETAJL 1 — SIDRANJE")
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
    # načrt 8: dimenziji sidranja (≈ priporočeno ali iskren ?? — brez izmišljanja)
    g_napis, r_napis = napisi_sidranja(c.get("podlaga"))
    ax.text(cx, cy - r - 11, g_napis, ha="center", va="center",
            fontsize=5.5, color="#555555")
    ax.text(cx, cy - r - 15, r_napis, ha="center", va="center",
            fontsize=5.5, color="#555555")

    # ==================== DETAJL 2 — LAMELE ====================
    oznaka(ax, 172, 104, "DETAJL 2 — LAMELE")
    cx2, cy2, r2 = 192, 74, 20
    sl = min(0.4, 30 / m["lamela_v"], 14 / m["debelina"])
    lw_, hh_ = m["debelina"] * sl, m["lamela_v"] * sl
    pravokotnik(ax, cx2 - lw_ / 2, cy2 - hh_ / 2, lw_, hh_, fill=b_lam,
                lw=0.5)
    # ISO 128-50: prerezana površina je šrafirana (45° tanke črte, PREKO polnila)
    sachiranje(ax, cx2 - lw_ / 2, cy2 - hh_ / 2,
               cx2 + lw_ / 2, cy2 + hh_ / 2, razmak=1.6, lw=0.2, z=4)
    ax.add_patch(Circle((cx2, cy2), r2, facecolor="none", edgecolor=CRNA,
                        lw=LW_THICK, zorder=8))
    # načrt 12: simbol usmerjenosti kos (▲ VRH) + iskrena opomba
    oznaka_usmerjenosti(ax, cx2 - lw_ / 2 - 6, cy2, visina=11)
    ax.text(cx2, cy2 - r2 - 3, "▲ VRH — usmerjenost po risbi",
            fontsize=6, ha="center", va="center", color=CRNA)
    ax.text(cx2, cy2 - r2 - 7,
            "vidno stran profila preveri pri proizvajalcu — NI izmerjeno",
            fontsize=5, ha="center", va="center", color="#555555")
    ax.text(cx2, cy2 - r2 - 11,
            "šrafura 45° = prerezani material (ISO 128-50)",
            fontsize=5, ha="center", va="center", color="#555555")
    dim_v(ax, cy2 - hh_ / 2, cy2 + hh_ / 2, cx2 + r2 + 4, cx2 + lw_ / 2,
          cx2 + lw_ / 2, f"{fmt(m['lamela_v'])} mm")
    dim_h(ax, cx2 - lw_ / 2, cx2 + lw_ / 2, cy2 + hh_ / 2 + 4, None, None,
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
        model = proizvodni_model(c)          # kanonični izračun (issue #6)
        nosilec_dim = c.get("nosilec_dim") or "50×50×5"
        deli = [
            ["Zgornji profil", mat, c.get("profil_zg_dim") or "80×40×3", "1 kos"],
            [f"WPC deska {profil}", ml,
             f"{fmt(m['lamela_v'])}×{fmt(m['debelina'])}",
             f"{model['n_kosov']} kos"],
            ["Spodnji profil", mat, c.get("profil_sp_dim") or "60×40×3", "1 kos"],
            [f"Nosilni nosilec {nosilec_dim}", "Jeklo", nosilec_dim,
             f"{model['n_nosilcev']} kos"],
            [vijak_lamela_naziv, pritrdilo_material(vijak_lamela_naziv),
             vijak_dim(vijak_lamela_naziv), f"{model['vijaki_element']} kos"],
            [vijak_nosilec_naziv, pritrdilo_material(vijak_nosilec_naziv),
             vijak_dim(vijak_nosilec_naziv, "Ø8×80"),
             f"{model['pritrdila_nosilec']} kos"],
        ]
    vrste = [["Št.", "Naziv dela", "Material", "Dimenzije (mm)", "Količina"]]
    vrste += [[i] + list(d) for i, d in enumerate(deli, 1)]
    tabela(ax, 246, 131, [10, 58, 44, 30, 20], 6.5, vrste,
           naslov="SEZNAM SESTAVNIH DELOV")

    # ==================== OPOMBE ====================
    opombe = c.get("opombe") or [
        "Vse mere v mm (tolerance ISO 2768-m — glej blok SPLOŠNE "
        "TOLERANCE); pred izdelavo preveri dejanske mere na objektu.",
        f"Lamele: {profil} — WPC (bambus + HDPE), 15 let garancije, brez barvanja.",
        "Profili/nosilci: aluminij, prašno barvano (RAL po dogovoru, privzeto RAL 7016).",
        f"Pritrditev: {pritrditev} — pritrdilni material prilagodi "
        "podlagi na objektu (beton/zid/les/jeklo); predrtje Ø + 1 mm.",
        f"Razmak nosilcev največ {fmt(m.get('razmak_nosilcev', 1000))} mm; "
        "količine pritrdilnih elementov orientacijske.",
        "Risba NI statični izračun — nosilnost, sidranje in veterno breme "
        "preveri usposobljen strokovnjak.",
    ]
    opombe_blok(ax, 246, 74, 162, opombe, dno=40)  # dno = vrh naslovnega bloka
    blok_toleranc(ax, 120, 172)          # načrt 9: kota brez ± ni določena

    # ==================== ISO NASLOVNI BLOK + REVIZIJE ====================
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    revizije = c.get("revizije") or [
        ["A", datum, "Prva izdaja", c["izdelal"] or "—"]]
    tabela_revizij(ax, 10, 10, [15, 35, 150, 30], revizije)
    mat_cel = ("ALU okvir + WPC lamele"
               if "WPC" in (c.get("material_lamel") or "").upper()
               else c["material"])[:26]
    naslovni_blok(ax, {
        "status": (c.get("status_dokumenta") or "V DELU").upper(),
        "podjetje": c.get("podjetje") or "—",
        "ime": c["ime"], "risba_st": c["risba_st"],
        "rev": revizije[-1][0], "merilo": merilo_niz,
        "datum": datum, "izdelal": c["izdelal"],
        "pregledal": c.get("pregledal") or "—",
        "odobril": c.get("odobril") or "—",
        "material": mat_cel, "list": "1 od 2",
        "stranka": c.get("stranka") or "—", "objekt": c.get("objekt") or "—",
    })


PREDLOGE = {}  # izpolnjeno spodaj
PREDLOGE["ograda"] = narisi_ogrado      # star ključ (združljivost)
PREDLOGE["ograja"] = narisi_ogrado      # pravilno slovensko ime
PREDLOGE["pokončna"] = narisi_pokoncna


# ---------------------------------------------------------------- konfiguracija

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


def delovne_tocke(ax, xs, y_ref):
    """Delovne točke T1…Tn (načrt 12): krog na presečišču konstrukcijske
    osi (nosilec/steber) z referenčno črto (tla).

    Profesionalna praksa: mere in kote se vodijo od delovnih točk —
    BREZ verižnega seštevanja (primerjava-risbe.md).
    """
    for i, x in enumerate(xs, 1):
        ax.add_patch(Circle((x, y_ref), 1.1, facecolor="white",
                            edgecolor=CRNA, lw=0.8, zorder=9))
        ax.text(x - 2.6, y_ref + 3.0, f"T{i}", fontsize=6,
                fontweight="bold", ha="right", va="center", zorder=9)


def oznaka_usmerjenosti(ax, x, y_sredina, visina=11):
    """▲ VRH (načrt 12): simbol usmerjenosti kos.

    Oznaka na kosu/nalepki prepreči obrnjeno vgradnjo; usmerjenost je
    določena po risbi (ne izmišljena mera).
    """
    ax.annotate("", xy=(x, y_sredina + visina / 2),
                xytext=(x, y_sredina - visina / 2),
                arrowprops=dict(arrowstyle="->", lw=1.0, color=CRNA))
    ax.text(x, y_sredina + visina / 2 + 2.4, "▲ VRH", fontsize=6,
            fontweight="bold", ha="center", va="center", color=CRNA)


def srafura_betona(ax, x0, y0, w, h, barva="#555555"):
    """Šrafura betona po ISO 128-50 (drobci + trikotniki) — za sidranje.

    Določen vzorec (brez naključja), da so risbe ponovljive.
    """
    korak = max(2.2, min(3.2, h / 1.6, w / 4))
    vrstica = 0
    y = y0 + korak * 0.5
    while y < y0 + h - 1e-9:
        x = x0 + korak * (0.5 + (0.5 if vrstica % 2 else 0.0))
        while x < x0 + w - 1e-9:
            if vrstica % 2:
                ax.plot([x], [y], marker="^", markersize=1.6,
                        color=barva, zorder=4)
            else:
                ax.plot([x], [y], marker=".", markersize=1.8,
                        color=barva, zorder=4)
            x += korak
        vrstica += 1
        y += korak * 0.8


def napisi_sidranja(podlaga):
    """Napisa za DETAJL 1 — SIDRANJE: globina sidra in oddaljenost roba (načrt 8).

    Eno vir resnice (jedro.priporoceno_sidranje). Vrednosti so ≈
    priporočene (potrdi strokovnjak) ali iskren '??' (NEZNANO) —
    nikoli izmišljene.
    """
    _vrsta, _sidro, globina = priporoceno_sidranje(podlaga)
    if globina is not None:
        g = f"globina sidra ≈ {globina} mm — priporočeno, potrdi strokovnjak"
    else:
        g = "globina sidra ?? — določi projektant po podlagi"
    r = "oddaljenost roba sidra ?? — določi projektant po podlagi"
    return g, r


def qc_blok(ax, x0, y_top, sirina, skupine):
    """Kontrolni seznam QC (načrt 10) — potrditvena polja, kriteriji vezani na risbo.

    skupine: [(naslov_skupine, ["☐ točka — kriterij", ...]), ...]
    Polja so PRAZNA (obrazec) — nič ni označeno kot opravljeno.
    """
    nas_h, vrst = 8.5, 3.1
    n_vrst = sum(1 + len(t) for _g, t in skupine)
    visina = nas_h + n_vrst * vrst + 1
    pravokotnik(ax, x0, y_top - visina, sirina, visina, fill="white", lw=0.8)
    pravokotnik(ax, x0, y_top - nas_h, sirina, nas_h, fill=BARVA_OZN, lw=0)
    ax.text(x0 + sirina / 2, y_top - nas_h / 2, "KONTROLNI SEZNAM (QC)",
            ha="center", va="center", fontsize=8, fontweight="bold",
            color="white")
    y = y_top - nas_h - 1.6
    for skupina, tocke in skupine:
        ax.text(x0 + 2, y, skupina, fontsize=6.5, fontweight="bold",
                ha="left", va="center")
        y -= vrst
        for tocka in tocke:
            ax.text(x0 + 4, y, tocka, fontsize=6.3, ha="left", va="center")
            y -= vrst
    return y_top - visina


def montazni_sidranje(ax, x0, y_top, sirina=120):
    """Priporočene globine sidranja po podlagi — potrdi strokovnjak.

    Podatki iz SIDRANJA_PODLAGE (en vir resnice z DETAJL 1 — SIDRANJE).
    """
    nas_h, h = 7.5, 7
    pravokotnik(ax, x0, y_top - nas_h, sirina, nas_h, fill=BARVA_OZN, lw=0)
    ax.text(x0 + sirina / 2, y_top - nas_h / 2,
            "SIDRANJE (priporočeno) — DETAJL 1",
            ha="center", va="center", fontsize=7.5, fontweight="bold",
            color="white")
    y = y_top - nas_h
    for _kljuci, podlaga, sidro, glob in SIDRANJA_PODLAGE:
        pravokotnik(ax, x0, y - h, sirina, h, fill="#eef1f6", lw=0.5)
        ax.text(x0 + 2, y - h / 2, podlaga, fontsize=6.5, ha="left", va="center")
        ax.text(x0 + 62, y - h / 2, sidro, fontsize=6.5, ha="left", va="center")
        ax.text(x0 + sirina - 2, y - h / 2, f"{glob} mm", fontsize=6.5,
                ha="right", va="center")
        y -= h
    ax.text(x0, y - 3, "(preveri usposobljen strokovnjak)", fontsize=6,
            color="#888888", ha="left", va="center")


def montazni_sestava(ax, x0, y_top, sirina, sestava):
    """Shematska razstavljena sestava (od zgoraj navzdol = vrstni red)."""
    nas_h = 7.5
    pravokotnik(ax, x0, y_top - nas_h, sirina, nas_h, fill=BARVA_OZN, lw=0)
    ax.text(x0 + sirina / 2, y_top - nas_h / 2, "SESTAVA (razstavljeno)",
            ha="center", va="center", fontsize=7.5, fontweight="bold",
            color="white")
    sred = x0 + sirina / 2
    y = y_top - nas_h
    for i, (naziv, dim) in enumerate(sestava):
        hh = 11
        y -= 9
        w = sirina - 34
        pravokotnik(ax, sred - w / 2, y - hh, w, hh, fill="#c9d2e0",
                    lw=0.6)
        ax.text(sred, y - hh / 2, naziv, ha="center", va="center",
                fontsize=6.5, fontweight="bold")
        ax.text(sred + w / 2 + 4, y - hh / 2, dim, fontsize=6.5, ha="left",
                va="center", color="#333333")
        if i < len(sestava) - 1:
            crta(ax, sred, y - hh, sred, y - 9, lw=0.5, stil=(0, (3, 2)))
        y -= hh
    ax.text(x0, y - 4, "od zgoraj navzdol = vrstni red vgradnje",
            fontsize=6, color="#888888", ha="left", va="center")


def _primerjava_reza(skupine_kosov, c):
    """Besedilo primerjave optimizatorja z ročnim rezanjem (Plan 3).

    POZOR (popravka po uporabniškem testu):
    1. primerjava teče VSAKO SKUPINO kosov (profil) ZASE in se sešteje —
       različni profili ne morejo deliti iste palice;
    2. ročni rez kosovnik bere PO VRSTNEM REDU SEZNAMA (kot delavec),
       ne po že optimiziranih trakovih — sicer je „ročno“ po krivici
       enako dobro kot optimizator.

    ``skupine_kosov``: [[(oznaka, dolzina), ...], ...]
    """
    kerf = float(c.get("kerf", 3.0) or 0.0)
    zaloga = c.get("dolzine_deske") or [c.get("dolzina_deske", 5800)]
    rocno = opt = 0.0
    for kosi in skupine_kosov:
        if not kosi:
            continue
        try:
            m = metrika_reza(kosi, zaloga, kerf)
        except ValueError:
            return ""
        rocno += m["rocno_poraba_mm"]
        opt += m["opt_poraba_mm"]
    prihranek = rocno - opt
    if prihranek <= 1e-6:
        return ""
    return (f" • primerjava brez ostankov (vsak profil zase): ročno "
            f"{rocno / 1000:.2f} m → prihranek {prihranek / 1000:.2f} m")


def _rezni_nacrt_izracun_montazni(skupine, c):
    """Napredni rezni načrt (issue #14); ob napaki None — brez škode."""
    try:
        return rezni_nacrt_izracun(skupine, c)
    except Exception:
        return None


def _rezni_nacrt_vpliva(rn, pot_rows, viz_traki):
    """Le POTRJEN načrt upravlja razporeditev in nabavo (issue #14).

    Sistem ne zamenja potrjenega načrta tiho; nepotrjenega (samodejnega)
    pa ne vsili — ta ostane informativen (primerjava v meniju Orodja).
    """
    if not rn or rn.get("status_izbire") != "potrjen":
        return viz_traki
    viz_nov = [t for s in rn.get("skupine") or [] for t in s["viz_traki"]]
    if viz_nov:
        viz_traki = viz_nov
        if pot_rows and pot_rows[0]:
            pot_rows[0][1] = (" + ".join(f"{t} × {fmt(B)} mm"
                                        for B, t in traki_nabava(viz_nov))
                              or pot_rows[0][1])
            pot_rows[0][2] = f"{len(viz_nov)} kos"
    return viz_traki


def montazni_osnova(ax, c, pot_rows, rez_rows, viz_traki, koraki,
                    sestava=None, primerjava="", rezni_nacrt=None):
    """Skupni izgled montažnega lista (stran 2) za vse predloge."""
    iso_okvir(ax)
    oznaka(ax, 20, 286, "MONTAŽNI LIST (LIST 2/2) — POTREBŠČINE")
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    # načrt 11: status/revizija vidna tudi v delavnici in na terenu
    status_ml = (c.get("status_dokumenta") or "V DELU").upper()
    rev_ml = (c.get("revizije") or [["A"]])[-1][0]
    status_vodni_zig(ax, status_ml)
    ax.text(20, 278, f"Naloga: {c['risba_st']}   •   Datum: {datum}",
            fontsize=9, ha="left", va="center")
    ax.text(20, 272, f"Stranka: {c.get('stranka') or '—'}   •   Objekt: "
            f"{c.get('objekt') or '—'}", fontsize=9, ha="left", va="center")
    ax.text(20, 266, f"STATUS: {status_ml}   •   REV. {rev_ml}",
            fontsize=9, ha="left", va="center", fontweight="bold")

    tabela(ax, 20, 256, [90, 60, 35, 75], 7.0,
           [["NAZIV", "SPECIFIKACIJA", "KOLIČINA", "OPOMBA"], *pot_rows],
           naslov="POTREBŠČINE")

    y_rez_konec = 197.0 - 20
    if rez_rows:
        n_vrst_r = len(rez_rows) - 1
        vrstice_rez = rez_rows
        if n_vrst_r > 10:
            vrstice_rez = rez_rows[:11] + [[
                f"… ostalih {n_vrst_r - 10} vrst", "",
                "polna kosovnica: CSV + nalepke", ""]]
            n_vrst_r = 11
        tabela(ax, 20, 197, [45, 55, 75, 45, 40], 7.0, vrstice_rez,
               naslov="REZALNI NAČRT")
        y_rez_konec = 197 - (8.5 + 7 + n_vrst_r * 7)
    else:
        opombe_blok(ax, 20, 197, 260,
                    ["Deska je krajša od enega kosa — spoj/rez po dogovoru "
                     "s proizvajalcem."], naslov_t="REZALNI NAČRT")

    kerf = c.get("kerf", 3.0)
    b_lam = barva_hex(c.get("barva"))
    y = y_rez_konec - 21
    if rezni_nacrt:
        izb = rezni_nacrt.get("izbrani_nacrt") or "samodejno"
        kit = rezni_nacrt.get("kriterij") or "odpad"
        st_izb = rezni_nacrt.get("status_izbire") or ""
        bil = {"odrez_mm": 0.0, "kerf_mm": 0.0, "ostanek_mm": 0.0,
               "odpad_mm": 0.0}
        for s in rezni_nacrt.get("skupine") or []:
            for k in bil:
                bil[k] += (s.get("bilanca") or {}).get(k) or 0.0
        ax.text(20, y + 10,
                f"NAČRT RAZREZA: {izb} • kriterij: {kit} • {st_izb} • "
                f"bilanca trakov: odrez {fmt(bil['odrez_mm'])} + kerf "
                f"{fmt(bil['kerf_mm'])} + uporabni ostanki "
                f"{fmt(bil['ostanek_mm'])} + odpad "
                f"{fmt(bil['odpad_mm'])} mm",
                fontsize=6.5, color="#555555", ha="left", va="center")
    if viz_traki:
        maxdl = max(dl for dl, _ in viz_traki)
        sk = 260.0 / maxdl
        prikaz_b = min(len(viz_traki), 5)
        skup_k = sum(ln for _, kosi in viz_traki for _, ln in kosi)
        skup_d = sum(dl for dl, _ in viz_traki)
        izk = skup_k / skup_d * 100 if skup_d else 0
        ax.text(20, y + 2, f"VIZUALNI REZ • kerf {fmt(kerf)} mm • "
                f"izkoristek {izk:.0f} % • ostanek = trak − kosi − rez"
                + (f" • prikazanih {prikaz_b} od {len(viz_traki)} trakov"
                   if len(viz_traki) > prikaz_b else "")
                + primerjava,
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
            ost = max(0, dl - sum(ln for _, ln in kosi)
                      - kerf * len(kosi))
            w_ost = max(2.0, ost * sk)
            pravokotnik(ax, x, y, w_ost, 7, fill="#e9e9e9", lw=0.5)
            if w_ost > 16:
                ax.text(x + w_ost / 2, y + 3.5, f"ostanek {fmt(ost)}",
                        ha="center", va="center", fontsize=6)
            ax.text(18, y + 3.5, f"{ti + 1}", ha="right", va="center",
                    fontsize=6.5, fontweight="bold")
        y -= 8

    # načrt 10: vsak korak ima potrditveno polje (monter kljukira opravljeno)
    koraki = [f"☐ {k}" for k in koraki]
    vrst_k = sum(len(textwrap.wrap(f"{i}. {o}", width=86) or [""])
                 for i, o in enumerate(koraki, 1))
    h_kor = 8.5 + vrst_k * 3.9 + 2
    if y - 6 - h_kor < 30 and sestava is None:
        opombe_blok(ax, 288, 173, 120, koraki,
                    naslov_t="MONTAŽNI KORAKI — potrdi ☐",
                    velikost=7.5, wrap=68)
    else:
        opombe_blok(ax, 20, y - 6, 260, koraki,
                    naslov_t="MONTAŽNI KORAKI — potrdi ☐")

    # načrt 10: QC seznam — delavnica + teren, kriteriji vezani na risbo
    # (zamenjuje 'KONTROLA NA TERENU'; vsebinsko premoženje je ohranjeno)
    qc_blok(ax, 288, 256, 120, [
        ("DELAVNICA", [
            "☐ Mere in kote — str. 1, blok toleranc",
            "☐ Material in barva — vzorec proizvajalca",
            "☐ Kosi in nalepke — str. 2, rezalni načrt",
            "☐ Sidranje: tip, globina — DETAJL 1",
        ]),
        ("TEREN", [
            "☐ Dejanske mere, lege pritrditve, razvod",
            "☐ Višina, raven (in delovanje vrat)",
            "☐ Statiko potrdil strokovnjak — opomba 6",
            "☐ Slika končne izvedbe",
        ]),
    ])

    montazni_sidranje(ax, 288, 214)
    if sestava:
        montazni_sestava(ax, 288, 180, 120, sestava)

    # načrt 10: podpis kontrole (QC) — prej IZDELAL/STRANKA/DATUM
    for x0, w, ime in ((20, 98, "IZDELAL (podpis)"),
                       (122, 98, "KONTROLA (QC podpis)"),
                       (224, 98, "STRANKA (prejem dela)"),
                       (326, 82, "DATUM MONTAŽE")):
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
    xs_nos, razmak_dejanski = pozicije_nosilcev(sir, raz)
    n_nos = len(xs_nos)
    model = proizvodni_model(c)              # kanonični izračun (issue #6)
    vijaki = model["vijaki_element"]
    profil = c.get("profil") or "ROMB 67"
    dl_deske = c.get("dolzina_deske", 5800)
    dl_palice = c.get("dolzina_palice", 6000)
    kerf = c.get("kerf", 3.0)
    podlaga = c.get("podlaga") or ""
    vijak_lamela_naziv = c.get("vijak_lamela") or "RF vijak M8×70 (lamela↔profil)"
    vijak_nosilec_naziv = c.get("vijak_nosilec") or         f"Pritrdilni vijaki za {podlaga or 'podlago'}"

    # vrata/prehodi (issue #3) — vplivajo na polnilo, količine in razrez
    vp = vrata_podatki(c)
    for op in vp["opozorila"]:
        _opozori(op)

    # rezalni načrt — EN VIR RESNICE (razrez_podatki): A3/A5/B1
    if vp["odprtine"]:
        # lamele so razrezane okoli odprtin — kosi različnih dolžin
        kosi_l: list = []
        for _z0, _z1 in lamele:
            for xa, xb in razdeli_po_odprtinah(0, sir, vp["odprtine"]):
                kosi_l.append((f"L{len(kosi_l) + 1}", xb - xa))
        rp = razrez_kosov_podatki(kosi_l, c, oznaka="L", glava="LAMELE ŠT.")
        uporabno_m = sum(d for _o, d in kosi_l) / 1000.0
    else:
        rp = razrez_podatki(sir, n, c, oznaka="L", glava="LAMELE ŠT.")
        uporabno_m = n * sir / 1000.0
    traki = rp["traki"]
    rez_rows = rp["rez_rows"]
    viz_traki = rp["viz_traki"]
    kos_iz_ost = rp["iz_ost_kos"]
    kosi_lamel = kosi_l if vp["odprtine"] else [
        (f"L{i + 1}", float(sir)) for i in range(n)]
    kosi_vrat = []                         # skupina profilov: vratni kosi
    if vp["vrata"] or vp["prehodi"]:
        # kosi okvirjev/kril vrat — ločen rez (različni profili)
        kos_v = []
        for enota in vp["vrata"] + vp["prehodi"]:
            for ozn_k, dol, _sir_k, kol, _op, _kl in enota["kosovnica"]["izdelani"]:
                for _ in range(int(kol)):
                    kos_v.append((f"{enota['oznaka']}-{ozn_k}", float(dol)))
        if kos_v:
            rv = razrez_kosov_podatki(kos_v, c, oznaka="V", glava="VRATA ŠT.")
            rp["rez_rows"] += rv["rez_rows"][1:]
            kosi_vrat = kos_v
            rp["viz_traki"] += rv["viz_traki"]
    # Plan 3 (popravka po uporabniškem testu): vsak profil zase + vrstni
    # red kosovnika (ne optimizirani traki)
    primerjava = _primerjava_reza([kosi_lamel, kosi_vrat], c)
    # 2 U-profila (zgornji + spodnji) sta RAZLIČNI sekciji — vsaka svoja zaloga
    palice_zg = stevilo_palic(sir, 1, dl_palice, kerf)
    palice_sp = stevilo_palic(sir, 1, dl_palice, kerf)
    palice = palice_zg + palice_sp
    dim_zg = c.get("profil_zg_dim") or "80×40×3"
    dim_sp = c.get("profil_sp_dim") or "60×40×3"
    dim_nos = c.get("nosilec_dim") or "50×50×5"
    pot = [
        [f"WPC deska {profil}",
         " + ".join(f"{t} × {fmt(B)} mm" for B, t in traki_nabava(traki))
         or f"{fmt(dl_deske)} mm", f"{len(traki)} kos",
         (f"za {fmt(uporabno_m)} m lamel; {kos_iz_ost} kos iz "
          f"ostankov" if kos_iz_ost else
          f"skupaj {fmt(uporabno_m)} m lamel")],
        [f"Alu profil {dim_zg} (zgornji)", f"{fmt(dl_palice)} mm",
         f"{palice_zg} kos", f"dolg {fmt(sir)} mm"],
        [f"Alu profil {dim_sp} (spodnji)", f"{fmt(dl_palice)} mm",
         f"{palice_sp} kos", f"dolg {fmt(sir)} mm"],
        [f"Nosilni nosilec {dim_nos}", "—",
         f"{n_nos} kos",
         f"razmak ≤ {fmt(raz)} mm • dejanski {fmt(round(razmak_dejanski))} mm"],
        [vijak_lamela_naziv, "—", f"{vijaki} kos",
         f"2 na stik ({model['n_stikov']} stikov) • Ø+1 mm"],
        [vijak_nosilec_naziv, "—", f"{n_nos * 2} kos", "2 na nosilec"],
    ]
    if kos_iz_ost:
        pot.insert(1, ["Uporabljeni ostanki (iz skladišča)", "—",
                       f"{kos_iz_ost} kos", "ni nabave"])
    pot += vrata_vrstice_potrebscine(vp)   # VRATA/PREHODI (issue #3)

    # issue #14: napredni rezni načrt — le POTRJEN upravlja vizijo/nabavo
    rn = _rezni_nacrt_izracun_montazni(
        [("LAMELE", kosi_lamel, c.get("barva") or "",
          c.get("profil") or ""),
         ("VRATA", kosi_vrat, c.get("barva") or "", "vrata")], c)
    viz_traki = _rezni_nacrt_vpliva(rn, pot, viz_traki)

    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lego nosilcev (razmak največ {fmt(raz)} mm, dejanski "
        f"{fmt(round(razmak_dejanski))} mm); "
        "preveri razvod inštalacij pred vrtanjem.",
        "Pritrdi nosilce (bočno/vrh po dogovoru — glej DETAJL "
        "PRITRJEVANJA); za WPC vedno predrtje Ø + 1 mm.",
        "Vgradi zgornji in spodnji alu profil; kontroliraj višino "
        "in ravnost.",
        f"Vgradi lamele ({vijak_lamela_naziv} skozi notranjo alu cev; "
        "brez predrtja ne vrtaj!; vsako lamelo z oznako ▲ VRH navzgor).",
        "Kontrola ravni in višine, slika izvedbo, pridobi podpis "
        "stranke.",
    ]
    montazni_osnova(ax, c, pot, rez_rows, viz_traki, koraki,
                    primerjava=primerjava,
                    rezni_nacrt=(rn if rn else None))

    # izračun višine + poraba/odpad (viden na montažnem listu)
    cona_z = zg[0] - sp[1]
    n_vrst_r = min(len(rez_rows) - 1, 11) if rez_rows else 0
    y_iz = 197 - (8.5 + 7 + n_vrst_r * 7) - 5.5
    ax.text(20, y_iz, f"IZRAČUN VIŠINE: {fmt(m['visina'])} = "
            f"{fmt(m['profil_v'])} (zgornji profil) + {fmt(cona_z)} "
            f"(lamele: {n} × {fmt(m['lamela_v'])} + {n - 1} × vrzel "
            f"{vrzel:.1f} mm) + {fmt(m['profil_v'])} (spodnji profil) + "
            f"{fmt(m['odcep'])} (odcep)", fontsize=6.5, color="#555555",
            ha="left", va="center")
    por_m = sum(B for B, _ in traki) / 1000
    odp_m = por_m - uporabno_m
    ax.text(20, y_iz - 5, f"PORABA: nabavne deske {len(traki)} kos = "
            f"{por_m:.2f} m • odpad {odp_m:.2f} m "
            f"({odp_m / por_m * 100:.0f} %) • alu palice {palice} kos = "
            f"{palice * dl_palice / 1000:.1f} m", fontsize=6.5,
            color="#555555", ha="left", va="center")
    return izracunaj_kolicine(c, rp=rp)


def narisi_montazni_pokoncna(ax, c):
    """Stran 2 za predlogo "pokončna" (stebri + navpične deske)."""
    m = c["mere"]
    sir, vis = m["sirina"], m["visina"]
    odcep = m["odcep"]
    p = razpored_pokoncna(m)
    n_d, n_s = p["n_desk"], p["n_stebrov"]
    deska_h = p["deske_h"]
    profil = c.get("profil") or "POLNA DESKA 100"
    vijak_lamela_naziv = c.get("vijak_lamela") or "Vijak M8×70 (deska↔steber)"
    vijak_nosilec_naziv = c.get("vijak_nosilec") or "Anker M10"
    dl_deske = c.get("dolzina_deske", 5800)
    dl_palice = c.get("dolzina_palice", 6000)
    kerf = c.get("kerf", 3.0)

    # vrata/prehodi (issue #3) — deske, ki jih seka odprtina, se razrežejo
    vp = vrata_podatki(c)
    for op in vp["opozorila"]:
        _opozori(op)
    if vp["odprtine"]:
        kosi_d = []
        for xr in p["deske_x"]:
            kosi_d += razdeli_po_odprtinah(xr, xr + (m.get("deska_sirina", 100) or 100),
                                          vp["odprtine"])
        n_eff = len(kosi_d)
    else:
        n_eff = n_d
    model = proizvodni_model(c)              # kanonični izračun (issue #6)

    # rezalni načrt — EN VIR RESNICE (razrez_podatki): A3/A5/B1
    rp = razrez_podatki(deska_h, n_eff, c, oznaka="D", glava="DESKE ŠT.")
    traki = rp["traki"]
    rez_rows = rp["rez_rows"]
    viz_traki = rp["viz_traki"]
    kos_iz_ost = rp["iz_ost_kos"]
    kosi_desk = [(f"D{i + 1}", float(deska_h)) for i in range(n_eff)]
    kosi_vrat = []                         # skupina profilov: vratni kosi
    if vp["vrata"] or vp["prehodi"]:
        kos_v = []
        for enota in vp["vrata"] + vp["prehodi"]:
            for ozn_k, dol, _sir_k, kol, _op, _kl in enota["kosovnica"]["izdelani"]:
                for _ in range(int(kol)):
                    kos_v.append((f"{enota['oznaka']}-{ozn_k}", float(dol)))
        if kos_v:
            rv = razrez_kosov_podatki(kos_v, c, oznaka="V", glava="VRATA ŠT.")
            rp["rez_rows"] += rv["rez_rows"][1:]
            kosi_vrat = kos_v
            rp["viz_traki"] += rv["viz_traki"]
    primerjava = _primerjava_reza([kosi_desk, kosi_vrat], c)
    steber_dim = f"{fmt(m['steber_sirina'])}×{fmt(m['steber_debelina'])}"
    palice_s = stevilo_palic(vis, n_s, dl_palice, kerf)  # regresija agregatne formule
    vijaki = model["vijaki_element"]  # 2 vijaka na stik (B2: 2 stika na desko)
    pot = [
        [f"WPC deska {profil}",
         " + ".join(f"{t} × {fmt(B)} mm" for B, t in traki_nabava(traki))
         or f"{fmt(dl_deske)} mm", f"{len(traki)} kos",
         (f"za {fmt((n_eff - kos_iz_ost) * deska_h / 1000)} m desek; "
          f"{kos_iz_ost} kos iz ostankov"
          if kos_iz_ost else
          f"skupaj {fmt(n_eff * deska_h / 1000)} m desek")],
        [f"Alu steber {steber_dim}", f"{fmt(dl_palice)} mm", f"{palice_s} kos",
         f"{n_s} stebrov (L = {fmt(vis)} mm)"],
        ["Ročaj (WPC/alu)", f"{fmt(sir)} mm", "1 kos",
         "pritrjen na steber"],
        ["Osnova za steber (vrh)", c.get("osnova_dim") or "90×90×6",
         f"{n_s} kos",
         f"{vijak_nosilec_naziv} × 2 na osnovo"],
        [vijak_lamela_naziv, "—", f"{vijaki} kos",
         "2 na stik, 4 na desko (levo + desno) • Ø+1 mm"],
        [vijak_nosilec_naziv, "—", f"{n_s * 2} kos",
         "2 na osnovo • sidranje ≥ 60 mm (beton C20/25)"],
    ]
    pot += vrata_vrstice_potrebscine(vp)   # VRATA/PREHODI (issue #3)
    if kos_iz_ost:
        pot.insert(1, ["Uporabljeni ostanki (iz skladišča)", "—",
                       f"{kos_iz_ost} kos", "ni nabave"])

    # issue #14: napredni rezni načrt — le POTRJEN upravlja vizijo/nabavo
    rn = _rezni_nacrt_izracun_montazni(
        [("DESKE", kosi_desk, c.get("barva") or "",
          c.get("profil") or ""),
         ("VRATA", kosi_vrat, c.get("barva") or "", "vrata")], c)
    viz_traki = _rezni_nacrt_vpliva(rn, pot, viz_traki)

    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lege stebrov (razmak največ {fmt(m['razmak_stebrov'])} mm); "
        "preveri razvod inštalacij pred vrtanjem.",
        f"Pritrdi osnove z {vijak_nosilec_naziv} (vrh v ploščo — glej "
        "DETAJL PRITRJEVANJA); kontroliraj ravnost.",
        "Postavi stebre; kontroliraj navpičnost.",
        f"Vgradi deske po poljih med stebri ({vijak_lamela_naziv}: "
        "2 vijaka na stik, 4 na desko; predrtje Ø + 1 mm; vsako desko "
        "z oznako ▲ VRH navzgor).",
        "Vgradi ročaj, kontrola ravni in višine, slika izvedbo, podpis "
        "stranke.",
    ]

    sestava = [
        ("Ročaj (WPC/alu)", f"L = {fmt(sir)} mm"),
        (f"WPC deska {profil}",
         f"{fmt(m['deska_sirina'])}×{fmt(m['deska_debelina'])} mm"),
        (f"Alu steber {steber_dim}", f"L = {fmt(vis)} mm"),
        (f"Osnova za steber {c.get('osnova_dim') or '90×90×6'}",
         f"{vijak_nosilec_naziv} × 2"),
    ]
    montazni_osnova(ax, c, pot, rez_rows, viz_traki, koraki, sestava=sestava,
                    primerjava=primerjava,
                    rezni_nacrt=(rn if rn else None))

    n_vrst_r = min(len(rez_rows) - 1, 11) if rez_rows else 0
    y_iz = 197 - (8.5 + 7 + n_vrst_r * 7) - 5.5
    ax.text(20, y_iz, f"IZRAČUN VIŠINE: {fmt(vis)} = {fmt(m['rocaj_v'])} "
            f"(ročaj) + {fmt(deska_h)} (deske) + {fmt(odcep)} (odcep) • "
            f"ŠIRINA: {fmt(sir)} = {n_s} stebrov + {n_s - 1} polj; "
            f"deske po poljih med stebri, vrzel {fmt(p['vrzel'])} mm",
            fontsize=6.5, color="#555555", ha="left", va="center")
    por_s = sum(B for B, _ in traki) / 1000
    odp_s = por_s - n_eff * deska_h / 1000
    ax.text(20, y_iz - 5, f"PORABA: nabavne deske {len(traki)} kos = "
            f"{por_s:.2f} m • odpad {odp_s:.2f} m "
            f"({odp_s / por_s * 100:.0f} %) • alu palice {palice_s} kos = "
            f"{palice_s * dl_palice / 1000:.1f} m", fontsize=6.5,
            color="#555555", ha="left", va="center")
    return izracunaj_kolicine(c, rp=rp)


def narisi_nalepke(ax, c, kosovnica):
    """Stran 4: nalepke za kose (izreži, označi, prilepi na kos)."""
    iso_okvir(ax)
    oznaka(ax, 20, 286, "NALEPKE ZA KOSE (PRILAGA — ni risalni list)")
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    ax.text(20, 278, f"Naloga: {c['risba_st']} • Datum: {datum} • "
            f"izreži vsak kos in prilepi oznako", fontsize=8.5,
            ha="left", va="center")
    ax.text(20, 271.5,
            "▲ VRH = usmerjenost kosov: stran, ki po vgradnji gleda "
            "navzgor — vgradi z oznako NAVZGOR. Usmerjenost je določena "
            "po risbi; vidno stran profila preveri pri proizvajalcu "
            "(NI izmerjeno).",
            fontsize=6.5, color="#555555", ha="left", va="center")
    n = len(kosovnica)
    prikaz = min(n, 12)
    cols, cw, chh, x0, y0 = 3, 118, 52, 25, 245
    for i, (oz, dol, vir, mat) in enumerate(kosovnica[:prikaz]):
        col, row = i % cols, i // cols
        x = x0 + col * (cw + 8)
        y = y0 - row * (chh + 8)
        pravokotnik(ax, x, y - chh, cw, chh, fill="white", lw=1.0)
        ax.text(x + 5, y - 9, oz, fontsize=13, fontweight="bold",
                ha="left", va="center")
        ax.text(x + cw - 5, y - 9, "▲ VRH", fontsize=9,
                fontweight="bold", ha="right", va="center", color=CRNA)
        ax.text(x + 5, y - 21, f"{fmt(dol)} mm", fontsize=10,
                fontweight="bold", ha="left", va="center")
        ax.text(x + 5, y - 31, c.get("profil") or "", fontsize=6.5,
                color="#555555", ha="left", va="center")
        ax.text(x + 5, y - 40, f"barva: {c.get('barva') or ''}", fontsize=6.5,
                color="#555555", ha="left", va="center")
        ax.text(x + cw - 5, y - 44, vir, fontsize=6, color="#888888",
                ha="right", va="center")
    if n > prikaz:
        ax.text(x0, y0 - 4 * (chh + 8) - 4, f"… ostalih {n - prikaz} nalepk "
                "je v kosovnici (CSV)", fontsize=7, color="#888888",
                ha="left", va="center")


def narisi_predracun(ax, c, postavke):
    """Stran 3: orientacijski predračun (samo če so cene v konfiguraciji).

    A8: če so vse uporabljene cene 0.00 (PRIMER vrednosti), se predračun
    izpiše kot INFORMATIVEN — brez zavajajočih zneskov „0,00 EUR“.
    """
    cene = c.get("cene") or {}
    uporabljene = [float(cene.get(kljuc) or 0)
                   for (_n, _k, _e, kljuc, num) in postavke if num]
    if cene.get("dela_ure") and cene.get("dela_ur_cena"):
        uporabljene.append(float(cene.get("dela_ur_cena") or 0))
    vse_nic = all(abs(v) < 1e-9 for v in uporabljene) if uporabljene else True
    delno = any(abs(v) < 1e-9 for v in uporabljene) and not vse_nic

    iso_okvir(ax)
    if vse_nic:
        oznaka(ax, 20, 286,
               "PREDRAČUN (INFORMATIVEN — BREZ VELJAVNEGA CENIKA) — PRILAGA")
    else:
        oznaka(ax, 20, 286,
               "PREDRAČUN (ORIENTACIJSKI) — PRILAGA (ni risalni list)")
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    ax.text(20, 278, f"Naloga: {c['risba_st']}   •   Datum: {datum}   •   "
            f"Veljavnost: 30 dni", fontsize=9, ha="left", va="center")
    ax.text(20, 272, f"Stranka: {c.get('stranka') or '—'}   •   Objekt: "
            f"{c.get('objekt') or '—'}", fontsize=9, ha="left", va="center")

    # Plan A: EN algoristem za seštevek (živi povzetek v vmesniku ga deli)
    znesek = predracun_znesek(cene, postavke)
    vse_nic = znesek["vse_nic"]
    delno = znesek["delno"]
    manjkajoce_cene = znesek["manjkajoce_cene"]
    skup = znesek["skupaj"]
    vrste = [["POSTAVKA", "KOLIČINA", "CENA ENOTE", "SKUPAJ"]]         + znesek["vrstice"]
    if vse_nic:
        vrste.append(["SKUPAJ (brez DDV)", "", "", "ni obračunano"])
    elif delno:
        vrste.append(["SKUPAJ (delno — manjkajoče cene niso upoštevane)",
                      "", "", f"{skup:.2f} EUR"])
    else:
        vrste.append(["SKUPAJ (brez DDV)", "", "", f"{skup:.2f} EUR"])
    tabela(ax, 20, 256, [110, 55, 60, 45], 7.5, vrste, naslov="PREDRAČUN")

    opombe = []
    if vse_nic:
        opombe.append("Cenik vsebuje samo PRIMER vrednosti (0.00) — zneski "
                      "NISO obračunani in ta predračun ni ponudba.")
    elif delno:
        opombe.append("Cenik ni popoln — postavke brez cene niso "
                      "obračunane.")
    if manjkajoce_cene:
        opombe.append("Manjkajoče cene (dodaj jih v 'cene'): "
                      + ", ".join(manjkajoce_cene)
                      + " — te postavke NISO vštevete v seštevek!")
        _opozori("Predračun: manjkajo cene za " + ", ".join(manjkajoce_cene)
                 + " — postavke brez cene niso vštete v seštevek.")
    opombe += [
        "Predračun je ORIENTACIJSKI in brez DDV; veljavnost 30 dni.",
        "Postavke z napisom 'cena po dogovoru' niso vštete v SKUPAJ.",
        "Cene materialov so nastavljene v konfiguraciji ('cene'); "
        "količine po dejanski porabi, odpad je prikazan posebej.",
        "Konstrukcijsko ustreznost (nosilnost, sidranje, veterno breme) "
        "preveri usposobljen strokovnjak — risba ni statični izračun.",
        "Montaža po dogovoru; končno poravnanje po prevzemu dela.",
    ]
    opombe_blok(ax, 20, 185, 260, opombe, naslov_t="OPOMBE K PREDRAČUNU")


# ---------------------------------------------------------------- glavno
ZADNJA_OPOZORILA: list = []   # opozorila zadnjega generiraj() (npr. padel list 2)


def _opozori(sporocilo):
    """Zabeleži opozorilo o nepopolnem dokumentu (A1): vidno uporabniku.

    Enaka opozorila se zabeležijo le enkrat (vrata se preverjajo v več
    pogledih — brez podvajanja).
    """
    if sporocilo in ZADNJA_OPOZORILA:
        return
    ZADNJA_OPOZORILA.append(sporocilo)
    print("OPOZORILO: " + sporocilo, file=sys.stderr)


def generiraj(cfg, dpi_png=200):
    """Iz konfiguracije nariše risbo in vrne (pot_pdf, pot_png, dodatni, kolicine).

    Vse strani PDF se zapišejo v ENEM življenjskem ciklu PdfPages (A1) —
    nobenega savefig po zaprtju (matplotlib bi sicer tiho prepisal datoteko).
    Figure se vedno zaprejo tudi ob napaki (try/finally). Če kateri list
    odpove, je to jasno zapisano v ZADNJA_OPOZORILA in na stderr — nepopoln
    dokument NI prikazan kot običajen uspeh.
    """
    if not (cfg or {}).get("izhod"):
        raise ValueError("Manjka 'izhod' (pot do PDF). Brez njega se PDF "
                         "ne sme tiho zapisati v trenutno mapo.")
    cfg = zdruzi(cfg or {})
    surovo = str(cfg.get("predloga", "") or "ograja").strip().lower()
    pred_norm = {"ograda": "ograja"}.get(surovo, surovo)
    if pred_norm not in ("ograja", "pokončna"):
        raise ValueError(f"Neznana predloga: {cfg.get('predloga')!r} "
                         f"(na voljo: ograja, pokončna)")
    predloga = PREDLOGE[pred_norm]
    napake = preveri_cfg(cfg)
    if napake:
        raise ValueError("Kontrola pravilnosti ni uspela — PDF ni bil "
                         "izdelan:\n- " + "\n- ".join(napake))
    del ZADNJA_OPOZORILA[:]
    izhod = os.path.abspath(cfg["izhod"])
    ml_fn = {"ograja": narisi_montazni_list,
             "ograda": narisi_montazni_list,
             "pokončna": narisi_montazni_pokoncna}.get(pred_norm)

    fig = fig2 = fig3 = fig4 = None
    try:
        fig, ax = nov_list()
        predloga(ax, cfg)

        kolicine = None
        if ml_fn:
            try:
                fig2, ax2 = nov_list()
                kolicine = ml_fn(ax2, cfg)
            except Exception as napaka:
                if fig2 is not None:
                    plt.close(fig2)
                fig2 = None
                _opozori(f"Montažni list (list 2/2) ni bil izdelan — PDF "
                         f"vsebuje samo risbo (list 1/2). Vzrok: {napaka}")

        if kolicine and (cfg.get("cene") or {}):
            try:
                fig3, ax3 = nov_list()
                narisi_predracun(ax3, cfg, kolicine["postavke"])
            except Exception as napaka:
                if fig3 is not None:
                    plt.close(fig3)
                fig3 = None
                _opozori(f"Predračun (priloga) ni bil izdelan — PDF je brez "
                         f"strani s predračunom. Vzrok: {napaka}")

        if kolicine and kolicine.get("kosovnica"):
            try:
                fig4, ax4 = nov_list()
                narisi_nalepke(ax4, cfg, kolicine["kosovnica"])
            except Exception as napaka:
                if fig4 is not None:
                    plt.close(fig4)
                fig4 = None
                _opozori(f"Nalepke (priloga) niso bile izdelane — PDF je brez "
                         f"strani z nalepkami. Vzrok: {napaka}")

        # VSE strani v enem PdfPages ciklu (A1) — vrstni red: risba,
        # montažni list, predračun, nalepke.
        with PdfPages(izhod) as pdf:
            pdf.savefig(fig)
            for f in (fig2, fig3, fig4):
                if f is not None:
                    pdf.savefig(f)

        # dodatni izvozi (PNG/CSV/TXT) — po zaprtju PDF, ne vplivajo nanj
        png = os.path.splitext(izhod)[0] + ".png"
        fig.savefig(png, dpi=dpi_png)
        dodatni = []
        if kolicine and kolicine.get("kosovnica"):
            cs_pot = os.path.splitext(izhod)[0] + "-kosovnica.csv"
            with open(cs_pot, "w", encoding="utf-8-sig", newline="") as f:
                f.write("Oznaka;Dolzina (mm);Vir;Material\n")
                for (oz, dol, vir, mat) in kolicine["kosovnica"]:
                    f.write(f"{oz};{fmt(dol)};{vir};{mat}\n")
            dodatni.append(cs_pot)
            if fig4 is not None:
                p4 = os.path.splitext(izhod)[0] + "-nalepke.png"
                fig4.savefig(p4, dpi=dpi_png)
                dodatni.append(p4)
        if kolicine and kolicine.get("narocilo"):
            n_pot = os.path.splitext(izhod)[0] + "-narocilo.txt"
            with open(n_pot, "w", encoding="utf-8") as f:
                f.write(kolicine["narocilo"])
            dodatni.append(n_pot)
        if fig2 is not None:
            p2 = os.path.splitext(izhod)[0] + "-montazni-list.png"
            fig2.savefig(p2, dpi=dpi_png)
            dodatni.append(p2)
        if fig3 is not None:
            p3 = os.path.splitext(izhod)[0] + "-predracun.png"
            fig3.savefig(p3, dpi=dpi_png)
            dodatni.append(p3)
        return izhod, png, dodatni, kolicine
    finally:
        for f in (fig, fig2, fig3, fig4):
            if f is not None:
                plt.close(f)


def generiraj_z_opozorili(cfg, dpi_png=200):
    """Kot generiraj(), a opozorila vrne kot del rezultata (F2, issue #5).

    Vrne (izhod, png, dodatni, kolicine, opozorila) — opozorila so
    kopija ZADNJA_OPOZORILA tega generiranja (ne globalni dostop).
    Stari generiraj() ostane za združljivost (4-terica + ZADNJA_OPOZORILA).
    """
    ZADNJA_OPOZORILA.clear()
    izhod, png, dodatni, kolicine = generiraj(cfg, dpi_png=dpi_png)
    return izhod, png, dodatni, kolicine, list(ZADNJA_OPOZORILA)


def main():
    ap = argparse.ArgumentParser(description="Generator tehničnih risb (PDF A3).")
    ap.add_argument("konf", nargs="?",
                    help="pot do projekt.yaml (brez: vprašanja v terminalu)")
    ap.add_argument("-o", "--izhod", help="ime izhodne PDF datoteke")
    ap.add_argument("--potrosi-ostanke", action="store_true",
                    help="odpiše porabljene ostanke iz ostanki.yaml")
    ap.add_argument("--dxf", action="store_true",
                    help="izvozi tudi DXF za CAD/CNC (ezdxf, mm 1:1)")
    a = ap.parse_args()

    cfg = nalozi_konf(a.konf) if a.konf else interaktivno()
    if a.izhod:
        cfg["izhod"] = a.izhod

    try:
        izhod, png, dodatni, kolicine = generiraj(cfg)
    except ValueError as e:
        sys.exit(str(e))

    print(f"[OK] Risba:    {izhod}")
    print(f"[OK] Predogled: {png}")
    if a.dxf:
        try:
            import dxf_izvoz
            pot_dxf, por = dxf_izvoz.izvozi_dxf(cfg)
            print(f"[OK] DXF:      {pot_dxf}")
        except Exception as e:
            sys.exit(f"Napaka pri DXF izvozu: {e}")
    for p in dodatni:
        print(f"[OK] Dodatno: {p}")
    if a.potrosi_ostanke:
        if not kolicine or kolicine.get("ostanki_posodobitev") is None:
            print("[INFO] Ni sprememb skladišča ostankov za odpis.")
        else:
            pot, backup = shrani_ostanke(kolicine["ostanki_posodobitev"])
            print(f"[OK] Ostanki odpisani iz skladišča: {pot}")
            if backup:
                print(f"[OK] Varnostna kopija: {backup}")
    if ZADNJA_OPOZORILA:
        print("[OPOZORILO] Dokument NI popoln — poglej opozorila zgoraj.",
              file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
