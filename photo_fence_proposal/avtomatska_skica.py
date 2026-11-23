# -*- coding: utf-8 -*-
"""Avtomatska tehnična skica iz fotografije (A3, v slogu referenčnih risb).

Sestavine lista (kot pri referencah):
- SPREDNJI POGLLED z verigami mer (W, H, vertikalna veriga, stebri)
- STRANSKI PRESEZ A-A (betonska plošča, lamelе, stebri, sidrna plošča)
- DETAJL B' — profil lamelе
- FOTO (rektificirano) — dokazni posnetek
- OPOMBE, KOSOVNICA, LEGENDA STATUSOV, NASLOVNI BLOK

POŠTENO: vsaka mera nosi status († izmerjeno / ‡ izračunano /
≈ ocenjeno / ?? neznano). Brez reference uporabnika so mere ≈ ocenjeno.
"""
import datetime
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages

import cv2

from model import Mera, IZMERJENO, IZRACUNANO, OCENJENO, NEZNANO
import rektifikacija

A3_W, A3_H = 420.0, 297.0
CRNA = "#111111"
SIVA = "#777777"


# ---------------------------------------------------------------- risalni pomočniki
def _crta(ax, x0, y0, x1, y1, lw=0.7, stil="-", barva=CRNA):
    ax.plot([x0, x1], [y0, y1], color=barva, lw=lw, linestyle=stil,
            solid_capstyle="butt")


def _kvadrat(ax, x, y, w, h, polni=None, lw=0.9, barva=CRNA):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=polni or "none",
                           edgecolor=barva, lw=lw))


def _srafura(ax, x, y, w, h, korak=2.2):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#e9e9e9",
                           edgecolor=CRNA, lw=0.6))
    n = int((w + h) / korak) + 2
    for i in range(n):
        x0 = x + i * korak
        ax.plot([max(x, x0), min(x + w, x0 + h)],
                [y + max(0, x - x0), y + min(h, x + w - x0)],
                color=SIVA, lw=0.35, clip_path=None)


def _dim_h(ax, x0, x1, y, oznaka_tekst):
    _crta(ax, x0, y, x1, y, lw=0.5)
    for x in (x0, x1):
        ax.plot([x, x], [y - 1.2, y + 1.2], color=CRNA, lw=0.5)
    ax.text((x0 + x1) / 2, y + 1.8, oznaka_tekst, ha="center", va="bottom",
            fontsize=6.5)


def _dim_v(ax, y0, y1, x, oznaka_tekst):
    _crta(ax, x, y0, x, y1, lw=0.5)
    for y in (y0, y1):
        ax.plot([x - 1.2, x + 1.2], [y, y], color=CRNA, lw=0.5)
    ax.text(x + 1.8, (y0 + y1) / 2, oznaka_tekst, rotation=90, ha="left",
            va="center", fontsize=6.5)


def _oznaka(ax, x, y, tekst, vel=8, teza="bold", barva=CRNA):
    ax.text(x, y, tekst, fontsize=vel, fontweight=teza, color=barva,
            ha="left", va="center")


def _tabela(ax, x, y_top, sirine, vrste, vis=4.6, fs=6.2):
    y = y_top
    for i, vrstica in enumerate(vrste):
        x_t = x
        for j, celica in enumerate(vrstica):
            _kvadrat(ax, x_t, y - vis, sirine[j], vis,
                     polni="#f2f2f2" if i == 0 else None, lw=0.5)
            ax.text(x_t + 1.2, y - vis / 2, str(celica), fontsize=fs,
                    va="center", ha="left",
                    fontweight="bold" if i == 0 else "normal")
            x_t += sirine[j]
        y -= vis
    return y


def _oznaka_mere(m):
    """Oznaka Mere z statusom (†/‡/≈/??) — nikoli gola številka."""
    return m.oznaka if m is not None else "?? mm (neznano — potrdi)"


