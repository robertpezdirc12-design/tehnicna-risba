"""Orodja, ki uporabljajo vozlice (večdatotečna naloga)."""

from __future__ import annotations

from vozlice import sestej


def povprecje(vrednosti):
    raise NotImplementedError("povprecje")


def vsota_in_povprecje(vrednosti):
    return sestej(len(vrednosti), 0), povprecje(vrednosti)
