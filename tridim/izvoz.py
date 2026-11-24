# -*- coding: utf-8 -*-
"""Izvoz mrež v STL / OBJ / GLB — sami pisalniki, brez zunanjih knjižnic.

Zakaj ročni pisalniki: STL in OBJ sta besedilno/binarno preprosta formata,
GLB (binarni glTF 2.0) pa je ovojnica z dvema blokoma. S tem 3D izvoz v
EXE ne prinese nobene dodatne odvisnosti in nobene licenčne obveznosti.

Formati:
- **STL (binarni)** — natiski in 3D-pregledovalniki; 84-bajtna glava,
  50 bajtov na trikotnik. Normalo zapišemo (nekateri bralsniki jo
  zahtevajo), a je izračunljiva iz oglišč.
- **OBJ** — izmenjava z modelirniki; besedilo, 1-indeksirane ploskve.
- **GLB** — glTF 2.0 v eni datoteki (JSON + BIN); primerno za splet.
"""

from __future__ import annotations

import json
import pathlib
import struct

from tridim.mreza import Mreza, Tocka, Trikotnik

STL_GLAVA = 80
_STL_BAJT_TRIKOTNIKA = 50


# ------------------------------------------------------------------- STL


def shrani_stl(mreza: Mreza, pot: str | pathlib.Path,
               ime: str = "tehnicna-risba") -> pathlib.Path:
    """Zapiše binarni STL. Vrne pot."""
    if not mreza.trikotniki:
        raise ValueError("prazne mreže ni mogoče izvoziti")
    normale = mreza.normale()
    glava = ime.encode("ascii", "replace")[:STL_GLAVA].ljust(STL_GLAVA, b"\0")
    kosi: list[bytes] = [glava, struct.pack("<I", len(mreza.trikotniki))]
    for (a, b, c), n in zip(mreza.trikotniki, normale):
        p, q, r = mreza.tocke[a], mreza.tocke[b], mreza.tocke[c]
        kosi.append(struct.pack("<12fH", n[0], n[1], n[2],
                                p[0], p[1], p[2], q[0], q[1], q[2],
                                r[0], r[1], r[2], 0))
    cilj = pathlib.Path(pot)
    cilj.write_bytes(b"".join(kosi))
    return cilj


def preberi_stl(pot: str | pathlib.Path) -> Mreza:
    """Prebere binarni STL (za preverjanje izvoza)."""
    podatki = pathlib.Path(pot).read_bytes()
    if len(podatki) < STL_GLAVA + 4:
        raise ValueError("datoteka je prekratka za binarni STL")
    (stevilo,) = struct.unpack_from("<I", podatki, STL_GLAVA)
    if len(podatki) != STL_GLAVA + 4 + stevilo * _STL_BAJT_TRIKOTNIKA:
        raise ValueError("dolžina datoteke ne ustreza številu trikotnikov")
    tocke: list[Tocka] = []
    trikotniki: list[Trikotnik] = []
    for i in range(stevilo):
        vrednosti = struct.unpack_from("<12f", podatki,
                                       STL_GLAVA + 4 + i * _STL_BAJT_TRIKOTNIKA)
        trikotniki.append((3 * i, 3 * i + 1, 3 * i + 2))
        for k in range(3):
            tocke.append((vrednosti[3 + 3 * k], vrednosti[4 + 3 * k],
                          vrednosti[5 + 3 * k]))
    return Mreza(tuple(tocke), tuple(trikotniki))


# ------------------------------------------------------------------- OBJ


def shrani_obj(mreza: Mreza, pot: str | pathlib.Path,
               ime: str = "tehnicna-risba") -> pathlib.Path:
    """Zapiše tekstovni OBJ (oglišča + ploskve, brez normal)."""
    if not mreza.trikotniki:
        raise ValueError("prazne mreže ni mogoče izvoziti")
    vrstice = [f"# {ime} (mm)", f"o {ime}"]
    vrstice.extend(f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in mreza.tocke)
    vrstice.extend(f"f {a + 1} {b + 1} {c + 1}"
                   for a, b, c in mreza.trikotniki)
    cilj = pathlib.Path(pot)
    cilj.write_text("\n".join(vrstice) + "\n", encoding="ascii")
    return cilj


def preberi_obj(pot: str | pathlib.Path) -> Mreza:
    """Prebere OBJ, ki ga zapiše :func:`shrani_obj`."""
    tocke: list[Tocka] = []
    trikotniki: list[Trikotnik] = []
    for vrstica in pathlib.Path(pot).read_text(encoding="ascii").splitlines():
        deli = vrstica.split()
        if not deli:
            continue
        if deli[0] == "v":
            tocke.append((float(deli[1]), float(deli[2]), float(deli[3])))
        elif deli[0] == "f":
            trikotniki.append(tuple(int(d.split("/")[0]) - 1
                                    for d in deli[1:4]))  # type: ignore[arg-type]
    return Mreza(tuple(tocke), tuple(trikotniki))


# ------------------------------------------------------------------- GLB

