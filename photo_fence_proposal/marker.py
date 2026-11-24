# -*- coding: utf-8 -*-
"""ArUco marker kot merilo v ravnini ograje (brez AI, brez mreže).

Zakaj marker: iz štirih kotov same ograje širine NI mogoče izračunati —
pravokotnik razmerja 6:1 od daleč in pravokotnik 3:1 pod drugim kotom dasta
isto sliko (geometrijska nedoločenost). Marker znane velikosti v isti
ravnini to odpravi: njegove 4 točke določijo homografijo ravnine v mm,
zato sta dolžina in višina ograje merljivi tudi pri poševnem posnetku.

Uporaba: natisni marker (shrani_list), prilepi ga na ograjo (v isto
ravnino!), fotografiraj tako, da je viden, in v programu podaj 4 kote
ograje. Napaka meritve je reda velikosti napake zaznave kotov markerja
(1–3 %).
"""
from __future__ import annotations

import cv2
import numpy as np

SLIKAR = cv2.aruco.DICT_4X4_50
ID_MARKERJA = 0
STRANICA_MM = 150.0      # privzeta stranica natisnjenega markerja
MIN_STRANICA_PX = 60     # manjši marker v sliki ni zanesljiv
DOBRA_STRANICA_PX = 120  # pod to velikostjo je napaka lahko nekaj %


def ustvari_marker(stranica_px: int = 600,
                   obroba_px: int = 80) -> np.ndarray:
    """BGR slika markerja z belo obrobo (tiha cona za zaznavo)."""
    slovar = cv2.aruco.getPredefinedDictionary(SLIKAR)
    jedro = cv2.aruco.generateImageMarker(slovar, ID_MARKERJA, stranica_px)
    jedro = cv2.copyMakeBorder(jedro, obroba_px, obroba_px, obroba_px,
                               obroba_px, cv2.BORDER_CONSTANT, value=255)
    return cv2.cvtColor(jedro, cv2.COLOR_GRAY2BGR)


