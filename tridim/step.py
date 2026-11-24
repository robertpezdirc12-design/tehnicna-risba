# -*- coding: utf-8 -*-
"""Neobvezni STEP izvoz prek cadqueryja — NIKOLI vgrajen v izvršilno datoteko.

Zakaj ločen most in ne vgrajen uvoz:

- cadquery je Apache-2.0, a njegov jedrni odvisnik ``cadquery-ocp`` vsebuje
  OpenCASCADE (LGPL-2.1-only z izjemo ``OCCT-exception-1.0``), ``casadi``
  v odvisnostih pa je LGPL-3.0. Vgradnja teh knjižnic v naš EXE bi bila
  distribucija LGPL kode; politika projekta (MIT) copyleft v izdelek ne
  vgrajuje.
- Zato je STEP most **neobvezen**: če cadquery ni nameščen, funkcija
  pove, kaj manjka in kako ga namestiti — ne ugiba in ne ustvari lažnega
  STEP zapisa iz mreže (triangulirana ploskev ni CAD model).

Zapis je pravi BREP: vsak del je kvader, zato je geometrija enaka kot v
mrežnem izvozu, le brez triangulacije.
"""

from __future__ import annotations

import pathlib
from typing import Any

from tridim.sestav import deli_pokoncne


class ManjkaKnjiznica(RuntimeError):
    """Zahtevana neobvezna knjižnica ni nameščena."""


NAVODILO = (
    "STEP izvoz potrebuje cadquery, ki uporablja OpenCASCADE "
    "(LGPL-2.1 z izjemo OCCT-exception-1.0) in casadi (LGPL-3.0). "
    "Zato cadquery NI vgrajen v ta program — namesti ga ločeno v svoje "
    "okolje: python -m pip install cadquery. Mrežni izvoz (STL/OBJ/GLB) "
    "deluje brez njega."
)


def na_voljo() -> bool:
    """Ali je cadquery mogoče uvoziti v tem okolju."""
    try:
        import cadquery  # noqa: F401
    except Exception:                     # noqa: BLE001 — vsak uvoz lahko pade
        return False
    return True


def izvozi_step(cfg: dict[str, Any], pot: str | pathlib.Path) -> dict[str, Any]:
    """Zapiše STEP (AP214) iz kvadrov modela; vrne povzetek."""
    try:
        import cadquery as cq
    except Exception as napaka:            # noqa: BLE001 — sporočimo vzrok
        raise ManjkaKnjiznica(NAVODILO) from napaka

    podatki = deli_pokoncne(cfg)
    telesa = []
    for k in podatki["kvadri"]:
        kos = (cq.Workplane("XY")
               .box(k.dx, k.dy, k.dz, centered=(False, False, False))
               .translate((k.x0, k.y0, k.z0)))
        telesa.append(kos.val())

    skupina = cq.Compound.makeCompound(telesa)
    cilj = pathlib.Path(pot)
    cq.exporters.export(skupina, str(cilj))
    return {
        "pot": str(cilj),
        "teles": len(telesa),
        "opombe": podatki["opombe"],
    }
