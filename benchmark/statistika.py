# -*- coding: utf-8 -*-
"""Statistika ocenjevanja — vse deterministično (zrno je obvezen vhod).

Zakaj ravno te metode (javna praksa, glej docs/benchmark-modelov.md):
- pass@k: nepristranska ocena Chen idr. (HumanEval), ne surovi delež —
  pri več poskusih na nalogo ne precenjuje.
- Wilsonov interval: interval zaupanja za delež pri majhnem n.
- Parni bootstrap: interval za razliko dveh modelov na ISTIH nalogah.
- McNemar: test na neskl adjenih parih (kjer se modela razlikujeta).
- Znakovni test: točen test za majhne serije, kjer bootstrap ni zanesljiv.

Vse funkcije so čiste (brez globalnega stanja) in ponovljive.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

Z95 = 1.959963984540054


def pass_at_k(n: int, c: int, k: int) -> float:
    """Nepristranski pass@k: 1 - C(n-c, k) / C(n, k).

    n = število poskusov na nalogo, c = število uspešnih poskusov.
    Velja za k <= n; pri c = 0 je 0.0, pri n - c < k je 1.0.
    """
    if n <= 0:
        raise ValueError("n mora biti pozitivno")
    if k <= 0 or k > n:
        raise ValueError(f"k mora biti v [1, n] (n={n}, k={k})")
    if c < 0 or c > n:
        raise ValueError(f"c mora biti v [0, n] (n={n}, c={c})")
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def povprecni_pass_at_k(
    poskusi: Sequence[tuple[int, int]], k: int,
) -> float:
    """Povprečje pass@k čez naloge; vsaka naloga = (n, c)."""
    if not poskusi:
        raise ValueError("seznam nalog je prazen")
    return sum(pass_at_k(n, c, k) for n, c in poskusi) / len(poskusi)


def wilson_interval(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilsonov interval zaupanja za delež k/n (nikoli zunaj [0, 1])."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    imenovalec = 1.0 + z * z / n
    sredina = (p + z * z / (2.0 * n)) / imenovalec
    polsirina = (
        z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / imenovalec
    )
    return (max(0.0, sredina - polsirina), min(1.0, sredina + polsirina))


def mcnemar_exact(b: int, c: int) -> float:
    """Dvostranski točni McNemarjev test.

    b = pari, kjer je uspel samo model A; c = samo model B.
    p = min(1, 2 · P(X <= min(b, c))), X ~ Bin(b + c, 1/2).
    Pari, kjer sta oba uspela ali oba padla, ne povedo ničesar.
    """
    if b < 0 or c < 0:
        raise ValueError("b in c morata biti nenegativna")
    n = b + c
    if n == 0:
        return 1.0
    m = min(b, c)
    rep = sum(math.comb(n, i) for i in range(m + 1))
    return min(1.0, 2.0 * rep / (2 ** n))


def bootstrap_razlika(
    a: Sequence[float],
    b: Sequence[float],
    ponovitve: int = 10_000,
    zrno: int = 42,
) -> tuple[float, float, float]:
    """Parni bootstrap za razliko B − A (95 % interval + točka).

    Vrne (spodnja, zgornja, ocena). Resampling je parni: iste naloge
    se vzorčijo za oba modela, zato je razlika smiselna tudi pri majhnem n.
    """
    if len(a) != len(b):
        raise ValueError("seriji morata biti enako dolgi (parni test)")
    if not a:
        raise ValueError("serija je prazna")
    if ponovitve <= 0:
        raise ValueError("ponovitve morajo biti pozitivne")
    razlike = [float(y) - float(x) for x, y in zip(a, b)]
    ocena = sum(razlike) / len(razlike)
    rng = random.Random(zrno)
    n = len(razlike)
    vzorci: list[float] = []
    for _ in range(ponovitve):
        vsota = 0.0
        for _ in range(n):
            vsota += razlike[rng.randrange(n)]
        vzorci.append(vsota / n)
    vzorci.sort()
    spodnja = vzorci[int(0.025 * (ponovitve - 1))]
    zgornja = vzorci[int(0.975 * (ponovitve - 1))]
    return (spodnja, zgornja, ocena)


def znakovni_test(
    a: Sequence[float],
    b: Sequence[float],
    zrno: int = 42,
    monte_karlo: int = 20_000,
) -> float:
    """Točni znakovni test za parne razlike (B − A).

    Pod ničelno hipotezo je predznak vsake razlike enako verjeten.
    n <= 20: točno (dinamično programiranje po vsotah, brez 2^n zanke).
    n > 20: Monte Carlo z danim zrnom (ocena, ne točna vrednost).
    """
    if len(a) != len(b):
        raise ValueError("seriji morata biti enako dolgi (parni test)")
    if not a:
        raise ValueError("serija je prazna")
    razlike = [float(y) - float(x) for x, y in zip(a, b)]
    if all(d == 0.0 for d in razlike):
        return 1.0
    opazovana = abs(sum(razlike))

    if len(razlike) <= 20:
        # porazdelitev vsot pod naključnimi predznaki
        porazdelitev: dict[float, int] = {0.0: 1}
        for d in razlike:
            nova: dict[float, int] = {}
            for vsota, stevilo in porazdelitev.items():
                for kandidat in (vsota + d, vsota - d):
                    nova[kandidat] = nova.get(kandidat, 0) + stevilo
            porazdelitev = nova
        skupaj = 2 ** len(razlike)
        ekstremnih = sum(
            stevilo for vsota, stevilo in porazdelitev.items()
            if abs(vsota) >= opazovana - 1e-12
        )
        return ekstremnih / skupaj

    rng = random.Random(zrno)
    ekstremnih_mk = 0
    for _ in range(monte_karlo):
        vsota = 0.0
        for d in razlike:
            vsota += d if rng.random() < 0.5 else -d
        if abs(vsota) >= opazovana - 1e-12:
            ekstremnih_mk += 1
    return ekstremnih_mk / monte_karlo


def primerjaj(
    a: Sequence[bool], b: Sequence[bool], zrno: int = 42,
) -> dict[str, float]:
    """Povzetek primerjave dveh modelov na ISTIH nalogah (parno)."""
    if len(a) != len(b):
        raise ValueError("seriji morata biti enako dolgi (parni test)")
    if not a:
        raise ValueError("serija je prazna")
    xa = [1.0 if v else 0.0 for v in a]
    xb = [1.0 if v else 0.0 for v in b]
    samo_a = sum(1 for x, y in zip(a, b) if x and not y)
    samo_b = sum(1 for x, y in zip(a, b) if y and not x)
    spodnja, zgornja, ocena = bootstrap_razlika(xa, xb, zrno=zrno)
    return {
        "uspeh_a": sum(a) / len(a),
        "uspeh_b": sum(b) / len(b),
        "razlika": ocena,
        "razlika_ci_2_5": spodnja,
        "razlika_ci_97_5": zgornja,
        "samo_a": float(samo_a),
        "samo_b": float(samo_b),
        "p_mcnemar": mcnemar_exact(samo_a, samo_b),
        "p_znakovni": znakovni_test(xa, xb, zrno=zrno),
        "n": float(len(a)),
    }
