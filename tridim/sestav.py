# -*- coding: utf-8 -*-
"""Sestav 3D modela ograje iz obstoječih mer (en vir resnice: ``jedro``).

Model vsebuje natanko tiste dele, ki jih našteje tudi kosovnica risbe:
stebre, deske, ročaj in (pri pritrditvi »vrh«) osnovne plošče. Vijakov,
sidr in nosilcev za deske **ne modeliramo** — zanje v risbi ni
prostorskih podatkov; izmišljene lege bi bile laž.

Globinski odmiki med deli prav tako niso modelirani: 2D risba jih ne
poda, zato so vsi deli izstisnjeni iz ravnine y = 0. To je zapisano v
``opombe`` vsakega modela, da uporabnik ve, kaj model je in česa ni.

Geometrija je opisana kot seznam kvadrov (:class:`Kvader`), ker so vsi
deli ograje pravokotni profili. Isti opis uporablja mrežni izvoz
(STL/OBJ/GLB) in neobvezni BREP izvoz (STEP prek cadqueryja).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import jedro
from tridim.mreza import Mreza, kvader

_OSNOVA_VZOREC = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_DEBELINA_VZOREC = re.compile(r"(\d+(?:[.,]\d+)?)\s*mm")


@dataclass(frozen=True)
class Kvader:
    """Pravokotni del: ime + izhodišče + dimenzije (vse v mm)."""

    ime: str
    x0: float
    y0: float
    z0: float
    dx: float
    dy: float
    dz: float

    def v_mrezo(self) -> Mreza:
        return kvader(self.x0, self.y0, self.z0, self.dx, self.dy, self.dz)


@dataclass(frozen=True)
class Del:
    """En kos modela z imenom, ki ga je mogoče povezati s kosovnico."""

    ime: str
    mreza: Mreza


def _osnova(vrednost: str) -> tuple[float, float, float] | None:
    """Razbere »90×90×6« v (a, b, debelina); nečitljivo vrne None."""
    zadetek = _OSNOVA_VZOREC.search(str(vrednost or ""))
    if not zadetek:
        return None
    try:
        a, b, t = (float(z.replace(",", ".")) for z in zadetek.groups())
    except ValueError:
        return None
    if min(a, b, t) <= 0:
        return None
    return a, b, t


def _debelina_rocaja(cfg: dict[str, Any]) -> float:
    """Debelina ročaja: iz naziva profila, sicer debelina stebra."""
    mere = cfg.get("mere") or {}
    for vir in (cfg.get("rocaj_dim"), cfg.get("osnova_dim")):
        if vir:
            zadetek = _DEBELINA_VZOREC.search(str(vir))
            if zadetek:
                vrednost = float(zadetek.group(1).replace(",", "."))
                if 5.0 <= vrednost <= 200.0:
                    return vrednost
    return float(mere.get("steber_debelina") or 60.0)


PREDLOGE = ("pokončna", "pokoncna")


def _preveri_predlogo(cfg: dict[str, Any]) -> None:
    """Prečna predloga ima drugačno geometrijo — ne ugibamo je."""
    predloga = str(cfg.get("predloga") or "").strip().lower()
    if predloga not in PREDLOGE:
        raise ValueError(
            f"3D izvoz je za zdaj samo za predlogo »pokončna« "
            f"(prejeta: {predloga or 'prazna'!r}). Za prečno ograjo "
            "uporabi 3D predogled v GUI (tridimenzionalno.py); izvoz "
            "prečne predloge bi zahteval ločen sestav.")


def deli_pokoncne(cfg: dict[str, Any]) -> dict[str, Any]:
    """Vrne kvadre, opombe in povzetek mer za pokončno ograjo."""
    _preveri_predlogo(cfg)
    mere = cfg["mere"]
    sirina = float(mere["sirina"])
    visina = float(mere["visina"])
    ss = float(mere["steber_sirina"])
    sd = float(mere.get("steber_debelina") or ss)
    ds = float(mere["deska_sirina"])
    dd = float(mere.get("deska_debelina") or mere.get("debelina") or 20.0)

    razpored = jedro.razpored_pokoncna(mere)
    kvadri: list[Kvader] = []

    for i, cx in enumerate(razpored["centri"], start=1):
        kvadri.append(Kvader(f"steber S{i}", cx - ss / 2, 0.0, 0.0,
                             ss, sd, visina))

    z0, z1 = razpored["deske_z"]
    for i, x in enumerate(razpored["deske_x"], start=1):
        kvadri.append(Kvader(f"deska D{i}", x, 0.0, z0, ds, dd, z1 - z0))

    rocaj_od, rocaj_do = razpored["rocaj"]
    kvadri.append(Kvader("rocaj", 0.0, 0.0, rocaj_od, sirina,
                         _debelina_rocaja(cfg), rocaj_do - rocaj_od))

    opombe: list[str] = [
        "Mreza je masni model: globinski odmiki med deli niso modelirani "
        "(2D risba jih ne poda), zato so vsi deli izstisnjeni iz y = 0.",
        "Vijaki, sidra in nosilci desk niso modelirani — zanje ni "
        "prostorskih podatkov; kolicine so v kosovnici, ne v 3D.",
    ]
    if float(mere.get("globina") or 0.0) > 0.0:
        opombe.append(
            "Stranski segment (globina > 0) ni modeliran: model je en "
            "raven odsek. 3D predogled v GUI (tridimenzionalno.py) "
            "prikaze se stranski krak v L-obliki.")

    if str(cfg.get("pritrditev") or "").lower() == "vrh":
        osnova = _osnova(cfg.get("osnova_dim") or "90×90×6")
        if osnova is None:
            opombe.append("Osnovna plosca ni modelirana: mere osnove niso "
                          "berljive (pricakovano npr. 90×90×6).")
        else:
            a, b, t = osnova
            for i, cx in enumerate(razpored["centri"], start=1):
                kvadri.append(Kvader(f"osnova O{i}", cx - a / 2, 0.0, visina,
                                     a, b, t))
    else:
        opombe.append("Osnovne plosce niso modelirane: pritrditev ni »vrh«.")

    return {
        "kvadri": kvadri,
        "opombe": opombe,
        "mere": {
            "sirina": sirina, "visina": visina,
            "stebrov": len(razpored["centri"]),
            "desk": len(razpored["deske_x"]),
            "deska_h": round(razpored["deske_h"], 3),
        },
    }


def model_pokoncne(cfg: dict[str, Any]) -> dict[str, Any]:
    """Zgradi mrežni 3D model pokončne ograje.

    Vrne dict: ``mreza`` (združena), ``deli`` (seznam :class:`Del`),
    ``opombe`` in ``mere`` (povzetek z izračunano prostornino).
    """
    podatki = deli_pokoncne(cfg)
    kvadri: list[Kvader] = podatki["kvadri"]
    deli = [Del(k.ime, k.v_mrezo()) for k in kvadri]
    mreza = deli[0].mreza.zdruzi(*(d.mreza for d in deli[1:]))
    mere = dict(podatki["mere"])
    mere["prostornina_mm3"] = round(mreza.prostornina(), 1)
    mere["povrsina_mm2"] = round(mreza.povrsina(), 1)
    return {"mreza": mreza, "deli": deli, "opombe": podatki["opombe"],
            "mere": mere}
