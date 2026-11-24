# -*- coding: utf-8 -*-
"""3D sloj ograje — mreže brez copyleft odvisnosti.

Razlog za ta paket je licenčna odločitev, ne okus: cadquery/OCP prinašata
LGPL (OpenCASCADE) in LGPL-3.0 (casadi), zato v izdelek ne gresta. Namesto
tega imamo svoj mrežni sloj — dovolj za STL/OBJ/GLB, brez ene same nove
odvisnosti:

- :mod:`tridim.mreza` — zaprte trikotniške mreže, prizme, kontrola zaprtosti,
- :mod:`tridim.izvoz` — pisalniki in bralniki STL / OBJ / GLB,
- :mod:`tridim.sestav` — sestav ograje iz mer, ki jih izračuna ``jedro``,
- :mod:`tridim.step` — neobvezni BREP most (cadquery), namenoma len.

Podrobnosti in viri: ``docs/odlocitev-3d-in-ocr.md``.
"""

from __future__ import annotations

import importlib
from typing import Any

from tridim.izvoz import PISALNIKI, preberi_glb, preberi_obj, preberi_stl, shrani
from tridim.mreza import Mreza, kvader, prizma, trianguliraj
from tridim.sestav import (Del, Kvader, deli_pokoncne, deli_precne,
                           model_ograde, model_pokoncne, model_precne)

__all__ = [
    "Mreza", "kvader", "prizma", "trianguliraj",
    "shrani", "preberi_stl", "preberi_obj", "preberi_glb", "PISALNIKI",
    "Kvader", "Del", "deli_pokoncne", "deli_precne",
    "model_pokoncne", "model_precne", "model_ograde", "step",
]


def __getattr__(ime: str) -> Any:
    """``tridim.step`` se uvozi šele ob uporabi (cadquery je neobvezen)."""
    if ime == "step":
        return importlib.import_module("tridim.step")
    raise AttributeError(f"modul 'tridim' nima atributa {ime!r}")
