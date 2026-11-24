# -*- coding: utf-8 -*-
"""Preverjanje obvestil o licencah (PyInstaller odreže priložena besedila)."""

from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import preveri_licence as pl  # noqa: E402


def test_obvestilo_je_usklajeno():
    assert pl.OBVESTILO.is_file()
    assert pl.preveri() == 0


def test_tabela_vsebuje_vse_zahteve_in_opencv():
    tabela = pl.tabela()
    for ime in pl._paketi():
        assert f"| {ime} |" in tabela, f"v tabeli manjka {ime}"
    assert "| opencv-python |" in tabela
    assert "PyInstaller" in tabela


def test_vsak_paket_ima_dokumentirano_licenco():
    for ime in pl._paketi():
        assert ime.lower() in pl.V_EXE, f"{ime} ni v V_EXE"
        assert "NEZNANO" not in pl._licenca(ime)[1]


def test_odkrije_razliko(monkeypatch, tmp_path):
    vsebina = pl.OBVESTILO.read_text(encoding="utf-8")
    pokvarjeno = vsebina.replace("| numpy |", "| numpy-stara-razlicica |")
    cilj = tmp_path / "obvestilo.md"
    cilj.write_text(pokvarjeno, encoding="utf-8")
    monkeypatch.setattr(pl, "OBVESTILO", cilj)
    assert pl.preveri() == 1


def test_zapisi_brez_oznak_opozori(monkeypatch, tmp_path):
    cilj = tmp_path / "brez.md"
    cilj.write_text("brez oznak", encoding="utf-8")
    monkeypatch.setattr(pl, "OBVESTILO", cilj)
    assert pl.zapisi() == 2
    assert pl.preveri() == 2


def test_main_brez_argumentov_vrne_napako():
    assert pl.main([]) == 2
