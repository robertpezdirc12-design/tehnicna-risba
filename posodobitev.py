# -*- coding: utf-8 -*-
"""Preverjanje posodobitev (Plan 5) — GitHub Releases API.

Zasnovano po raziskavi distribucije namiznih aplikacij: uporabniki brez
avtomatskega preverjanja obtičijo na starih različicah. Omrežni klic je
LOČEN od čiste logike (``odpri_zadnjo_izdajo``), da testi preverjajo
primerjalno logiko BREZ omrežja.

Politika (iskreno): aplikacija samo OPOMORI na novo različico in pokaže
povezavo — NE namešča posodobitev sama (za to je potreben podpisan
namestitveni paket, glej docs/plan-5-podpis-posodobitve.md).
"""
import json
import urllib.request

# Usklajeno z zadnjo oznako (git tag). Ob izdaji se dvigne skupaj z oznako.
# Preverjanje: tests/test_build.py (modul = pyproject.toml = najnovejši
# CHANGELOG) — verzija se je nekoč ustavila na 1.2, GUI pa je ponujal
# "novo" različico, ki je bila že nameščena.
VERZIJA = "1.5.2"
REPO = "robertpezdirc12-design/tehnicna-risba"
URL_ZADNJA = f"https://api.github.com/repos/{REPO}/releases/latest"


def primerjaj_verziji(a, b):
    """Numerična primerjava različic ('1.2' < '1.10', 'v1.3' = '1.3').

    Vrne -1 (a < b), 0 (enaki), 1 (a > b). Neštevilčni deli (npr. '-rc1')
    se pri štetju ignorirajo — za našo shemo 'x.y' zadošča.
    """
    def deli(v):
        out = []
        for kos in str(v).strip().lstrip("vV").split("."):
            stevka = ""
            for z in kos:
                if z.isdigit():
                    stevka += z
                else:
                    break
            if stevka:
                out.append(int(stevka))
        return out or [0]
    da, db = deli(a), deli(b)
    dol = max(len(da), len(db))
    da += [0] * (dol - len(da))
    db += [0] * (dol - len(db))
    return (da > db) - (da < db)


def odpri_zadnjo_izdajo(url=URL_ZADNJA, casovna_omejitev=6.0):
    """Omrežni klic (ločen, da ga testi nadomestijo). Vrne razčlenjen JSON."""
    with urllib.request.urlopen(url, timeout=casovna_omejitev) as odziv:
        return json.loads(odziv.read().decode("utf-8"))


def preveri_posodobitev(trenutna=VERZIJA, url=URL_ZADNJA, casovna_omejitev=6.0):
    """Preveri, ali je na GitHub Releases nova različica.

    Vrne dict: {"novo": bool, "verzija": str|None, "url": str|None,
                "napaka": str|None}. Omrežne napake NISO kritične —
    vrnejo se z "napaka" in "novo": False, aplikacija teče dalje.
    """
    try:
        podatki = odpri_zadnjo_izdajo(url, casovna_omejitev)
        oznaka = (podatki.get("tag_name") or "").strip()
        if not oznaka:
            return {"novo": False, "verzija": None, "url": None,
                    "napaka": "Odziv nima oznake (tag_name)."}
        return {"novo": primerjaj_verziji(trenutna, oznaka) < 0,
                "verzija": oznaka,
                "url": podatki.get("html_url"),
                "napaka": None}
    except Exception as e:                      # omrežje: ne kritično
        return {"novo": False, "verzija": None, "url": None,
                "napaka": f"{type(e).__name__}: {e}"}