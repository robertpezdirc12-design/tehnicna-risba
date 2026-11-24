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
from functools import lru_cache
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


PRAG_ZAUPANJA = 0.60


@dataclass
class RezultatBesedila:
    """Rezultat OCR (neobvezna pot): prebrane vrstice + najdene oznake."""

    oznake: list[Oznaka] = field(default_factory=list)
    vrstice: list[tuple[str, float]] = field(default_factory=list)
    opozorila: list[str] = field(default_factory=list)

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


NAVODILO_BESEDILO = (
    "Branje besedila (OCR) potrebuje neobvezni paket "
    "rapidocr-onnxruntime (Apache-2.0; vključuje ONNX-uteži, izpeljane "
    "iz PaddleOCR). Namesti ga ločeno: "
    "python -m pip install rapidocr-onnxruntime. QR pot deluje brez "
    "njega in je zanesljivejša — OCR je samo nadomestna pot za "
    "natisnjene oznake brez QR kode. Samostojni EXE je zgrajen BREZ "
    "tega paketa (TehnicnaRisba.spec izključi rapidocr/onnxruntime) — "
    "tam OCR ni na voljo; uporabi QR pot ali Python različico."
)


def _ocr_motor() -> Any:
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except Exception as napaka:            # noqa: BLE001 — vsak uvoz lahko pade
        raise ManjkajocaKnjiznica(NAVODILO_BESEDILO) from napaka
    return _motor_global()


@lru_cache(maxsize=1)
def _motor_global() -> Any:
    """En motor za celo sejo — nalaganje modelov je počasno (~10 s)."""
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _preberi_sliko(vir: str | pathlib.Path | Any) -> Any:
    """Naloži sliko iz poti ali sprejmi že naloženo (numpy)."""
    import numpy as np

    if isinstance(vir, (str, pathlib.Path)):
        cv2 = _cv2()
        slika = cv2.imread(str(vir), cv2.IMREAD_COLOR)
        if slika is None:
            raise OSError(f"slike ni mogoče prebrati: {vir}")
        return slika
    if not isinstance(vir, np.ndarray) or vir.size == 0:
        raise ValueError("slika je prazna ali ni slika")
    return vir


def preberi_besedilo(vir: str | pathlib.Path | Any,
                     prag: float = PRAG_ZAUPANJA) -> RezultatBesedila:
    """Prebere besedilo s slike (OCR) in iz njega izlušči oznake TR1.

    To je **neobvezna nadomestna pot**: QR koda je deterministična, OCR
    pa je verjetnosten. Zato se vsaka vrstica pod pragom zaupanja zavrže
    z razlogom, neveljavne vrstice pa se ne popravljajo.
    """
    motor = _ocr_motor()
    slika = _preberi_sliko(vir)
    rezultat = RezultatBesedila()

    try:
        zadetki, _cas = motor(slika)
    except Exception as napaka:            # noqa: BLE001 — napaka motorja
        raise RuntimeError(f"OCR ni uspel: {napaka}") from napaka

    if not zadetki:
        rezultat.opozorila.append(
            "V sliki ni berljivega besedila (poskusi z večjo in "
            "ostrejšo sliko).")
        return rezultat

    for zadetek in zadetki:
        besedilo = str(zadetek[1]).strip()
        try:
            zaupanje = float(zadetek[2])
        except (TypeError, ValueError, IndexError):
            zaupanje = 0.0
        if not besedilo:
            continue
        rezultat.vrstice.append((besedilo, zaupanje))
        if zaupanje < prag:
            rezultat.opozorila.append(
                f"Vrstica {besedilo!r} ima zaupanje {zaupanje:.2f} < "
                f"{prag:.2f} — ni upoštevana.")
            continue
        try:
            rezultat.oznake.append(razcleni_oznako(besedilo))
        except NeveljavnaOznaka as napaka:
            rezultat.opozorila.append(
                f"Vrstica {besedilo!r} ni veljavna oznaka {PREDPONA}: "
                f"{napaka}")

    if not rezultat.oznake and not any(
            "ni upoštevana" in o for o in rezultat.opozorila):
        rezultat.opozorila.append(
            f"V besedilu ni oznake {PREDPONA} (pričakovano "
            "TR1|projekt|šifra|višina|širina).")
    return rezultat


@dataclass
class Najdba:
    """Kaj je našla skupna pot: oznake + od kod (qr / ocr)."""

    oznake: list[Oznaka] = field(default_factory=list)
    vir: str = ""
    opozorila: list[str] = field(default_factory=list)

    @property
    def uspeh(self) -> bool:
        return bool(self.oznake)


def najdi_oznake(vir: str | pathlib.Path | Any,
                 dovoli_ocr: bool = True) -> Najdba:
    """Najprej QR (deterministično), nato OCR kot nadomestna pot."""
    qr = preberi_oznake(vir)
    if qr.uspeh:
        return Najdba(oznake=qr.oznake, vir="qr", opozorila=qr.opozorila)

    najdba = Najdba(opozorila=list(qr.opozorila))
    if not dovoli_ocr:
        return najdba
    try:
        ocr = preberi_besedilo(vir)
    except (ManjkajocaKnjiznica, OSError, ValueError, RuntimeError) as napaka:
        najdba.opozorila.append(f"OCR ni na voljo: {napaka}")
        return najdba
    najdba.oznake = ocr.oznake
    najdba.opozorila.extend(ocr.opozorila)
    if ocr.uspeh:
        najdba.vir = "ocr"
        najdba.opozorila.insert(
            0, "Oznaka je prebrana z OCR (ne QR) — vrednosti PREVERI "
               "pred uporabo.")
    return najdba


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
                         help="preberi oznake s slike (najprej QR, nato OCR)")
    razclenjevalnik.add_argument("--izhod", default="oznaka.png",
                                 help="izhodna slika pri --zapisi")
    razclenjevalnik.add_argument("--brez-ocr", action="store_true",
                                 help="pri --preberi ne uporabi OCR "
                                      "(samo QR)")
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
        najdba = najdi_oznake(argumenti.preberi, not argumenti.brez_ocr)
    except (OSError, ValueError) as napaka:
        print(f"NAPAKA: {napaka}", file=sys.stderr)
        return 2
    if najdba.vir:
        print(f"Vir: {najdba.vir.upper()}")
    for oznaka in najdba.oznake:
        print(f"Projekt: {oznaka.projekt}  (risba {oznaka.sifra})")
        print(f"  visina: {oznaka.mere['visina']:g} mm, "
              f"širina: {oznaka.mere['sirina']:g} mm")
    for opozorilo in najdba.opozorila:
        print(f"OPOZORILO: {opozorilo}")
    return 0 if najdba.uspeh else 1


if __name__ == "__main__":
    raise SystemExit(main())
