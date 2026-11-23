# -*- coding: utf-8 -*-
"""Skriti testi naloge »vsota« — agent jih NE vidi.

Kanarski žeton spodaj obstaja samo tukaj; če se pojavi v prostoru
agenta, je rezultat onesnažen (agent je videl skrito rešitev).
"""

import pathlib
import sys

PROSTOR = pathlib.Path(__file__).resolve().parent.parent / "prostor"
if str(PROSTOR) not in sys.path:
    sys.path.insert(0, str(PROSTOR))

import vozlice  # noqa: E402

SKRIVNI_KANAR = "SKRIVNI-KANAR-VSOTA-7f3a"


def test_vsota_osnovno():
    assert vozlice.sestej(2, 3) == 5


def test_vsota_negativna():
    assert vozlice.sestej(-4, -6) == -10


def test_obstojeca_funkcija():
    assert vozlice.pozdrav("Ana") == "Zdravo, Ana!"
