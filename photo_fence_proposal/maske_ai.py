# -*- coding: utf-8 -*-
"""Maske elementov iz zunanjega AI orodja (Grounded SAM 2) — varnostni sloj.

AI NI del izdelka in ni odvisnost: program zna prebrati **datoteko z
maskami** (JSON), ki jo ustvari ločeno orodje, in iz nje **deterministično**
prešteti elemente. Če datoteke ni, se nič ne spremeni.

Zakaj tako:

- uteži + torch so ~1 GB in se ne dobavljajo z MIT izdelkom;
- AI maska ni mera, zato ne sme dvigniti statusa (`izmerjeno`/`izracunano`)
  — lahko le POTRDI naše štetje (dve neodvisni metodi se ujemata) ali
  sproži opozorilo, ko se ne ujemata;
- štetje iz mask je projekcija intervalov + združevanje: brez naključja,
  brez modela, ponovljivo.

Oblika datoteke (v1):

    {"vir": "grounded-sam-2", "slika": "foto.jpg",
     "sirina_px": 1800, "visina_px": 900,
     "maske": [{"oznaka": "steber", "zaupanje": 0.93,
                 "poligon": [[120, 300], [180, 300],
                              [180, 800], [120, 800]]}]}
"""
from __future__ import annotations

import json
import pathlib
import statistics
from dataclasses import dataclass

OZNAKE = ("steber", "lamela")
PRAG_ZDRIZEVANJA = 0.3     # del mediane širine: manjši razmik = isti element


@dataclass(frozen=True)
class Maska:
    """En obris elementa: oznaka + poligon v pikslih + zaupanje."""

    oznaka: str
    poligon: tuple[tuple[float, float], ...]
    zaupanje: float = 1.0


@dataclass(frozen=True)
class Maske:
    """Vse maske ene fotografije in velikost slike, na katero se nanašajo."""

    slika: str
    sirina_px: int
    visina_px: int
    maske: tuple[Maska, ...]
    vir: str = "neznan"


@dataclass(frozen=True)
class Primerjava:
    """Ali se AI maske in naše štetje ujemata (in kaj, če se ne)."""

    stevilo_maske: int
    stevilo_zaznava: int | None
    ujemanje: bool | None
    opozorila: tuple[str, ...] = ()


def preberi(pot) -> Maske:
    """Preberi in STROGO preveri datoteko z maskami (slovenske napake)."""
    pot = pathlib.Path(pot)
    try:
        with pot.open(encoding="utf-8") as f:
            podatki = json.load(f)
    except OSError as e:
        raise ValueError(
            f"Datoteke z maskami ni mogoče prebrati: {pot} ({e})") from e
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Datoteka z maskami ni veljaven JSON: {pot} ({e})") from e
    if not isinstance(podatki, dict):
        raise ValueError("Maske morajo biti objekt JSON, ne seznam.")
    for kljuc in ("slika", "sirina_px", "visina_px", "maske"):
        if kljuc not in podatki:
            raise ValueError(f"V datoteki z maskami manjka ključ {kljuc!r}.")
    try:
        sirina = int(podatki["sirina_px"])
        visina = int(podatki["visina_px"])
    except (TypeError, ValueError) as e:
        raise ValueError(
            "sirina_px in visina_px morata biti celi števili") from e
    if sirina <= 0 or visina <= 0:
        raise ValueError("sirina_px in visina_px morata biti pozitivna.")
    if not isinstance(podatki["maske"], list):
        raise ValueError("Ključ 'maske' mora biti seznam.")
    maske: list[Maska] = []
    for i, m in enumerate(podatki["maske"], 1):
        if not isinstance(m, dict):
            raise ValueError(f"Maska #{i} ni objekt JSON.")
        oznaka = m.get("oznaka")
        if oznaka not in OZNAKE:
            raise ValueError(
                f"Maska #{i}: oznaka {oznaka!r} ni znana "
                f"(dovoljeno: {', '.join(OZNAKE)}).")
        poligon = m.get("poligon")
        if not isinstance(poligon, list) or len(poligon) < 3:
            raise ValueError(
                f"Maska #{i}: poligon potrebuje vsaj 3 točke.")
        tocke: list[tuple[float, float]] = []
        for t in poligon:
            if not isinstance(t, (list, tuple)) or len(t) != 2:
                raise ValueError(
                    f"Maska #{i}: vsaka točka mora biti [x, y].")
            try:
                x, y = float(t[0]), float(t[1])
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"Maska #{i}: koordinate morajo biti števila.") from e
            if not (0 <= x <= sirina and 0 <= y <= visina):
                raise ValueError(
                    f"Maska #{i}: točka ({x:.0f}, {y:.0f}) je zunaj slike "
                    f"{sirina}×{visina} px.")
            tocke.append((x, y))
        try:
            zaupanje = float(m.get("zaupanje", 1.0))
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Maska #{i}: zaupanje mora biti število 0–1.") from e
        if not 0.0 <= zaupanje <= 1.0:
            raise ValueError(
                f"Maska #{i}: zaupanje mora biti med 0 in 1.")
        maske.append(Maska(str(oznaka), tuple(tocke), zaupanje))
    return Maske(str(podatki["slika"]), sirina, visina, tuple(maske),
                 str(podatki.get("vir", "neznan")))