def shrani_list(pot: str, stranica_mm: float = STRANICA_MM,
                dpi: int = 300) -> str:
    """Shrani A4 list z markerjem v NATANČNI velikosti (mm) za tisk."""
    if not (30.0 <= stranica_mm <= 190.0):
        raise ValueError("stranica markerja mora biti med 30 in 190 mm "
                         "(A4)")
    mm_na_px = dpi / 25.4
    a4 = (int(round(210 * mm_na_px)), int(round(297 * mm_na_px)))
    list_ = np.full((a4[1], a4[0], 3), 255, np.uint8)
    stranica_px = int(round(stranica_mm * mm_na_px))
    obroba = max(8, int(round(10 * mm_na_px)))      # 10 mm tiha cona
    slovar = cv2.aruco.getPredefinedDictionary(SLIKAR)
    jedro = cv2.aruco.generateImageMarker(slovar, ID_MARKERJA, stranica_px)
    jedro = cv2.copyMakeBorder(jedro, obroba, obroba, obroba, obroba,
                               cv2.BORDER_CONSTANT, value=255)
    jedro = cv2.cvtColor(jedro, cv2.COLOR_GRAY2BGR)
    y = int(round(40 * mm_na_px))
    x = (a4[0] - jedro.shape[1]) // 2
    list_[y:y + jedro.shape[0], x:x + jedro.shape[1]] = jedro
    cv2.putText(list_, f"ArUco marker - natisni v merilu 1:1 "
                f"(stranica {stranica_mm:.0f} mm)",
                (int(30 * mm_na_px), int(25 * mm_na_px)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(list_, "Preveri ravnilo na listu: crta spodaj je 100 mm.",
                (int(30 * mm_na_px), int(285 * mm_na_px)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    merilo_x = int(30 * mm_na_px)
    merilo_y = int(290 * mm_na_px)
    cv2.line(list_, (merilo_x, merilo_y),
             (merilo_x + int(100 * mm_na_px), merilo_y), (0, 0, 0), 2)
    cv2.imwrite(pot, list_)
    return pot


def zaznaj_marker(slika: np.ndarray) -> np.ndarray | None:
    """Vrne 4 kote markerja (TL, TR, BR, BL) ali None.

    Uporablja podpikselno izboljšavo kotov: brez nje je pri markerju,
    velikem ~70 px, napaka meritve tudi 5–8 %, z njo 1–3 %.
    """
    if slika is None or slika.size == 0:
        return None
    slovar = cv2.aruco.getPredefinedDictionary(SLIKAR)
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.cornerRefinementWinSize = 5
    params.cornerRefinementMaxIterations = 50
    params.cornerRefinementMinAccuracy = 0.01
    detektor = cv2.aruco.ArucoDetector(slovar, params)
    koti, ids, _ = detektor.detectMarkers(slika)
    if ids is None or len(koti) == 0:
        return None
    for i, id_ in enumerate(ids.ravel()):
        if int(id_) != ID_MARKERJA:
            continue
        vogali = koti[i].reshape(-1, 2).astype(np.float32)
        stranica = float(np.linalg.norm(vogali[1] - vogali[0]))
        if stranica < MIN_STRANICA_PX:
            continue
        return vogali
    return None


def stranica_px(koti_markerja: np.ndarray) -> float:
    """Povprečna stranica markerja v pikslih (za oceno natančnosti)."""
    q = np.asarray(koti_markerja, dtype=np.float64)
    return float(np.mean([np.linalg.norm(q[(i + 1) % 4] - q[i])
                          for i in range(4)]))


def homografija_ravnine(koti_markerja: np.ndarray,
                        stranica_mm: float = STRANICA_MM) -> np.ndarray:
    """Homografija ravnina (mm) → slika (px) iz 4 kotov markerja."""
    if stranica_mm <= 0:
        raise ValueError("stranica markerja mora biti pozitivna (mm)")
    mm = np.asarray([[0.0, 0.0], [stranica_mm, 0.0],
                     [stranica_mm, stranica_mm], [0.0, stranica_mm]],
                    dtype=np.float32)
    return cv2.getPerspectiveTransform(mm, np.asarray(koti_markerja,
                                                     dtype=np.float32))


def izmeri_kvadrilateral(kvadrat_px, koti_markerja: np.ndarray,
                         stranica_mm: float = STRANICA_MM
                         ) -> tuple[float, float] | None:
    """Izmeri pravokotnik ograje v mm (širina, višina) prek markerja.

    kvadrat_px: 4 koti ograje (TL, TR, BR, BL) v pikslih.
    Vrne None, kadar geometrija ni veljavna (degeneriran marker).
    """
    if kvadrat_px is None or len(kvadrat_px) != 4:
        return None
    try:
        H = homografija_ravnine(koti_markerja, stranica_mm)
        if abs(np.linalg.det(H)) < 1e-12:
            return None
        Hi = np.linalg.inv(H)
    except (np.linalg.LinAlgError, ValueError):
        return None
    q = np.asarray(kvadrat_px, dtype=np.float32).reshape(-1, 1, 2)
    mm = cv2.perspectiveTransform(q, Hi).reshape(-1, 2)
    if not np.all(np.isfinite(mm)):
        return None
    sirina = 0.5 * (np.linalg.norm(mm[1] - mm[0])
                    + np.linalg.norm(mm[2] - mm[3]))
    visina = 0.5 * (np.linalg.norm(mm[3] - mm[0])
                    + np.linalg.norm(mm[2] - mm[1]))
    if sirina <= 0 or visina <= 0:
        return None
    return float(sirina), float(visina)


def main(argv=None) -> int:
    """CLI: natisni A4 list z markerjem (`python marker.py --izhod ...`)."""
    import argparse

    p = argparse.ArgumentParser(
        prog="marker",
        description="Pripravi A4 list z ArUco markerjem za merjenje ograje")
    p.add_argument("--izhod", default="marker-ograja.png",
                   help="kam shraniti list (PNG, 300 dpi)")
    p.add_argument("--stranica-mm", type=float, default=STRANICA_MM,
                   help=f"stranica markerja v mm (privzeto {STRANICA_MM:.0f})")
    args = p.parse_args(argv)
    try:
        pot = shrani_list(args.izhod, args.stranica_mm)
    except ValueError as e:
        print(f"NAPAKA: {e}")
        return 2
    print(f"Marker shranjen: {pot}")
    print("Natisni v merilu 1:1 (brez 'prilagodi strani'), preveri "
          "100-mm crto, prilepi marker v RAVNINO ograje in fotografiraj "
          "tako, da je viden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def poravnaj_ravnino(slika: np.ndarray, koti_markerja: np.ndarray,
                     obmocje_px, stranica_mm: float = STRANICA_MM,
                     mm_na_px: float = 0.5) -> tuple[np.ndarray, float]:
    """Zravnaj ravnino ograje v merilo mm/px (za štetje in risanje)."""
    H = homografija_ravnine(koti_markerja, stranica_mm)
    q = np.asarray(obmocje_px, dtype=np.float32).reshape(-1, 1, 2)
    Hi = np.linalg.inv(H)
    mm = cv2.perspectiveTransform(q, Hi).reshape(-1, 2)
    x0, y0 = np.floor(mm.min(axis=0))
    x1, y1 = np.ceil(mm.max(axis=0))
    T = np.array([[mm_na_px, 0, -x0 * mm_na_px],
                  [0, mm_na_px, -y0 * mm_na_px],
                  [0, 0, 1.0]], dtype=np.float64)
    M = T @ Hi
    W = max(8, int(round((x1 - x0) * mm_na_px)))
    Hh = max(8, int(round((y1 - y0) * mm_na_px)))
    return cv2.warpPerspective(slika, M, (W, Hh), flags=cv2.INTER_LINEAR), mm_na_px
