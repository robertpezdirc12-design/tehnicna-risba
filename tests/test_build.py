# -*- coding: utf-8 -*-
"""Kakovostna vrata izdaje: različica in vsebina EXE.

Dve napaki, ki ju je vredno preprečiti trajno:
1. `posodobitev.VERZIJA` je obstala na 1.2, zato je GUI ponujal
   posodobitev na različico, ki je bila že nameščena.
2. EXE je bil 312 MB, ker je PyInstaller za OCR potegnil torch —
   izločitve v `.spec` so zdaj testirane, ne le zapisane v dokumentaciji.
"""
from __future__ import annotations

import ast
import pathlib
import tomllib

import posodobitev

REPO = pathlib.Path(__file__).resolve().parents[1]


def _najnovejsa_izdaja():
    for vrstica in (REPO / "CHANGELOG.md").read_text(
            encoding="utf-8").splitlines():
        if vrstica.startswith("## v"):
            return vrstica.split()[1].lstrip("v")
    raise AssertionError("CHANGELOG nima nobene izdaje")


def test_verzija_usklajena_na_treh_mestih():
    with open(REPO / "pyproject.toml", "rb") as f:
        projekt = tomllib.load(f)["project"]["version"]
    izdaja = _najnovejsa_izdaja()
    assert posodobitev.VERZIJA == projekt == izdaja, (
        "posodobitev.VERZIJA, pyproject.toml in CHANGELOG se razhajajo: "
        f"{posodobitev.VERZIJA} / {projekt} / {izdaja}")


def _izloki_iz_spec():
    drevo = ast.parse((REPO / "TehnicnaRisba.spec").read_text(
        encoding="utf-8"))
    for vozel in ast.walk(drevo):
        if (isinstance(vozel, ast.Call)
                and isinstance(vozel.func, ast.Name)
                and vozel.func.id == "Analysis"):
            for kljuc in vozel.keywords:
                if kljuc.arg == "excludes":
                    return {e.value for e in kljuc.value.elts
                            if isinstance(e, ast.Constant)}
    raise AssertionError("v TehnicnaRisba.spec ni Analysis(excludes=...)")


def test_spec_izloci_ocr_verigo():
    izloki = _izloki_iz_spec()
    for ime in ("rapidocr_onnxruntime", "onnxruntime", "transformers",
                "torch", "pandas"):
        assert ime in izloki, f"{ime} ni v excludes (EXE bi spet narasel)"


def _imena_paketov(datoteka):
    imena = set()
    for vrstica in (REPO / datoteka).read_text(encoding="utf-8").splitlines():
        vrstica = vrstica.split("#", 1)[0].strip()
        if not vrstica:
            continue
        ime = vrstica
        for locilo in ("[", " ", "<", ">", "=", "!", "~", ";"):
            ime = ime.split(locilo, 1)[0]
        imena.add(ime.strip().lower())
    return imena


def test_ocr_ni_v_izdelku_je_pa_v_razvojnih_zahtevah():
    izdelek = _imena_paketov("requirements.txt")
    razvoj = _imena_paketov("requirements-dev.txt")
    for paket in ("rapidocr-onnxruntime", "onnxruntime", "torch"):
        assert paket not in izdelek, f"{paket} ne sodi v requirements.txt"
    assert "rapidocr-onnxruntime" in razvoj
    assert "rapidocr" in (REPO / "THIRD_PARTY_NOTICES.md").read_text(
        encoding="utf-8").lower()