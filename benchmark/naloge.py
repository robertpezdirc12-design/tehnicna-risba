# -*- coding: utf-8 -*-
"""Nalaganje in preverjanje definicij nalog (YAML).

Pravila, ki jih preverjanje vsili (in zakaj):
- ``fail_to_pass`` ne sme biti prazen — naloga brez merljivega cilja ni
  naloga (SWE-bench: FAIL_TO_PASS mora obstajati).
- ``pass_to_pass`` je lahko prazen, a če ni, ščiti pred regresijami.
- ``canary`` je neobvezen, a priporočen: prestreže uhajanje rešitve.
- Neznana polja so NAPAKA (ne tiho ignoriranje) — napačno črkovano polje
  bi sicer pomenilo, da se omejitev ne uporabi.
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml

from .model import Naloga

OBVEZNA_POLJA = ("id", "opis", "predloga", "fail_to_pass")
ZNANA_POLJA = OBVEZNA_POLJA + (
    "pass_to_pass", "cas_s", "canary", "ukaz_testov", "opombe",
)


class NapakaNaloge(ValueError):
    """Definicija naloge je neveljavna."""


def _besedilo(podatek: dict[str, Any], ime: str, kje: str) -> str:
    vrednost = podatek.get(ime)
    if not isinstance(vrednost, str) or not vrednost.strip():
        raise NapakaNaloge(f"{kje}: polje {ime!r} mora biti neprazno besedilo")
    return vrednost.strip()


def _seznam(podatek: dict[str, Any], ime: str, kje: str) -> tuple[str, ...]:
    vrednost = podatek.get(ime)
    if vrednost is None:
        return ()
    if not isinstance(vrednost, list) or not all(
        isinstance(v, str) and v.strip() for v in vrednost
    ):
        raise NapakaNaloge(
            f"{kje}: polje {ime!r} mora biti seznam nepraznih besedil")
    return tuple(v.strip() for v in vrednost)


def nalozi_nalogo(pot: str | pathlib.Path) -> Naloga:
    """Naloži in preveri eno YAML definicijo naloge."""
    mapa = pathlib.Path(pot)
    if not mapa.is_file():
        raise NapakaNaloge(f"datoteka ne obstaja: {mapa}")
    try:
        podatek = yaml.safe_load(mapa.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise NapakaNaloge(f"{mapa}: neveljaven YAML: {e}") from e
    if not isinstance(podatek, dict):
        raise NapakaNaloge(f"{mapa}: vsebina mora biti slovar")

    kje = mapa.name
    neznana = set(podatek) - set(ZNANA_POLJA)
    if neznana:
        raise NapakaNaloge(
            f"{kje}: neznana polja {sorted(neznana)} — dovoljena: "
            f"{list(ZNANA_POLJA)}")
    manjkajoca = [p for p in OBVEZNA_POLJA if p not in podatek]
    if manjkajoca:
        raise NapakaNaloge(f"{kje}: manjkajo polja {manjkajoca}")

    fail_to_pass = _seznam(podatek, "fail_to_pass", kje)
    if not fail_to_pass:
        raise NapakaNaloge(
            f"{kje}: 'fail_to_pass' ne sme biti prazen — naloga brez "
            "merljivega cilja ni merljiva")
    pass_to_pass = _seznam(podatek, "pass_to_pass", kje)
    podvojeni = set(fail_to_pass) & set(pass_to_pass)
    if podvojeni:
        raise NapakaNaloge(
            f"{kje}: testi v obeh seznamih {sorted(podvojeni)} — "
            "isti test ne more biti hkrati cilj in zaščita")

    cas = podatek.get("cas_s", 120.0)
    if not isinstance(cas, (int, float)) or isinstance(cas, bool) or cas <= 0:
        raise NapakaNaloge(f"{kje}: 'cas_s' mora biti pozitivno število")

    return Naloga(
        id=_besedilo(podatek, "id", kje),
        opis=_besedilo(podatek, "opis", kje),
        predloga=_besedilo(podatek, "predloga", kje),
        fail_to_pass=fail_to_pass,
        pass_to_pass=pass_to_pass,
        cas_s=float(cas),
        canary=_seznam(podatek, "canary", kje),
        ukaz_testov=_seznam(podatek, "ukaz_testov", kje),
        opombe=str(podatek.get("opombe") or ""),
    )


def nalozi_vse(koren: str | pathlib.Path) -> list[Naloga]:
    """Naloži vse naloge iz imenika (vsak podimenik = ena naloga).

    Vrstni red je determinističen (urejeno po poti), da so zrna in
    ponovitve ponovljive.
    """
    osnova = pathlib.Path(koren)
    if not osnova.is_dir():
        raise NapakaNaloge(f"imenik nalog ne obstaja: {osnova}")
    naloge: list[Naloga] = []
    for mapa in sorted(p for p in osnova.iterdir() if p.is_dir()):
        datoteka = mapa / "task.yaml"
        if datoteka.is_file():
            naloge.append(nalozi_nalogo(datoteka))
    if not naloge:
        raise NapakaNaloge(f"v {osnova} ni nobene naloge (task.yaml)")
    ids = [n.id for n in naloge]
    if len(set(ids)) != len(ids):
        raise NapakaNaloge(f"podvojeni id nalog: {ids}")
    return naloge
