# -*- coding: utf-8 -*-
"""Revizije risbe + diff povzetek (načrt 7).

Profesionalni postopek: vsaka sprememba izdelka = nova revizija z oznako
(ISO 7200: črke A..Z brez I in O) in opisom, KAJ se je spremenilo. Industrija
opozarja, da „revision clouds spregledajo spremembe“ (Operon) — zato povzetek
ni ročni, ampak izračunan iz dejanske razlike konfiguracij (diff).

Shranjevanje (v cfg, ki je že vir resnice za projekt):
    cfg["revizije"]     = [[oznaka, datum, opis, izdelal], ...]
    cfg["rev_snapshot"] = snapshot(cfg) ob zadnji reviziji

Modul je knjižnica brez GUI — uporabljata ga vmesnik in risba.
"""
from __future__ import annotations

import copy
import datetime

# ISO 7200: indeks revizije so črke, ki se ne uporabljajo: I in O
# (zamenljivi s številkama 1 in 0).
REVIZIJSKE_CRKE = "ABCDEFGHJKLMNPQRSTUVWXYZ"

# Ključi, ki NISO del izdelka — njihova sprememba ni revizija:
# revizije same, izpisna pot, datum (se napolni sam) in status dokumenta
# (sprememba procesa, ne risbe — za to je tok ZA POTRDITEV → IZVEDENO).
IZLOCI_IZ_SNAPSHOTA = frozenset({
    "revizije", "rev_snapshot", "izhod", "datum", "status_dokumenta",
})

# Slovenska imena polj za diff povzetek (sicer se uporabi kar ključ).
IMENA = {
    "predloga": "predloga",
    "ime": "ime risbe",
    "risba_st": "številka risbe",
    "izdelal": "izdelal",
    "stranka": "naročnik",
    "objekt": "objekt",
    "podjetje": "podjetje",
    "pregledal": "pregledal",
    "odobril": "odobril",
    "merilo": "merilo",
    "format": "format",
    "barva": "barva",
    "profil": "profil",
    "material": "material",
    "material_lamel": "material lamel",
    "dobavitelj": "dobavitelj",
    "pritrditev": "pritrditev",
    "pritrditev_nacin": "pritrditev",
    "uporabi_ostanke": "uporabi ostanke",
    "klik_cel_zaslon": "klik cel zaslon",
    "preprost_nacin": "preprost način",
    "kerf": "širina reza (kerf)",
    "dolzina_palice": "dolžina palice",
    "dolzine_deske": "dolžine desk",
    "vijak_lamela": "vijak lamele",
    "vijak_nosilec": "vijak nosilca",
    "vrata": "vrata",
    "mere": "",
    "cene": "cene",
    "sirina": "širina",
    "visina": "višina",
    "globina": "globina",
    "lamele": "število lamel",
    "lamela_v": "višina lamele",
    "debelina": "debelina lamele",
    "vrzel": "vrzel med lamelami",
    "odcep": "odcep",
    "razmak_nosilcev": "razmak nosilcev",
    "razmak_stebrov": "razmak stebrov",
    "deska_sirina": "širina deske",
}


def _ime(kljuc: str) -> str:
    return IMENA.get(kljuc, kljuc)


def naslednja_oznaka(obstojoce) -> str:
    """Naslednja revizijska oznaka. Prazno -> 'A'; drugače črka po zadnji.

    ISO 7200 preskoči I in O. Čez Z se nadaljuje z AA, AB, …
    """
    crke = REVIZIJSKE_CRKE
    zadnja = ""
    for vnos in (obstojoce or []):
        if isinstance(vnos, (list, tuple)) and vnos:
            zadnja = str(vnos[0]).strip().upper()
        elif isinstance(vnos, dict):
            zadnja = str(vnos.get("oznaka", "")).strip().upper()
    if not zadnja:
        return "A"
    # vzemi zadnjo črko oznake (A -> A, AA -> A)
    zadnja_crka = zadnja[-1]
    if zadnja_crka not in crke:
        return "A"
    i = crke.index(zadnja_crka)
    if i + 1 < len(crke):
        # če je oznaka enočrkovna, naslednja črka; sicer (AA) napredek zadnje
        return (crke[i + 1] if len(zadnja) == 1
                else zadnja[:-1] + crke[i + 1])
    # Z -> AA (ali napredek predpone: AZ -> BA ni podprt; zadostuje AA…)
    return "A" * (len(zadnja) + 1) if len(zadnja) > 1 else "AA"


