# -*- coding: utf-8 -*-
"""F3 (issue #5): varnost API-ja in prag zanesljivosti merjenja.

- S1/S2: odsevni XSS v sporočilu o napaki je ESKAPIRAN
- S5: prazen/blokiran User-Agent je zavrnjen (403) pred obdelavo
- S3: omejevalnik zahtevkov po IP (10/min) vrne 429
- merjenje: zaupanje zaznave je izračunano in uporabnik opozorjen
"""
import pytest

merjenje = pytest.importorskip("merjenje")


def _app():
    pytest.importorskip("flask")
    import importlib
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
    import index as api_index
    return importlib.reload(api_index)


# ---------------------------------------------------------------------------
# S1/S2 — odsevni XSS
# ---------------------------------------------------------------------------

def test_xss_v_sporocilu_o_napaki_je_izpahunjen():
    api = _app()
    k = api.app.test_client()
    r = k.get("/app?napaka=<script>alert(1)</script>",
              headers={"User-Agent": "pytest"})
    telo = r.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in telo
    assert "&lt;script&gt;" in telo


def test_html_napake_izpahne_vsebino():
    api = _app()
    r = api.html_napake(["<img src=x onerror=alert(1)>"])
    telo = r.get_data(as_text=True)
    assert "<img src=x" not in telo
    assert "&lt;img" in telo


# ---------------------------------------------------------------------------
# S5 — User-Agent
# ---------------------------------------------------------------------------

def test_prazen_user_agent_zavrnjen():
    api = _app()
    k = api.app.test_client()
    r = k.post("/generiraj", data={}, headers={"User-Agent": ""})
    assert r.status_code == 403


def test_blokiran_user_agent_zavrnjen():
    api = _app()
    k = api.app.test_client()
    r = k.post("/generiraj", data={}, headers={"User-Agent": "sqlmap/1.0"})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# S3 — omejevalnik zahtevkov
# ---------------------------------------------------------------------------

def test_omejevalnik_zahtevkov_deluje():
    api = _app()
    api._ZAPISKI.clear()
    ip = "203.0.113.7"
    for _ in range(api._OMEJITEV):
        assert not api._prevec_zahtevkov(ip)
    assert api._prevec_zahtevkov(ip)           # 11. zahtevek zavrnjen
    # drug IP ni prizadet
    assert not api._prevec_zahtevkov("203.0.113.8")
    api._ZAPISKI.clear()


# ---------------------------------------------------------------------------
# merjenje — prag zanesljivosti
# ---------------------------------------------------------------------------

def test_zaupanje_in_opozorilo_zaznave():
    # redna periodika -> visoko zaupanje, brez opozorila
    dobro = {"stevilo": 10, "nepravilnost": 0.02}
    assert merjenje.zaupanje_zaznave(dobro) > 0.9
    assert merjenje.opozorilo_zaznave(dobro) == ""
    # kaotična periodika -> nizko zaupanje + JASNO opozorilo
    slabo = {"stevilo": 12, "nepravilnost": 0.9}
    assert merjenje.zaupanje_zaznave(slabo) < 0.5
    assert "NEGOTOVA" in merjenje.opozorilo_zaznave(slabo).upper()
    # nič zaznanega -> iskreno sporočilo
    assert "ni uspela" in merjenje.opozorilo_zaznave({"stevilo": 0})


def test_zaznaj_lamele_vrne_nepravilnost(tmp_path):
    import cv2
    import numpy as np
    slika = np.zeros((300, 400), dtype=np.uint8)
    for y in range(20, 290, 30):               # redni pasovi
        slika[y:y + 15, :] = 220
    pot = str(tmp_path / "pasovi.png")
    cv2.imwrite(pot, slika)
    pasovi, info = merjenje.zaznaj_lamele(pot)
    assert info["stevilo"] > 0
    assert info.get("nepravilnost") is not None
    assert merjenje.zaupanje_zaznave(info) is not None