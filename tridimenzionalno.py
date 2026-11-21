# -*- coding: utf-8 -*-
"""tridimenzionalno.py — shematski 3D prikaz ograje (UI/UX Plan I).

Vzor: Visual Fence Pro 3D ogled („spin it, layer by layer“).

ISKRENO: to je SHEMATSKI 3D prikaz za predstavo (ni fotorealistično, ni
konstrukcijski model). Mere prihajajo iz istega `cfg` kot risba — EN vir
resnice (issue #6). Brez AI (omejitev #8).

Uporaba:
    import tridimenzionalno as t3
    fig = t3.sestavi_3d(cfg)          # matplotlib Figure
    t3.narisi_3d_png(cfg, "3d.png")
    t3.pokazi_3d(cfg, master)         # interaktivno okno (vrtenje)
"""
from jedro import razpored, razpored_pokoncna, pozicije_nosilcev, vrata_podatki

BARVA_DESKE = "#8d6e63"
BARVA_PROFIL = "#90a4ae"
BARVA_STEBER = "#455a64"
BARVA_TLA = "#e0e0e0"
BARVA_OKVIR = "#1565c0"


def _skatla(kol, x0, x1, y0, y1, z0, z1, barva):
    """Ena skatla (12 trikotnikov) v Poly3DCollection."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    plasti = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
              (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)]
    obrazi = [[v[i] for i in pl] for pl in plasti]
    kol.add_collection3d(Poly3DCollection(obrazi, facecolors=barva,
                                          edgecolors="#333333",
                                          linewidths=0.25, alpha=0.95))


def sestavi_3d(c):
    """Sestavi matplotlib 3D figuro ograje iz konfiguracije."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = c["mere"]
    sir = float(m["sirina"] or 0)
    vis = float(m["visina"] or 0)
    glob = float(m.get("globina") or 60)
    odcep = float(m.get("odcep") or 0)
    predloga = c.get("predloga") or "ograda"
    vp = vrata_podatki(c)
    odprtine = vp["odprtine"]

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection="3d")

    # tla
    _skatla(ax, -200, sir + 200, -150, 150, -20, 0, BARVA_TLA)

    if predloga == "pokončna":
        p = razpored_pokoncna(m)
        ds = float(m.get("deska_sirina", 100) or 100)
        dt = float(m.get("deska_debelina", 20) or 20)
        visina_deske = p["deske_h"]
        for xr in p["deske_x"]:
            # deska je lahko razrezana okoli odprtin
            kosi = _razdeli(xr, xr + ds, odprtine)
            for xa, xb in kosi:
                _skatla(ax, xa, xb, -dt / 2, dt / 2,
                        odcep, odcep + visina_deske, BARVA_DESKE)
        # stebri
        for xs in p["centri"]:
            _skatla(ax, xs - 30, xs + 30, -40, 40,
                    odcep - 40, odcep + vis, BARVA_STEBER)
        # ročaj
        rz0, rz1 = p["rocaj"]
        _skatla(ax, 0, sir, -35, 35, odcep + rz0, odcep + rz1,
                BARVA_PROFIL)
    else:
        zg, sp, lamele, _vrzel, n = razpored(m)
        deb = float(m.get("debelina", 20) or 20)
        # lamele (vodoravne) — zareze okoli odprtin
        for z0, z1 in lamele:
            for xa, xb in _razdeli(0.0, sir, odprtine):
                _skatla(ax, xa, xb, -deb / 2, deb / 2, z0, z1, BARVA_DESKE)
        # profila (zgornji/spodnji) — po celotni širini, prekinjena pri vratih
        for z0, z1 in ((zg[0], zg[1]), (sp[0], sp[1])):
            for xa, xb in _razdeli(0.0, sir, odprtine):
                _skatla(ax, xa, xb, -40, 40, z0, z1, BARVA_PROFIL)
        # nosilci
        xs_nos, _razmak = pozicije_nosilcev(sir,
                                            float(m.get("razmak_nosilcev",
                                                        1000) or 1000))
        for xn in xs_nos:
            if not _znotraj_odprtine(xn, odprtine):
                _skatla(ax, xn - 30, xn + 30, -60, -40,
                        sp[0], zg[1], BARVA_STEBER)

    # okvirji vrat/prehodov
    for (ox0, ox1, ozn) in odprtine:
        vis_o = 2000.0
        for enota in vp["vrata"] + vp["prehodi"]:
            if enota.get("oznaka") == ozn:
                vis_o = float(enota["g"]["odprtina"]["visina"])
        _skatla(ax, ox0, ox0 + 60, -70, -50, odcep, odcep + vis_o,
                BARVA_OKVIR)
        _skatla(ax, ox1 - 60, ox1, -70, -50, odcep, odcep + vis_o,
                BARVA_OKVIR)
        _skatla(ax, ox0, ox1, -70, -50, odcep + vis_o - 60,
                odcep + vis_o, BARVA_OKVIR)

    ax.set_xlabel("širina (mm)")
    ax.set_ylabel("globina (mm)")
    ax.set_zlabel("višina (mm)")
    ax.set_title(f"3D predogled — {c.get('ime') or 'ograda'} "
                 f"(shematsko, ni konstrukcijski model)")
    ax.set_box_aspect((max(sir, 1), max(glob * 3, 1), max(vis, 1)))
    ax.view_init(elev=18, azim=-55)
    return fig


def _razdeli(x0, x1, odprtine):
    """Intervali [x0, x1] brez odprtin (kot jedro.razdeli_po_odprtinah)."""
    intervali = [(float(x0), float(x1))]
    for od in odprtine:
        ox0, ox1 = float(od[0]), float(od[1])
        novi = []
        for a, b in intervali:
            if ox1 <= a or ox0 >= b:
                novi.append((a, b))
            else:
                if a < ox0:
                    novi.append((a, ox0))
                if ox1 < b:
                    novi.append((ox1, b))
        intervali = novi
    return [(a, b) for a, b in intervali if b - a > 1e-6]


def _znotraj_odprtine(x, odprtine):
    return any(float(od[0]) - 1e-6 <= x <= float(od[1]) + 1e-6
               for od in odprtine)


def narisi_3d_png(c, pot, dpi=110):
    """Shrani 3D prikaz v PNG (za ponudbo/dokumentacijo)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = sestavi_3d(c)
    fig.savefig(pot, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return pot


def pokazi_3d(c, master=None):
    """Odpri interaktivno 3D okno (vrtenje/povečava z miško)."""
    import tkinter as tk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
    import matplotlib.pyplot as plt

    fig = sestavi_3d(c)
    okno = tk.Toplevel(master) if master is not None else tk.Tk()
    okno.title("3D predogled ograje (vrti z miško)")
    canvas = FigureCanvasTkAgg(fig, master=okno)
    canvas.get_tk_widget().pack(fill="both", expand=True)
    orodna = NavigationToolbar2Tk(canvas, okno)
    orodna.update()
    canvas.draw()

    def _zapri():
        plt.close(fig)
        okno.destroy()

    okno.protocol("WM_DELETE_WINDOW", _zapri)
    return okno