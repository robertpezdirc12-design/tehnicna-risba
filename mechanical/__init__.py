# -*- coding: utf-8 -*-
"""Mehansko katalogsko jedro (F0/F1) — aditivno, brez povezave z ograjno kodo.

Javni API (terminologija docs/f1-specifikacija.md):

- :func:`razresi` (``resolve``) — katalog resolver: dimenzije + provenenca,
  napake brez ugibanja, strogo ločena profila ``iso`` / ``legacy_din``;
- :func:`izpelji_bom` (``derive_bom``) — izpeljava BOM iz sestava in delov;
- :func:`preveri` (``validate``) — kontrola dokumenta (popolnost, reference,
  standardi, enote, gating) s poročilom v JSON ali berljivi obliki.

Katalogske vrstice: ``mechanical/catalog/*.yaml`` (s provenenco).
Primer dokumenta: ``mechanical/examples/vijacnik.yaml``.

Fasada nalaga podmodule šele ob prvi uporabi (PEP 562), da ``python -m
mechanical.kontrola`` / ``python -m mechanical.resolver`` ne izvajata
modulov dvakrat.
"""
import importlib

__all__ = [
    "KOREN_KATALOGA", "PROFILI",
    "NapakaKataloga", "NeznanProfil", "NeznanStandard", "ManjkajocaVarianta",
    "NapakaBOM",
    "nalozi_katalog", "razresi", "resolve",
    "izpelji_bom", "derive_bom",
    "nalozi_dokument", "preveri", "validate", "pripis_clovek",
]

_VIRI = {
    "KOREN_KATALOGA": "resolver", "PROFILI": "resolver",
    "NapakaKataloga": "resolver", "NeznanProfil": "resolver",
    "NeznanStandard": "resolver", "ManjkajocaVarianta": "resolver",
    "nalozi_katalog": "resolver", "razresi": "resolver", "resolve": "resolver",
    "NapakaBOM": "bom", "izpelji_bom": "bom", "derive_bom": "bom",
    "nalozi_dokument": "kontrola", "preveri": "kontrola",
    "validate": "kontrola", "pripis_clovek": "kontrola",
}


def __getattr__(ime):
    """Leni uvoz javnih imen iz podmodulov (PEP 562)."""
    if ime in _VIRI:
        return getattr(importlib.import_module("." + _VIRI[ime], __name__), ime)
    raise AttributeError("module %r nima atributa %r" % (__name__, ime))


def __dir__():
    return sorted(set(globals()) | set(__all__))