# -*- coding: utf-8 -*-
"""ponudba.py — PDF ponudba za stranko z opcijami Good/Better/Best.

UI/UX Plan G (raziskava: Visual Fence Pro „Good/Better/Best“, Paper2Quote
predloge ponudb).

POŠTENOST (projektna pravila): cene se NE izmišljajo z množitelji.
Opciji OSNOVNA in PREMIUM se izračunata iz konfiguracijskih cenikov
`cene_osnovna` / `cene_premium`; če cenika ni, je znesek opcije
„cena po dogovoru“ — brez izmišljene številke.

Uporaba:
    import ponudba
    ponudba.narisi_ponudbo("ponudba.pdf", cfg)
"""
import datetime

from proizvodnja import izracunaj_kolicine, kolicina_z_enoto, predracun_znesek

# barve kartic (osnovna, priporočena, premium)
BARVE = ("#455a64", "#2e7d32", "#6a1b9a")

OPISI_PRIVZETO = {
    "OSNOVNA": "Standardna izvedba — standardni materiali in pritrdila.",
    "PRIPOROČENA": "Priporočena izvedba — cenik iz konfiguracije "
                   "(ravnotežje cena/kakovost).",
    "PREMIUM": "Premium izvedba — premium materiali in oprema "
               "(cenik `cene_premium`).",
}


def sestavi_moznosti(c):
    """Tri opcije ponudbe (Good/Better/Best) IZ konfiguracije.

    Vrne [{"ime", "opis", "znesek" (ali None = po dogovoru),
           "manjkajoce" (cene), "oznaka"}].
    """
    kol = izracunaj_kolicine(c)
    variante = (
        ("OSNOVNA", "cene_osnovna"),
        ("PRIPOROČENA", None),          # glavni cenik (cene)
        ("PREMIUM", "cene_premium"),
    )
    out: list = []
    for (ime, kljuc_cenika) in variante:
        cene = (c.get("cene") if kljuc_cenika is None
                else c.get(kljuc_cenika))
        if not cene:
            out.append({
                "ime": ime,
                "opis": (OPISI_PRIVZETO[ime] + " Cenik ni podan — "
                         "znesek se določi po dogovoru."),
                "znesek": None,
                "manjkajoce": [],
                "oznaka": "cena po dogovoru",
            })
            continue
        z = predracun_znesek(cene, kol["postavke"])
        if z["vse_nic"]:
            oznaka = "ni obračunano (cene so PRIMER)"
        elif z["delno"]:
            oznaka = f"{z['skupaj']:.2f} EUR (delno — manjkajoče cene)"
        else:
            oznaka = f"{z['skupaj']:.2f} EUR"
        out.append({
            "ime": ime,
            "opis": OPISI_PRIVZETO[ime],
            "znesek": z["skupaj"] if not z["vse_nic"] else None,
            "manjkajoce": z["manjkajoce_cene"],
            "oznaka": oznaka,
        })
    return out


def _zavij(ax, x, y, besedilo, max_zn, fs=7.0, barva="#333333"):
    import textwrap
    for vrstica in textwrap.wrap(besedilo, width=max_zn) or [""]:
        ax.text(x, y, vrstica, fontsize=fs, ha="left", va="top",
                color=barva)
        y -= fs * 0.55
    return y


