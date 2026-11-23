# -*- coding: utf-8 -*-
"""Izvedba ene naloge in strojna ocena izida.

Tok (po SWE-bench, prilagojen za en sam model/agent):
1. delovni prostor se ustvari iz PREDLOGE (nikoli iz živega repozitorija),
2. agent dobi poziv in prostor, skritih testov še NE vidi,
3. po agentu se v prostoru poiščejo canary žetoni (uhajanje rešitve),
4. skriti testi se prekopirajo v ločen imenik in zaženejo z JUnit izhodom,
5. izid se razvrsti: uspeh zahteva FAIL_TO_PASS zelene IN PASS_TO_PASS
   nespremenjene; canary zadetek razveljavi rezultat.

Omejitev (iskreno): to NI varnostni sandbox. Nezaupanja vreden agent
lahko pobegne iz prostora; za takšne primere uporabi VM/container.
"""

from __future__ import annotations

import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from .model import (
    NAPAKA_OKOLJA,
    NI_RESEN,
    ONESNAZENO,
    POKVARJEN,
    PREKORACEN_CAS,
    RESEN,
    Naloga,
    RezultatNaloge,
)

_BINARNE_KONCNICE = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".exe", ".dll",
    ".so", ".pyc", ".db", ".sqlite", ".woff", ".woff2", ".ttf", ".mp4",
}
_PRESKOCI_MAPE = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache"}
_NAJ_VELIKOST = 2 * 1024 * 1024


def _tekstovne_datoteke(koren: pathlib.Path):
    for pot in sorted(koren.rglob("*")):
        if any(del_ in _PRESKOCI_MAPE for del_ in pot.parts):
            continue
        if not pot.is_file() or pot.suffix.lower() in _BINARNE_KONCNICE:
            continue
        try:
            if pot.stat().st_size > _NAJ_VELIKOST:
                continue
            yield pot, pot.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue


def poisci_canary(
    prostor: pathlib.Path, dodatna_besedila: list[str], canary: tuple[str, ...],
) -> list[str]:
    """Vrne canary žetone, ki so se pojavili v prostoru ali izhodu agenta.

    Namen: zaznati, da je agent prebral skrito rešitev/teste (uhajanje),
    ne da bi to vplivalo na oceno. Najdba onesnaži rezultat.
    """
    if not canary:
        return []
    zadeti: set[str] = set()
    for _pot, vsebina in _tekstovne_datoteke(prostor):
        for zeton in canary:
            if zeton in vsebina:
                zadeti.add(zeton)
    for besedilo in dodatna_besedila:
        for zeton in canary:
            if zeton in besedilo:
                zadeti.add(zeton)
    return sorted(zadeti)


def beri_junit(pot: pathlib.Path) -> dict[str, bool]:
    """Razčleni JUnit XML v preslikavo ime_testa → uspel.

    Ključi so tako ``ime`` kot ``razred::ime`` — naloge lahko navedejo
    kratko ali polno ime.
    """
    try:
        koren = ET.parse(pot).getroot()
    except (OSError, ET.ParseError) as e:
        raise ValueError(f"JUnit izhoda ni mogoče prebrati: {e}") from e
    izid: dict[str, bool] = {}
    for primer in koren.iter("testcase"):
        ime = primer.get("name") or ""
        razred = primer.get("classname") or ""
        neuspeh = any(
            otrok.tag in ("failure", "error") for otrok in primer
        )
        uspel = not neuspeh
        if ime:
            izid[ime] = uspel
            if razred:
                izid[f"{razred}::{ime}"] = uspel
    if not izid:
        raise ValueError("JUnit izhod ne vsebuje nobenega testa")
    return izid


def _pozeni(
    ukaz: list[str], cwd: pathlib.Path, cas_s: float,
    okolje: dict[str, str] | None = None,
) -> tuple[int | None, str, float, bool]:
    """Zažene ukaz; vrne (izhod, izhodno besedilo, trajanje, prekoračeno)."""
    zacetek = time.monotonic()
    try:
        dokoncan = subprocess.run(
            ukaz, cwd=str(cwd), capture_output=True, text=True,
            errors="replace", timeout=cas_s, env=okolje,
        )
    except subprocess.TimeoutExpired as e:
        trajanje = time.monotonic() - zacetek
        delno = ""
        if isinstance(e.stdout, str):
            delno += e.stdout
        if isinstance(e.stderr, str):
            delno += e.stderr
        return (None, delno, trajanje, True)
    except OSError as e:
        return (None, f"ukaza ni mogoče zagnati: {e}",
                time.monotonic() - zacetek, False)
    trajanje = time.monotonic() - zacetek
    return (dokoncan.returncode, (dokoncan.stdout or "") + (dokoncan.stderr or ""),
            trajanje, False)


def _najdi_test(izid: dict[str, bool], ime: str) -> bool | None:
    if ime in izid:
        return izid[ime]
    zadetki = [v for k, v in izid.items() if k.endswith(f"::{ime}")]
    if zadetki:
        return all(zadetki)
    return None


def _zamenjaj_oznake(argument: str, zamenjave: dict[str, str]) -> str:
    """Zamenja oznake tudi znotraj argumenta (npr. ``--junitxml={junit}``)."""
    for oznaka, vrednost in zamenjave.items():
        argument = argument.replace(oznaka, vrednost)
    return argument


def _privzeti_ukaz_testov() -> tuple[str, ...]:
    return ("{python}", "-m", "pytest", "{skriti}", "-q", "-o", "addopts=",
            "-p", "no:cacheprovider", "--confcutdir={skriti}",
            "--junitxml={junit}", "-c", "{ini}")


