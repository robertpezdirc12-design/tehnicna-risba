# -*- coding: utf-8 -*-
"""F4 (issue #5): pilot novih vrst ograj — deklarativna polja, količine,
predogled.

Ročno izračunani primer (default): sirina 6000, deska 140, vrzel 20
-> korak 160; n_desk = floor((6000+20)/160) = 37; razmak stebrov 2000
-> n_polj = 3, n_stebrov = 4; letve = 3 polja × 2 = 6;
vijaki = 37 × 2 × 2 = 148; sidra = 4 × 2 = 8.
"""
import os


import nova_vrsta


def test_deklarativna_polja_imajo_oznake():
    for ime, oznaka, enota, privzeto, opis in nova_vrsta.POLJA:
        assert ime and oznaka and enota      # NIČ polj brez oznak (U3)
        assert isinstance(privzeto, (int, float))
        assert opis


def test_kolicine_rocni_izracun():
    k = nova_vrsta.kolicine({})
    assert k["n_desk"] == 37                 # floor((6000+20)/160)
    assert k["n_polj"] == 3                  # ceil(6000/2000)
    assert k["n_stebrov"] == 4
    assert k["n_letvi"] == 6                 # 3 polja × 2 letvi
    assert k["vijaki"] == 148                # 37 desk × 2 letvi × 2 vijaka
    assert k["sidra"] == 8                   # 4 stebri × 2


def test_preveri_z_znackami_polj():
    napake = nova_vrsta.preveri({"visina": -5, "letve": 9})
    assert any("Višina ograje" in n for n in napake)     # oznaka, ne ključ
    assert any("vodoravnih letvi" in n for n in napake)
    assert nova_vrsta.preveri({}) == []                  # default veljaven


def test_preview_ustvari_png(tmp_path):
    pot = str(tmp_path / "predogled.png")
    pot2, k = nova_vrsta.preview({}, pot)
    assert pot2 == pot
    assert os.path.getsize(pot) > 5000                   # slika res nastane
    assert k["tip"] == nova_vrsta.IME