def narisi_ponudbo(pot_pdf, c, moznosti=None):
    """Nariši PDF ponudbo (A4 pokončno)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    moznosti = moznosti if moznosti is not None else sestavi_moznosti(c)
    kol = izracunaj_kolicine(c)

    fig = plt.figure(figsize=(8.27, 11.69))          # A4 pokončno
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, 210)
    ax.set_ylim(0, 297)
    ax.axis("off")

    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")

    # ---- glava ----
    ax.add_patch(plt.Rectangle((12, 268), 186, 20, facecolor="#eceff1",
                               edgecolor="#90a4ae", lw=0.8))
    ax.text(16, 282, f"{c.get('podjetje') or '—'}",
            fontsize=13, fontweight="bold", va="center")
    ax.text(16, 273.5, "PONUDBA ZA IZDELAVO IN MONTAŽO OGRAJE",
            fontsize=10, va="center", color="#37474f")
    ax.text(194, 282, f"Št.: {c.get('risba_st') or '—'}",
            fontsize=9, ha="right", va="center")
    ax.text(194, 275, f"Datum: {datum}", fontsize=9, ha="right",
            va="center")

    ax.text(12, 262, f"Stranka: {c.get('stranka') or '—'}", fontsize=9)
    ax.text(12, 257, f"Objekt: {c.get('objekt') or '—'}", fontsize=9)
    ax.text(12, 252, f"Projekt: {c.get('ime') or '—'}", fontsize=9)
    ax.text(12, 247, "Veljavnost ponudbe: 30 dni od datuma",
            fontsize=9, color="#546e7a")

    # ---- vključene količine ----
    ax.text(12, 238, "V CENO SO UPRAŠTEVANI (po izračunu količin):",
            fontsize=9.5, fontweight="bold")
    y = 233.0
    for (naziv, kol_str, enota, _k, _n) in kol["postavke"][:8]:
        ax.text(14, y, f"• {naziv}: {kolicina_z_enoto(kol_str, enota)}",
                fontsize=7.8, va="top")
        y -= 4.2
    if len(kol["postavke"]) > 8:
        ax.text(14, y, f"• … skupaj {len(kol['postavke'])} postavk "
                       "(podroben popis v prilogi k risbi)",
                fontsize=7.8, va="top", color="#546e7a")
        y -= 4.2

    # ---- tri opcije (Good/Better/Best) ----
    y_kartice = y - 6
    ax.text(12, y_kartice + 2, "IZVEDBENE MOŽNOSTI:",
            fontsize=9.5, fontweight="bold")
    yk = y_kartice - 6
    for i, m in enumerate(moznosti):
        barva = BARVE[min(i, len(BARVE) - 1)]
        ax.add_patch(plt.Rectangle((12, yk - 30), 186, 30,
                                   facecolor="#ffffff", edgecolor=barva,
                                   lw=1.4))
        ax.add_patch(plt.Rectangle((12, yk - 8), 186, 8,
                                   facecolor=barva, edgecolor=barva))
        ax.text(16, yk - 4.5, f"{i + 1}. {m['ime']}", fontsize=10,
                fontweight="bold", color="white", va="center")
        ax.text(194, yk - 4.5, m["oznaka"], fontsize=10,
                fontweight="bold", color="white", ha="right", va="center")
        _zavij(ax, 16, yk - 10.5, m["opis"], 105, fs=7.2)
        if m["manjkajoce"]:
            ax.text(16, yk - 27, "Manjkajoče cene: "
                    + ", ".join(m["manjkajoce"]), fontsize=6.8,
                    color="#b26a00", va="bottom")
        yk -= 34

    # ---- opombe (poštenost) ----
    y_op = yk - 4
    ax.text(12, y_op, "OPOMBE IN POGOJI:", fontsize=9.5,
            fontweight="bold")
    opombe = [
        "Vse cene so BREZ DDV in orientacijske; veljajo 30 dni.",
        "Kjer znesek ni naveden („cena po dogovoru“), se cena določi "
        "po ogledu objekta in dogovoru o obsegu.",
        "Mere temeljijo na podatkih naročnika/meritvah s fotografije in se "
        "pred izdelavo OBVEZNO preverijo na objektu.",
        "Ponudba NI statični izračun — nosilnost, sidranje in veterno "
        "breme preveri usposobljen strokovnjak.",
        "Rok izvedbe in plačilni pogoji se določijo ob potrditvi ponudbe.",
    ]
    yy = y_op - 5
    for o in opombe:
        yy = _zavij(ax, 14, yy, "• " + o, 100, fs=7.2, barva="#455a64")
        yy -= 1.2

    # ---- podpisna vrstica ----
    ax.text(12, 28, "Kraj in datum: ______________________",
            fontsize=9)
    ax.text(12, 18, "Podpis naročnika: ______________________",
            fontsize=9)
    ax.text(120, 18, "Za izvajalca: ______________________",
            fontsize=9)

    with PdfPages(pot_pdf) as pdf:
        pdf.savefig(fig)
    plt.close(fig)
    return pot_pdf