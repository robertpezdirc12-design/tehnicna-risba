# -*- coding: utf-8 -*-
"""Ilustracije za marketing prek Cloudflare Workers AI (FLUX.1 [schnell]).

Zakaj LOČEN skript: generativne slike ne sodijo v izdelek — tehnične risbe
morajo ostati deterministične (matplotlib/ezdxf), spletna stran pa prikazuje
resnične izdelke programa. Skript je zato namenjen izključno ročni pripravi
ilustracij in ga aplikacija NIKOLI ne kliče; v EXE ne gre.

Brezplačna kvota Cloudflare Workers AI: 10 000 nevronov na dan na račun,
obnova ob 00:00 UTC (pozimi 01:00, poleti 02:00 po lokalnem času).
Cena modela flux-1-schnell: 4,80 nevrona na ploščico 512x512 in 9,60
nevrona na korak — pri 1024x1024 in 4 korakih je to ~58 nevronov oz.
približno 170 slik na dan.

Uporaba (PowerShell):
    $env:CLOUDFLARE_API_TOKEN = "…"
    $env:CLOUDFLARE_ACCOUNT_ID = "…"
    python scripts/slike_cloudflare.py "antracitna ograja, produktna fotografija" \
        --izhod ilustracije/ograja.jpg

Ključ se bere IZKLJUČNO iz okoljskih spremenljivk — nikoli iz datoteke v
repozitoriju, nikoli iz ukazne vrstice (zgodovina ukazov).
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Any

MODEL = "@cf/black-forest-labs/flux-1-schnell"
KONCNICA = "https://api.cloudflare.com/client/v4/accounts/{racun}/ai/run/{model}"
SPREMENLJIVKE = ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")

# Cenik (uradno: developers.cloudflare.com/workers-ai/platform/pricing).
NEVRONOV_PLOSCICA = 4.8
NEVRONOV_KORAK = 9.6
DNI_KVOTA = 10_000.0
KONCNICE_SLIKE = (".jpg", ".jpeg", ".png")


class Napaka(Exception):
    """Razumljiva napaka — skript nikoli ne odpove tiho ali nejasno."""


def oceni_nevrone(sirina: int, visina: int, koraki: int) -> float:
    """Ocena porabe nevronov po uradni formuli (ploščice + koraki)."""
    if sirina <= 0 or visina <= 0:
        raise Napaka(f"Velikost slike mora biti pozitivna (dano {sirina}x{visina}).")
    if not 1 <= koraki <= 8:
        raise Napaka(f"Koraki morajo biti 1–8 (dano {koraki}); model podpira največ 8.")
    ploscice = -(-sirina // 512) * -(-visina // 512)
    return ploscice * NEVRONOV_PLOSCICA + koraki * NEVRONOV_KORAK


def preberi_okolje(okolje: dict[str, str] | None = None) -> tuple[str, str]:
    """Vrne (žeton, ID računa); ob manjkajoči spremenljivki pove KATERO."""
    vir = os.environ if okolje is None else okolje
    manjkajo = [k for k in SPREMENLJIVKE if not vir.get(k, "").strip()]
    if manjkajo:
        raise Napaka(
            "Manjka okoljska spremenljivka: " + ", ".join(manjkajo)
            + ". Nastavi jo v okolju (PowerShell: $env:IME = \"…\")."
            " Ključa ne zapisuj v datoteke v repozitoriju."
        )
    return vir["CLOUDFLARE_API_TOKEN"].strip(), vir["CLOUDFLARE_ACCOUNT_ID"].strip()


def _sporocilo(odgovor: dict[str, Any]) -> str:
    """Sestavi sporočilo napake iz odgovora Cloudflare (+ namig o kvoti)."""
    napake = odgovor.get("errors") or []
    deli = [str(n.get("message", n)) if isinstance(n, dict) else str(n) for n in napake]
    besedilo = "; ".join(d for d in deli if d) or "neznana napaka"
    if "neuron" in besedilo.lower() or "quota" in besedilo.lower():
        besedilo += (
            " — dnevna brezplačna kvota je 10 000 nevronov in se obnovi ob"
            " 00:00 UTC (pozimi 01:00 po lokalnem času)."
        )
    return besedilo


def _klic(
    url: str, zeton: str, telo: dict[str, Any], omejitev: float,
) -> dict[str, Any]:
    """Enojni HTTP POST; omrežni del je ločen, da ga testi nadomestijo."""
    zahteva = urllib.request.Request(
        url,
        data=json.dumps(telo).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {zeton}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(zahteva, timeout=omejitev) as odgovor:
            surovo = odgovor.read()
    except urllib.error.HTTPError as e:
        surovo = e.read()
        try:
            podatki = json.loads(surovo.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            raise Napaka(f"Cloudflare: HTTP {e.code} brez veljavnega JSON odgovora.") from e
        if isinstance(podatki, dict) and podatki.get("errors"):
            raise Napaka(f"Cloudflare: HTTP {e.code} — {_sporocilo(podatki)}") from e
        raise Napaka(f"Cloudflare: HTTP {e.code} — {surovo[:200]!r}") from e
    except urllib.error.URLError as e:
        raise Napaka(f"Ni povezave do Cloudflare: {e.reason}") from e
    try:
        odgovor_json = json.loads(surovo.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise Napaka("Cloudflare je vrnil odgovor, ki ni JSON.") from e
    if not isinstance(odgovor_json, dict):
        raise Napaka("Cloudflare je vrnil nepričakovano obliko odgovora.")
    return odgovor_json


def ustvari(
    povprasevanje: str,
    *,
    koraki: int = 4,
    omejitev: float = 120.0,
    okolje: dict[str, str] | None = None,
) -> bytes:
    """Vrne JPEG/PNG kot bajte; ob napaki dvigne Napaka z razlogom."""
    besedilo = povprasevanje.strip()
    if not besedilo:
        raise Napaka("Povpraševanje je prazno — brez opisa ni slike.")
    if not 1 <= koraki <= 8:
        raise Napaka(f"Koraki morajo biti 1–8 (dano {koraki}); model podpira največ 8.")
    zeton, racun = preberi_okolje(okolje)
    url = KONCNICA.format(racun=racun, model=MODEL)
    odgovor = _klic(url, zeton, {"prompt": besedilo, "steps": koraki}, omejitev)
    if not odgovor.get("success"):
        raise Napaka("Cloudflare: " + _sporocilo(odgovor))
    rezultat = odgovor.get("result") or {}
    zapis = rezultat.get("image") if isinstance(rezultat, dict) else None
    if not isinstance(zapis, str) or not zapis:
        raise Napaka("Cloudflare je vrnil uspeh brez slike — preveri kvoto.")
    try:
        bajti = base64.b64decode(zapis, validate=True)
    except (binascii.Error, ValueError) as e:
        raise Napaka(f"Slika ni veljaven base64: {e}") from e
    if not (bajti.startswith(b"\xff\xd8") or bajti.startswith(b"\x89PNG")):
        raise Napaka("Vsebina ni JPEG ali PNG — Cloudflare je vrnil nekaj drugega.")
    return bajti


def shrani(
    povprasevanje: str,
    cilj: pathlib.Path,
    *,
    koraki: int = 4,
    omejitev: float = 120.0,
    okolje: dict[str, str] | None = None,
) -> pathlib.Path:
    """Ustvari sliko in jo zapiše na `cilj` (mapo ustvari, če manjka)."""
    if cilj.suffix.lower() not in KONCNICE_SLIKE:
        dovoljene = ", ".join(KONCNICE_SLIKE)
        raise Napaka(
            f"Končnica {cilj.suffix!r} ni slika — uporabi eno od: {dovoljene}."
        )
    bajti = ustvari(povprasevanje, koraki=koraki, omejitev=omejitev, okolje=okolje)
    cilj.parent.mkdir(parents=True, exist_ok=True)
    cilj.write_bytes(bajti)
    return cilj


def main(argv: list[str] | None = None) -> int:
    """Ukazna vrstica: python scripts/slike_cloudflare.py "opis" --izhod x.jpg"""
    parser = argparse.ArgumentParser(
        description="Brezplačne ilustracije prek Cloudflare Workers AI (FLUX.1 schnell).",
    )
    parser.add_argument("povprasevanje", help="opis slike v angleščini (model ne razume slovenščine dobro)")
    parser.add_argument("--izhod", default="ilustracije/slika.jpg", help="pot do zapisa (privzeto ilustracije/slika.jpg)")
    parser.add_argument("--koraki", type=int, default=4, help="število difuzijskih korakov 1–8 (privzeto 4)")
    args = parser.parse_args(argv)

    try:
        nevroni = oceni_nevrone(1024, 1024, args.koraki)
        print(
            f"cena: ~{nevroni:.0f} nevronov -> do ~{int(DNI_KVOTA / nevroni)} slik/dan"
            " (kvota 10 000/dan, obnova 00:00 UTC; skupna z drugimi modeli)",
        )
        pot = shrani(args.povprasevanje, pathlib.Path(args.izhod), koraki=args.koraki)
    except Napaka as e:
        print(f"napaka: {e}", file=sys.stderr)
        return 2
    print(f"shranjeno: {pot} ({pot.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
