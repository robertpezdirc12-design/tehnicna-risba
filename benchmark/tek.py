# -*- coding: utf-8 -*-
"""CLI ocenjevalnika: izvedba serije in primerjava dveh rezultatov.

Zagon (agent je poljuben ukaz; ocenjevalnik ne kliče modelov sam):

    python -m benchmark.tek --seznam
    python -m benchmark.tek \\
        --agent "python -m benchmark.ponarejeni_agent --nacin ok" \\
        --ponovitve 3 --izhod rezultati.json
    python -m benchmark.tek --primerjaj a.json b.json

Pravila: zrno je obvezno za ponovljivost; vsaka ponovitev je zabeležena;
povzetek navaja pass@k, interval zaupanja in število onesnaženih nalog.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from . import naloge as modul_nalog
from . import ocenjevanje, statistika
from .model import ONESNAZENO, RESEN, RezultatNaloge, RezultatSerije

KOREN = pathlib.Path(__file__).resolve().parent
PRIVZETE_NALOGE = KOREN / "naloge"


def _preberi(pot: pathlib.Path) -> dict[str, Any]:
    try:
        podatek = json.loads(pot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"rezultata ni mogoče prebrati ({pot}): {e}")
    if not isinstance(podatek, dict):
        raise SystemExit(f"{pot}: pričakovan je bil objekt")
    return podatek


def _delez_po_nalogi(serije: list[dict[str, Any]]) -> dict[str, float]:
    """Delež uspešnih ponovitev za vsako nalogo (uredjeno po id)."""
    zbirka: dict[str, list[float]] = {}
    for serija in serije:
        for rez in serija.get("rezultati") or []:
            ime = str(rez.get("naloga", ""))
            zbirka.setdefault(ime, []).append(1.0 if rez.get("uspesna") else 0.0)
    return {ime: sum(v) / len(v) for ime, v in sorted(zbirka.items())}


def povzetek(podatek: dict[str, Any]) -> dict[str, Any]:
    """Izračuna povzetek serije: deleži, pass@k, zaupanje, onesnaženje."""
    serije = podatek.get("serije") or []
    ponovitve = int(podatek.get("ponovitve") or len(serije) or 1)
    vsi: list[RezultatNaloge] = []
    po_nalogi: dict[str, list[bool]] = {}
    for serija in serije:
        for rez in serija.get("rezultati") or []:
            objekt = RezultatNaloge.iz_slovarja(rez)
            vsi.append(objekt)
            po_nalogi.setdefault(objekt.naloga, []).append(objekt.uspesna)

    uspesnih = sum(1 for r in vsi if r.status == RESEN)
    onesnazenih = sum(1 for r in vsi if r.status == ONESNAZENO)
    spodnja, zgornja = statistika.wilson_interval(uspesnih, len(vsi)) \
        if vsi else (0.0, 1.0)
    # pass@k: pri enaki k in n na vseh nalogah je dovolj povprečje (n, c)
    pari = [(len(v), sum(1 for x in v if x)) for v in po_nalogi.values()]
    pass_k = statistika.povprecni_pass_at_k(
        pari, min(ponovitve, min((n for n, _c in pari), default=1))) if pari else 0.0
    return {
        "agent": podatek.get("agent"),
        "zrno": podatek.get("zrno"),
        "ponovitve": ponovitve,
        "stevilo_izvedb": len(vsi),
        "uspesnih": uspesnih,
        "delez": (uspesnih / len(vsi)) if vsi else 0.0,
        "delez_ci_95": [round(spodnja, 4), round(zgornja, 4)],
        "pass_at_k": round(pass_k, 4),
        "k": min(ponovitve, min((n for n, _c in pari), default=1)) if pari else 0,
        "onesnazenih": onesnazenih,
        "po_nalogi": {ime: round(sum(v) / len(v), 4)
                      for ime, v in sorted(po_nalogi.items())},
    }


def izvedi(
    agent: str, ponovitve: int, zrno: int, koren_nalog: pathlib.Path,
    izhod: pathlib.Path | None, cas_agent: float | None,
) -> dict[str, Any]:
    vsi = modul_nalog.nalozi_vse(koren_nalog)
    ukaz = ocenjevanje.razcleni_ukaz(agent)
    serije: list[RezultatSerije] = []
    for ponovitev in range(1, ponovitve + 1):
        serija = RezultatSerije(agent=agent, ponovitev=ponovitev,
                                zrno=zrno + ponovitev - 1)
        for naloga in vsi:
            print(f"[{ponovitev}/{ponovitve}] {naloga.id} ... ",
                  end="", flush=True)
            rez = ocenjevanje.izvedi_nalogo(
                naloga, ukaz, koren_nalog, cas_agent_s=cas_agent)
            serija.rezultati.append(rez)
            print(f"{rez.status}"
                  + (f" ({rez.sporočilo})" if rez.sporočilo else ""))
        serije.append(serija)

    podatek: dict[str, Any] = {
        "agent": agent,
        "zrno": zrno,
        "ponovitve": ponovitve,
        "naloge": [n.id for n in vsi],
        "serije": [s.v_slovar() for s in serije],
    }
    podatek["povzetek"] = povzetek(podatek)
    if izhod is not None:
        izhod.write_text(
            json.dumps(podatek, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nZapisano: {izhod}")
    return podatek


def primerjaj(pot_a: pathlib.Path, pot_b: pathlib.Path, zrno: int) -> None:
    a = _preberi(pot_a)
    b = _preberi(pot_b)
    delez_a = _delez_po_nalogi(a.get("serije") or [])
    delez_b = _delez_po_nalogi(b.get("serije") or [])
    skupne = sorted(set(delez_a) & set(delez_b))
    if not skupne:
        raise SystemExit("seriji nimata skupnih nalog — primerjava ni mogoča")
    if set(delez_a) != set(delez_b):
        print("Opozorilo: seriji se razlikujeta v naboru nalog; "
              f"primerjam le {len(skupne)} skupnih.", file=sys.stderr)
    xa = [delez_a[i] for i in skupne]
    xb = [delez_b[i] for i in skupne]
    spodnja, zgornja, ocena = statistika.bootstrap_razlika(xa, xb, zrno=zrno)
    p_znak = statistika.znakovni_test(xa, xb, zrno=zrno)
    samo_a = sum(1 for x, y in zip(xa, xb) if x > y)
    samo_b = sum(1 for x, y in zip(xa, xb) if y > x)
    p_mc = statistika.mcnemar_exact(samo_a, samo_b) if (
        all(x in (0.0, 1.0) for x in xa) and all(x in (0.0, 1.0) for x in xb)
    ) else float("nan")
    print(f"A: {a.get('agent')}")
    print(f"B: {b.get('agent')}")
    print(f"skupnih nalog: {len(skupne)}")
    print(f"uspeh A: {sum(xa) / len(xa):.3f}   uspeh B: {sum(xb) / len(xb):.3f}")
    print(f"razlika B - A: {ocena:+.3f}  "
          f"95 % CI [{spodnja:+.3f}, {zgornja:+.3f}]")
    print(f"p (znakovni test): {p_znak:.4f}")
    if p_mc == p_mc:  # ni NaN
        print(f"p (McNemar): {p_mc:.4f}")
    bolje = "B" if ocena > 0 else "A" if ocena < 0 else "nihče"
    zanesljivo = spodnja > 0 or zgornja < 0
    print(f">> bolje: {bolje}"
          + (" (interval zaupanja ne vsebuje 0)" if zanesljivo
             else " (interval zaupanja vsebuje 0 — razlika ni dokazana)"))


def main(argv: list[str] | None = None) -> int:
    razclenjevalnik = argparse.ArgumentParser(
        description="Skriptni ocenjevalnik kodiranja (brez AI-žirije).")
    razclenjevalnik.add_argument("--naloge", type=pathlib.Path,
                                default=PRIVZETE_NALOGE)
    razclenjevalnik.add_argument(
        "--agent", help="predloga ukaza agenta; {prostor}, {poziv}, {naloga}")
    razclenjevalnik.add_argument("--ponovitve", type=int, default=1)
    razclenjevalnik.add_argument("--zrno", type=int, default=42)
    razclenjevalnik.add_argument("--cas-agenta", type=float, default=None,
                                help="omejitev časa agenta v sekundah")
    razclenjevalnik.add_argument("--izhod", type=pathlib.Path, default=None)
    razclenjevalnik.add_argument("--seznam", action="store_true",
                                help="izpiši naloge in končaj")
    razclenjevalnik.add_argument("--primerjaj", nargs=2,
                                type=pathlib.Path, metavar=("A", "B"))
    argumenti = razclenjevalnik.parse_args(argv)

    if argumenti.seznam:
        for naloga in modul_nalog.nalozi_vse(argumenti.naloge):
            prva = naloga.opis.strip().splitlines()[0]
            print(f"{naloga.id:20s} cilj={len(naloga.fail_to_pass)} "
                  f"zascita={len(naloga.pass_to_pass)}  {prva}")
        return 0
    if argumenti.primerjaj:
        primerjaj(argumenti.primerjaj[0], argumenti.primerjaj[1], argumenti.zrno)
        return 0
    if not argumenti.agent:
        razclenjevalnik.error("podaj --agent, --seznam ali --primerjaj")
    if argumenti.ponovitve <= 0:
        razclenjevalnik.error("--ponovitve mora biti pozitivno")

    podatek = izvedi(argumenti.agent, argumenti.ponovitve, argumenti.zrno,
                     argumenti.naloge, argumenti.izhod, argumenti.cas_agenta)
    p = podatek["povzetek"]
    print(f"\nuspeh: {p['uspesnih']}/{p['stevilo_izvedb']} "
          f"({p['delez']:.1%}), 95 % CI "
          f"[{p['delez_ci_95'][0]:.1%}, {p['delez_ci_95'][1]:.1%}]")
    print(f"pass@{p['k']}: {p['pass_at_k']:.3f}   "
          f"onesnaženo: {p['onesnazenih']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