def izvedi_nalogo(
    naloga: Naloga,
    agent_ukaz: list[str],
    koren_nalog: pathlib.Path,
    cas_agent_s: float | None = None,
    okolje_dodatno: dict[str, str] | None = None,
) -> RezultatNaloge:
    """Izvede eno nalogo v svežem začasnem prostoru in jo oceni."""
    rezultat = RezultatNaloge(naloga=naloga.id, status=NAPAKA_OKOLJA)
    predloga = koren_nalog / naloga.predloga
    skriti_vir = koren_nalog / naloga.id / "skriti_testi"
    if not predloga.is_dir():
        rezultat.sporočilo = f"predloga ne obstaja: {predloga}"
        return rezultat
    if not skriti_vir.is_dir():
        rezultat.sporočilo = f"skriti testi ne obstajajo: {skriti_vir}"
        return rezultat

    osnovni = pathlib.Path(tempfile.mkdtemp(prefix=f"bench-{naloga.id}-"))
    try:
        prostor = osnovni / "prostor"
        shutil.copytree(predloga, prostor)
        poziv = osnovni / "poziv.txt"
        poziv.write_text(naloga.opis, encoding="utf-8")

        okolje = dict(os.environ)
        okolje["BENCHMARK_NALOGA"] = naloga.id
        if okolje_dodatno:
            okolje.update(okolje_dodatno)

        zamenjave = {
            "{prostor}": str(prostor),
            "{poziv}": str(poziv),
            "{naloga}": naloga.id,
            "{python}": sys.executable,
        }
        ukaz = [_zamenjaj_oznake(del_, zamenjave) for del_ in agent_ukaz]
        izhod, besedilo, cas_a, prekoracen = _pozeni(
            ukaz, prostor, cas_agent_s or naloga.cas_s, okolje)
        rezultat.izhod_agenta = izhod
        rezultat.cas_agenta_s = cas_a
        if prekoracen:
            rezultat.status = PREKORACEN_CAS
            rezultat.sporočilo = f"agent je presegel {naloga.cas_s:.0f} s"
            return rezultat

        # 3) canary: preveri PRED kopiranjem skritih testov
        rezultat.canary_zadet = poisci_canary(prostor, [besedilo], naloga.canary)

        # 4) skriti testi: ločen imenik, brez možnosti vračanja v prostor
        skriti = osnovni / "skriti_testi"
        shutil.copytree(skriti_vir, skriti)
        # agentova morebitna lastna mapa skriti_testi se zavrže (ni del rešitve)
        if (prostor / "skriti_testi").exists():
            shutil.rmtree(prostor / "skriti_testi")
        ini = osnovni / "pytest.ini"
        ini.write_text("[pytest]\n", encoding="utf-8")
        junit = osnovni / "junit.xml"

        predloga_ukaza = naloga.ukaz_testov or _privzeti_ukaz_testov()
        zamenjave.update({
            "{skriti}": str(skriti),
            "{junit}": str(junit),
            "{ini}": str(ini),
        })
        ukaz_testov = [_zamenjaj_oznake(del_, zamenjave) for del_ in predloga_ukaza]
        _izhod_t, besedilo_t, cas_t, prekoracen_t = _pozeni(
            ukaz_testov, osnovni, naloga.cas_s + 120.0, okolje)
        rezultat.cas_testov_s = cas_t
        if prekoracen_t:
            rezultat.status = PREKORACEN_CAS
            rezultat.sporočilo = "testi so presegli časovno omejitev"
            return rezultat
        try:
            izid_testov = beri_junit(junit)
        except ValueError as e:
            rezultat.status = NAPAKA_OKOLJA
            rezultat.sporočilo = f"{e}; izhod testov: {besedilo_t[-800:]}"
            return rezultat

        # 5) razvrstitev
        for ime in naloga.fail_to_pass:
            stanje = _najdi_test(izid_testov, ime)
            if stanje is None:
                rezultat.manjkajoci_testi.append(ime)
            elif stanje:
                rezultat.fail_to_pass_ok.append(ime)
            else:
                rezultat.fail_to_pass_napaka.append(ime)
        for ime in naloga.pass_to_pass:
            stanje = _najdi_test(izid_testov, ime)
            if stanje is None:
                rezultat.manjkajoci_testi.append(ime)
            elif stanje:
                rezultat.pass_to_pass_ok.append(ime)
            else:
                rezultat.pass_to_pass_napaka.append(ime)

        if rezultat.canary_zadet:
            rezultat.status = ONESNAZENO
            rezultat.sporočilo = (
                "canary žeton najden — agent je imel dostop do skrite "
                f"rešitve/testov: {rezultat.canary_zadet}")
        elif rezultat.pass_to_pass_napaka:
            rezultat.status = POKVARJEN
            rezultat.sporočilo = (
                "regresija: prej zeleni testi so padli: "
                f"{rezultat.pass_to_pass_napaka}")
        elif rezultat.manjkajoci_testi:
            rezultat.status = NAPAKA_OKOLJA
            rezultat.sporočilo = (
                f"testov ni v izhodu: {rezultat.manjkajoci_testi}")
        elif rezultat.fail_to_pass_napaka:
            rezultat.status = NI_RESEN
            rezultat.sporočilo = (
                f"ciljni testi niso zeleni: {rezultat.fail_to_pass_napaka}")
        else:
            rezultat.status = RESEN
        return rezultat
    finally:
        shutil.rmtree(osnovni, ignore_errors=True)


def razcleni_ukaz(predloga: str) -> list[str]:
    """Razdeli predlogo ukaza agenta na argumente (podpira navidezne oklepaje)."""
    deli = shlex.split(predloga)
    if not deli:
        raise ValueError("predloga ukaza agenta je prazna")
    return deli
