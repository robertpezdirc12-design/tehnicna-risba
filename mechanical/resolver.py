# -*- coding: utf-8 -*-
"""F1 — katalogsko jedro: nalaganje katalogskih vrstic in resolver.

Pogodba (docs/f1-specifikacija.md, razdelek 1):

- vhod: ``(designation, standard, profil)`` — npr. ``("M10", "ISO 4032", "iso")``
  ali ``("M10x35", "ISO 4017", "iso")``;
- izhod: dimenzije + provenenca (vir, datum dostopa/preverjanja, opombe);
- napake **brez ugibanja**: neznan profil, neznan standard v danem profilu,
  manjkajoča velikost/varianta;
- profila ``iso`` in ``legacy_din`` sta strogo ločena — resolver nikoli ne
  vrne vrednosti iz drugega profila.

Katalogske vrstice živijo v ``mechanical/catalog/*.yaml`` in morajo nositi
provenenco (vir + datum dostopa) — brez nje vrstice ne sprejmemo (B4).

Uporaba z ukazno vrstico::

    python -m mechanical.resolver M10 "ISO 4032" iso
"""
import os
import sys

import yaml

KOREN_KATALOGA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog")

# Znana katalogska profila (F0): `iso` primarni, `legacy_din` eksplicitno ločen.
PROFILI = ("iso", "legacy_din")


class NapakaKataloga(Exception):
    """Osnovna napaka katalogskega jedra — vedno pove razlog, nikoli ne ugiba."""


class NeznanProfil(NapakaKataloga):
    """Profil kataloga ni poznan (npr. ``din`` namesto ``legacy_din``)."""


class NeznanStandard(NapakaKataloga):
    """Standard ni vpisan v danem profilu (npr. DIN 934 v profilu ``iso``)."""


class ManjkajocaVarianta(NapakaKataloga):
    """Velikost/varianta (designation) ni vpisana za ta standard v tem profilu."""


# ---------- normalizacija (poenoten zapis, NE ugibanje vrednosti) ----------

def _norm_oznaka(vrednost):
    """Oznaka velikosti: ``M10×35``, ``M10 x 35`` in ``m10x35`` pomenijo isto."""
    return str(vrednost).strip().replace("\u00d7", "x").replace(" ", "").casefold()


def _norm_besedilo(vrednost):
    """Standard/profil: poenotitev presledkov in velikosti črk."""
    return " ".join(str(vrednost).split()).casefold()


# ---------- nalaganje kataloga ----------

def _izvleci_provenenco(blok, pot):
    """Provenenca je obvezna: vsak vir mora imeti ime in datum dostopa."""
    if not isinstance(blok, dict):
        raise NapakaKataloga("%s: manjka blok `provenance` (obvezno polje)" % pot)
    viri = blok.get("sources")
    if viri is None and "source" in blok:
        # dopusten tudi singularni zapis (source / source_url / accessed)
        viri = [{
            "name": blok.get("source"),
            "url": blok.get("source_url"),
            "accessed": blok.get("accessed"),
            "note": None,
        }]
    if not isinstance(viri, list) or not viri:
        raise NapakaKataloga(
            "%s: `provenance` mora navajati vsaj en vir (`sources`)" % pot)
    izhod = []
    for vir in viri:
        if not isinstance(vir, dict) or not vir.get("name") or not vir.get("accessed"):
            raise NapakaKataloga(
                "%s: vsak vir potrebuje `name` in `accessed` (datum preverjanja)" % pot)
        izhod.append({k: vir.get(k) for k in ("name", "url", "accessed", "note")})
    return izhod, blok.get("note")


def _preveri_vrstico(data, pot):
    """Preveri in normaliziraj eno katalogsko vrstico; sicer napaka (brez ugibanja)."""
    if not isinstance(data, dict):
        raise NapakaKataloga("%s: katalogska vrstica mora biti YAML objekt" % pot)
    katalog = data.get("catalog")
    if not isinstance(katalog, dict):
        raise NapakaKataloga("%s: manjka blok `catalog`" % pot)
    for polje in ("profil", "standard", "designation"):
        if not katalog.get(polje):
            raise NapakaKataloga("%s: `catalog.%s` je obvezno" % (pot, polje))
    if katalog["profil"] not in PROFILI:
        raise NapakaKataloga(
            "%s: neznan profil %r (dovoljena: %s)"
            % (pot, katalog["profil"], ", ".join(PROFILI)))
    dimenzije = data.get("dimensions")
    if not isinstance(dimenzije, dict) or not dimenzije:
        raise NapakaKataloga(
            "%s: `dimensions` mora vsebovati vsaj eno dimenzijo" % pot)
    viri, opomba = _izvleci_provenenco(data.get("provenance"), pot)
    return {
        "profil": katalog["profil"],
        "standard": katalog["standard"],
        "designation": katalog["designation"],
        "nominal_diameter": katalog.get("nominal_diameter"),
        "length_mm": katalog.get("length_mm"),
        "opis": katalog.get("description"),
        "dimenzije": dimenzije,
        "provenenca": viri,
        "provenenca_opomba": opomba,
        "status": data.get("status", "reference"),
        "vir": os.path.basename(pot),
    }