# ---------------------------------------------------------------- sestava lista
def _zavij(besedilo, sirina):
    """Enostavno lomljenje vrstic za OPOMBE."""
    besede = besedilo.split()
    vrstice, trenutna = [], ""
    for b in besede:
        if len(trenutna) + len(b) + 1 > sirina:
            vrstice.append(trenutna)
            trenutna = b
        else:
            trenutna = (trenutna + " " + b).strip()
    if trenutna:
        vrstice.append(trenutna)
    return vrstice or [""]


def narisi_skico(pod, pot_pdf):
    """Nariše celoten A3 list avtomatske skice.

    ``pod``: slovar z ključi: mere (dict Mera), ritem (dict), slika_rect
    (ndarray ali None), lokacija, tip, material, opozorila (list),
    vir_slike (str), merilo (str npr. "1:20").
    """
    mere = pod["mere"]
    ritem = pod.get("ritem") or {}
    with PdfPages(pot_pdf) as pdf:
        fig = plt.figure(figsize=(A3_W / 25.4, A3_H / 25.4))
        ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
        ax.set_xlim(0, A3_W)
        ax.set_ylim(0, A3_H)
        ax.axis("off")
        _kvadrat(ax, 8, 8, A3_W - 16, A3_H - 16, lw=1.2)

        # ==================== NASLOV ====================
        ax.text(A3_W / 2, A3_H - 15, f"TEHNICNA RISBA — {pod.get('tip') or 'OGRAJA'}",
                ha="center", va="center", fontsize=12, fontweight="bold")
        ax.text(A3_W / 2, A3_H - 22,
                "AVTOMATSKA SKICA IZ FOTOGRAFIJE — mere s statusi; "
                "pred uporabo potrdi vse mere na objektu!",
                ha="center", va="center", fontsize=7, color="#8a1c1c")

        # ============== SPREDNJI POGLLED (x 16..256, y 62..232) ==============
        _oznaka(ax, 14, 243, f"SPREDNJI POGLLED — {pod.get('merilo', '')}")
        W = mere.get("dolzina_ograje")
        H = mere.get("visina_ograje")
        w_mm = W.vrednost_mm or 6000.0
        h_mm = H.vrednost_mm or 1000.0
        s_mer = min(230.0 / max(w_mm, 1.0), 150.0 / max(h_mm, 1.0))
        x0, y0 = 30.0, 66.0
        w_r, h_r = w_mm * s_mer, h_mm * s_mer

        # betonska plošča / parapet
        _srafura(ax, x0 - 4, y0 - 12, w_r + 8, 12)
        _crta(ax, x0 - 8, y0, x0 + w_r + 8, y0, lw=1.0)
        # lamele (vodoravne) — enakomerno čez višino
        n_lam = int(ritem.get("n_lamel") or 0) or max(int(h_mm // 87), 2)
        n_lam = max(2, min(n_lam, 40))
        deb_mm = (mere.get("visina_lamele").vrednost_mm
                  if mere.get("visina_lamele") and mere.get("visina_lamele").vrednost_mm
                  else 67.0)
        korak = h_mm / n_lam
        vis_lam = min(deb_mm, korak * 0.85)
        for i in range(n_lam):
            z_mm = i * korak
            _kvadrat(ax, x0, y0 + z_mm * s_mer, w_r, vis_lam * s_mer,
                     polni="#565656", lw=0.3, barva="#333333")
        # stebri
        n_st = 0
        m_st = mere.get("stevilo_stebrov")
        if m_st and m_st.vrednost_mm:
            n_st = int(m_st.vrednost_mm)
        n_st = max(2, min(n_st, 24)) if n_st else max(2, int(w_mm // 1500) + 1)
        for i in range(n_st):
            x_p = x0 + (w_r * i / (n_st - 1) if n_st > 1 else 0)
            _kvadrat(ax, x_p - 18 * s_mer, y0, 36 * s_mer, h_r,
                     polni="#222222", lw=0.35, barva="#222222")
        # ročaj / zgornji profil
        _kvadrat(ax, x0 - 6 * s_mer, y0 + h_r, w_r + 12 * s_mer,
                 30 * s_mer, polni="#222222", lw=0.35)

        # verige mer: W zgoraj, H levo, vertikalna desno
        _dim_h(ax, x0, x0 + w_r, y0 + h_r + 30 * s_mer + 12,
               f"W = {_oznaka_mere(W)}")
        _dim_v(ax, y0, y0 + h_r, x0 - 12, f"H = {_oznaka_mere(H)}")
        xk = x0 + w_r + 8
        _dim_v(ax, y0, y0 + h_r / 2, xk,
               f"{n_lam // 2}x({vis_lam:.0f}+{korak - vis_lam:.0f})")
        _dim_v(ax, y0 + h_r / 2, y0 + h_r, xk,
               f"{n_lam - n_lam // 2}x({vis_lam:.0f}+{korak - vis_lam:.0f})")
        ax.text(x0 + w_r / 2, y0 - 18,
                f"NOSILNI STEBRICEK — {n_st} kos "
                f"({_oznaka_mere(mere.get('stevilo_stebrov'))})",
                ha="center", fontsize=6.2)

        # ============== PRESEZ A-A (x 282..408, y 150..252) ==============
        _oznaka(ax, 284, 252, f"PRESEZ A-A — {pod.get('merilo', '')}")
        xs, ys = 300.0, 158.0
        _srafura(ax, xs - 2, ys, 44, 13)
        _crta(ax, xs - 10, ys + 13, xs + 52, ys + 13, lw=0.8)
        vis_s = 84.0
        n_prikaz = min(n_lam, 14)
        for i in range(n_prikaz):
            z = 17 + i * (vis_s - 17) / max(n_prikaz, 1)
            _kvadrat(ax, xs + 14, ys + z, 12, 4.2, polni="#565656", lw=0.3)
        _kvadrat(ax, xs + 28, ys + 15, 5, vis_s, polni="#222222", lw=0.35)
        _kvadrat(ax, xs + 22, ys + 12, 17, 4.5, polni="#888888", lw=0.4)
        ax.text(xs - 10, ys + vis_s + 24,
                "LAMELA 67x20 [pribl.]  •  ALU STEBER 60x40 [pribl.]\n"
                "SIDRNA PLOSCA 120x80 [pribl.]  •  BETONSKA PLOSCA",
                fontsize=6, va="top")
        _dim_v(ax, ys, ys + vis_s, xs + 40,
               f"{h_mm:.0f} mm " + ("[pribl.]" if not (H and H.je_potrjena) else "[*]"))

        # ============== DETAJL 'B' (x 282..408, y 105..142) ==============
        _oznaka(ax, 284, 140, "DETAJL 'B' — PROFIL LAMELE")
        _kvadrat(ax, 300, 112, 34, 10, polni="#565656", lw=0.8)
        _dim_h(ax, 300, 334, 108, f"{deb_mm:.0f} mm [pribl.]")
        _dim_v(ax, 112, 122, 338, "20 mm [pribl.]")

        # ============== FOTO (x 282..408, y 45..100) ==============
        slika = pod.get("slika_rect")
        if slika is not None:
            _oznaka(ax, 284, 98, "FOTO — REKTIFICIRANO (dokaz)")
            h_img, w_img = slika.shape[:2]
            ax.imshow(cv2.cvtColor(slika, cv2.COLOR_BGR2RGB),
                      extent=(284, 284 + 86, 48, 48 + 86 * h_img / max(w_img, 1)),
                      aspect="auto", alpha=0.95)
            _kvadrat(ax, 284, 48, 86, 86 * h_img / max(w_img, 1), lw=0.6)

        # ============== KOSOVNICA (x 14..146) ==============
        _oznaka(ax, 14, 44.5, "KOSOVNICA (predvideni material)", vel=7)
        _tabela(ax, 14, 42, [30, 28, 26, 14, 20],
                [["NAZIV", "MATERIAL", "DIM.", "KOL.", "STATUS"],
                 *pod.get("kosovnica_vrstice", [])], vis=4.4, fs=5.9)

        # ============== OPOMBE (x 152..258) ==============
        _oznaka(ax, 152, 42, "OPOMBE:", vel=7)
        y = 37.0
        for opomba in pod.get("opombe", []):
            for delcek in _zavij(opomba, 52):
                ax.text(152, y, delcek, fontsize=5.4, va="top")
                y -= 3.6

        # ============== LEGENDA + NASLOVNI BLOK ==============
        _oznaka(ax, 262, 44.5, "NASLOVNI BLOK", vel=7)
        ax.text(14, 12, "LEGENDA:  * izmerjeno (kalibrirano)   "
                        "‡ izracunano   ~ ocenjeno (NI potrjeno)   "
                        "?? neznano — potrdi",
                fontsize=5.8, va="bottom")
        _kvadrat(ax, 262, 10, A3_W - 274, 33, lw=1.0)
        _crta(ax, 262, 21, A3_W - 12, 21, lw=0.5)
        _crta(ax, 262, 32, A3_W - 12, 32, lw=0.5)
        _crta(ax, 338, 10, 338, 43, lw=0.5)
        ax.text(264, 37.5, f"NASLOV: {pod.get('ime', 'AVTOMATSKA SKICA')}",
                fontsize=6, va="center")
        ax.text(264, 26.5, f"LOKACIJA: {pod.get('lokacija', '—')}    "
                           f"TIP: {pod.get('tip', '—')}",
                fontsize=5.8, va="center")
        ax.text(264, 15.5, f"MERILO: {pod.get('merilo', '—')}    "
                           f"ENOTA: mm    FORMAT: A3",
                fontsize=5.8, va="center")
        ax.text(340, 26.5, f"MATERIAL: {pod.get('material', '—')}",
                fontsize=5.8, va="center")
        ax.text(340, 15.5, f"DATUM: {datetime.date.today().strftime('%d.%m.%Y')}"
                           "    IZVOR: fotografija (avtomatsko)",
                fontsize=5.8, va="center")

        pdf.savefig(fig)
        plt.close(fig)
    return pot_pdf


# ---------------------------------------------------------------- sestava podatkov
def sestavi_podatke(mere, ritem, slika_rect, lokacija="—",
                    tip="WPC LAMELNA OGRAJA (HORIZONTALNA)",
                    material="WPC lamela + ALU podkonstrukcija",
                    ime="AVTOMATSKA SKICA — OGRAJA IZ FOTOGRAFIJE",
                    opozorila=None):
    """Sestavi slovar za narisi_skico — vključno s KOSOVNICO in OPOMBAMI."""
    w = mere.get("dolzina_ograje")
    h = mere.get("visina_ograje")
    n_lam = int(ritem.get("n_lamel") or 0)
    n_st = 0
    if w and w.vrednost_mm:
        n_st = max(2, int(w.vrednost_mm // 1500) + 1)
    vijaki = n_lam * n_st * 2 if n_lam and n_st else None

    def _kos(naziv, material, dim, kolicina):
        st = kolicina[1] if isinstance(kolicina, tuple) else "ocenjeno"
        kol = f"{kolicina[0]:.0f} kos" if isinstance(kolicina, tuple) else "—"
        return [naziv, material, dim, kol, st]

    kosovnica = [
        _kos("WPC lamela", "WPC", f"{(mere.get('visina_lamele').vrednost_mm if mere.get('visina_lamele') and mere.get('visina_lamele').vrednost_mm else 67):.0f}×20",
             (n_lam * max(1, int((w.vrednost_mm or 0) // 6000) + 1) if w and w.vrednost_mm and n_lam else 0,
              "ocenjeno" if not (h and h.je_potrjena) else "izracunano")),
        _kos("ALU steber", "Aluminij", "60×40", (n_st, "ocenjeno" if n_st else "neznano")),
        _kos("Sidrna plošča", "Jeklo", "120×80", (n_st, "ocenjeno" if n_st else "neznano")),
        _kos("Vijaki M8×70", "Inox", "M8×70", (vijaki or 0, "izracunano" if vijaki else "neznano")),
    ]

    opombe = [
        "Mere iz ene fotografije so lahko NETOČNE (perspektiva, zaznava) — "
        "pred izdelavo OBVEZNO preveri vse mere na objektu.",
        "Risba NI statični izračun — nosilnost, sidranje in veterno breme "
        "preveri usposobljen strokovnjak.",
        "Vse mere v mm; statusi mer so označeni z legendami (†/‡/≈/??).",
    ]
    for o in (opozorila or []):
        opombe.append("OPOZORILO: " + o)

    # merilo lista: najlepše od 1:5 .. 1:100 glede na širino
    w_mm = (w.vrednost_mm if w else None) or 6000.0
    merilo_x = max(1, int(math.ceil(w_mm / 240.0 / 5.0)) * 5)
    return {
        "mere": mere, "ritem": ritem, "slika_rect": slika_rect,
        "lokacija": lokacija, "tip": tip, "material": material,
        "ime": ime, "merilo": f"1:{merilo_x}",
        "kosovnica_vrstice": kosovnica, "opombe": opombe,
    }

# ---------------------------------------------------------------- pogon
def generiraj(slika_pot, pot_pdf, lokacija="—", referenca=None, vogali=None):
    """Celoten tok: fotografija → avtomatska A3 skica (PDF).

    referenca: (kaj, vrednost_mm) ali None. Brez reference so vse mere
    OCENJENO (standardna lamela) — nikoli izmišljene kot izmerjene.

    vogali: [(x, y) × 4] v slikovnih pikah (TL, TR, BR, BL) — uporabnik
    klikne vogale ograje (P1). S klikanimi vogali + referenco so mere
    IZRAČUNANO iz trdne geometrije (ne več le ocena).
    """
    import detekcija
    import zaznavanje

    slika = cv2.imread(slika_pot)
    if slika is None:
        raise ValueError(f"Slike ni mogoče odpreti: {slika_pot}")
    zaznava = zaznavanje.zaznaj(slika_pot)
    obmocje = (list(vogali) if vogali else zaznava.obmocje_ograje_px)
    rect, _H, meta = rektifikacija.rektificiraj(slika, obmocje)
    ritem = detekcija.lamelni_ritem_kontrolirano(rect)
    if vogali:
        # klikani vogali = ograja sama → merimo celotno rektificirano polje
        y0, y1, x0, x1 = 0, rect.shape[0], 0, rect.shape[1]
        vis_px = float(rect.shape[0])
        sir_px = float(rect.shape[1])
    else:
        # pas OGRAJE (ne cele slike!) — skala in mere merijo pas lamel
        pas = rektifikacija.pas_ograje(rect, ritem.get("pitch_px"))
        if pas:
            y0, y1, x0, x1 = pas
            vis_px = float(y1 - y0)
            sir_px = float(x1 - x0)
        else:
            y0, y1, x0, x1 = 0, rect.shape[0], 0, rect.shape[1]
            vis_px = float(rect.shape[0])
            sir_px = float(rect.shape[1])
    rect_pas = rect[y0:y1, x0:x1]
    if vogali and referenca:
        kaj_ref, vrednost_ref = referenca
        if kaj_ref == "visina_ograje":
            mm_na_px = float(vrednost_ref) / max(vis_px, 1e-9)
        elif kaj_ref == "dolzina_ograje":
            mm_na_px = float(vrednost_ref) / max(sir_px, 1e-9)
        else:
            raise ValueError(f"Neznana referenca {kaj_ref!r} — dovoljeni: "
                             "'visina_ograje', 'dolzina_ograje'")
        meritev_skale = Mera(float(vrednost_ref), IZMERJENO,
                             f"{kaj_ref} (referenca uporabnika + klikani vogali)")
    else:
        mm_na_px, meritev_skale = rektifikacija.skala_mm(
            ritem, referenca, visina_slike_px=vis_px)

    mere = {}
    opozorila = list(zaznava.opozorila) + list(meta.get("opozorila") or [])
    negotova = any(("negotov" in o.lower()) or ("neenakomern" in o.lower())
                   for o in zaznava.opozorila)
    # Kontrola dveh estimatorjev (profil/robovi): ob NESOGLASJU se vrednosti
    # NE izberejo tiho — ritemske mere se doljajo na OCENJENO in uporabnik
    # dobi eksplicitno opozorilo ("brez ugibanja").
    nesoglasje = bool(ritem.get("nesoglasje"))
    if nesoglasje:
        opozorila.append(
            "Estimatorja ritma (profil/robovi) se ne strinjata: "
            + (ritem.get("kontrola") or {}).get("razlog", "neznan razlog")
            + " — ritemske mere so OCENJENO, potrdi na objektu.")

    def _st(ref):
        if referenca is not None and ref:
            return IZMERJENO
        if vogali and referenca is not None:
            return IZRACUNANO   # trdna geometrija klikanih vogalov
        if referenca is not None and not negotova:
            return IZRACUNANO
        return OCENJENO

    n_lam = int(ritem.get("n_lamel") or 0)
    # okno ritma je vzorec — skupno število lamel čez celotno ograjo:
    if ritem.get("pitch_px") and n_lam:
        n_lam_skupaj = max(1, int(round(vis_px / ritem["pitch_px"])))
    else:
        n_lam_skupaj = n_lam
    ritem = dict(ritem)
    ritem["n_lamel"] = n_lam_skupaj   # za risbo/kosovnico: skupaj
    MEJE = {"visina_ograje": (200.0, 3000.0),
            "dolzina_ograje": (300.0, 50000.0),
            "visina_lamele": (15.0, 250.0), "vrzel": (1.0, 120.0)}

    def _verodostojno(ime, v):
        lo, hi = MEJE[ime]
        return v is not None and lo <= v <= hi

    def _mera(ime, v, status, opis):
        if not _verodostojno(ime, v):
            opozorila.append(
                f"Izračun {ime} = {v:.0f} mm ni fizično verodostojen — "
                "zavrnjen (zaznava ali skala napačna).")
            return Mera(None, NEZNANO,
                        f"izračunana vrednost {v:.0f} mm ni fizično "
                        "verodostojna — zavrnjena")
        return Mera(v, status, opis
                    + ((" — zaznava NEGOTOVA, ocena!" if negotova and not vogali
                        else "")))

    if mm_na_px and n_lam and ritem.get("pitch_px"):
        vis_mm = vis_px * mm_na_px
        mere["visina_ograje"] = _mera(
            "visina_ograje", vis_mm, _st(referenca is not None),
            "višina ograje (pas lamel × skala)")
        # dolžina = širina pasu ograje × skala
        dolz_mm = sir_px * mm_na_px
        mere["dolzina_ograje"] = _mera(
            "dolzina_ograje", dolz_mm, _st(False),
            "dolžina ograje (pas lamel × skala)")
        st_ritem = OCENJENO if nesoglasje else _st(False)
        mere["visina_lamele"] = _mera(
            "visina_lamele", ritem["debelina_px"] * mm_na_px, st_ritem,
            "višina lamelе (ritem × skala)")
        mere["vrzel"] = _mera(
            "vrzel", (ritem.get("vrzel_px") or 0.0) * mm_na_px, st_ritem,
            "fuga med lamelami (ritem × skala)")
        mere["stevilo_lamel"] = Mera(
            float(n_lam_skupaj),
            IZRACUNANO if not (negotova or nesoglasje) else OCENJENO,
            "preštete lamele na rektificiranem pogledu", enota="kos")
    else:
        mere["visina_ograje"] = Mera(None, NEZNANO,
                                     "ritem lamel ni zaznan — potrebna referenca")
        mere["dolzina_ograje"] = Mera(None, NEZNANO,
                                      "ritem lamel ni zaznan — potrebna referenca")

    if referenca is None:
        opozorila.append(
            "Brez referenčne mere: vse dimenzije so ≈ OCENJENO "
            "(standardna lamela) in NISO meritev objekta!")
    pod = sestavi_podatke(mere, ritem, rect_pas, lokacija=lokacija,
                          opozorila=opozorila)
    pod["ime"] = "AVTOMATSKA SKICA — " + (
        slika_pot.split("/")[-1].split("\\")[-1].upper())
    return narisi_skico(pod, pot_pdf), pod


def _povecava(rgb, x, y, polmer=70, faktor=3):
    """Povečan izrez okoli (x, y) za LUPO — čista funkcija (testna).

    Vrne (izrez_rgb, sredisce) kjer je sredisce položaj (x, y) znotraj
    izreza (ko slika nima robov).
    """
    h, w = rgb.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, x1 = max(x - polmer, 0), min(x + polmer, w)
    y0, y1 = max(y - polmer, 0), min(y + polmer, h)
    izrez = rgb[y0:y1, x0:x1]
    if izrez.size == 0:
        izrez = rgb[max(y - 1, 0):y + 1, max(x - 1, 0):x + 1]
    return izrez, (x - x0, y - y0)


class _KlikVogalov:
    """Logika klika vogalov (Plan B) — ločena od matplotlib dogodkov (testna).

    Metode klik()/tipka()/premik() kličejo dogodki matplotlib ALI testi
    neposredno. Lupa je vstavek (inset) s povečanim izrezom okoli kurzorja.
    """

    OZNAKE = ("TL", "TR", "BR", "BL")

    def __init__(self, rgb, ax, lupa_ax, fig):
        self.rgb = rgb
        self.ax = ax
        self.lupa_ax = lupa_ax
        self.fig = fig
        self.tocke = []

    def narisi(self):
        ax = self.ax
        ax.clear()
        ax.imshow(self.rgb)
        ax.set_title("Klikni 4 VOGALE (TL, TR, BR, BL) • u = razveljavi • "
                     "Enter = konec", fontsize=9)
        if self.tocke:
            xs = [t[0] for t in self.tocke]
            ys = [t[1] for t in self.tocke]
            ax.plot(xs, ys, "r+-", ms=10, lw=1)
            for i, (x, y) in enumerate(self.tocke):
                ax.annotate(self.OZNAKE[i], (x, y), color="red", fontsize=9,
                            xytext=(4, 4), textcoords="offset points")
        self.fig.canvas.draw_idle()

    def lupa(self, x, y):
        izrez, (cx, cy) = _povecava(self.rgb, x, y)
        self.lupa_ax.clear()
        self.lupa_ax.imshow(izrez)
        self.lupa_ax.plot([cx], [cy], "r+", ms=6)
        self.lupa_ax.set_title(f"Lupa  x={x:.0f}  y={y:.0f}", fontsize=7)
        self.lupa_ax.axis("off")
        self.fig.canvas.draw_idle()

    def premik(self, x, y):
        if x is not None and y is not None:
            self.lupa(x, y)

    def klik(self, x, y, button=1):
        if button == 1:
            if len(self.tocke) < 4 and x is not None and y is not None:
                self.tocke.append((float(x), float(y)))
                self.narisi()
        elif button == 3 and self.tocke:
            self.tocke.pop()
            self.narisi()

    def tipka(self, key):
        if key in ("u", "U", "backspace"):
            if self.tocke:
                self.tocke.pop()
                self.narisi()
        elif key == "enter" and len(self.tocke) == 4:
            plt.close(self.fig)


def izberi_vogale(slika_pot, vnosi=None):
    """Interaktivni klik 4 vogalov ograje (TL, TR, BR, BL) z Lupo (Plan B).

    - premik miške: lupa (povečan izrez s križcem) sledi kurzorju,
    - levi klik: postavi vogal (1–4),
    - tipka `u` / desni klik: razveljavi zadnji klik,
    - tipka `Enter`: zaključi (ko so 4 točke).

    vnosi: [(x, y) × 4] — programski vnos (brez okna) za teste/avtomatizacijo.
    Deluje le v GUI-okolju; za polno avtomatsko pot uporabi --vogali.
    """
    if vnosi is not None:
        if len(vnosi) != 4:
            raise ValueError("Potrebni so točno 4 točke (TL, TR, BR, BL).")
        return [(float(x), float(y)) for x, y in vnosi]

    slika = cv2.imread(slika_pot)
    if slika is None:
        raise ValueError(f"Slike ni mogoče odpreti: {slika_pot}")
    rgb = cv2.cvtColor(slika, cv2.COLOR_BGR2RGB)
    fig, ax = plt.subplots()
    lupa_ax = fig.add_axes((0.72, 0.72, 0.26, 0.26))
    lupa_ax.axis("off")
    inter = _KlikVogalov(rgb, ax, lupa_ax, fig)

    def na_premik(ev):
        if ev.inaxes is ax:
            inter.premik(ev.xdata, ev.ydata)

    def na_klik(ev):
        inter.klik(ev.xdata, ev.ydata, getattr(ev, "button", 1))

    def na_tipko(ev):
        inter.tipka(ev.key)

    fig.canvas.mpl_connect("motion_notify_event", na_premik)
    fig.canvas.mpl_connect("button_press_event", na_klik)
    fig.canvas.mpl_connect("key_press_event", na_tipko)
    inter.narisi()
    inter.lupa(rgb.shape[1] / 2, rgb.shape[0] / 2)
    plt.show()
    if len(inter.tocke) != 4:
        raise ValueError("Potrebni so točno 4 kliki (TL, TR, BR, BL).")
    return [(float(x), float(y)) for x, y in inter.tocke]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Avtomatska A3 skica iz fotografije")
    ap.add_argument("fotografija")
    ap.add_argument("--izhod", required=True, help="izhodni PDF")
    ap.add_argument("--lokacija", default="—")
    ap.add_argument("--referenca", default=None,
                    help="npr. visina_ograje=1050 ali dolzina_ograje=4200 (mm)")
    ap.add_argument("--vogali", default=None,
                    help="4 vogali ograje v pikah: 'x1,y1 x2,y2 x3,y3 x4,y4' "
                         "(TL, TR, BR, BL)")
    ap.add_argument("--interaktivno", action="store_true",
                    help="klikni vogale v oknu slike")
    args = ap.parse_args()
    ref = None
    if args.referenca:
        kaj, v = args.referenca.split("=")
        ref = (kaj.strip(), float(v))
    vogali = None
    if args.interaktivno:
        vogali = izberi_vogale(args.fotografija)
    elif args.vogali:
        vogali = [tuple(float(t) for t in par.split(","))
                  for par in args.vogali.split()]
        if len(vogali) != 4:
            raise ValueError("--vogali zahteva točno 4 točke.")
    pot, pod = generiraj(args.fotografija, args.izhod,
                         lokacija=args.lokacija, referenca=ref, vogali=vogali)
    print("Skica:", pot)
    for ime, m in sorted(pod["mere"].items()):
        print(f"  {ime}: {m.oznaka}")
    for o in pod["opombe"]:
        if o.startswith("OPOZORILO"):
            print(" !", o)


if __name__ == "__main__":
    main()
