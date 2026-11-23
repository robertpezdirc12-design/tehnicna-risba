# -*- coding: utf-8 -*-
"""Skriptni ocenjevalnik kodiranja — BREZ modela v zanki.

Zakaj brez AI-žirije: sodba o kakovosti kode je merljiva z izvajanjem
testov. Vsak rezultat je ponovljiv, strojno preverljiv in sledljiv —
brez subjektivne ocene, brez pristranskosti ocenjevalca.

Vzorec po javnih praksah (glej docs/benchmark-modelov.md):
- SWE-bench: popravek se uporabi na pripeti različici, nato se zaženejo
  FAIL_TO_PASS in PASS_TO_PASS testi; uspeh = oboji padejo skozi.
- Aider polyglot: testi, ki jih model NE vidi; omejitev časa = neuspeh.
- Chen idr. (HumanEval): nepristranski pass@k = 1 - C(n-c,k)/C(n,k).
- Primerjava dveh modelov: McNemar (parni) + bootstrap interval zaupanja.
- Preprečevanje uhajanja: canary žetoni v skritih testih/ rešitvi.

Moduli:
    model       podatkovni razredi (Naloga, RezultatNaloge, ...)
    naloge      nalaganje in preverjanje YAML definicij nalog
    ocenjevanje izvedba naloge v izoliranem prostoru + ocena
    statistika  pass@k, Wilson, bootstrap, McNemar, znakovni test
    tek         CLI: izvedba serije, primerjava dveh rezultatov
"""

from __future__ import annotations

__all__ = [
    "model",
    "naloge",
    "ocenjevanje",
    "statistika",
    "tek",
]
