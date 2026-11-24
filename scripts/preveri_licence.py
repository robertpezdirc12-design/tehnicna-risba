# -*- coding: utf-8 -*-
"""Preveri in osveži seznam licenc vgrajenih knjižnic.

Zakaj: PyInstaller rad odreže licenčna besedila vgrajenih paketov
(github.com/pyinstaller/pyinstaller/issues/5666), zato mora obvestilo
obstajati v repozitoriju in se ujemati z dejansko nameščenimi
različicami. Skript bere metapodatke paketov (brez uvažanja kode) in
primerja tabelo v ``THIRD_PARTY_NOTICES.md``.

Uporaba::

    python scripts/preveri_licence.py --preveri   # CI: 0 = usklajeno
    python scripts/preveri_licence.py --zapisi    # prepiše tabelo
"""

from __future__ import annotations

import pathlib
import sys
from importlib import metadata

KOREN = pathlib.Path(__file__).resolve().parents[1]
OBVESTILO = KOREN / "THIRD_PARTY_NOTICES.md"
ZAHTEVE = KOREN / "requirements.txt"
ZACETEK = "<!-- ZACETEK-TABELE -->"
KONEC = "<!-- KONEC-TABELE -->"

# Paket iz requirements.txt -> (ali je v EXE, opomba)
V_EXE: dict[str, tuple[str, str]] = {
    "flask": ("ne", "samo `api/index.py` (spletni API), ni v GUI build"),
    "matplotlib": ("da", "risanje PDF"),
    "pyyaml": ("da", "konfiguracije in katalogi"),
    "numpy": ("da", "geometrija in slike"),
    "ezdxf": ("da", "DXF izvoz (pin 1.4.5)"),
    "pillow": ("da", "slike in Tk"),
    "ttkbootstrap": ("da", "teme GUI (neobvezno)"),
    "opencv-python": ("ne", "`TehnicnaRisba.spec` izključi `cv2`; "
                            "foto/QR dela samo v Python različici"),
}


def _paketi() -> list[str]:
    imena: list[str] = []
    for vrstica in ZAHTEVE.read_text(encoding="utf-8").splitlines():
        vrstica = vrstica.split("#")[0].strip()
        if not vrstica or vrstica.startswith("-"):
            continue
        ime = vrstica.split("==")[0].split(">=")[0].split("<")[0].strip()
        if ime:
            imena.append(ime)
    return imena


def _licenca(ime: str) -> tuple[str, str]:
    """Vrne (različica, licenca) iz metapodatkov; brez uvažanja paketa."""
    try:
        meta = metadata.metadata(ime)
        razlicica = metadata.version(ime)
    except metadata.PackageNotFoundError:
        return ("—", "NI NAMEŠČEN")
    izraz = meta.get("License-Expression")
    if izraz:
        return (razlicica, izraz.strip())
    klasifikatorji = [k.split("::")[-1].strip()
                      for k in (meta.get_all("Classifier") or [])
                      if k.startswith("License")]
    if klasifikatorji:
        return (razlicica, klasifikatorji[0])
    licenca = (meta.get("License") or "").strip().splitlines()
    if licenca and len(licenca[0]) <= 40:
        return (razlicica, licenca[0])
    return (razlicica, "NEZNANO")


def tabela() -> str:
    vrstice = ["| Paket | Različica | Licenca | V EXE | Opomba |",
               "|---|---|---|---|---|"]
    for ime in _paketi():
        razlicica, licenca = _licenca(ime)
        v_exe, opomba = V_EXE.get(ime.lower(), ("?", "ni dokumentirano"))
        vrstice.append(f"| {ime} | {razlicica} | {licenca} | {v_exe} | {opomba} |")
    # opencv-python je v requirements-build.txt (ne v requirements.txt),
    # a spec ga izključi — zato mora biti dokumentiran posebej.
    razlicica, licenca = _licenca("opencv-python")
    v_exe, opomba = V_EXE["opencv-python"]
    vrstice.append(f"| opencv-python | {razlicica} | {licenca} | {v_exe} | "
                   f"{opomba} |")
    vrstice.append("| PyInstaller (bootloader) | "
                   f"{_licenca('pyinstaller')[0]} | GPL-2.0 z izjemo za "
                   "vgrajevanje | da | orodje, ne knjižnica izdelka |")
    return "\n".join(vrstice)


def _preberi_tabelo() -> str:
    if not OBVESTILO.is_file():
        return ""
    vsebina = OBVESTILO.read_text(encoding="utf-8")
    if ZACETEK not in vsebina or KONEC not in vsebina:
        return ""
    return vsebina.split(ZACETEK)[1].split(KONEC)[0].strip()


def zapisi() -> int:
    vsebina = OBVESTILO.read_text(encoding="utf-8")
    if ZACETEK not in vsebina or KONEC not in vsebina:
        print("NAPAKA: v obvestilu ni oznak za tabelo", file=sys.stderr)
        return 2
    pred, ostalo = vsebina.split(ZACETEK)
    _, po = ostalo.split(KONEC)
    OBVESTILO.write_text(f"{pred}{ZACETEK}\n{tabela()}\n{KONEC}{po}",
                         encoding="utf-8")
    print("Tabela licenc osvežena.")
    return 0


def preveri() -> int:
    if not OBVESTILO.is_file():
        print("NAPAKA: THIRD_PARTY_NOTICES.md manjka", file=sys.stderr)
        return 2
    zapisano = _preberi_tabelo()
    if not zapisano:
        print("NAPAKA: v obvestilu ni tabele med oznakama", file=sys.stderr)
        return 2
    pricakovano = tabela()
    if zapisano != pricakovano:
        print("NAPAKA: tabela licenc se ne ujema z nameščenimi različicami.",
              file=sys.stderr)
        for vrstica in pricakovano.splitlines():
            if vrstica not in zapisano.splitlines():
                print(f"  manjka/razlikuje se: {vrstica}", file=sys.stderr)
        print("  popravi: python scripts/preveri_licence.py --zapisi",
              file=sys.stderr)
        return 1
    print(f"Licence: tabela usklajena ({len(_paketi())} paketov + "
          "PyInstaller).")
    return 0


def main(argv: list[str] | None = None) -> int:
    argumenti = argv if argv is not None else sys.argv[1:]
    if "--zapisi" in argumenti:
        return zapisi()
    if "--preveri" in argumenti:
        return preveri()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
