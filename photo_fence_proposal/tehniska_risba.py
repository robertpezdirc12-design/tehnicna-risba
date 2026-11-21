"""photo_fence_proposal — tehnična risba nove ograje s kotiranjem in statusi (B).

Sprednji pogled + kote z oznakami zanesljivosti († izmerjeno, ‡ izračunano,
≈ ocenjeno, ?? neznano) + kosovnica + opozorila. PDF prek matplotlib (kot v
obstoječem projektu, a SAMOSTOJNO — brez uvoza risba.py).

Dokument je označen z oznako rezultata: informativni predlog, dokler ključne
mere niso potrjene (issue #8: "ne sme si izmišljati mer").
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from model import Rezultat, NEZNANO

MERILO_RISBE = 0.06  # px/mm risalne enote (za A3 stran)


def _kota(ax, x0, y0, x1, y1, besedilo, offset=40.0, navpicno=False):
    barva = "#1f4e9c"
    if navpicno:
        ax.annotate("", xy=(x0, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="<->", color=barva, lw=0.8))
        ax.text(x0 - offset, (y0 + y1) / 2, besedilo, rotation=90,
                ha="center", va="center", fontsize=8, color=barva)
    else:
        ax.annotate("", xy=(x1, y0), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="<->", color=barva, lw=0.8))
        ax.text((x0 + x1) / 2, y0 - offset, besedilo, ha="center", va="center",
                fontsize=8, color=barva)


def narisi_tehnisko_risbo(rezultat: Rezultat, pot: str) -> str:
    mere = rezultat.mere
    dolzina = mere.get("dolzina_ograje")
    visina = mere.get("visina_ograje")
    dolz = dolzina.vrednost_mm if dolzina and dolzina.vrednost_mm else None
    vis = visina.vrednost_mm if visina and visina.vrednost_mm else None

    # risalne mere (če so neznane, se nariše shematsko z ??? — NE izmišljeno)
    L = dolz if dolz else 3000.0
    H = vis if vis else 1800.0

    with PdfPages(pot) as pdf:
        fig = plt.figure(figsize=(16.54, 11.69))  # A3 ležeče (palcev)
        ax = fig.add_axes([0.05, 0.18, 0.9, 0.62])
        ax.set_aspect("equal")
        ax.axis("off")

        # --- sprednji pogled ---
        # tla
        ax.plot([0, L * 1.15], [0, 0], color="#000000", lw=1.2)
        # okvir ograje
        ax.add_patch(plt.Rectangle((0, 0), L, H, fill=False,
                                   edgecolor="#222222", lw=1.4))
        # lamele
        param = rezultat.parametri
        korak = param.sirina_lamele_mm + param.razmak_mm
        y = 0.0
        while y < H:
            y += param.sirina_lamele_mm
            if y < H:
                ax.plot([0, L], [y, y], color="#33465c", lw=2.2)
            y += param.razmak_mm
        # stebri
        n_stebrov = 2
        st = mere.get("stevilo_stebrov")
        if st and st.vrednost_mm:
            n_stebrov = int(st.vrednost_mm)
        for i in range(n_stebrov):
            x = L * i / max(1, n_stebrov - 1)
            ax.add_patch(plt.Rectangle((x - 30, -200), 60, H + 200,
                                       fill=False, edgecolor="#111111", lw=1.6))

        # --- kote s statusi ---
        oznaka_d = (dolzina.oznaka if dolzina else "?? mm (neznano)")
        oznaka_v = (visina.oznaka if visina else "?? mm (neznano)")
        _kota(ax, 0, -420, L, -420, f"Dolžina: {oznaka_d}")
        _kota(ax, L * 1.12, 0, L * 1.12, H, f"Višina: {oznaka_v}", navpicno=True)

        # --- naslov ---
        naslov = (f"SPREDNJI POGLED — {param.tip.replace('_', ' ')}   |   "
                  f"{rezultat.oznaka_dokumenta}")
        if dolz is None or vis is None:
            naslov += "   |   shematski prikaz (mere niso znane)"
        ax.set_title(naslov, fontsize=11, loc="left")

        # --- kosovnica ---
        ax2 = fig.add_axes([0.05, 0.02, 0.55, 0.14])
        ax2.axis("off")
        vrstice = [["Naziv", "Material", "Dimenzija", "Kol.", "Status mer"]]
        for p in rezultat.kosovnica:
            vrstice.append([p.naziv, p.material, p.dimenzija,
                            f"{p.kolicina:.0f} {p.enota}", p.status_mer])
        tabela = ax2.table(cellText=vrstice[1:], colLabels=vrstice[0],
                           loc="upper center", cellLoc="left")
        tabela.auto_set_font_size(False)
        tabela.set_fontsize(7)
        tabela.scale(1, 1.4)
        ax2.set_title("KOSOVNICA (informativna, če mere niso potrjene)",
                      fontsize=9, loc="left")

        # --- opozorila in legenda ---
        ax3 = fig.add_axes([0.63, 0.02, 0.32, 0.14])
        ax3.axis("off")
        besedilo = ["LEGENDA MER:",
                    "† izmerjeno (kalibrirano)   ‡ izračunano",
                    "≈ ocenjeno (NI potrjeno)   ?? neznano — potrdi", ""]
        besedilo += ["OPOZORILA:"]
        besedilo += [f"• {o}" for o in rezultat.opozorila[:6]]
        ax3.text(0, 1, "\n".join(besedilo), fontsize=6.5, va="top",
                 family="monospace")

        pdf.savefig(fig)
        plt.close(fig)
        meta = pdf.infodict()
        meta["Title"] = f"Tehnična risba — {rezultat.oznaka_dokumenta}"
        meta["Creator"] = "photo_fence_proposal (brez AI modelov)"
    return pot