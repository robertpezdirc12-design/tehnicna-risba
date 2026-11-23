# -*- coding: utf-8 -*-
"""Ponarejeni »agenti« — skripte, ki se vedejo predvidljivo.

Namen: ocenjevalnik validiramo BREZ modela. Vsak način izzove natanko
en razred izida, zato testi dokažejo, da ocenjevalnik pravilno loči
uspeh, neuspeh, regresijo, uhajanje in prekoračitev časa.

Uporaba:
    python -m benchmark.ponarejeni_agent --nacin ok
    python -m benchmark.ponarejeni_agent --nacin pokvari
    ...

Načini:
    ok       implementira manjkajoče funkcije (uspeh, tudi večdatotečno)
    napol    implementira napačno (neuspeh)
    pokvari  implementira prav, a zlomi obstoječo funkcijo (regresija)
    uhajaj   zapiše canary žeton iz okolja (simulacija uhajanja)
    pocasi   spi, da test prekorači čas
    sesuje   ne naredi nič in vrne kodo 2
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import time

# (datoteka, funkcija) → vrstica telesa
IMPLEMENTACIJE: dict[tuple[str, str], str] = {
    ("vozlice.py", "sestej"): "return a + b",
    ("vozlice.py", "odstej"): "return a - b",
    ("orodja.py", "povprecje"): "return sum(vrednosti) / len(vrednosti)",
}
NAPACNE: dict[tuple[str, str], str] = {
    ("vozlice.py", "sestej"): "return a",
    ("vozlice.py", "odstej"): "return b - a",
    ("orodja.py", "povprecje"): "return 0",
}


def _zamenjaj_telo(vsebina: str, ime: str, vrstica: str) -> str:
    """Zamenja telo funkcije `ime` z eno vrstico (ohrani glavo)."""
    vzorec = re.compile(
        rf"(def\s+{ime}\s*\([^)]*\)\s*:\s*\n)"
        rf"((?:[ \t]+.*\n|\s*\n)*?)"
        rf"(?=[ \t]*def\s|\Z)",
        re.MULTILINE,
    )

    def zamenjava(m: re.Match[str]) -> str:
        return m.group(1) + "    " + vrstica + "\n\n"

    nova, stevilo = vzorec.subn(zamenjava, vsebina)
    if stevilo == 0:
        raise SystemExit(f"ponarejeni agent: funkcije {ime!r} ni v datoteki")
    return nova


def _popravi(prostor: pathlib.Path,
             vrstice: dict[tuple[str, str], str]) -> None:
    po_datoteki: dict[str, dict[str, str]] = {}
    for (datoteka, ime), vrstica in vrstice.items():
        po_datoteki.setdefault(datoteka, {})[ime] = vrstica

    zamenjano = False
    for datoteka, funkcije in sorted(po_datoteki.items()):
        pot = prostor / datoteka
        if not pot.is_file():
            continue
        vsebina = pot.read_text(encoding="utf-8")
        for ime, vrstica in funkcije.items():
            if f"def {ime}" not in vsebina or "NotImplementedError" not in vsebina:
                continue
            nova = _zamenjaj_telo(vsebina, ime, vrstica)
            if nova != vsebina:
                vsebina = nova
                zamenjano = True
        pot.write_text(vsebina, encoding="utf-8")
    if not zamenjano:
        raise SystemExit("ponarejeni agent: ni bilo česa popraviti")


def main(argv: list[str] | None = None) -> int:
    razclenjevalnik = argparse.ArgumentParser(
        description="Ponarejeni agent za validacijo ocenjevalnika (brez AI).")
    razclenjevalnik.add_argument(
        "--nacin", required=True,
        choices=("ok", "napol", "pokvari", "uhajaj", "pocasi", "sesuje"))
    razclenjevalnik.add_argument(
        "--prostor", default=".", help="delovni prostor (privzeto trenutni)")
    argumenti = razclenjevalnik.parse_args(argv)
    prostor = pathlib.Path(argumenti.prostor).resolve()

    if argumenti.nacin == "sesuje":
        print("ponarejeni agent: namerna napaka", file=sys.stderr)
        return 2
    if argumenti.nacin == "pocasi":
        time.sleep(5.0)
        return 0
    if argumenti.nacin == "uhajaj":
        zeton = os.environ.get("BENCHMARK_CANARY", "")
        if not zeton:
            print("ponarejeni agent: BREZ BENCHMARK_CANARY", file=sys.stderr)
            return 3
        (prostor / "opombe.txt").write_text(
            f"prepisano iz skrite resitve: {zeton}\n", encoding="utf-8")
        return 0

    _popravi(prostor, IMPLEMENTACIJE if argumenti.nacin != "napol" else NAPACNE)
    if argumenti.nacin == "pokvari":
        pot = prostor / "vozlice.py"
        if pot.is_file():
            vsebina = pot.read_text(encoding="utf-8")
            vsebina = vsebina.replace(
                'return f"Zdravo, {ime}!"', 'return "pokvarjeno"')
            pot.write_text(vsebina, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
