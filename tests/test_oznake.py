# -*- coding: utf-8 -*-
"""Testi QR oznak: zapis, branje, odpornost in strogo preverjanje.

Filozofija je enaka kot drugje v projektu: koda, ki je ni mogoče
preveriti, se zavrne z razlogom — nikoli se ne popravi tiho. Zato testi
pokrijejo tudi napačne predpone, manjkajoča polja in tuje QR kode.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import oznake  # noqa: E402
from conftest import osnovni_cfg  # noqa: E402

VELJAVNA = "TR1|PO-TEST|PO-009|1850|2500"


# ------------------------------------------------------- sestavljanje


def test_sestavi_oznako_iz_konfiguracije(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    assert oznake.sestavi_oznako(cfg) == VELJAVNA


@pytest.mark.parametrize("polje, vrednost, vzorec", [
    ("ime", "", "imena projekta"),
    ("risba_st", "", "šifre risbe"),
    ("ime", "a|b", "znaka"),
])
def test_sestavi_zavrne_manjkajoce_podatke(tmp_path, polje, vrednost, vzorec):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg[polje] = vrednost
    with pytest.raises(oznake.NeveljavnaOznaka, match=vzorec):
        oznake.sestavi_oznako(cfg)


def test_sestavi_zavrne_neveljavne_mere(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["mere"]["visina"] = 0
    with pytest.raises(oznake.NeveljavnaOznaka, match="pozitivno"):
        oznake.sestavi_oznako(cfg)
    cfg["mere"]["visina"] = "visoko"
    with pytest.raises(oznake.NeveljavnaOznaka, match="ni število"):
        oznake.sestavi_oznako(cfg)


# ------------------------------------------------------------- branje


def test_razcleni_veljavno():
    o = oznake.razcleni_oznako(VELJAVNA)
    assert o.projekt == "PO-TEST"
    assert o.sifra == "PO-009"
    assert o.mere == {"visina": 1850.0, "sirina": 2500.0}
    assert o.surovo == VELJAVNA


@pytest.mark.parametrize("besedilo, vzorec", [
    ("", "5 polj"),
    ("TR1|a|b|1", "5 polj"),
    ("XX1|a|b|1|2", "predpona"),
    ("TR1||b|1|2", "prazno"),
    ("TR1|a|b|visoko|2", "ni število"),
    ("TR1|a|b|1|0", "pozitivno"),
    ("https://example.com", "5 polj"),
])
def test_razcleni_zavrne_neveljavno(besedilo, vzorec):
    with pytest.raises(oznake.NeveljavnaOznaka, match=vzorec):
        oznake.razcleni_oznako(besedilo)


def test_oznake_za_polja():
    polja = oznake.oznake_za_polja(oznake.razcleni_oznako(VELJAVNA))
    assert polja == {"ime": "PO-TEST", "risba_st": "PO-009",
                     "visina": "1850", "sirina": "2500"}


# ----------------------------------------------------------- slika/QR


def test_roundtrip_zapis_in_branje(tmp_path):
    pot = oznake.zapisi_oznako(VELJAVNA, tmp_path / "oznaka.png")
    assert pot.is_file()
    rezultat = oznake.preberi_oznake(pot)
    assert rezultat.uspeh
    assert rezultat.kod_v_sliki == 1
    assert rezultat.oznake[0].projekt == "PO-TEST"
    assert rezultat.oznake[0].mere["sirina"] == 2500.0
    assert rezultat.opozorila == []


def test_zapis_preveri_velikost_in_rob(tmp_path):
    with pytest.raises(ValueError, match="vsaj 64"):
        oznake.zapisi_oznako(VELJAVNA, tmp_path / "a.png", velikost_px=32)
    with pytest.raises(ValueError, match="tihi rob"):
        oznake.zapisi_oznako(VELJAVNA, tmp_path / "b.png", rob_px=4)


def _platno(velikost=420, koda_px=240, rob=90):
    """Koda s tihim robom, nalepljena na belo platno (kot fotografija)."""
    import cv2
    import tempfile

    with tempfile.TemporaryDirectory() as mapa:
        p = oznake.zapisi_oznako(VELJAVNA, pathlib.Path(mapa) / "o.png",
                                 velikost_px=koda_px, rob_px=40)
        koda = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    platno = np.full((velikost, velikost), 255, dtype=np.uint8)
    vis, sir = koda.shape
    platno[rob:rob + vis, rob:rob + sir] = koda
    return platno


def test_odpornost_na_obrat_sum_in_zameglitev():
    import cv2

    # cv2 stubs ne pokrijejo vseh overloadov (borderValue) — zato Any alias,
    # enako kot drugje v projektu; koda je preverjena z izvajanjem.
    zavrti: Any = cv2.warpAffine
    matrika: Any = cv2.getRotationMatrix2D
    platno = _platno()
    sredina = (platno.shape[1] / 2, platno.shape[0] / 2)
    primeri = {
        "obrat": zavrti(platno, matrika(sredina, 25, 1.0),
                        platno.shape[::-1], borderValue=255),
        "sum": np.clip(platno.astype(np.int16) + np.random.default_rng(0)
                       .normal(0, 20, platno.shape), 0, 255).astype(np.uint8),
        "zameglitev": cv2.GaussianBlur(platno, (5, 5), 0),
        "pomanjsano": cv2.resize(platno, (200, 200),
                                 interpolation=cv2.INTER_AREA),
    }
    for ime, slika in primeri.items():
        rezultat = oznake.preberi_oznake(slika)
        assert rezultat.uspeh, f"{ime}: {rezultat.opozorila}"
        assert rezultat.oznake[0].surovo == VELJAVNA


def test_perspektiva_ne_zmoti():
    import cv2

    preslikaj: Any = cv2.warpPerspective
    homografija: Any = cv2.getPerspectiveTransform
    platno = _platno()
    vir = np.asarray([[90, 90], [330, 90], [330, 330], [90, 330]],
                     dtype=np.float32)
    cilj = np.asarray([[120, 130], [315, 100], [340, 320], [80, 305]],
                      dtype=np.float32)
    slika = preslikaj(platno, homografija(vir, cilj), (420, 420),
                      borderValue=255)
    rezultat = oznake.preberi_oznake(slika)
    assert rezultat.uspeh
    assert rezultat.oznake[0].mere["visina"] == 1850.0


def test_prazna_slika_pove_kaj_narediti():
    rezultat = oznake.preberi_oznake(np.full((300, 300), 255, dtype=np.uint8))
    assert not rezultat.uspeh
    assert rezultat.kod_v_sliki == 0
    assert "ni berljive QR kode" in rezultat.opozorila[0]


def test_tuja_qr_koda_ni_tiho_sprejeta(tmp_path):
    pot = oznake.zapisi_oznako("https://example.com/xyz", tmp_path / "tuja.png")
    rezultat = oznake.preberi_oznake(pot)
    assert not rezultat.uspeh
    assert rezultat.kod_v_sliki == 1
    assert "ni veljavna oznaka TR1" in rezultat.opozorila[0]


def test_manjkajoca_slika():
    with pytest.raises(OSError, match="ni mogoče prebrati"):
        oznake.preberi_oznake("C:/ne-obstaja/slika.png")


def test_preberi_vec_kod(tmp_path):
    import cv2

    leva = oznake.zapisi_oznako(VELJAVNA, tmp_path / "l.png",
                               velikost_px=200, rob_px=24)
    desna = oznake.zapisi_oznako("TR1|PO-2026-015|PO-010|1600|3000",
                                 tmp_path / "d.png", velikost_px=200,
                                 rob_px=24)
    sl = cv2.resize(cv2.imread(str(leva), cv2.IMREAD_GRAYSCALE), (240, 240))
    sd = cv2.resize(cv2.imread(str(desna), cv2.IMREAD_GRAYSCALE), (240, 240))
    platno = np.full((300, 560), 255, dtype=np.uint8)
    platno[30:270, 20:260] = sl
    platno[30:270, 300:540] = sd

    rezultat = oznake.preberi_oznake(platno)
    assert len(rezultat.oznake) == 2
    assert {o.projekt for o in rezultat.oznake} == {"PO-TEST", "PO-2026-015"}


# ---------------------------------------------------------------- CLI


def test_cli_zapisi_in_preberi(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    import yaml

    vhod = tmp_path / "projekt.yaml"
    vhod.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    slika = tmp_path / "oznaka.png"

    import subprocess

    dokoncan = subprocess.run(
        [sys.executable, "oznake.py", "--zapisi", str(vhod),
         "--izhod", str(slika)],
        cwd=str(REPO), capture_output=True, text=True, timeout=180)
    assert dokoncan.returncode == 0, dokoncan.stderr
    assert VELJAVNA in dokoncan.stdout

    dokoncan = subprocess.run(
        [sys.executable, "oznake.py", "--preberi", str(slika)],
        cwd=str(REPO), capture_output=True, text=True, timeout=180)
    assert dokoncan.returncode == 0, dokoncan.stderr
    assert "PO-TEST" in dokoncan.stdout
    assert "1850 mm" in dokoncan.stdout


# ------------------------------------------------- vezava na glavni GUI


class _Var:
    """Nadomestek za tk.StringVar (brez Tk)."""

    def __init__(self, vrednost=""):
        self.vrednost = vrednost

    def set(self, vrednost):
        self.vrednost = vrednost

    def get(self):
        return self.vrednost


class _Status:
    def __init__(self):
        self.besedilo = ""

    def config(self, text=None):
        if text is not None:
            self.besedilo = text


class _App:
    """Minimalni nadomestek App za preizkus metod brez okna."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.v = {k: _Var() for k in ("ime", "risba_st", "visina", "sirina")}
        self.status = _Status()

    def _zberi_cfg(self):
        return self.cfg