_GLB_MAGIC = 0x46546C67          # "glTF"
_CHUNK_JSON = 0x4E4F534A         # "JSON"
_CHUNK_BIN = 0x004E4942          # "BIN\0"


def _poravnaj(podatki: bytes, polnilo: bytes) -> bytes:
    ostanek = len(podatki) % 4
    return podatki + polnilo * ((4 - ostanek) % 4)


def shrani_glb(mreza: Mreza, pot: str | pathlib.Path,
               ime: str = "tehnicna-risba") -> pathlib.Path:
    """Zapiše glTF 2.0 kot eno samo .glb datoteko (JSON + BIN)."""
    if not mreza.trikotniki:
        raise ValueError("prazne mreže ni mogoče izvoziti")
    lege = b"".join(struct.pack("<3f", *t) for t in mreza.tocke)
    indeksi = b"".join(struct.pack("<3I", *t) for t in mreza.trikotniki)
    lege = _poravnaj(lege, b"\0")
    indeksi_odmik = len(lege)
    binar = _poravnaj(lege + indeksi, b"\0")

    (minx, miny, minz), (maxx, maxy, maxz) = mreza.meje()
    dokument = {
        "asset": {"version": "2.0", "generator": f"{ime} (brez odvisnosti)"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": ime}],
        "meshes": [{"name": ime, "primitives": [
            {"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
        "buffers": [{"byteLength": len(binar)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(lege),
             "target": 34962},
            {"buffer": 0, "byteOffset": indeksi_odmik,
             "byteLength": len(indeksi), "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(mreza.tocke),
             "type": "VEC3", "min": [minx, miny, minz],
             "max": [maxx, maxy, maxz]},
            {"bufferView": 1, "componentType": 5125,
             "count": 3 * len(mreza.trikotniki), "type": "SCALAR"},
        ],
    }
    json_blok = _poravnaj(json.dumps(dokument, ensure_ascii=False)
                          .encode("utf-8"), b" ")
    skupaj = 12 + 8 + len(json_blok) + 8 + len(binar)
    kosi = [struct.pack("<III", _GLB_MAGIC, 2, skupaj),
            struct.pack("<II", len(json_blok), _CHUNK_JSON), json_blok,
            struct.pack("<II", len(binar), _CHUNK_BIN), binar]
    cilj = pathlib.Path(pot)
    cilj.write_bytes(b"".join(kosi))
    return cilj


def preberi_glb(pot: str | pathlib.Path) -> tuple[dict, Mreza]:
    """Prebere GLB, ki ga zapiše :func:`shrani_glb`; vrne (json, mreža)."""
    podatki = pathlib.Path(pot).read_bytes()
    if len(podatki) < 20:
        raise ValueError("datoteka je prekratka za GLB")
    magic, razlicica, dolzina = struct.unpack_from("<III", podatki, 0)
    if magic != _GLB_MAGIC:
        raise ValueError("ni GLB (napačna magija)")
    if razlicica != 2:
        raise ValueError(f"nepodprta različica glTF: {razlicica}")
    if dolzina != len(podatki):
        raise ValueError("dolžina v glavi se ne ujema z velikostjo datoteke")

    odmik = 12
    dokument: dict | None = None
    binar = b""
    while odmik + 8 <= len(podatki):
        velikost, vrsta = struct.unpack_from("<II", podatki, odmik)
        vsebina = podatki[odmik + 8: odmik + 8 + velikost]
        if vrsta == _CHUNK_JSON:
            dokument = json.loads(vsebina.decode("utf-8"))
        elif vrsta == _CHUNK_BIN:
            binar = vsebina
        odmik += 8 + velikost
    if dokument is None:
        raise ValueError("GLB brez JSON bloka")

    lege_view = dokument["bufferViews"][0]
    ind_view = dokument["bufferViews"][1]
    n_tock = dokument["accessors"][0]["count"]
    n_ind = dokument["accessors"][1]["count"]
    zacetek = lege_view["byteOffset"]
    tocke = [struct.unpack_from("<3f", binar, zacetek + 12 * i)
             for i in range(n_tock)]
    zacetek = ind_view["byteOffset"]
    indeksi = [struct.unpack_from("<3I", binar, zacetek + 12 * i)
               for i in range(n_ind // 3)]
    return dokument, Mreza(tuple(tocke), tuple(indeksi))


# ---------------------------------------------------------------- skupno

PISALNIKI = {
    ".stl": shrani_stl,
    ".obj": shrani_obj,
    ".glb": shrani_glb,
}

BRALNIKI = {
    ".stl": preberi_stl,
    ".obj": preberi_obj,
}


def shrani(mreza: Mreza, pot: str | pathlib.Path) -> pathlib.Path:
    """Izbere zapis po končnici (.stl, .obj, .glb)."""
    koncnica = pathlib.Path(pot).suffix.lower()
    pisalnik = PISALNIKI.get(koncnica)
    if pisalnik is None:
        raise ValueError(f"nepodprt zapis {koncnica!r} "
                         f"(podprto: {', '.join(sorted(PISALNIKI))})")
    return pisalnik(mreza, pot)
