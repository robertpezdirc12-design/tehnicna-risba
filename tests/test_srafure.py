# -*- coding: utf-8 -*-
"""Šrafure po ISO 128-50 — konvencija vzeta iz CAD sveta (docs/gstarcad-
povezava.md), implementirana samostojno v risba.py (brez zunanjih orodij).

- sachiranje: 45° diagonale s clipom na pravokotnik (zid/tla/PREREZ)
- srafura_betona: drobci + trikotniki (beton)
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import risba  # noqa: E402


def _os():
    fig = plt.figure(figsize=(4, 3))
    return fig, fig.add_subplot(111)


def test_sachiranje_tanka_crta_za_prerez():
    """Prerez ima tanke črte (lw≈0,2), zid ostane pri debelih (0,55)."""
    fig, ax = _os()
    try:
        risba.sachiranje(ax, 0, 0, 10, 5, razmak=1.6, lw=0.2)
        crte = [l for l in ax.lines]
        assert crte, "šrafura ni narisanа"
        assert all(abs(l.get_linewidth() - 0.2) < 1e-9 for l in crte)
    finally:
        plt.close(fig)


def test_sachiranje_privzeto_ostane_debelo():
    """Obstoječe šrafure zidu (6 klicev) se NE spreminjajo."""
    fig, ax = _os()
    try:
        risba.sachiranje(ax, 0, 0, 10, 5)          # brez novih parametrov
        assert ax.lines and abs(ax.lines[0].get_linewidth() - 0.55) < 1e-9
    finally:
        plt.close(fig)


def test_sachiranje_diagonale_45_in_clip():
    """Diagonale so pod 45° in imajo clip na pravokotnik."""
    fig, ax = _os()
    try:
        risba.sachiranje(ax, 2, 3, 12, 9, razmak=1.6, lw=0.2)
        for l in ax.lines:
            (x0, x1), (y0, y1) = l.get_data()
            assert abs((y1 - y0) - (x1 - x0)) < 1e-9, "ni 45°"
            # pravokoten patch clip matplotlib shrani kot clipbox
            assert (l.get_clip_path() is not None or
                    l.get_clip_box() is not None), "brez clipa"
    finally:
        plt.close(fig)


def test_srafura_betona_determinirana():
    """Betonska šrafura je determinirana (brez naključja) — drobci in trikotniki."""
    fig, ax = _os()
    try:
        risba.srafura_betona(ax, 0, 0, 20, 6)
        oznake = [l.get_marker() for l in ax.lines]
        assert "^" in oznake and "." in oznake, oznake
        # determiniranost: ponovni klic da enako število oznak
        fig2, ax2 = _os()
        risba.srafura_betona(ax2, 0, 0, 20, 6)
        assert len(ax.lines) == len(ax2.lines)
        plt.close(fig2)
    finally:
        plt.close(fig)


def test_pdf_vsebuje_opombo_o_srafuri():
    """Obe predlogi v DETAJL 2 pojasnita šrafuro (iskrena označba)."""
    import os
    import tempfile
    from pypdf import PdfReader

    for predloga in ("ograja", "pokončna"):
        cfg = {"tip": "ograja", "sirina": 2500, "visina": 1850, "odcep": 250,
               "globina": 40, "stevilo_lamel": 13, "barva": "Teak",
               "vrata": [], "predloga": predloga, "izhod": "r.pdf"}
        with tempfile.TemporaryDirectory() as td:
            pot = os.path.join(td, "r.pdf")
            cfg["izhod"] = pot
            risba.generiraj(cfg, dpi_png=30)
            besedilo = "".join(
                (p.extract_text() or "") for p in PdfReader(pot).pages)
            assert "šrafura 45° = prerezani material (ISO 128-50)" in besedilo, \
                predloga

def test_prerez_je_preko_polnila():
    """Šrafura prereza mora biti PREKO barvnega polnila (zorder 4),
    sicer je nevidna (napaka iz vizualnega preizkusa)."""
    fig, ax = _os()
    try:
        risba.sachiranje(ax, 0, 0, 10, 5, razmak=1.6, lw=0.2, z=4)
        assert all(l.get_zorder() == 4 for l in ax.lines)
        # zid/tla ostanejo zadaj (privzeti z=1)
        risba.sachiranje(ax, 20, 0, 30, 5)
        assert any(l.get_zorder() == 1 for l in ax.lines)
    finally:
        plt.close(fig)


def test_opombe_blok_ne_prekrije_naslovni_blok():
    """Zadnje opombe se ne smejo SKRITI za naslovnim blokom (dno=40).

    To je bila prava napaka: 6 privzetih opomb je zašlo pod naslovni blok
    in bilo v risbi nevidno (v PDF besedilu pa sicer izvlečeno)."""
    fig, ax = _os()
    try:
        opombe = [
            "Vse mere v mm (tolerance ISO 2768-m — glej blok SPLOŠNE "
            "TOLERANCE); pred izdelavo preveri dejanske mere na objektu.",
            "Lamele: ROMB 67 — WPC (bambus + HDPE), 15 let garancije, brez barvanja.",
            "Profili/nosilci: aluminij, prašno barvano (RAL po dogovoru, privzeto RAL 7016).",
            "Pritrditev: vrh — pritrdilni material prilagodi podlagi na objektu "
            "(beton/zid/les/jeklo); predrtje Ø + 1 mm.",
            "Razmak nosilcev največ 1000 mm; količine pritrdilnih elementov orientacijske.",
            "Risba NI statični izračun — nosilnost, sidranje in veterno breme "
            "preveri usposobljen strokovnjak.",
        ]
        risba.opombe_blok(ax, 246, 74, 162, opombe, dno=40)
        najnizja = min(t.get_position()[1] for t in ax.texts)
        assert najnizja >= 40, f"opombe segajo do y={najnizja} (< 40)"
    finally:
        plt.close(fig)


def test_opombe_blok_iskreno_opozori_pri_prevelikem():
    """Če tudi skrčitev ne zadostuje, je odrez označen (ne tiho)."""
    fig, ax = _os()
    try:
        opombe = ["zelo dolga opomba " * 40 for _ in range(30)]
        risba.opombe_blok(ax, 246, 74, 162, opombe, dno=40)
        besedila = [t.get_text() for t in ax.texts]
        assert any("PRESEGAJO PROSTOR" in b for b in besedila), besedila
    finally:
        plt.close(fig)
