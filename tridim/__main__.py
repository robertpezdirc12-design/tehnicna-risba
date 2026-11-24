# -*- coding: utf-8 -*-
"""Ukazna vrstica: ``python -m tridim --vhod projekt.yaml --izhod model.stl``.

Izvoz je namenoma ločen od risanja PDF: 3D model se zgradi iz istih mer
kot risba (``jedro``), zato se ne more »pobeliti« od nje.
"""

from __future__ import annotations

import argparse
import sys

import jedro
from tridim.izvoz import shrani
from tridim.sestav import model_ograde


def main(argv: list[str] | None = None) -> int:
    razclenjevalnik = argparse.ArgumentParser(
        prog="python -m tridim",
        description="3D model pokončne ograje (STL/OBJ/GLB) iz konfiguracije.")
    razclenjevalnik.add_argument("--vhod", required=True,
                                 help="konfiguracija (YAML ali JSON)")
    razclenjevalnik.add_argument("--izhod", default="model.stl",
                                 help="izhodna datoteka (.stl, .obj, .glb)")
    razclenjevalnik.add_argument("--step", default=None,
                                 help="neobvezno: STEP prek cadqueryja "
                                      "(ni vgrajen)")
    razclenjevalnik.add_argument("--tiho", action="store_true",
                                 help="brez izpisa povzetka")
    argumenti = razclenjevalnik.parse_args(argv)

    try:
        cfg = jedro.nalozi_konf(argumenti.vhod)
    except (OSError, ValueError) as napaka:
        print(f"NAPAKA: konfiguracije ni mogoče prebrati: {napaka}",
              file=sys.stderr)
        return 2

    try:
        model = model_ograde(cfg)
    except (KeyError, ValueError) as napaka:
        print(f"NAPAKA: modela ni mogoče zgraditi: {napaka}", file=sys.stderr)
        return 2

    tezave = model["mreza"].preveri()
    if tezave:
        print("NAPAKA: mreza ni uporabna: " + "; ".join(tezave),
              file=sys.stderr)
        return 3

    try:
        pot = shrani(model["mreza"], argumenti.izhod)
    except (OSError, ValueError) as napaka:
        print(f"NAPAKA: izvoza ni mogoče zapisati: {napaka}", file=sys.stderr)
        return 2
    if not argumenti.tiho:
        mere = model["mere"]
        (x0, y0, z0), (x1, y1, z1) = model["mreza"].meje()
        print(f"Zapisano: {pot}")
        if "desk" in mere:
            sestava = (f"stebri {mere['stebrov']}, deske {mere['desk']}, "
                       "rocaj + osnove")
        else:
            sestava = (f"lamele {mere['lamel']}, profili, nosilci"
                       + (f", odprtine {mere['odprtin']}" if mere.get("odprtin")
                          else ""))
        print(f"  deli: {len(model['deli'])} ({sestava})")
        print(f"  predloga: {cfg.get('predloga')}")
        print(f"  trikotniki: {len(model['mreza'].trikotniki)}")
        print(f"  obseg: {x1 - x0:.1f} × {y1 - y0:.1f} × {z1 - z0:.1f} mm")
        print(f"  prostornina: {mere['prostornina_mm3'] / 1e9:.4f} m³")
        for opomba in model["opombe"]:
            print(f"  opomba: {opomba}")

    if argumenti.step:
        from tridim.step import ManjkaKnjiznica, izvozi_step

        try:
            povzetek = izvozi_step(cfg, argumenti.step)
        except ManjkaKnjiznica as napaka:
            print(f"STEP ni izvožen: {napaka}", file=sys.stderr)
            return 4
        if not argumenti.tiho:
            print(f"STEP: {povzetek['pot']} ({povzetek['teles']} teles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
