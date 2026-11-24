# -*- coding: utf-8 -*-
"""Uporabniški vnos kotov: skupna, preprosta razčlenitev (brez odvisnosti).

Oblika: `x,y;x,y;x,y;x,y` — 4 koti ograje v vrstnem redu TL, TR, BR, BL.
Ločila med točkami so `;` ali `|`, decimalke so lahko s piko ali vejico.
"""
from __future__ import annotations


def razcleni_kote(besedilo: str) -> list[tuple[float, float]]:
    """Razčleni 4 kote iz besedila; ValueError z razumljivim sporočilom."""
    if not besedilo or not str(besedilo).strip():
        raise ValueError("Vnos kotov je prazen")
    kos = str(besedilo).replace("|", ";").split(";")
    kos = [k.strip() for k in kos if k.strip()]
    if len(kos) != 4:
        raise ValueError(
            f"Potrebni so natanko 4 koti v obliki 'x,y;x,y;x,y;x,y' "
            f"(dobljenih {len(kos)})")
    tocke: list[tuple[float, float]] = []
    for i, k in enumerate(kos, 1):
        deli = [d.strip() for d in k.split(",")]
        if len(deli) != 2:
            raise ValueError(
                f"{i}. kot mora biti v obliki 'x,y' (dobljeno {k!r})")
        try:
            x = float(deli[0].replace(",", "."))
            y = float(deli[1].replace(",", "."))
        except ValueError:
            raise ValueError(
                f"{i}. kot ni število (dobljeno {k!r})") from None
        tocke.append((x, y))
    return tocke