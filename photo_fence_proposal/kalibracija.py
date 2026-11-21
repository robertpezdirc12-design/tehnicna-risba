"""photo_fence_proposal — kalibracija in izpeljava mer s statusi.

Ena znana referenčna mera uporabnika (npr. "razmak stebrov je 2000 mm")
pretvori slike v milimetre. Vse ostalo je izpeljano (IZRACUNANO) ali
ocenjeno (OCENJENO) ali NEZNANO — nikoli tiho izmišljeno.

OMEJITEV (izpisano v izhodu): single-view kalibracija predpostavlja čeln
pogled; pod kotom je napaka lahko večja — zato je napaka navedena kot
ocena in dokument ostane informativen, dokler uporabnik ne potrdi mer.
"""
from __future__ import annotations

import numpy as np

from model import (Kalibracija, Mera, Zaznava, Rezultat, ParametriNove,
                   NEZNANO, OCENJENO, IZMERJENO, IZRACUNANO)


def razdalje_stebrov_px(zaznava: Zaznava) -> list:
    """Razmaki med sosednjimi zaznanimi stebri v slikovnih pikah."""
    x_stebri = sorted(t[0] for e in zaznava.elementi if e.vrsta == "steber"
                      for t in e.tocke_px[:1])
    return [x_stebri[i + 1] - x_stebri[i] for i in range(len(x_stebri) - 1)]


def visina_ograje_px(zaznava: Zaznava) -> float | None:
    """Višina območja ograje v pikah (če je območje zaznano)."""
    if not zaznava.obmocje_ograje_px:
        return None
    ys = [t[1] for t in zaznava.obmocje_ograje_px]
    return max(ys) - min(ys)


def dolzina_ograje_px(zaznava: Zaznava) -> float | None:
    if not zaznava.obmocje_ograje_px:
        return None
    xs = [t[0] for t in zaznava.obmocje_ograje_px]
    return max(xs) - min(xs)


def kalibriraj_referenca(zaznava: Zaznava, kaj: str, vrednost_mm: float
                         ) -> Kalibracija:
    """Uporabnikova referenčna mera → kalibracija.

    kaj: "razmak_stebrov" (povprečje zaznanih razmakov) ali "visina_ograje".
    """
    if vrednost_mm <= 0:
        raise ValueError("Referenčna mora biti pozitivna")
    if kaj == "razmak_stebrov":
        razmaki = razdalje_stebrov_px(zaznava)
        if not razmaki:
            raise ValueError("Ni zaznanih stebrov — kalibracije z razmakom ni "
                             "mogoče izvesti; uporabite 'visina_ograje'")
        dolzina_px = float(np.mean(razmaki))
    elif kaj == "visina_ograje":
        v = visina_ograje_px(zaznava)
        if not v:
            raise ValueError("Višine ograje ni mogoče zaznati")
        dolzina_px = float(v)
    else:
        raise ValueError(f"Neznana referenca {kaj!r} — dovoljeni: "
                         "'razmak_stebrov', 'visina_ograje'")
    return Kalibracija(dolzina_px=dolzina_px, dolzina_mm=vrednost_mm,
                       opis=f"{kaj} = {vrednost_mm:.0f} mm (potrdil uporabnik)")


def izpelji_mere(zaznava: Zaznava, parametri: ParametriNove,
                 kalibracija: Kalibracija | None) -> dict:
    """Iz zaznave (+ kalibracije) sestavi mere s statusi."""
    mere: dict[str, Mera] = {}

    # Dolžina ograje
    dolz_px = dolzina_ograje_px(zaznava)
    if dolz_px and kalibracija:
        mere["dolzina_ograje"] = kalibracija.v_mere(
            dolz_px, "širina zaznanega območja ograje", status=IZMERJENO)
    elif dolz_px:
        mere["dolzina_ograje"] = Mera(
            None, NEZNANO, "zaznana širina v pikah, brez kalibracije",
            vir=f"{dolz_px:.0f} px")
    else:
        mere["dolzina_ograje"] = Mera(None, NEZNANO, "območje ograje ni zaznano")

    # Višina ograje
    vis_px = visina_ograje_px(zaznava)
    if vis_px and kalibracija:
        mere["visina_ograje"] = kalibracija.v_mere(
            vis_px, "višina zaznanega območja ograje", status=IZMERJENO)
    elif vis_px:
        mere["visina_ograje"] = Mera(
            None, NEZNANO, "zaznana višina v pikah, brez kalibracije",
            vir=f"{vis_px:.0f} px")
    else:
        mere["visina_ograje"] = Mera(None, NEZNANO, "višina ograje ni zaznana")

    # Število polj / stebrov (štetje je zanesljivo tudi brez kalibracije)
    st_stebrov = len({round(t[0], 1) for e in zaznava.elementi
                      if e.vrsta == "steber" for t in e.tocke_px[:1]})
    if st_stebrov >= 2:
        mere["stevilo_stebrov"] = Mera(float(st_stebrov), IZMERJENO,
                                       "prešteti zaznani stebri",
                                       vir="zaznavanje", enota="kos")
        mere["stevilo_polj"] = Mera(float(st_stebrov - 1), IZRACUNANO,
                                    "polja med stebri", vir="štetje", enota="kos")
    else:
        mere["stevilo_stebrov"] = Mera(None, NEZNANO,
                                       "stebri niso zanesljivo zaznani")

    # Razmak stebrov
    razmaki = razdalje_stebrov_px(zaznava)
    if razmaki and kalibracija:
        mere["razmak_stebrov"] = kalibracija.v_mere(
            float(np.mean(razmaki)), "povprečni razmak stebrov",
            status=IZRACUNANO)
    elif razmaki:
        mere["razmak_stebrov"] = Mera(
            None, NEZNANO, "razmak v pikah, brez kalibracije",
            vir=f"{np.mean(razmaki):.0f} px")

    # Parametri nove ograje — OCENJENO, dokler uporabnik ne potrdi
    mere["sirina_lamele"] = Mera(parametri.sirina_lamele_mm, OCENJENO,
                                 "standardna širina lamele (ni izmerjena)",
                                 vir="parametri")
    mere["razmak_lamel"] = Mera(parametri.razmak_mm, OCENJENO,
                                "razmak med lamelami (izbira uporabnika)",
                                vir="parametri")
    return mere


def napaka_na_testni_sliki(mere: dict, resni: dict) -> dict:
    """Za testne slike z ZNANIMI merami: izračunaj napako kalibriranih mer.

    Uporabljeno samo v testih (Faza 4) — resni vrednosti prideta iz
    generatorja testnih slik, ne iz fotografije.
    """
    napake = {}
    for ime, resnicna in resni.items():
        m = mere.get(ime)
        if m and m.vrednost_mm is not None:
            napake[ime] = abs(m.vrednost_mm - resnicna)
    return napake