def shrani(maske: Maske, pot) -> None:
    """Zapiši maske v isti obliki, kot jo bere :func:`preberi`."""
    podatki = {
        "vir": maske.vir,
        "slika": maske.slika,
        "sirina_px": int(maske.sirina_px),
        "visina_px": int(maske.visina_px),
        "maske": [{"oznaka": m.oznaka,
                    "zaupanje": round(float(m.zaupanje), 4),
                    "poligon": [[round(x, 1), round(y, 1)]
                                for x, y in m.poligon]}
                   for m in maske.maske],
    }
    pathlib.Path(pot).write_text(
        json.dumps(podatki, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


def _intervali(maske: Maske, oznaka: str, os: str = "x"):
    """(min, max) po izbrani osi za vsako masko dane oznake."""
    out = []
    i = 0 if os == "x" else 1
    for m in maske.maske:
        if m.oznaka != oznaka:
            continue
        vrednosti = [p[i] for p in m.poligon]
        out.append((min(vrednosti), max(vrednosti)))
    return out


def _zdruzi(intervali) -> int:
    """Preštej skupine prekrivajočih se intervalov (fragmenti = en element)."""
    if not intervali:
        return 0
    sirine = [b - a for a, b in intervali]
    mediana = statistics.median(sirine)
    prag = PRAG_ZDRIZEVANJA * mediana if mediana > 0 else 0.0
    urejeni = sorted(intervali)
    skupin = 1
    konec = urejeni[0][1]
    for zacetek, konec_nov in urejeni[1:]:
        if zacetek <= konec + prag:
            konec = max(konec, konec_nov)
        else:
            skupin += 1
            konec = konec_nov
    return skupin


def prestej_stebre(maske: Maske) -> int:
    """Število stebrov: stebri so navpični pasovi → intervali po X."""
    return _zdruzi(_intervali(maske, "steber", "x"))


def prestej_lamel(maske: Maske) -> int:
    """Število lamel: vodoravne deske → intervali po Y."""
    return _zdruzi(_intervali(maske, "lamela", "y"))


def primerjaj(zaznava: int | None, maske: Maske) -> Primerjava:
    """Primerjaj AI maske z našim štetjem — brez tihega prevzemanja."""
    n_m = prestej_stebre(maske)
    opozorila: list[str] = []
    if n_m == 0:
        opozorila.append(
            "V datoteki z maskami ni nobenega stebra — AI ni našel "
            "elementov; naše štetje ostane nespremenjeno.")
        return Primerjava(0, zaznava, None, tuple(opozorila))
    if zaznava is None:
        opozorila.append(
            f"AI maske kažejo {n_m} stebrov, našega štetja ni — vrednost "
            "iz mask je le ocena.")
        return Primerjava(n_m, None, None, tuple(opozorila))
    ujemanje = n_m == zaznava
    if not ujemanje:
        opozorila.append(
            f"AI maske kažejo {n_m} stebrov, naše periodično štetje "
            f"{zaznava} — metodi se ne ujemata, zato je število "
            "OCENJENO; preveri ročno (AI ni del izdelka in ni dokaz).")
    return Primerjava(n_m, zaznava, ujemanje, tuple(opozorila))
