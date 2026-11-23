# -*- coding: utf-8 -*-
"""Skriti testi naloge »razlika«."""

import pathlib
import sys

PROSTOR = pathlib.Path(__file__).resolve().parent.parent / "prostor"
if str(PROSTOR) not in sys.path:
    sys.path.insert(0, str(PROSTOR))

import vozlice  # noqa: E402


def test_odstej_osnovno():
    assert vozlice.odstej(9, 4) == 5


def test_odstej_negativno():
    assert vozlice.odstej(3, 8) == -5


def test_sestej_ostane():
    assert vozlice.sestej(10, 5) == 15