def podtakni(app: _App) -> Any:
    """Metode App pričakujejo App; testni nadomestek je namerno lažji."""
    return app


def test_gui_preberi_oznako_potrditev(monkeypatch, tmp_path):
    import vmesnik

    cfg = osnovni_cfg(tmp_path / "x.pdf")
    app = _App(cfg)
    pot = oznake.zapisi_oznako(VELJAVNA, tmp_path / "o.png")
    monkeypatch.setattr(vmesnik.messagebox, "askyesno", lambda *a, **k: True)
    vmesnik.App._oznaka_preberi(podtakni(app), str(pot))
    assert app.v["ime"].get() == "PO-TEST"
    assert app.v["risba_st"].get() == "PO-009"
    assert app.v["visina"].get() == "1850"
    assert app.v["sirina"].get() == "2500"
    assert "preveri" in app.status.besedilo


def test_gui_preberi_oznako_zavrnitev(monkeypatch, tmp_path):
    import vmesnik

    app = _App(osnovni_cfg(tmp_path / "x.pdf"))
    pot = oznake.zapisi_oznako(VELJAVNA, tmp_path / "o.png")
    monkeypatch.setattr(vmesnik.messagebox, "askyesno", lambda *a, **k: False)
    vmesnik.App._oznaka_preberi(podtakni(app), str(pot))
    assert app.v["ime"].get() == ""       # nič ni bilo prepisano