def nalozi_katalog(koren=KOREN_KATALOGA):
    """Naloži vse katalogske vrstice iz ``koren/*.yaml`` → indeks.

    Ključ indeksa je ``(_norm profil, _norm standard, _norm oznaka)``;
    vrednost je normalizirana vrstica (dimenzije + provenenca).
    """
    if not os.path.isdir(koren):
        raise NapakaKataloga("mapa kataloga ne obstaja: %s" % koren)
    indeks = {}
    for ime in sorted(os.listdir(koren)):
        if not ime.endswith((".yaml", ".yml")):
            continue
        pot = os.path.join(koren, ime)
        with open(pot, encoding="utf-8") as dat:
            data = yaml.safe_load(dat)
        vrstica = _preveri_vrstico(data, pot)
        kljuc = (
            _norm_besedilo(vrstica["profil"]),
            _norm_besedilo(vrstica["standard"]),
            _norm_oznaka(vrstica["designation"]),
        )
        if kljuc in indeks:
            raise NapakaKataloga(
                "%s: dvojna katalogska vrstica %s %s"
                % (pot, vrstica["standard"], vrstica["designation"]))
        indeks[kljuc] = vrstica
    return indeks


_PRIVZETI_KATALOG = None


def _katalog():
    """Privzeti katalog (iz ``mechanical/catalog``) — naložen enkrat, na zahtevo."""
    global _PRIVZETI_KATALOG
    if _PRIVZETI_KATALOG is None:
        _PRIVZETI_KATALOG = nalozi_katalog()
    return _PRIVZETI_KATALOG


# ---------- resolver ----------

def razresi(designation, standard, profil, katalog=None):
    """Razreši katalogsko vrstico ``designation``/``standard`` v ``profilu``.

    Vrne normalizirano vrstico z dimenzijami in provenenco. Napake brez
    ugibanja: :class:`NeznanProfil`, :class:`NeznanStandard`,
    :class:`ManjkajocaVarianta`.
    """
    indeks = _katalog() if katalog is None else katalog
    p = _norm_besedilo(profil)
    znani = sorted({kljuc[0] for kljuc in indeks})
    if p not in znani:
        raise NeznanProfil(
            "neznan profil %r; znani profili: %s" % (profil, ", ".join(znani) or "—"))
    s = _norm_besedilo(standard)
    v_profilu = {kljuc[1]: vrstica for kljuc, vrstica in indeks.items()
                 if kljuc[0] == p}
    if s not in v_profilu:
        raise NeznanStandard(
            "standard %r ni vpisan v profilu %r; v profilu: %s"
            % (standard, profil,
               ", ".join(sorted({v["standard"] for v in v_profilu.values()})) or "—"))
    d = _norm_oznaka(designation)
    kljuc = (p, s, d)
    if kljuc not in indeks:
        na_voljo = sorted({v["designation"] for k, v in indeks.items()
                           if k[0] == p and k[1] == s})
        raise ManjkajocaVarianta(
            "%s %s ni vpisan v profilu %r; na voljo: %s"
            % (standard, designation, profil, ", ".join(na_voljo) or "—"))
    return indeks[kljuc]


# angleška sopomenka po terminologiji specifikacije F1
resolve = razresi


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Razreši katalogsko vrstico (F1) in izpiše dimenzije + provenenco.")
    parser.add_argument("designation", help="npr. M10 ali M10x35")
    parser.add_argument("standard", help="npr. 'ISO 4032' ali 'DIN 933'")
    parser.add_argument("profil", help="iso ali legacy_din")
    argumenti = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # dosleden UTF-8 izpis tudi na Windows
    try:
        vrstica = razresi(argumenti.designation, argumenti.standard, argumenti.profil)
    except NapakaKataloga as napaka:
        sys.stderr.write("NAPAKA: %s\n" % napaka)
        sys.exit(1)
    sys.stdout.write(yaml.safe_dump(vrstica, allow_unicode=True, sort_keys=False))