def snapshot(cfg) -> dict:
    """Globoka kopija oblikovalsko relevantnih polj cfg (brez revizij, poti)."""
    return {k: copy.deepcopy(v) for k, v in cfg.items()
            if k not in IZLOCI_IZ_SNAPSHOTA}


def _niz(v) -> str:
    """Kompakten čitljiv zapis vrednosti za diff povzetek."""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, bool):
        return "da" if v else "ne"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{_ime(k)} {_niz(x)}" for k, x in v.items()) + "}"
    return str(v)


def _opis_vrat(v) -> str:
    """Kratek opis enih vrat za diff: 'enokrilna 900×1500 @200'."""
    if not isinstance(v, dict):
        return _niz(v)
    tip = str(v.get("tip", "?"))
    sirina = v.get("sirina", "?")
    visina = v.get("visina", "?")
    x = v.get("x", "")
    return f"{tip} {sirina}×{visina} @{x}" if x != "" else f"{tip} {sirina}×{visina}"


def diff_povzetek(staro, novo) -> list:
    """Slovenski seznam sprememb med dvema snapshotoma/konfiguracijama.

    Prazno = vsebina se ni spremenila. Rezultat je namenjen človeku
    (opis revizije), ne stroju.
    """
    staro = staro or {}
    novo = novo or {}
    spremembe = []

    def ravnaj(kljuc, a, b):
        ime = _ime(kljuc)
        pred = f"{ime}: " if ime else ""
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                ravnaj(k, a.get(k), b.get(k))
            return
        if kljuc == "vrata" and isinstance(a, list) and isinstance(b, list):
            stari = [_opis_vrat(v) for v in a]
            novi = [_opis_vrat(v) for v in b]
            dodani = [v for v in novi if v not in stari]
            odstranjeni = [v for v in stari if v not in novi]
            if dodani:
                spremembe.append(f"{pred}dodano: " + ", ".join(dodani))
            if odstranjeni:
                spremembe.append(f"{pred}odstranjeno: " + ", ".join(odstranjeni))
            return
        if a != b:
            spremembe.append(f"{pred}{_niz(a)} → {_niz(b)}")

    for kljuc in sorted(set(staro) | set(novo)):
        ravnaj(kljuc, staro.get(kljuc), novo.get(kljuc))
    return spremembe


def nova_revizija(cfg, opis="", izdelal=None):
    """Doda revizijo v cfg. Vrne (vnos, povzetek_sprememb).

    - oznaka: naslednja po obstoječih (prva = 'A');
    - povzetek: diff trenutnega stanja proti `cfg["rev_snapshot"]`
      (brez zapisa = prva revizija, povzetek prazen);
    - če je `opis` prazen, se vanj zapiše diff povzetek (če je);
    - `cfg["rev_snapshot"]` se osveži na trenutno stanje.
    """
    povzetek = diff_povzetek(cfg.get("rev_snapshot"), snapshot(cfg))
    if not cfg.get("revizije"):
        povzetek = []          # prva revizija — ni prejšnje za primerjavo
    oznaka = naslednja_oznaka(cfg.get("revizije"))
    datum = datetime.date.today().strftime("%d.%m.%Y")
    if not (opis or "").strip():
        opis = "; ".join(povzetek) if povzetek else "Prva izdaja"
    if izdelal is None:
        izdelal = cfg.get("izdelal") or "—"
    vnos = [oznaka, datum, opis[:300], str(izdelal)[:40]]
    cfg.setdefault("revizije", [])
    if not isinstance(cfg["revizije"], list):
        cfg["revizije"] = []
    cfg["revizije"].append(vnos)
    cfg["rev_snapshot"] = snapshot(cfg)
    return vnos, povzetek