def test_gui_preberi_brez_kode_opozori(monkeypatch, tmp_path):
    import cv2
    import vmesnik

    app = _App(osnovni_cfg(tmp_path / "x.pdf"))
    prazna = tmp_path / "prazna.png"
    cv2.imwrite(str(prazna), np.full((200, 200), 255, dtype=np.uint8))
    sporocila = []
    monkeypatch.setattr(vmesnik.messagebox, "showwarning",
                        lambda naslov, besedilo: sporocila.append(besedilo))
    vmesnik.App._oznaka_preberi(podtakni(app), str(prazna))
    assert sporocila and "ni berljive QR kode" in sporocila[0]
    assert app.v["ime"].get() == ""


def test_gui_zapisi_oznako(monkeypatch, tmp_path):
    import vmesnik

    cfg = osnovni_cfg(tmp_path / "x.pdf")
    app = _App(cfg)
    cilj = tmp_path / "izvoz.png"
    monkeypatch.setattr(vmesnik.filedialog, "asksaveasfilename",
                        lambda **k: str(cilj))
    vmesnik.App._oznaka_zapisi(podtakni(app))
    assert cilj.is_file()
    rezultat = oznake.preberi_oznake(cilj)
    assert rezultat.oznake[0].projekt == "PO-TEST"
    assert "shranjena" in app.status.besedilo


def test_gui_zapisi_brez_podatkov_opozori(monkeypatch, tmp_path):
    import vmesnik

    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["ime"] = ""
    app = _App(cfg)
    sporocila = []
    monkeypatch.setattr(vmesnik.messagebox, "showerror",
                        lambda naslov, besedilo: sporocila.append(besedilo))
    vmesnik.App._oznaka_zapisi(podtakni(app))
    assert sporocila and "imena projekta" in sporocila[0]


# ----------------------------------------------- OCR (neobvezna pot)
# OCR inferenca traja ~7 s na sliko (merjeno), zato so ti testi označeni
# kot "pocasi" — hitra zanka jih preskoči (-m "not pocasi").


def _slika_z_besedilom(besedilo: str, velikost: int = 64):
    """Nariše besedilo na belo sliko (kot natisnjena oznaka)."""
    from PIL import Image, ImageDraw, ImageFont

    slika = Image.new("RGB", (1500, 260), "white")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", velikost)
    except Exception:                       # pragma: no cover — brez pisave
        font = ImageFont.load_default()
    ImageDraw.Draw(slika).text((30, 80), besedilo, fill="black", font=font)
    return np.asarray(slika)


def _ima_ocr() -> bool:
    import importlib.util

    return importlib.util.find_spec("rapidocr_onnxruntime") is not None


