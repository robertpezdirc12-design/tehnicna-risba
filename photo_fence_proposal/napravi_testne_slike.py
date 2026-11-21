"""photo_fence_proposal — generator testnih fotografij z ZNANIMI merami.

Ker v repozitoriju NI resničnih fotografij starih ograj, se za merjenje
napake zaznavanja in kalibracije ustvarijo sintetični prizori z:
- perspektivnim nagibom, sencami, šumom in svetlobnim gradientom
- ZAPISANIMI resničnimi merami v .json (za izračun napake v testih)

Poštenost: sintetični primeri NE nadomestijo terenskih fotografij —
rezultati na njih merijo napako algoritma v nadzorovanih pogojih.
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np


def narisi_prizor(pot: str, dolzina_mm: float = 6000.0, visina_mm: float = 1800.0,
                  st_polj: int = 3, nagib: float = 0.0, sem: int = 7) -> dict:
    """Nariše fotografiji podoben prizor ograje in zapiše resnične mere."""
    rng = np.random.default_rng(sem)
    sirina, visina = 1280, 860
    slika = np.full((visina, sirina, 3), 205, dtype=np.uint8)

    # svetlobni gradient (nebo/tla)
    for y in range(visina):
        slika[y, :] = np.clip(205 + 30 * (y / visina - 0.5), 140, 235)

    # ograja: v mm → px prek lestvice (znano!)
    lestvica = min(0.16, (sirina * 0.8) / dolzina_mm)  # px na mm
    sirina_ograje_px = dolzina_mm * lestvica
    visina_ograje_px = visina_mm * lestvica
    x0 = (sirina - sirina_ograje_px) / 2
    y1 = visina * 0.72
    y0 = y1 - visina_ograje_px

    # nagib (perspektiva — oteži zaznavanje)
    premik = np.tan(np.radians(nagib)) * visina_ograje_px / 2

    barva_ograje = (70, 80, 95)

    # polja + pokončne deske
    korak_polja = sirina_ograje_px / st_polj
    for i in range(st_polj):
        px0 = x0 + i * korak_polja + premik
        px1 = x0 + (i + 1) * korak_polja - premik
        # deske
        x = px0 + 4
        while x < px1 - 4:
            cv2.line(slika, (int(x), int(y0 + premik * 0.2)),
                     (int(x), int(y1 - premik * 0.2)), barva_ograje, 4)
            x += 14
        # vodoravni letvi (zgoraj in spodaj)
        cv2.line(slika, (int(px0), int(y0 + premik * 0.2)),
                 (int(px1), int(y0 + premik * 0.2)), (50, 60, 75), 6)
        cv2.line(slika, (int(px0), int(y1 - premik * 0.2)),
                 (int(px1), int(y1 - premik * 0.2)), (50, 60, 75), 6)

    # stebri (na robovih polj)
    for i in range(st_polj + 1):
        x = x0 + i * korak_polja
        cv2.rectangle(slika, (int(x - 6), int(y0 - 10)), (int(x + 6), int(y1 + 10)),
                      (35, 40, 50), -1)

    # senca (diagonalni gradient čez ograjo)
    maska = np.zeros((visina, sirina), dtype=np.uint8)
    cv2.rectangle(maska, (int(x0), int(y0)), (int(x0 + sirina_ograje_px), int(y1)),
                  60, -1)
    senca = cv2.GaussianBlur(maska, (81, 81), 0).astype(np.int16)
    slika = np.clip(slika.astype(np.int16) - (senca[:, :, None] // 3), 0,
                    255).astype(np.uint8)

    # šum + mehka svetloba
    sum = rng.normal(0, 6, slika.shape).astype(np.int16)
    slika = np.clip(slika.astype(np.int16) + sum, 0, 255).astype(np.uint8)
    slika = cv2.GaussianBlur(slika, (3, 3), 0)

    cv2.imwrite(pot, slika)
    resni = {
        "dolzina_ograje": dolzina_mm,
        "visina_ograje": visina_mm,
        "stevilo_polj": st_polj,
        "lestvica_px_na_mm": lestvica,
        "nagib_stopinj": nagib,
    }
    with open(pot + ".json", "w", encoding="utf-8") as f:
        json.dump(resni, f, ensure_ascii=False, indent=2)
    return resni


if __name__ == "__main__":
    mapa = os.path.join(os.path.dirname(__file__), "testni_primeri")
    os.makedirs(mapa, exist_ok=True)
    primeri = [
        ("prizor_cel.json", dict(dolzina_mm=6000, visina_mm=1800, st_polj=3,
                                 nagib=0.0, sem=1)),
        ("prizor_nagib.json", dict(dolzina_mm=5000, visina_mm=1700, st_polj=2,
                                   nagib=8.0, sem=2)),
        ("prizor_ozek.json", dict(dolzina_mm=3000, visina_mm=1500, st_polj=1,
                                  nagib=3.0, sem=3)),
        ("prizor_dolg.json", dict(dolzina_mm=9000, visina_mm=1800, st_polj=5,
                                  nagib=5.0, sem=4)),
        ("prizor_nizek.json", dict(dolzina_mm=4000, visina_mm=1000, st_polj=2,
                                   nagib=0.0, sem=5)),
    ]
    for ime, parametri in primeri:
        pot = os.path.join(mapa, ime.replace(".json", ".png"))
        resni = narisi_prizor(pot, **parametri)
        print(f"{os.path.basename(pot)}: {resni}")