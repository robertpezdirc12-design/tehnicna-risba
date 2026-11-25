# -*- coding: utf-8 -*-
"""Periodično štetje elementov ograje na poravnani sliki (brez AI).

Ograja je ponavljajoča se struktura. Namesto štetja VSEH navpičnih robov
(ki na balkonih ujame balustre, podboje oken, cevi) ta modul poišče
OSNOVNO PERIODO profila svetlosti in iz nje prešteje elemente. Rezultat
je stabilen tudi, ko je v kadru še kaj drugega.

Preverjene pasti:
- **harmonik**: najmočnejši vrh avtokorelacije je pogosto širina
  elementa (npr. 32 px), ne razmak (71 px) — zato vzamemo NAJKRAJŠI vrh,
  ki je blizu najvišjemu (delni prag 0,6), in ga nato izostrimo;
- **neenakomerna osvetlitev**: levi del slike ima drug kontrast kot desni,
  zato je prag za vrhove LOKALEN (CLAHE + okenska normalizacija);
- **poševni pogled**: brez poravnave v čelni pogled perioda „drsi“ in
  štetje je naključno — modul se uporablja NA REKTIFICIRANI sliki.

Rezultat je vedno označen z zanesljivostjo; pod pragom vrne None, da
poklicni kodo ne prisili v izmišljeno število.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

MIN_PERIODA_PX = 12.0     # ožje je šum, ne element
DELNI_PRAG = 0.6          # kandidat mora biti blizu najvišjemu vrhu
MIN_ZANESLJIVOST = 0.12   # pod tem je perioda šum — raje None


@dataclass(frozen=True)
class Perioda:
    """Rezultat periodičnega štetja (piksli poravnane slike)."""

    stevilo: int
    perioda_px: float
    zanesljivost: float
    pricakovano: int = 0      # round(širina / perioda) — kontrola popolnosti


def profil_svetlosti(pas: np.ndarray) -> np.ndarray:
    """1-D profil temnih elementov (stebri so temnejši od ozadja)."""
    if pas.ndim == 3:
        siva = cv2.cvtColor(pas, cv2.COLOR_BGR2GRAY)
    else:
        siva = pas
    siva = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(siva)
    profil = -siva.astype(np.float32).mean(axis=0)
    if len(profil) < 8:
        return profil - profil.mean()
    k = max(5, min(51, (len(profil) // 20) * 2 + 1))
    trend = cv2.blur(profil.reshape(1, -1), (k, 1)).ravel()
    return profil - trend


def _vrhovi_avtokorelacije(ac: np.ndarray, min_px: float,
                           max_px: float) -> list[int]:
    meja = int(min(max_px, len(ac) - 1))
    return [p for p in range(max(2, int(min_px)), meja)
            if ac[p] >= ac[p - 1] and ac[p] >= ac[p + 1]]


def _izostri(ac: np.ndarray, p: int, sirina: int = 4) -> int:
    """Izberi najmočnejši vrh v oknu ±sirina px (celoštevilsko)."""
    z = max(1, p - sirina)
    k = min(len(ac) - 1, p + sirina)
    return z + int(np.argmax(ac[z:k + 1]))


def _prestej_vrhove(e: np.ndarray, perioda: float) -> int:
    """Število elementov = lokalni vrhovi profila (CLAHE + lokalni prag)."""
    n = len(e)
    okno = max(9, int(3 * perioda) | 1)
    lok = cv2.dilate(np.abs(e).reshape(1, -1),
                     np.ones((1, okno), np.uint8)).ravel() + 1e-6
    en = e / lok                       # kontrast ne glede na osvetlitev
    med = float(np.median(en))
    prag = med + 0.35 * (float(en.max()) - med)
    najmanj = max(3, int(perioda * 0.6))
    vrhovi: list[int] = []
    for i in range(1, n - 1):
        if en[i] <= prag or en[i] < en[i - 1] or en[i] < en[i + 1]:
            continue
        if vrhovi and i - vrhovi[-1] < najmanj:
            if en[i] > en[vrhovi[-1]]:
                vrhovi[-1] = i
        else:
            vrhovi.append(i)
    return len(vrhovi)


def iz_profila(profil: np.ndarray, min_px: float = MIN_PERIODA_PX,
               max_px: float | None = None,
               delni_prag: float = DELNI_PRAG) -> Perioda | None:
    """Osnovna perioda + število elementov iz 1-D profila."""
    n = len(profil)
    if n < 4 * min_px:
        return None
    e = profil - profil.mean()
    if not np.any(e):
        return None
    ac = np.correlate(e, e, mode="full")[n - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    vrhovi = _vrhovi_avtokorelacije(ac, min_px, max_px or n // 2)
    if not vrhovi:
        return None
    najvec = float(max(ac[p] for p in vrhovi))
    if najvec <= 0:
        return None
    # najkrajši vrh blizu najvišjemu = osnovna perioda (ne harmonik)
    perioda = _izostri(ac, min(p for p in vrhovi
                                    if ac[p] >= delni_prag * najvec))
    zanesljivost = float(ac[perioda])
    if zanesljivost < MIN_ZANESLJIVOST:
        return None
    stevilo = _prestej_vrhove(e, perioda)
    if stevilo < 2:
        return None
    return Perioda(stevilo=stevilo, perioda_px=float(perioda),
                   zanesljivost=zanesljivost,
                   pricakovano=int(round(n / perioda)))




MIN_RAZMERJE_SIRINE = 1.8   # steber je vsaj toliko širši od deske
MAX_CV_RAZMERJE = 0.20      # večja neenakomernost ni ritem stebrov
# Perioda, manjša od tega deleža višine ograje, je ritem DESK, ne stebrov:
# deske so ~0,1 višine narazen, stebri pa ~1 višino (polje ~2 m, višina ~1,8 m).
# Razmerje je brez merila (piksli/piksli), zato deluje tudi brez markerja.
MIN_RAZMERJE_STEBROV = 0.35


@dataclass(frozen=True)
class Stebri:
    """Stebri, najdeni po ŠIRINI elementov (stebri so širši od desk)."""

    stevilo: int
    perioda_px: float
    zanesljivost: float


def _profil_za_sirino(pas: np.ndarray) -> np.ndarray:
    """Stolpčni profil za ločevanje po širini (brez CLAHE, kratko ozadje)."""
    siva = (cv2.cvtColor(pas, cv2.COLOR_BGR2GRAY) if pas.ndim == 3
            else pas).astype(np.float32)
    profil = siva.mean(axis=0)
    n = len(profil)
    if n < 9:
        return profil - profil.mean()
    k = max(9, (n // 8) | 1)      # kratko ozadje: stebri ostanejo ostri
    trend = cv2.blur(profil.reshape(1, -1), (k, 1)).ravel()
    return profil - trend


def _teki_temnega(profil: np.ndarray) -> list[tuple[int, int]]:
    """Zaporedni temni odseki profila kot (zacetek, konec), vključno."""
    naj = float(np.abs(profil).max())
    if naj <= 1e-6:
        return []
    temno = profil < -0.35 * naj
    teki: list[tuple[int, int]] = []
    zacetek: int | None = None
    for i, t in enumerate(temno):
        if t and zacetek is None:
            zacetek = i
        elif not t and zacetek is not None:
            teki.append((zacetek, i - 1))
            zacetek = None
    if zacetek is not None:
        teki.append((zacetek, len(temno) - 1))
    return teki


def poisci_stebre(pas: np.ndarray) -> Stebri | None:
    """Poišči STEBRE (ne desk) po širini: stebri so ~2× širši od desk."""

    # Deske so ozke in številne, stebri redki in široki. Če so vsi teki
    # enako široki (ograja brez izrazitih stebrov), funkcija vrne None —
    # bolje neznano kot napačno število.
    if pas is None or pas.size == 0:
        return None
    teki = _teki_temnega(_profil_za_sirino(pas))
    if len(teki) < 4:
        return None
    sirine = np.array([k - z + 1 for z, k in teki], dtype=float)
    mediana = float(np.median(sirine))
    if mediana <= 0:
        return None
    siroki = [t for t, w in zip(teki, sirine)
              if w >= MIN_RAZMERJE_SIRINE * mediana]
    if len(siroki) < 2:
        return None
    sredine = np.array([(z + k) / 2.0 for z, k in siroki])
    razmiki = np.diff(sredine)
    if len(razmiki) < 1 or float(razmiki.mean()) <= 0:
        return None
    cv = float(razmiki.std() / razmiki.mean())
    if cv > MAX_CV_RAZMERJE:
        return None
    return Stebri(stevilo=len(siroki), perioda_px=float(np.median(razmiki)),
                  zanesljivost=1.0 - cv)

def prestej(pas: np.ndarray, min_px: float = MIN_PERIODA_PX,
            max_px: float | None = None) -> Perioda | None:
    """Preštej elemente v pasu slike; None, če perioda ni zanesljiva."""
    if pas is None or pas.size == 0:
        return None
    return iz_profila(profil_svetlosti(pas), min_px=min_px, max_px=max_px)


def pas_ograje(slika: np.ndarray, zgoraj: float = 0.35,
               spodaj: float = 0.85) -> np.ndarray:
    """Srednji pas slike (brez neba in tal) — tam je ograja."""
    h = slika.shape[0]
    y0 = int(round(h * zgoraj))
    y1 = int(round(h * spodaj))
    if y1 - y0 < 8:
        return slika
    return slika[y0:y1]
