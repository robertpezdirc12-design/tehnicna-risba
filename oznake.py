# -*- coding: utf-8 -*-
"""Strojno berljive oznake projektov (QR) — deterministično, brez modelov.

Zakaj QR in ne OCR: OCR fotografije (npr. PaddleOCR/TrOCR) bi v program
prinesel 10–500 MB uteži in novo licenčno vprašanje (uteži imajo svoje
licence, ne le koda), poleg tega je branje ročne pisave negotovo. QR koda,
ki jo natisnemo sami, je berljiva z OpenCV (Apache-2.0, že vgrajen) in
daje **natanko zapisano vrednost** — brez ugibanja.

Zapis oznake (verzija 1)::

    TR1|<projekt>|<šifra risbe>|<višina mm>|<širina mm>
    TR1|PO-2026-014|PO-009|1850|2500

Pravila (usklajena s filozofijo projekta »brez ugibanja«):
- oznaka se sestavi samo iz podatkov, ki v konfiguraciji res obstajajo;
- pri branju se vsako polje preveri; neveljavna koda se **ne** popravi,
  ampak se zavrne z razlogom v ``opozorila``;
- branje nikoli ne spremeni podatkov samo — vrne predlog, uporabnik
  potrdi (glej ``vmesnik.py``).
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any

PREDPONA = "TR1"
POLJA = ("projekt", "sifra", "visina", "sirina")


class ManjkajocaKnjiznica(RuntimeError):
    """OpenCV ni nameščen (potreben za QR)."""


class NeveljavnaOznaka(ValueError):
    """Vsebina kode ni veljavna oznaka TR1."""


@dataclass(frozen=True)
class Oznaka:
    """Prebrana oznaka projekta."""

    projekt: str
    sifra: str
    mere: dict[str, float]
    surovo: str = ""

    def v_slovar(self) -> dict[str, Any]:
        return {"projekt": self.projekt, "sifra": self.sifra,
                "mere": dict(self.mere), "surovo": self.surovo}


@dataclass
class RezultatOznak:
    """Rezultat branja slike: najdene oznake + pojasnila."""

    oznake: list[Oznaka] = field(default_factory=list)
    opozorila: list[str] = field(default_factory=list)
    kod_v_sliki: int = 0

    @property
    def uspeh(self) -> bool:
        return bool(self.oznake)


def _cv2() -> Any:
    try:
        import cv2
    except Exception as napaka:            # noqa: BLE001 — vsak uvoz lahko pade
        raise ManjkajocaKnjiznica(
            "Branje in zapis QR oznak potrebujeta OpenCV (Apache-2.0). "
            "V Python različici: python -m pip install opencv-python. "
            "Samostojni EXE je zgrajen BREZ OpenCV (TehnicnaRisba.spec "
            "izključi cv2) — tam QR ni na voljo; uporabi Python različico "
            "ali zgradi EXE z vključenim cv2.") from napaka
    return cv2


def _stevilo(besedilo: str, ime: str) -> float:
    try:
        vrednost = float(besedilo.replace(",", "."))
    except ValueError:
        raise NeveljavnaOznaka(
            f"polje {ime!r} ni število: {besedilo!r}") from None
    if not (vrednost > 0):
        raise NeveljavnaOznaka(f"polje {ime!r} mora biti pozitivno")
    return vrednost


def sestavi_oznako(cfg: dict[str, Any]) -> str:
    """Sestavi oznako iz konfiguracije; manjkajoče podatke javi, ne izmisli."""
    projekt = str(cfg.get("ime") or "").strip()
    sifra = str(cfg.get("risba_st") or "").strip()
    mere = cfg.get("mere") or {}
    if not projekt:
        raise NeveljavnaOznaka("konfiguracija nima imena projekta (ime)")
    if not sifra:
        raise NeveljavnaOznaka("konfiguracija nima šifre risbe (risba_st)")
    if "|" in projekt or "|" in sifra:
        raise NeveljavnaOznaka("imena in šifre ne smejo vsebovati znaka '|'")
    visina = _stevilo(str(mere.get("visina", "")), "visina")
    sirina = _stevilo(str(mere.get("sirina", "")), "sirina")
    return "|".join((PREDPONA, projekt, sifra,
                     f"{visina:g}", f"{sirina:g}"))


def razcleni_oznako(besedilo: str) -> Oznaka:
    """Razčleni in preveri oznako; neveljavno zavrne z razlogom."""
    deli = str(besedilo or "").strip().split("|")
    if len(deli) != 5:
        raise NeveljavnaOznaka(
            f"pričakovanih 5 polj, dobljenih {len(deli)}")
    predpona, projekt, sifra, visina, sirina = deli
    if predpona != PREDPONA:
        raise NeveljavnaOznaka(
            f"neznana predpona {predpona!r} (pričakovano {PREDPONA!r})")
    if not projekt.strip() or not sifra.strip():
        raise NeveljavnaOznaka("prazno ime projekta ali šifra risbe")
    return Oznaka(projekt=projekt.strip(), sifra=sifra.strip(),
                  mere={"visina": _stevilo(visina, "visina"),
                        "sirina": _stevilo(sirina, "sirina")},
                  surovo=str(besedilo).strip())


def zapisi_oznako(besedilo: str, pot: str | pathlib.Path,
                  velikost_px: int = 240, rob_px: int = 40) -> pathlib.Path:
    """Zapiše QR kodo s tihim robom (quiet zone) kot PNG.

    Tihi rob je del standarda: brez njega bralniki kode ne najdejo.
    """
    cv2 = _cv2()
    if velikost_px < 64:
        raise ValueError("velikost QR kode mora biti vsaj 64 px")
    if rob_px < 16:
        raise ValueError("tihi rob mora biti vsaj 16 px")
    koda = cv2.QRCodeEncoder_create().encode(besedilo)
    if isinstance(koda, tuple):            # starejši OpenCV vrne (koda, …)
        koda = koda[0]
    koda = cv2.resize(koda, (velikost_px, velikost_px),
                      interpolation=cv2.INTER_NEAREST)
    import numpy as np

    platno = np.full((velikost_px + 2 * rob_px, velikost_px + 2 * rob_px),
                     255, dtype=np.uint8)
    platno[rob_px:rob_px + velikost_px, rob_px:rob_px + velikost_px] = koda
    cilj = pathlib.Path(pot)
    if not cv2.imwrite(str(cilj), platno):
        raise OSError(f"slike ni mogoče zapisati: {cilj}")
    return cilj


def preberi_oznake(vir: str | pathlib.Path | Any) -> RezultatOznak:
    """Poišče in prebere QR oznake na sliki (pot ali že naložena slika).

    Neveljavne kode se ne popravljajo; vsaka dobi svoje opozorilo.
    """
    cv2 = _cv2()
    import numpy as np

    if isinstance(vir, (str, pathlib.Path)):
        slika = cv2.imread(str(vir), cv2.IMREAD_COLOR)
        if slika is None:
            raise OSError(f"slike ni mogoče prebrati: {vir}")
    else:
        slika = vir
    if not isinstance(slika, np.ndarray) or slika.size == 0:
        raise ValueError("slika je prazna ali ni slika")

    detektor = cv2.QRCodeDetector()
    rezultat = RezultatOznak()
    besedila: list[str] = []
    try:
        najdeno, vec, _tocke, _ = detektor.detectAndDecodeMulti(slika)
        if najdeno:
            besedila = [b for b in vec if b]
    except cv2.error:                      # pragma: no cover — redka napaka
        besedila = []
    if not besedila:
        eno, _tocke, _ = detektor.detectAndDecode(slika)
        if eno:
            besedila = [eno]

    rezultat.kod_v_sliki = len(besedila)
    if not besedila:
        rezultat.opozorila.append(
            "V sliki ni berljive QR kode (poskusi: večja koda, manj "
            "zameglitve, boljša osvetlitev).")
        return rezultat

    for besedilo in besedila:
        try:
            rezultat.oznake.append(razcleni_oznako(besedilo))
        except NeveljavnaOznaka as napaka:
            rezultat.opozorila.append(
                f"Koda je prebrana, a ni veljavna oznaka {PREDPONA}: {napaka}")
    return rezultat


def oznake_za_polja(oznaka: Oznaka) -> dict[str, str]:
    """Preslikava oznake v polja glavnega obrazca (vrednosti kot besedilo)."""
    polja = {"ime": oznaka.projekt, "risba_st": oznaka.sifra}
    if "visina" in oznaka.mere:
        polja["visina"] = f"{oznaka.mere['visina']:g}"
    if "sirina" in oznaka.mere:
        polja["sirina"] = f"{oznaka.mere['sirina']:g}"
    return polja


def main(argv: list[str] | None = None) -> int:
    """CLI: ``--zapisi`` (iz YAML) ali ``--preberi`` (iz slike)."""
    import argparse
    import sys

    razclenjevalnik = argparse.ArgumentParser(
        prog="python oznake.py",
        description="QR oznake projektov (brez modelov, brez OCR).")
    skupina = razclenjevalnik.add_mutually_exclusive_group(required=True)
    skupina.add_argument("--zapisi", metavar="KONFIGURACIJA",
                         help="sestavi oznako iz konfiguracije (YAML/JSON)")
    skupina.add_argument("--preberi", metavar="SLIKA",
                         help="preberi oznake s slike")
    razclenjevalnik.add_argument("--izhod", default="oznaka.png",
                                 help="izhodna slika pri --zapisi")
    argumenti = razclenjevalnik.parse_args(argv)

    if argumenti.zapisi:
        import jedro

        try:
            cfg = jedro.nalozi_konf(argumenti.zapisi)
            besedilo = sestavi_oznako(cfg)
        except (OSError, ValueError) as napaka:
            print(f"NAPAKA: {napaka}", file=sys.stderr)
            return 2
        pot = zapisi_oznako(besedilo, argumenti.izhod)
        print(f"Zapisano: {pot}")
        print(f"  vsebina: {besedilo}")
        return 0

    try:
        rezultat = preberi_oznake(argumenti.preberi)
    except (OSError, ValueError) as napaka:
        print(f"NAPAKA: {napaka}", file=sys.stderr)
        return 2
    for oznaka in rezultat.oznake:
        print(f"Projekt: {oznaka.projekt}  (risba {oznaka.sifra})")
        print(f"  visina: {oznaka.mere['visina']:g} mm, "
              f"širina: {oznaka.mere['sirina']:g} mm")
    for opozorilo in rezultat.opozorila:
        print(f"OPOZORILO: {opozorilo}")
    return 0 if rezultat.uspeh else 1


if __name__ == "__main__":
    raise SystemExit(main())
