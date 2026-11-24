# -*- coding: utf-8 -*-
"""Montažni list (stran 2): krajšanje dolgih tabel — nikoli tiho.

Dolg rezalni načrt (več deset desk) ne sme tiho izginiti ali preliti
lista: pokaže se 10 vrst, zadnja vrstica pa pove, koliko vrst je ostalo
(polna kosovnica je v CSV in na nalepkah). Enako velja za vizualni rez:
največ 5 trakov, z zapisom „prikazanih 5 od N trakov“.
"""

import risba


def _narisi(rez_vrst, viz_traki):
    fig, ax = risba.nov_list()
    risba.montazni_osnova(
        ax, {"risba_st": "T-001"}, [["DESKE", "5800", "6 kos", ""]],
        rez_vrst, viz_traki, ["privij nosilce na deske"])
    return fig, ax


def _besedila(ax):
    return " ".join(t.get_text() for t in ax.texts)


def _rez_vrst(n):
    return ([["VIR", "KOSOV", "KOSI ŠT.", "OSTANEK PO REZU (mm)"]]
            + [[f"DESKA {i} (nabava, 5800 mm)", "2", f"{2 * i - 1}\u2013{2 * i}",
                "790"] for i in range(1, n + 1)])


def _viz_traki(n):
    return [(5800.0, [(f"D{2 * i - 1}", 2500.0), (f"D{2 * i}", 2500.0)])
        for i in range(1, n + 1)]


def test_rezalni_nacrt_nad_desetimi_vrstami_pove_koliko_jih_je_ostalo():
    """15 vrst -> 10 vidnih + jasna vrstica „… ostalih 5 vrst“."""
    fig, ax = _narisi(_rez_vrst(15), _viz_traki(2))
    try:
        bes = _besedila(ax)
        assert "ostalih 5 vrst" in bes
        assert "polna kosovnica: CSV + nalepke" in bes
        assert "DESKA 10" in bes          # 10. vrstica je še prikazana
        assert "DESKA 11" not in bes      # 11. je že skrita
        assert "DESKA 15" not in bes      # zadnja prav tako
    finally:
        risba.plt.close(fig)


def test_rezalni_nacrt_z_desetimi_vrstami_ni_okrnjen():
    """10 vrst je še celih — brez vrstice „… ostalih“."""
    fig, ax = _narisi(_rez_vrst(10), _viz_traki(2))
    try:
        bes = _besedila(ax)
        assert "ostalih" not in bes
        assert "DESKA 10" in bes
    finally:
        risba.plt.close(fig)


def test_vizualni_rez_pokaze_najvec_pet_trakov_in_pove_ostalo():
    """7 trakov -> 5 narisanih + „prikazanih 5 od 7 trakov“."""
    fig, ax = _narisi(_rez_vrst(2), _viz_traki(7))
    try:
        bes = _besedila(ax)
        assert "prikazanih 5 od 7 trakov" in bes
        assert "D10" in bes               # 5. trak je še narisan
        assert "D11" not in bes           # 6. trak ni
        assert "D14" not in bes
    finally:
        risba.plt.close(fig)


def test_vizualni_rez_brez_okrnitve_tega_ne_zapise():
    """Pri 5 trakovih ali manj stavka o prikazanih trakovih ni."""
    fig, ax = _narisi(_rez_vrst(2), _viz_traki(5))
    try:
        bes = _besedila(ax)
        assert "prikazanih" not in bes
        assert "D10" in bes
    finally:
        risba.plt.close(fig)
