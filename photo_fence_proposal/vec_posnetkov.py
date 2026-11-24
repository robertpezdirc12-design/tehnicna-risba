# -*- coding: utf-8 -*-
"""Soglasje več posnetkov iste ograje (brez novih odvisnosti, brez AI).

Ena fotografija da meritev z napako 0,03–3 % (odvisno od markerja in kota)
— in te napake s posnetka same NI mogoče videti. Če isto ograjo izmerimo
z dvema ali več posnetki (marker na vsakem, koti na vsakem), se napaka
pokaže kot NESOGLASJE. Zato ta modul ne vrne »povprečja« kar tako:

- meritve se primerjajo z mediano; razpršenost > 2 % pomeni, da vsaj en
  posnetek laže (napačno označeni koti, premajhen marker, ukrivljena
  ravnina) — takrat rezultat NI razglašen za izračunan;
- soglasje je vedno opremljeno z opozorilom, koliko posnetkov je bilo
  uporabljenih in kako velika je razpršenost.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

# Napaka ENEGA posnetka je izmerjena 0,03–3 % (marker 150–300 mm, kot).
# Prag mora zato ujeti GROBO napako (napačna stranica markerja 5–13 %,
# napačni koti), ne pa meriti lastnega šuma: 2 %.
PRAG_SOGLASJA = 0.02


@dataclass(frozen=True)
class Meritev:
    """Rezultat enega posnetka (mm); None pomeni »na tem posnetku ni bilo")."""

    pot: str
    dolzina_mm: float | None
    visina_mm: float | None
    stran_markerja_px: float = 0.0


@dataclass(frozen=True)
class Soglasje:
    """Skupna mera iz več posnetkov + ali ji smemo verjeti."""

    meritve: tuple[Meritev, ...]
    dolzina_mm: float | None
    visina_mm: float | None
    razprsenost: float
    dovolj: bool
    opozorila: tuple[str, ...] = ()


def izmeri(pot: str, vogali, stranica_mm: float = 150.0) -> Meritev:
    """Izmeri en posnetek: marker + 4 koti → dolžina/višina v mm."""
    import cv2

    import marker

    slika = cv2.imread(pot)
    if slika is None:
        raise ValueError(f"Slike ni mogoče odpreti: {pot}")
    if len(vogali) != 4:
        raise ValueError("za meritev so potrebni natanko 4 koti")
    visina_sl, sirina_sl = slika.shape[:2]
    for x, y in vogali:
        if not (0 <= float(x) < sirina_sl and 0 <= float(y) < visina_sl):
            raise ValueError(
                f"kot ({float(x):.0f}, {float(y):.0f}) je zunaj slike "
                f"{sirina_sl}×{visina_sl} px ({pot})")
    koti = marker.zaznaj_marker(slika)
    if koti is None:
        return Meritev(pot, None, None)
    stran = float(marker.stranica_px(koti))
    mere = marker.izmeri_kvadrilateral(vogali, koti, stranica_mm)
    if mere is None:
        return Meritev(pot, None, None, stran)
    return Meritev(pot, float(mere[0]), float(mere[1]), stran)


def _razprsenost(vrednosti: list[float]) -> float:
    """Največje relativno odstopanje od mediane (0 = popolno ujemanje)."""
    med = statistics.median(vrednosti)
    if not med:
        return 1.0
    return max(abs(v - med) / abs(med) for v in vrednosti)


def soglasje(meritve, prag: float = PRAG_SOGLASJA) -> Soglasje:
    """Mediana meritev + oznaka, ali se posnetki dovolj ujemajo."""
    meritve = tuple(meritve)
    dolzine = [m.dolzina_mm for m in meritve if m.dolzina_mm]
    visine = [m.visina_mm for m in meritve if m.visina_mm]
    brez = [m.pot for m in meritve if not (m.dolzina_mm and m.visina_mm)]
    opozorila: list[str] = []
    if brez:
        imena = ", ".join(p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
                          for p in brez)
        opozorila.append(
            f"Na {len(brez)} posnetkih markerja ni bilo mogoče prebrati "
            f"({imena}) — ti posnetki v soglasje ne štejejo.")
    if len(dolzine) < 2:
        opozorila.append(
            "Za soglasje sta potrebna vsaj DVA posnetka z zaznanim "
            "markerjem; ena meritev se ne more preveriti sama.")
        return Soglasje(meritve, None, None, 0.0, False, tuple(opozorila))
    dol = float(statistics.median(dolzine))
    vis = float(statistics.median(visine)) if visine else None
    raz = _razprsenost(dolzine)
    if visine:
        raz = max(raz, _razprsenost(visine))
    dovolj = raz <= prag
    if not dovolj:
        opozorila.append(
            "Posnetki se NE ujemajo: dolžina "
            f"{min(dolzine):.0f}–{max(dolzine):.0f} mm, višina "
            f"{min(visine):.0f}–{max(visine):.0f} mm "
            f"(razpršenost {raz * 100:.1f} % > {prag * 100:.0f} %) — "
            "meritev zato NI izračunana; preveri kote in marker na vsakem "
            "posnetku.")
        # ob nesoglasju mere NAMENOMA ne vrnemo: kdor bi jo vzel, bi
        # dobil povprečje dveh različnih resnic
        return Soglasje(meritve, None, None, raz, False, tuple(opozorila))
    return Soglasje(meritve, dol, vis, raz, True, tuple(opozorila))


def razcleni_dodatno(niz: str) -> tuple[str, list[tuple[float, float]]]:
    """`pot|x,y;x,y;x,y;x,y` (ali `pot:...`) → (pot, 4 koti)."""
    import vnos

    besedilo = str(niz).strip()
    if not besedilo:
        raise ValueError("prazen vnos dodatnega posnetka")
    locilo = "|" if "|" in besedilo else ":"
    if locilo not in besedilo:
        raise ValueError(
            "pričakujem 'pot|x,y;x,y;x,y;x,y' (ali 'pot:...')")
    pot, koti = besedilo.rsplit(locilo, 1)
    pot = pot.strip().strip('"')
    if not pot:
        raise ValueError("manjka pot do dodatne fotografije")
    return pot, vnos.razcleni_kote(koti)