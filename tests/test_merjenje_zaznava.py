"""Testi zaznavanja merjenja (merjenje.py) — lamele, vijaki, politika zaupanja.

Merjenje s fotografije je POMOŽNO — a tudi pomožni rezultat mora biti
pošten: ploščata slika NE sme dati »zanesljive« fantomske zaznave,
negotovost mora biti označena, neznano ne izmišljeno.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import merjenje  # noqa: E402
import cv2  # noqa: E402


def _shrani(tmp_path, g, ime="slika.png"):
    pot = str(tmp_path / ime)
    assert cv2.imwrite(pot, g)
    return pot


def _poceni_slika(w=480, h=240, vrednost=200):
    return np.full((h, w), vrednost, dtype=np.uint8)


# ------------------------------------------------------------------ _obrez


def test_obrez_brez_roi():
    assert merjenje._obrez(None, 100, 80) == (0, 0, 100, 80)


def test_obrez_omeji_in_normalizira():
    assert merjenje._obrez((-10, -5, 500, 400), 100, 80) == (0, 0, 100, 80)
    assert merjenje._obrez((50, 40, 10, 5), 100, 80) == (10, 5, 50, 40)


# ------------------------------------------------------- 1-D periodika


def test_vrhovi_najde_znane():
    x = [0.0, 1.0, 5.0, 1.0, 0.0, 1.0, 4.0, 1.0, 0.0]
    vr = merjenje.vrhovi(x, 3, 1.0)
    assert 2 in vr and 6 in vr


def test_vrhovi_spoštuje_razmak():
    x = [0.0, 5.0, 1.0, 5.0, 0.0]
    vr = merjenje.vrhovi(x, 5, 1.0)
    assert len(vr) == 1


def test_najboljsi_periodicni_period():
    prof = np.tile(np.concatenate([np.full(20, 60.0), np.full(20, 200.0)]), 6)
    r = merjenje._najboljsi_periodicni(prof)
    assert r is not None
    rel, _pasovi, info = r
    assert rel < 0.15
    assert info["pitch_px"] == pytest.approx(40.0, abs=3.0)
    assert info["stevilo"] >= 4


# --------------------------------------------------------- zaznaj_lamele


def test_zaznaj_lamele_sintetika(tmp_path):
    g = _poceni_slika()
    for y in range(20, 220, 40):
        g[y:y + 20, :] = 60
    pot = _shrani(tmp_path, g)
    pasovi, info = merjenje.zaznaj_lamele(pot)
    assert len(pasovi) >= 3
    assert info["pitch_px"] == pytest.approx(40.0, abs=3.0)
    assert info["stevilo"] >= 4
    assert info["nepravilnost"] is not None


def test_zaznaj_lamele_roi_premajhno(tmp_path):
    pot = _shrani(tmp_path, _poceni_slika())
    with pytest.raises(ValueError, match="premajhno"):
        merjenje.zaznaj_lamele(pot, roi=(10, 10, 25, 25))


def test_zaznaj_lamele_ni_slike(tmp_path):
    with pytest.raises(ValueError, match="ni mogoče odpreti"):
        merjenje.zaznaj_lamele(str(tmp_path / "ne-obstaja.png"))


def test_plosca_slika_nima_fantomske_zaznave(tmp_path):
    """Ploščata slika (brez kontrasta) NE sme dati 'zanesljive' zaznave.

    Prejšnja hiba: vrhovi() na ničelnem gradientu je vrnil 'vrhove' povsod
    in kandidat 'robovi' z nepravilnost 0 = 'ZANESLJIVO' — fantom.
    """
    pot = _shrani(tmp_path, _poceni_slika())
    pasovi, info = merjenje.zaznaj_lamele(pot)
    assert pasovi == []
    assert info["stevilo"] == 0
    # in nikoli 'zanesljivo', če ni nič najdenega
    assert merjenje.opozorilo_zaznave(info) != ""


# --------------------------------------------------------- zaznaj_vijake


def _slika_z_pikami(tmp_path, centri, r=8):
    g = _poceni_slika()
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    for (cx, cy) in centri:
        maska = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
        g[maska] = 30
    return _shrani(tmp_path, g, "pike.png")


def test_zaznaj_vijake_sintetika(tmp_path):
    centri = [(100, 120), (180, 120), (260, 120)]
    pot = _slika_z_pikami(tmp_path, centri)
    pike, info = merjenje.zaznaj_vijake(pot)
    assert info["stevilo"] == 3
    assert len(pike) == 3
    assert info["razmak_px"] == pytest.approx(80.0, abs=6.0)
    # koordinate so v koordinatah CELE slike
    xs = sorted(round(p[0]) for p in pike)
    assert xs == [100, 180, 260]


def test_zaznaj_vijake_y_range_izloci(tmp_path):
    centri = [(100, 60), (180, 120), (260, 180)]
    pot = _slika_z_pikami(tmp_path, centri)
    pike, info = merjenje.zaznaj_vijake(pot, y_range=(90.0, 150.0))
    assert info["stevilo"] == 1
    assert round(pike[0][1]) == 120


def test_zaznaj_vijake_roi_premajhno(tmp_path):
    pot = _shrani(tmp_path, _poceni_slika())
    with pytest.raises(ValueError, match="premajhno"):
        merjenje.zaznaj_vijake(pot, roi=(0, 0, 15, 15))


# --------------------------------------------------- politika zaupanja


def test_zaupanje_zaznave_pravila():
    assert merjenje.zaupanje_zaznave({"nepravilnost": 0.0}) == 1.0
    z = merjenje.zaupanje_zaznave({"nepravilnost": 0.5})
    assert z == pytest.approx(1.0 - 0.5 / (0.5 + merjenje.PRAG_ZAUPANJA))
    assert merjenje.zaupanje_zaznave({"nepravilnost": None}) is None
    assert merjenje.zaupanje_zaznave({}) is None
    assert merjenje.zaupanje_zaznave(None) is None


def test_opozorilo_zaznave_pravila():
    assert "ni uspela" in merjenje.opozorilo_zaznave({"stevilo": 0})
    assert "NEGOTOVA" in merjenje.opozorilo_zaznave(
        {"stevilo": 5, "nepravilnost": 0.9})
    assert merjenje.opozorilo_zaznave(
        {"stevilo": 5, "nepravilnost": 0.05}) == ""


def test_status_meritve_pravila():
    barva, znak, _opis = merjenje.status_meritve("izmerjeno")
    assert barva.startswith("#") and znak == "†"
    # neznan status NE sme pasti neznano — dobi najšibkejši status
    _b, znak2, opis2 = merjenje.status_meritve("neki_drugace")
    assert znak2 == "??" and "neznano" in opis2


def test_barva_zaupanja_pragovi():
    assert merjenje.barva_zaupanja(1.0)[1] == "ZANESLJIVO"
    assert merjenje.barva_zaupanja(0.75)[1] == "ZANESLJIVO"
    assert merjenje.barva_zaupanja(0.5)[1] == "PREVERI"
    assert merjenje.barva_zaupanja(merjenje.PRAG_ZAUPANJA)[1] == "PREVERI"
    assert merjenje.barva_zaupanja(0.1)[1] == "NEGOTOVO"
    assert merjenje.barva_zaupanja(None)[1] == "NEGOTOVO"


# -------------------------------------------------------- oznaci_sliko


def test_oznaci_sliko_zapise(tmp_path):
    pot = _shrani(tmp_path, _poceni_slika(), "osnova.png")
    izhod = str(tmp_path / "oznaceno.png")
    merjenje.oznaci_sliko(pot, [(20, 40)], [(100.0, 120.0, 8.0)], izhod,
                         roi=(10, 10, 400, 200))
    assert os.path.isfile(izhod)
    slika = cv2.imread(izhod)
    assert slika is not None
    assert slika.shape[0] == 240