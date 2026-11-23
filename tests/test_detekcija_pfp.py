# -*- coding: utf-8 -*-
"""Robovna kontrola lamelnega ritma (photo_fence_proposal/detekcija.py).

Neodvisen estimator (scikit-image Canny) + kontrola soglasja s profilnim
estimatorjem. Testi uporabljajo sintetične rektificirane slike z ZNANIM
ritmom — kar vnesemo v sliko, mora biti izmerjeno (brez ugibanja).
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "photo_fence_proposal"))
import detekcija          # noqa: E402
import rektifikacija      # noqa: E402


def slika_lamel(w=640, h=200, pitch=40.0, deska=30.0, smer="navpicno",
                nagib=0.0, svetloba=0.4, hrup=2.0, seed=0):
    """Rektificirana slika ograje z znanim ritmom (fuge = temne črte).

    ``deska`` = širina svetlega pasu, fuga = pitch − deska; ``svetloba`` =
    amplituda glajenega neenakomernega osvetlitvenega gradienta.
    """
    rng = np.random.default_rng(seed)
    x = np.arange(w)[None, :]
    y = np.arange(h)[:, None]
    premik = (x + nagib * y) if smer == "navpicno" else (y + nagib * x)
    faza = np.mod(premik, pitch)
    slika = np.where(faza < deska, 180.0, 60.0)
    if svetloba:
        g = (x / max(w - 1, 1)) if smer == "navpicno" else (y / max(h - 1, 1))
        slika = slika * (1.0 + svetloba * (g - 0.5))
    if hrup:
        slika = slika + rng.normal(0.0, hrup, slika.shape)
    return np.clip(slika, 0, 255)


# --- robovni estimator ------------------------------------------------------

def test_robni_ritem_vertikalne_lamele():
    r = detekcija.robni_ritem(slika_lamel(pitch=40.0, deska=30.0))
    assert r["smer"] == "navpicno"
    assert abs(r["pitch_px"] - 40.0) <= 1.5
    # n_lamel so fuge v IZBRANEM oknu (ne čez celotno sliko)
    assert r["n_lamel"] >= 5
    assert abs(r["vrzel_px"] - 10.0) <= 2.0      # fuga 10 px
    assert abs(r["debelina_px"] - 30.0) <= 2.0   # deska 30 px
    assert r["nepravilnost"] is not None and r["nepravilnost"] < 0.25
    assert r["vir"] == "robovi"


def test_robni_ritem_horizontalne_lamele():
    r = detekcija.robni_ritem(slika_lamel(pitch=40.0, deska=30.0,
                                         smer="vodoravno"))
    assert r["smer"] == "vodoravno"
    assert abs(r["pitch_px"] - 40.0) <= 1.5


def test_robni_ritem_tanke_fuge():
    # fuga/pitch = 0.1 — izven tipičnega razmerja za profilni estimator;
    # robovni estimator temelji na robovih in jo mora najti
    r = detekcija.robni_ritem(slika_lamel(pitch=40.0, deska=36.0))
    assert r["pitch_px"] is not None
    assert abs(r["pitch_px"] - 40.0) <= 1.5


def test_robni_ritem_z_nagibom():
    # rahlo nagnjene lamele (perspektiva po rektifikaciji ni popolna)
    r = detekcija.robni_ritem(slika_lamel(pitch=40.0, deska=30.0, nagib=0.12))
    assert r["pitch_px"] is not None
    assert abs(r["pitch_px"] - 40.0) <= 2.5


def test_robni_ritem_brez_ritma():
    r = detekcija.robni_ritem(np.full((200, 400), 128.0))
    assert r["pitch_px"] is None
    assert r["n_lamel"] == 0


def test_robni_ritem_enako_kot_profilni_na_cisti_sintetiki():
    """Na čisti sintetiki se morata estimatorja strinjati (ista resnica)."""
    slika = slika_lamel(pitch=40.0, deska=30.0)
    rob = detekcija.robni_ritem(slika)
    prof = rektifikacija.lamelni_ritem(slika)
    assert prof["pitch_px"] is not None and rob["pitch_px"] is not None
    assert abs(prof["pitch_px"] - rob["pitch_px"]) <= 3.0


# --- kontrola soglasja ------------------------------------------------------

def test_soglasje_v_toleranci():
    a = {"pitch_px": 40.0, "n_lamel": 10}
    b = {"pitch_px": 41.0, "n_lamel": 10}
    s = detekcija.soglasje(a, b)
    assert s["soglasje"] is True
    assert s["odstopanje"] <= 0.10


def test_soglasje_izven_tolerance():
    s = detekcija.soglasje({"pitch_px": 40.0, "n_lamel": 10},
                           {"pitch_px": 60.0, "n_lamel": 7})
    assert s["soglasje"] is False
    assert "pitch" in s["razlog"]


def test_soglasje_razlicni_stevili():
    s = detekcija.soglasje({"pitch_px": 40.0, "n_lamel": 12},
                           {"pitch_px": 40.5, "n_lamel": 7})
    assert s["soglasje"] is False
    assert "stevili" in s["razlog"]


def test_soglasje_en_eden_zazna():
    s = detekcija.soglasje({"pitch_px": 40.0, "n_lamel": 10},
                           {"pitch_px": None, "n_lamel": 0})
    assert s["soglasje"] is False
    assert "ni nasel" in s["razlog"]


def test_kontrolirano_soglasje_na_sintetiki():
    r = detekcija.lamelni_ritem_kontrolirano(slika_lamel(pitch=40.0,
                                                        deska=30.0))
    assert r["kontrola"]["soglasje"] is True
    assert r["nesoglasje"] is False
    assert r["kontrola"]["pitch_rob_px"] is not None
    assert r["kontrola"]["pitch_profil_px"] is not None


def test_kontrolirano_nesoglasje_je_oznaceno(monkeypatch):
    """Nesoglasje NI tiha izbira: vrednosti ostanejo, status pade na klicajoca."""
    monkeypatch.setattr(
        detekcija.rektifikacija, "lamelni_ritem",
        lambda _s: {"n_lamel": 10, "pitch_px": 40.0, "debelina_px": 30.0,
                    "vrzel_px": 10.0, "nepravilnost": 0.02,
                    "smer": "navpicno", "y0": 0})
    monkeypatch.setattr(
        detekcija, "robni_ritem",
        lambda _s, **_k: {"n_lamel": 7, "pitch_px": 60.0, "debelina_px": 44.0,
                          "vrzel_px": 16.0, "nepravilnost": 0.05,
                          "smer": "navpicno", "y0": 0, "vir": "robovi"})
    r = detekcija.lamelni_ritem_kontrolirano(np.zeros((50, 50)))
    assert r["nesoglasje"] is True
    assert r["kontrola"]["soglasje"] is False
    assert "pitch" in r["kontrola"]["razlog"]
    assert r["pitch_px"] == 40.0          # profilni NI zamenjan tiho
    assert r["nepravilnost"] > 1.0        # oznaka slabše zanesljivosti


def test_kontrolirano_rob_ne_zazna_je_nevtralno(monkeypatch):
    """Odsotnost drugega mnenja NI nestrinjanje (nesoglasje ostane False)."""
    monkeypatch.setattr(
        detekcija.rektifikacija, "lamelni_ritem",
        lambda _s: {"n_lamel": 10, "pitch_px": 40.0, "debelina_px": 30.0,
                    "vrzel_px": 10.0, "nepravilnost": 0.02,
                    "smer": "navpicno", "y0": 0})
    monkeypatch.setattr(
        detekcija, "robni_ritem",
        lambda _s, **_k: {"n_lamel": 0, "pitch_px": None, "debelina_px": None,
                          "vrzel_px": None, "nepravilnost": None,
                          "vir": "robovi"})
    r = detekcija.lamelni_ritem_kontrolirano(np.zeros((50, 50)))
    assert r["nesoglasje"] is False
    assert r["kontrola"]["soglasje"] is False
    assert r["pitch_px"] == 40.0