"""Testi rektifikacije (photo_fence_proposal) — skala, VP, varovalke.

Matematika merjenja je jedro poštenosti »brez ugibanja«: skala/statusi,
točke izginjanja (VP) in fallbacki morajo biti zaklenjeni z testi.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import numpy as np

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PFP = os.path.join(_HERE, "photo_fence_proposal")
for _p in (PFP, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cv2  # noqa: E402
import rektifikacija  # noqa: E402


def _prazna_slika(w=640, h=480):
    return np.full((h, w), 200, dtype=np.uint8)


# --------------------------------------------------------------- skala_mm


def test_skala_referenca_visina():
    ritem = {"debelina_px": 2.0, "pitch_px": 5.0, "n_lamel": 10}
    mm_na_px, mera = rektifikacija.skala_mm(
        ritem, ("visina_ograje", 1800.0), visina_slike_px=300.0)
    assert mm_na_px == 6.0
    assert mera.status == "izmerjeno"
    assert mera.vrednost_mm == 1800.0


def test_skala_referenca_brez_visine_slike_pade_na_standard():
    """Brez visina_slike_px referenca NI izrabljena (brez ugibanja)
    — skala pade na standardno lamelo, status ostane ocenjeno."""
    ritem = {"debelina_px": 2.0}
    mm_na_px, mera = rektifikacija.skala_mm(ritem, ("visina_ograje", 1800.0))
    assert mera.status == "ocenjeno"
    assert mm_na_px is not None and mera.vrednost_mm is not None
    assert mm_na_px * ritem["debelina_px"] == mera.vrednost_mm


def test_skala_neznana_referenca_pade_na_standard():
    ritem = {"debelina_px": 2.0}
    mm_na_px, mera = rektifikacija.skala_mm(ritem, ("dolzina_ograje", 4500.0))
    assert mera.status == "ocenjeno"
    assert mm_na_px is not None


def test_skala_brez_ritma_neznana():
    mm_na_px, mera = rektifikacija.skala_mm({})
    assert mm_na_px is None
    assert mera.status == "neznano"
    assert mera.vrednost_mm is None


# ------------------------------------------------------- točke izginjanja


def _druzina_skoci(tocka, tocke_izhodisc, navpicno):
    """Premice skozi skupno točko (VP): p = točka na premici, d = smer."""
    linije = []
    for t in tocke_izhodisc:
        d = np.asarray(tocka, dtype=float) - np.asarray(t, dtype=float)
        d /= np.linalg.norm(d)
        linije.append((np.asarray(t, dtype=float), d))
    return linije


def test_vp_ransac_z_outlierji():
    vp = (100.0, 200.0)
    linije = _druzina_skoci(vp, [(0.0, 0.0), (0.0, 50.0), (0.0, 100.0),
                                 (0.0, 300.0), (10.0, 400.0)], False)
    # outlierja — popolnoma drugačni smeri, skozi drugi točki
    linije += _druzina_skoci((500.0, 50.0), [(0.0, 400.0), (30.0, 30.0)], False)
    kand = rektifikacija.vp_ransac(linije)
    assert kand is not None
    assert abs(kand[0] - vp[0]) < 5.0
    assert abs(kand[1] - vp[1]) < 5.0


def test_vp_ransac_malo_premic():
    assert rektifikacija.vp_ransac([((0.0, 0.0), (1.0, 0.0))]) is None


def test_iscisce_unicenja_presecisce():
    linije = _druzina_skoci((10.0, 20.0), [(0.0, 0.0), (0.0, 5.0),
                                           (2.0, 0.0)], False)
    v = rektifikacija._iscisce_unicenja(linije)
    assert v is not None
    assert abs(v[0] - 10.0) < 1e-6 and abs(v[1] - 20.0) < 1e-6


def test_iscisce_unicenja_vzporedne():
    """Popolnoma vzporedne premice nimajo presečišča — None, ne napaka."""
    linije = [(np.array([0.0, float(i)]), np.array([1.0, 0.0]))
              for i in range(3)]
    assert rektifikacija._iscisce_unicenja(linije) is None


# --------------------------------------------------- homografija_pogleja


def test_homografija_premalo_premic():
    H, meta = rektifikacija.homografija_pogleja(_prazna_slika())
    assert H is None
    assert "Premoč malo premic" in meta["opozorilo"]


def _perspektivna_slika(vh, vv, w: int = 1024, h: int = 768):
    """Slika z dvema pravokotnima družinama premic (vh vodoravni VP,
    vv navpični VP) — sintetičen pogled v perspektivo."""
    slika = np.full((h, w), 255, dtype=np.uint8)
    # cv2.line: stub overload ne sprejme numpy unsignedinteger[_8Bit]
    # (== uint8 v numpy 1.26) — resnična vrzel v stubu, ne v kodi.
    crta: Any = cv2.line
    # navpične: skozi vv (vprednost y je lahko zunaj slike)
    for x_i in range(80, w - 40, 120):
        t = (h - 1) / vv[1]          # vv je lahko zunaj slike (y < 0)
        x_d = x_i + (vv[0] - x_i) * t
        crta(slika, (int(x_i), 0), (int(x_d), h - 1), 0, 2)
    # vodoravne: skozi vh
    for y_i in range(120, h - 80, 90):
        m = (vh[1] - y_i) / (vh[0] - 0.0)
        y_d = int(y_i + m * (w - 1))
        crta(slika, (0, int(y_i)), (w - 1, y_d), 0, 2)
    return slika


def test_homografija_perspektiva_vrne_H():
    vh = (900.0, 384.0)
    vv = (400.0, -2000.0)   # daleč zgoraj — pravokotno na vh
    slika = _perspektivna_slika(vh, vv)
    H, meta = rektifikacija.homografija_pogleja(slika)
    assert H is not None
    assert np.all(np.isfinite(H))
    assert float(meta["gorisce"]) > 0


def test_homografija_nepravokotni_vp_zavrnjen():
    """Če točki izginjanja nista pravokotni (f² ≤ 0), VP ni metričen —
    zavrnitev z opozorilom, ne tiha uporaba."""
    vh = (800.0, 384.0)
    vv = (900.0, 5000.0)    # ista stran kot vh → nepravokotno
    slika = _perspektivna_slika(vh, vv)
    H, meta = rektifikacija.homografija_pogleja(slika)
    assert H is None
    assert "nista pravokotni" in meta["opozorilo"]


# ---------------------------------------------------------- rektificiraj


def test_rektificiraj_brez_obmocja():
    slika = _prazna_slika()
    rect, H, meta = rektifikacija.rektificiraj(slika, None)
    assert H is None
    assert meta["rektificirano"] is False
    assert any("ni zaznana" in o for o in meta["opozorila"])
    assert rect.shape == slika.shape


def test_rektificiraj_premajhno_obmocje():
    slika = _prazna_slika()
    rect, H, meta = rektifikacija.rektificiraj(
        slika, [(10, 10), (12, 10), (12, 12), (10, 12)])
    assert H is None
    assert meta["rektificirano"] is False
    assert any("premajhno" in o for o in meta["opozorila"])


def test_rektificiraj_vogali_vrne_pravokotnik():
    slika = _prazna_slika()
    obmocje = [(100, 50), (500, 100), (520, 400), (80, 380)]  # trapez
    rect, H, meta = rektifikacija.rektificiraj(slika, obmocje)
    assert meta["rektificirano"] is True
    assert H is not None
    assert rect.shape[0] >= 8 and rect.shape[1] >= 8


# ----------------------------------------------------------- pas_ograje


def test_pas_ograje_zazna_pas():
    """Slika: svetlo, pas z vodoravno periodiko (temno/svetlo), spet svetlo.
    pas_ograje meri energijo |I(y+pitch/2) − I(y)| — periodika po VRSTICAH."""
    h, w = 200, 400
    slika = np.full((h, w), 230, dtype=np.uint8)
    for y in range(60, 150, 20):
        slika[y:y + 10, :] = 60
    pas = rektifikacija.pas_ograje(slika, 20.0)
    assert pas is not None
    y0, y1, _x0, _x1 = pas
    assert y0 <= 65 and y1 >= 140


def test_pas_ograje_brez_vzorca():
    slika = np.full((200, 400), 128, dtype=np.uint8)
    assert rektifikacija.pas_ograje(slika, 20.0) is None