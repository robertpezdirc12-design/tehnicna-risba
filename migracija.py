"""YAML shema projekta: v2 + migracija iz v1 (issue #3).

Shema v1 (do vključno issue #2):
- en sam segment (``mere``), brez oznake sheme
- brez vrat/prehodov/segmentov

Shema v2:
- ključ ``shema: 2``
- ``segmenti``: seznam {ime, tip, mere, kot, vrata, prehodi} — vsak segment
  ima lahko lastne mere, vrata in prehode; kot je vogal med segmenti
- ``vrata``/``prehodi`` na nivoju projekta ostajata veljavna (en segment)

Načela:
- migracija NE piše nazaj v izvirno datoteko (nalaganje je brez posledic);
  shranjevanje je eksplicitno dejanje
- migracija je IDEMPOTENTNA
- neznana polja se OHRANIJO (round-trip brez izgube)
- v1 datoteke se prepoznajo samodejno (brez ``shema`` = v1)
"""
from __future__ import annotations

import copy
import os

import yaml

SHEMA_TRENUTNA = 2
SHEME = (1, 2)


def prepoznaj_shemo(cfg):
    """Vrne različico sheme (brez ključa ``shema`` = 1)."""
    if not isinstance(cfg, dict):
        raise ValueError("Projekt mora biti slika (YAML ključ: vrednost).")
    v = cfg.get("shema", 1)
    try:
        v = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"Neveljavna oznaka sheme: {v!r}")
    if v not in SHEME:
        raise ValueError(f"Neznana shema {v} (podprti: {', '.join(map(str, SHEME))})")
    return v


def migriraj_shemo(cfg):
    """Vrne NOVO strukturo v shemi v2 (vhod se ne mutira).

    Shema v2 doda ``shema: 2`` in ``segmenti``; vse obstoječe ključe in
    vrednosti ohrani dobesedno. Klic je idempotenten.
    """
    if not isinstance(cfg, dict):
        raise ValueError("Projekt mora biti slika (YAML ključ: vrednost).")
    prepoznaj_shemo(cfg)
    nov = copy.deepcopy(cfg)
    nov["shema"] = SHEMA_TRENUTNA
    if not nov.get("segmenti"):
        # v1 ekvivalent: en segment iz obstoječih polj (nespremenjenih)
        nov["segmenti"] = [{
            "ime": "Glavni",
            "tip": nov.get("predloga") or "ograja",
            "mere": copy.deepcopy(nov.get("mere") or {}),
            "kot": 0.0,
            "vrata": copy.deepcopy(nov.get("vrata") or []),
            "prehodi": copy.deepcopy(nov.get("prehodi") or []),
        }]
    else:
        if not isinstance(nov["segmenti"], list):
            raise ValueError("'segmenti' mora biti seznam segmentov.")
        for i, s in enumerate(nov["segmenti"], start=1):
            if not isinstance(s, dict):
                raise ValueError(f"Segment {i} mora biti slika.")
            s.setdefault("ime", f"S{i}")
            s.setdefault("tip", nov.get("predloga") or "ograja")
            s.setdefault("mere", {})
            s.setdefault("kot", 0.0)
            s.setdefault("vrata", [])
            s.setdefault("prehodi", [])
    return nov


def nalozi_projekt(pot):
    """Naloži projekt (v1 ali v2) in vrne strukturo v shemi v2.

    Izvirne datoteke NE spreminja.
    """
    if not os.path.exists(pot):
        raise ValueError(f"Projektna datoteka ne obstaja: {pot}")
    with open(pot, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("Projektna datoteka mora vsebovati sliko (ključ: vrednost).")
    return migriraj_shemo(cfg)


def shrani_projekt(cfg, pot):
    """Shrani projekt v shemi v2 (varno: začasna datoteka + os.replace)."""
    nov = migriraj_shemo(cfg)
    d = os.path.dirname(os.path.abspath(pot))
    os.makedirs(d, exist_ok=True)
    tmp = pot + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(nov, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, pot)
    return pot