# -*- coding: utf-8 -*-
"""F4 (issue #5): pilot novih vrst ograj — deklarativni opis polj + predogled.

Namen: dokazati razširljiv model BREZ posegov v obstoječe predloge.
- deklarativni opisi polj (POLJA) — GUI/forma generira oznake iz opisa
  (konec polj brez oznak, U3);
- ena nova vrsta: LESENA VERTIKALNA (deske na vodoravnih letveh);
- količine iz ENEGA izračuna (isti slog kot risba.proizvodni_model);
- hitri predogled (PNG) PRED generiranjem celotnega dokumenta.

Modul je namenoma ločen in majhen — pilot, ne nova monolitna predloga.
"""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IME = "lesena_vertikalna"

# ---------------------------------------------------------------- opisi polj
# Declarative field descriptors — GUI/forma iz tega generira oznake,
# enote in opise; NIČ polj brez oznak (issue #5, U3).
POLJA = [
    # (ime, oznaka, enota, privzeto, opis)
    ("sirina", "Dolžina ograje", "mm", 6000.0,
     "skupna dolžina od prvega do zadnjega stebra"),
    ("visina", "Višina ograje", "mm", 1800.0,
     "višina od tal do vrha deske"),
    ("deska_sirina", "Širina deske", "mm", 140.0,
     "širina posamezne lesene deske"),
    ("deska_debelina", "Debelina deske", "mm", 21.0,
     "debelina deske (mm)"),
    ("vrzel", "Razmak med deskami", "mm", 20.0,
     "svetla razdalja med sosednjima deskama"),
    ("razmak_stebrov", "Razmak stebrov", "mm", 2000.0,
     "največji razmak med sosednjima stebroma"),
    ("steber_sirina", "Širina stebra", "mm", 90.0,
     "kvadratni steber"),
    ("letve", "Število vodoravnih letvi", "kos", 2.0,
     "nosilne letve za deskami (2–4)"),
]

PRAG_LEVIH = 2     # minimalno letvi
PRAG_ZGORNJIH = 4  # maksimalno letvi


def normaliziraj(mere):
    """Normalizira mere; manjkajoča polja dobijo privzete vrednosti."""
    privzeto = {polje[0]: polje[3] for polje in POLJA}
    izhod = dict(privzeto)
    for kljuc, vrednost in (mere or {}).items():
        if kljuc in izhod and vrednost is not None:
            izhod[kljuc] = float(vrednost)
    return izhod


def preveri(mere):
    """Vrne seznam napak z OZNAKAMI polj (ne golih ključev)."""
    m = normaliziraj(mere)
    oznake = {p[0]: p[1] for p in POLJA}
    napake = []
    for ime, vrednost in m.items():
        if vrednost <= 0:
            napake.append(f"»{oznake[ime]}« mora biti večje od 0 "
                          f"(vpisano: {vrednost})")
    if m["deska_sirina"] + m["vrzel"] <= 0:
        napake.append("»Širina deske« + »Razmak med deskami« morata biti > 0")
    if not (PRAG_LEVIH <= m["letve"] <= PRAG_ZGORNJIH):
        napake.append(f"»Število vodoravnih letvi« mora biti "
                      f"{PRAG_LEVIH}–{PRAG_ZGORNJIH} (vpisano: {m['letve']:.0f})")
    if m["razmak_stebrov"] < m["sirina"] / 20:
        napake.append("»Razmak stebrov« je nesorazmerno majhen glede na dolžino")
    return napake


def kolicine(mere):
    """Količine za leseno vertikalno ograjo (EN izračun za vse izpise)."""
    m = normaliziraj(mere)
    korak = m["deska_sirina"] + m["vrzel"]
    n_desk = max(0, int(math.floor((m["sirina"] + m["vrzel"]) / korak)))
    n_polj = max(1, int(math.ceil(m["sirina"] / m["razmak_stebrov"])))
    n_stebrov = n_polj + 1
    dolzina_polja = m["sirina"] / n_polj
    # letve: dolžina polja, n letvi na polje
    dolzina_letve_skupaj = n_polj * m["letve"] * dolzina_polja
    # vijaki: deska se pritrdi na vsako letev z 2 vijakoma (rob deske)
    vijaki = n_desk * m["letve"] * 2
    # sidra: 2 na steber
    sidra = n_stebrov * 2
    return {
        "tip": IME,
        "n_desk": n_desk,
        "n_stebrov": n_stebrov,
        "n_polj": n_polj,
        "dolzina_polja": round(dolzina_polja, 1),
        "n_letvi": n_polj * m["letve"],
        "dolzina_letve_skupaj_mm": round(dolzina_letve_skupaj, 1),
        "vijaki": vijaki,
        "sidra": sidra,
        "mere": m,
    }


def preview(mere, pot_png):
    """Hitri vizualni predogled (PNG) — BREZ celotnega dokumenta.

    Namen: uporabnik PRED generiranjem vidi, kakšna bo ograja.
    """
    m = normaliziraj(mere)
    k = kolicine(m)
    fig, ax = plt.subplots(figsize=(9, 3.2))
    sir, vis = m["sirina"], m["visina"]
    ax.set_xlim(-300, sir + 300)
    ax.set_ylim(-200, vis + 250)
    ax.set_aspect("equal")
    ax.axis("off")
    # tla
    ax.plot([-200, sir + 200], [0, 0], color="#666", lw=1.2)
    # deske
    korak = m["deska_sirina"] + m["vrzel"]
    x = 0.0
    while x + m["deska_sirina"] <= sir + 1e-6:
        ax.add_patch(plt.Rectangle((x, 0), m["deska_sirina"], vis,
                                   facecolor="#b08968", edgecolor="#7f5539",
                                   lw=0.6))
        x += korak
    # stebri
    for i in range(k["n_stebrov"]):
        xc = i * k["dolzina_polja"]
        ax.add_patch(plt.Rectangle((xc - m["steber_sirina"] / 2, 0),
                                   m["steber_sirina"], vis + 80,
                                   facecolor="#555", edgecolor="#222", lw=0.8))
    # letve (za deskami — črtkano)
    for j in range(int(m["letve"])):
        z = vis * (j + 1) / (m["letve"] + 1)
        ax.plot([0, sir], [z, z], color="#333", lw=2.2, ls="--", alpha=0.55)
    ax.set_title(f"{IME.replace('_', ' ').title()} — predogled • "
                 f"{k['n_desk']} desk • {k['n_stebrov']} stebrov • "
                 f"{k['n_letvi']} letvi • {k['vijaki']} vijakov",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(pot_png, dpi=120)
    plt.close(fig)
    return pot_png, k