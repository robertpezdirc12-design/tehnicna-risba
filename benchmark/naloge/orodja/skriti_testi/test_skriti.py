# -*- coding: utf-8 -*-
"""Skriti testi naloge »povprecje« (večdatotečni popravek)."""

import pathlib
import sys

PROSTOR = pathlib.Path(__file__).resolve().parent.parent / "prostor"
if str(PROSTOR) not in sys.path:
    sys.path.insert(0, str(PROSTOR))

import orodja  # noqa: E402
import vozlice  # noqa: E402


def test_povprecje_osnovno():
    assert orodja.povprecje([2, 4]) == 3


def test_povprecje_en_element():
    assert orodja.povprecje([7]) == 7


def test_sestej_ostane():
    assert vozlice.sestej(1, 2) == 3