@pytest.mark.pocasi
def test_ocr_prebere_oznako():
    if not _ima_ocr():
        pytest.skip("rapidocr ni nameščen — OCR pot ni na voljo")
    rezultat = oznake.preberi_besedilo(_slika_z_besedilom(VELJAVNA))
    assert rezultat.uspeh, rezultat.opozorila
    oznaka = rezultat.oznake[0]
    assert oznaka.projekt == "PO-TEST"
    assert oznaka.mere == {"visina": 1850.0, "sirina": 2500.0}
    # vsaka vrstica ima zabeleženo zaupanje
    assert rezultat.vrstice and all(0.0 <= z <= 1.0 for _b, z in rezultat.vrstice)


@pytest.mark.pocasi
def test_ocr_napacna_vsebina_opozori():
    if not _ima_ocr():
        pytest.skip("rapidocr ni nameščen")
    rezultat = oznake.preberi_besedilo(
        _slika_z_besedilom("PO-009 visina 1850"))
    assert not rezultat.uspeh
    assert any("ni veljavna oznaka" in o for o in rezultat.opozorila)


@pytest.mark.pocasi
def test_ocr_zaupanje_pod_pragom_zavrne():
    if not _ima_ocr():
        pytest.skip("rapidocr ni nameščen")
    # prag 1.01 ni dosegljiv nobeni vrstici -> vse zavrnjene z razlogom
    rezultat = oznake.preberi_besedilo(
        _slika_z_besedilom(VELJAVNA), prag=1.01)
    assert not rezultat.uspeh
    assert any("ni upoštevana" in o for o in rezultat.opozorila)


@pytest.mark.pocasi
def test_ocr_prazna_slika():
    if not _ima_ocr():
        pytest.skip("rapidocr ni nameščen")
    rezultat = oznake.preberi_besedilo(
        np.full((240, 240, 3), 255, dtype=np.uint8))
    assert not rezultat.uspeh
    assert any("ni berljivega besedila" in o for o in rezultat.opozorila)


def test_najdi_oznake_qr_ima_prednost(monkeypatch, tmp_path):
    pot = oznake.zapisi_oznako(VELJAVNA, tmp_path / "o.png")

    def ne_klici(*_a, **_k):                  # OCR se ne sme poklicati
        raise AssertionError("OCR ne sme teci, ko QR uspe")

    monkeypatch.setattr(oznake, "preberi_besedilo", ne_klici)
    najdba = oznake.najdi_oznake(pot)
    assert najdba.uspeh and najdba.vir == "qr"


@pytest.mark.pocasi
def test_najdi_oznake_ocr_kot_nadomestna_pot(tmp_path):
    if not _ima_ocr():
        pytest.skip("rapidocr ni nameščen")
    pot = tmp_path / "oznaka_brez_qr.png"
    from PIL import Image

    Image.fromarray(_slika_z_besedilom(VELJAVNA)).save(pot)
    najdba = oznake.najdi_oznake(pot)
    assert najdba.uspeh and najdba.vir == "ocr"
    assert any("OCR (ne QR)" in o for o in najdba.opozorila)


def test_najdi_oznake_brez_ocr(monkeypatch, tmp_path):
    from PIL import Image

    pot = tmp_path / "samo_besedilo.png"
    Image.fromarray(_slika_z_besedilom(VELJAVNA)).save(pot)
    najdba = oznake.najdi_oznake(pot, dovoli_ocr=False)
    assert not najdba.uspeh and najdba.vir == ""


def test_ocr_manjkajoca_knjiznica(monkeypatch):
    import builtins

    pravi = builtins.__import__

    def lazni(ime, *a, **k):
        if ime.startswith("rapidocr"):
            raise ImportError("ni paketa")
        return pravi(ime, *a, **k)

    monkeypatch.setattr(builtins, "__import__", lazni)
    with pytest.raises(oznake.ManjkajocaKnjiznica, match="rapidocr"):
        oznake.preberi_besedilo(np.full((10, 10, 3), 255, dtype=np.uint8))


@pytest.mark.pocasi
def test_gui_oznaka_preberi_z_ocr(monkeypatch, tmp_path):
    """GUI uporabi OCR, a vseeno zahteva potrditev in opozori na vir."""
    import vmesnik

    if not _ima_ocr():
        pytest.skip("rapidocr ni nameščen")
    from PIL import Image

    pot = tmp_path / "brez_qr.png"
    Image.fromarray(_slika_z_besedilom(VELJAVNA)).save(pot)

    app = _App(osnovni_cfg(tmp_path / "x.pdf"))
    vprasanja = []
    monkeypatch.setattr(vmesnik.messagebox, "askyesno",
                        lambda naslov, besedilo, **k: vprasanja.append(besedilo) or True)
    vmesnik.App._oznaka_preberi(podtakni(app), str(pot))
    assert app.v["ime"].get() == "PO-TEST"
    assert vprasanja and "OCR" in vprasanja[0]
