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


PREDLOGE_PRECNE = ("ograja", "prečna", "precna")


def _je_precna(cfg: dict[str, Any]) -> bool:
    return str(cfg.get("predloga") or "").strip().lower() in PREDLOGE_PRECNE


def deli_precne(cfg: dict[str, Any]) -> dict[str, Any]:
    """Kvadri, opombe in mere za prečno ograjo (vodoravne lamele).

    Geometrija je enaka kot v shematskem predogledu
    (``tridimenzionalno.py``): lamele med profiloma, nosilci za lamelami,
    okvirji odprtin in (pri globini > 0) stranski krak v L-obliki.
    Tla iz predogleda **niso** del modela — so le orientacija.
    """
    mere = cfg["mere"]
    sirina = float(mere["sirina"])
    visina = float(mere["visina"])
    odcep = float(mere.get("odcep") or 0.0)
    globina = float(mere.get("globina") or 0.0)
    deb = float(mere.get("debelina") or 20.0)
    razmak_nos = float(mere.get("razmak_nosilcev") or 1000.0)

    zg, sp, lamele, _vrzel, _n = jedro.razpored(mere)
    vp = jedro.vrata_podatki(cfg)
    odprtine = vp["odprtine"]
    kvadri: list[Kvader] = []

    def razdeli(x0: float, x1: float) -> list[tuple[float, float]]:
        return jedro.razdeli_po_odprtinah(x0, x1, odprtine)

    for i, (z0, z1) in enumerate(lamele, start=1):
        for j, (a, b) in enumerate(razdeli(0.0, sirina), start=1):
            kvadri.append(Kvader(f"lamela L{i}.{j}", a, -deb / 2, z0,
                                 b - a, deb, z1 - z0))

    for ime, (z0, z1) in (("profil zgoraj", zg), ("profil spodaj", sp)):
        for j, (a, b) in enumerate(razdeli(0.0, sirina), start=1):
            kvadri.append(Kvader(f"{ime} {j}", a, -40.0, z0,
                                 b - a, 80.0, z1 - z0))

    pozicije, _dejanski = jedro.pozicije_nosilcev(sirina, razmak_nos)
    for i, x in enumerate(pozicije, start=1):
        if any(o[0] - 30.0 <= x <= o[1] + 30.0 for o in odprtine):
            continue
        glob_nosilca = 80.0 - deb / 2
        if glob_nosilca <= 0:              # debela lamela: nosilec ne obstaja
            continue
        kvadri.append(Kvader(f"nosilec N{i}", x - 30.0, -80.0, sp[0],
                             60.0, glob_nosilca, zg[1] - sp[0]))

    for oznaka, z0, z1 in [(o[2], odcep, odcep + 2000.0) for o in odprtine]:
        vis_o = z1
        for enota in vp["vrata"] + vp["prehodi"]:
            if enota.get("oznaka") == oznaka:
                vis_o = odcep + float(enota["g"]["odprtina"]["visina"])
        ox0, ox1 = next((o[0], o[1]) for o in odprtine if o[2] == oznaka)
        kvadri.append(Kvader(f"okvir {oznaka} levo", ox0, -70.0, z0,
                             60.0, 20.0, vis_o - z0))
        kvadri.append(Kvader(f"okvir {oznaka} desno", ox1 - 60.0, -70.0, z0,
                             60.0, 20.0, vis_o - z0))
        kvadri.append(Kvader(f"okvir {oznaka} precka", ox0, -70.0,
                             vis_o - 60.0, ox1 - ox0, 20.0, 60.0))

    opombe: list[str] = [
        "Tla iz 3D predogleda niso del modela — v predogledu so le "
        "orientacija.",
        "Vijaki, sidra in pritrdila niso modelirani — kolicine so v "
        "kosovnici, ne v 3D.",
    ]

    if globina > 0:
        # stranski krak: iste lamele in profili, le vzdolz y (kot predogled)
        for i, (z0, z1) in enumerate(lamele, start=1):
            kvadri.append(Kvader(f"stranska lamela SL{i}", -deb / 2, 0.0,
                                 z0, deb, globina, z1 - z0))
        for ime, (z0, z1) in (("stranski profil zgoraj", zg),
                              ("stranski profil spodaj", sp)):
            kvadri.append(Kvader(ime, -40.0, 0.0, z0, 80.0, globina,
                                 z1 - z0))
        steber_z0 = max(0.0, odcep - 40.0)
        for k, ys in enumerate((0.0, globina), start=1):
            kvadri.append(Kvader(f"stranski steber SS{k}", -40.0,
                                 max(0.0, ys - 30.0), steber_z0, 80.0, 60.0,
                                 visina - steber_z0))
    else:
        opombe.append("Stranski krak ni modeliran: globina je 0.")

    return {
        "kvadri": kvadri,
        "opombe": opombe,
        "mere": {
            "sirina": sirina, "visina": visina,
            "lamel": len(lamele),
            "odprtin": len(odprtine),
            "globina": globina,
        },
    }


def model_pokoncne(cfg: dict[str, Any]) -> dict[str, Any]:
    """Zgradi mrežni 3D model pokončne ograje.

    Vrne dict: ``mreza`` (združena), ``deli`` (seznam :class:`Del`),
    ``opombe`` in ``mere`` (povzetek z izračunano prostornino).
    """
    return _sestavi(deli_pokoncne(cfg))


def model_precne(cfg: dict[str, Any]) -> dict[str, Any]:
    """Zgradi mrežni 3D model prečne ograje (vodoravne lamele)."""
    return _sestavi(deli_precne(cfg))


def model_ograde(cfg: dict[str, Any]) -> dict[str, Any]:
    """Izbere sestav po predlogi konfiguracije (pokončna / prečna)."""
    if _je_precna(cfg):
        return model_precne(cfg)
    if str(cfg.get("predloga") or "").strip().lower() in PREDLOGE:
        return model_pokoncne(cfg)
    raise ValueError(
        f"neznana predloga {cfg.get('predloga')!r} "
        f"(podprto: {', '.join(PREDLOGE + PREDLOGE_PRECNE)})")


def _sestavi(podatki: dict[str, Any]) -> dict[str, Any]:
    """Skupna pot: kvadri → mreže → združena mreža + povzetek."""
    kvadri: list[Kvader] = podatki["kvadri"]
    if not kvadri:
        raise ValueError("model nima nobenega dela")
    deli = [Del(k.ime, k.v_mrezo()) for k in kvadri]
    mreza = deli[0].mreza.zdruzi(*(d.mreza for d in deli[1:]))
    mere = dict(podatki["mere"])
    mere["prostornina_mm3"] = round(mreza.prostornina(), 1)
    mere["povrsina_mm2"] = round(mreza.povrsina(), 1)
    return {"mreza": mreza, "deli": deli, "opombe": podatki["opombe"],
            "mere": mere}
