"""Testi DXF izvoza (issue #3) — po kontrolnem seznamu specifikacije.

Preverja se vsebina (ne le odsotnost izjem): enote mm, različica R2010,
fiksna shema plasti, zaprte konture brez ponovljene prve točke, realno
merilo 1:1, odsotnost podvojenih entitet, round-trip z ezdxf.readfile.
"""
# mypy: disable-error-code=attr-defined
# (ezdxf stubs ne ožijo DXFEntity/DXFGraphic na LWPOLYLINE — get_points,
#  plain_text, closed so legitimni atributi entitet ob izvedbi.)
from __future__ import annotations

import os

import ezdxf
import pytest

import dxf_izvoz
import vrata


@pytest.fixture()
def cfg_osnovni(tmp_path):
    return {
        "ime": "Test DXF",
        "stranka": "Naročnik Šček",
        "izhod": str(tmp_path / "T-001.pdf"),
        "predloga": "ograja",
        "mere": {"sirina": 3000, "visina": 2300, "odcep": 60},
    }


@pytest.fixture()
def cfg_z_vrati(cfg_osnovni):
    cfg = dict(cfg_osnovni)
    cfg["vrata"] = [{"tip": "enokrilna", "x": 200, "sirina": 1000,
                     "visina": 2000, "diagonala": True}]
    return cfg


# ---------------------------------------------------------------------------
# Enote / format
# ---------------------------------------------------------------------------

def test_dxf_enote_in_verzija(cfg_osnovni):
    pot, por = dxf_izvoz.izvozi_dxf(cfg_osnovni)
    doc = ezdxf.readfile(pot)
    assert doc.dxfversion == "AC1024"                 # R2010
    assert doc.header["$INSUNITS"] == 4               # mm
    assert doc.header["$MEASUREMENT"] == 1
    assert por["veljaven"]


def test_dxf_utf8_slovenski_znaki(cfg_osnovni):
    cfg = dict(cfg_osnovni)
    cfg["stranka"] = "Naročnik Žarn"
    pot, _ = dxf_izvoz.izvozi_dxf(cfg)
    doc = ezdxf.readfile(pot)
    besedila = [e.plain_text() for layout in doc.layouts
                for e in layout.query("MTEXT")]
    assert any("Žarn" in b for b in besedila)


# ---------------------------------------------------------------------------
# Plasti
# ---------------------------------------------------------------------------

def test_vse_plasti_po_shemi(cfg_osnovni):
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_osnovni)
    doc = ezdxf.readfile(pot)
    plasti = {l.dxf.name: l for l in doc.layers}
    for ime, (barva, ltype, _lw, _rez) in dxf_izvoz.PLASTI.items():
        assert ime in plasti, f"plast {ime} manjka"
        assert plasti[ime].dxf.color == barva
        assert plasti[ime].dxf.linetype.upper() == ltype.upper()


def test_datoteka_ni_prazna(cfg_osnovni):
    pot, por = dxf_izvoz.izvozi_dxf(cfg_osnovni)
    assert os.path.getsize(pot) > 0
    assert sum(por["stevila"].values()) > 0
    assert por["stevila"].get("M-ELEM-CONT") or por["stevila"].get("M-STEB-CONT")


# ---------------------------------------------------------------------------
# Konture / CNC
# ---------------------------------------------------------------------------

def test_vse_rezalne_konture_so_zaprte(cfg_z_vrati):
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_z_vrati)
    doc = ezdxf.readfile(pot)
    n_zaprtih = 0
    for e in doc.modelspace():
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer in ("M-ELEM-CONT", "M-STEB-CONT"):
            assert e.closed, f"odprta kontura na {e.dxf.layer}"
            tocke = list(e.get_points("xy"))
            assert len(tocke) >= 3
            assert tocke[0] != tocke[-1], "ponovljena prva točka = dvojni rez"
            n_zaprtih += 1
    assert n_zaprtih > 0


def test_brez_dvojnih_entitet(cfg_z_vrati):
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_z_vrati)
    doc = ezdxf.readfile(pot)
    videne = set()
    for e in doc.modelspace():
        if e.dxftype() == "LWPOLYLINE":
            kljuc = (e.dxf.layer, tuple(tuple(round(v, 6) for v in p)
                                        for p in e.get_points("xy")))
            assert kljuc not in videne, "podvojena kontura"
            videne.add(kljuc)


def test_luknje_na_plasti_holes(cfg_z_vrati):
    # Tečaji so M-OKOV-PRIT (informativno); CIRCLE je dovoljen le na
    # M-ODPR-CONT / M-OKOV-PRIT.
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_z_vrati)
    doc = ezdxf.readfile(pot)
    for e in doc.modelspace().query("CIRCLE"):
        assert e.dxf.layer in ("M-ODPR-CONT", "M-OKOV-PRIT")


# ---------------------------------------------------------------------------
# Realno merilo 1:1
# ---------------------------------------------------------------------------

def test_bbox_realno_merilo(cfg_osnovni):
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_osnovni)
    doc = ezdxf.readfile(pot)
    xs = [p[0] for e in doc.modelspace().query("LWPOLYLINE")
          for p in e.get_points("xy")]
    assert min(xs) >= -1e-6
    assert max(xs) == pytest.approx(3000.0, abs=1e-6)  # sirina ograje 1:1


def test_vrata_v_dxf_so_pravih_mer(cfg_z_vrati):
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_z_vrati)
    doc = ezdxf.readfile(pot)
    # Odprtina vrat: sirina 1000, H_o = 2000 (višina vrat iz konfiguracije).
    # Issue #6: veriga vključuje profile okvirja (60 + 5 + w_k + 5 + 60 = 1000).
    g = vrata.geometrija_vrat(cfg_z_vrati["vrata"][0], 1000, 2000)
    w_k = g["sirine_kril"][0]                        # 870 mm
    assert w_k == 870.0
    # Kontura krila (M-ELEM-CONT): w_k × h_k — F1 (issue #5, O2): krilo sega od
    # tal do tla + h_k (kot kosovnica: stojalo krila = h_k); prej h_k − 40
    # (risba neusklajena s kosovnico).
    h_konture = g["h_k"]
    najdeno = False
    for e in doc.modelspace().query("LWPOLYLINE"):
        tocke = list(e.get_points("xy"))
        xs = [p[0] for p in tocke]
        ys = [p[1] for p in tocke]
        if abs((max(xs) - min(xs)) - w_k) < 1e-6 and abs((max(ys) - min(ys)) - h_konture) < 1e-6:
            najdeno = True
    assert najdeno, "kontura krila pravih mer ni najdena"


# ---------------------------------------------------------------------------
# Round-trip / audit
# ---------------------------------------------------------------------------

def test_roundtrip_in_audit(cfg_z_vrati):
    pot, por = dxf_izvoz.izvozi_dxf(cfg_z_vrati)
    doc = ezdxf.readfile(pot)
    auditor = doc.audit()
    assert not auditor.errors
    assert por["stevila"]  # štetja po plasteh preživijo round-trip
    assert sum(por["stevila"].values()) == len(doc.modelspace())


def test_preveri_dxf_zavrača_prazno(tmp_path):
    prazna = tmp_path / "prazna.dxf"
    prazna.write_text("", encoding="utf-8")
    por = dxf_izvoz.preveri_dxf(str(prazna))
    assert not por["veljaven"]


# ---------------------------------------------------------------------------
# Več segmenti / prehodi
# ---------------------------------------------------------------------------

def test_tip_segmenta_velika_zacetnica_se_normalizira(tmp_path):
    cfg = {
        "izhod": str(tmp_path / "S-001.pdf"),
        "segmenti": [{"ime": "S1", "tip": "OGRAJA",
                      "mere": {"sirina": 2400, "visina": 2300, "odcep": 60}}],
    }
    assert dxf_izvoz.segmenti_iz_cfg(cfg)[0]["tip"] == "ograja"


def test_tip_segmenta_neznan_se_zavrne(tmp_path):
    cfg = {
        "izhod": str(tmp_path / "S-001.pdf"),
        "segmenti": [{"ime": "S1", "tip": "ograaj",
                      "mere": {"sirina": 2400, "visina": 2300, "odcep": 60}}],
    }
    with pytest.raises(ValueError, match="neznan tip"):
        dxf_izvoz.segmenti_iz_cfg(cfg)


def test_segmenti_zamaknjeni_brez_prekrivanja(tmp_path):
    cfg = {
        "ime": "Segmenti",
        "izhod": str(tmp_path / "S-001.pdf"),
        "segmenti": [
            {"ime": "S1", "tip": "ograja", "mere": {"sirina": 2400, "visina": 2300,
                                               "odcep": 60},
             "prehodi": [{"x": 500, "sirina": 1000, "visina": 2000}]},
            {"ime": "S2", "tip": "ograja", "mere": {"sirina": 2000, "visina": 2300,
                                               "odcep": 60},
             "vrata": [{"tip": "dvokrilna", "x": 300, "sirina": 1600,
                        "visina": 2000}]},
        ],
    }
    pot, por = dxf_izvoz.izvozi_dxf(cfg)
    assert por["veljaven"]
    doc = ezdxf.readfile(pot)
    tocke = [p for e in doc.modelspace().query("LWPOLYLINE")
             for p in e.get_points("xy")]
    xs = [p[0] for p in tocke]
    # S1: 0–2400, razmak 1000, S2: 3400–5400 — brez prekrivanja.
    assert max(xs) == pytest.approx(5400.0, abs=1e-6)
    assert not any(2400.0 + 1e-6 < x < 3400.0 - 1e-6 for x in xs)


def test_dxf_ne_obstoji_ob_zavrnitvi(cfg_osnovni):
    # Višina vrat z odcepom presega ograjo -> izvoz zavrne, brez datoteke.
    cfg = dict(cfg_osnovni)
    cfg["vrata"] = [{"tip": "enokrilna", "x": 0, "sirina": 900,
                     "visina": 3000}]
    with pytest.raises(ValueError, match="presega"):
        dxf_izvoz.izvozi_dxf(cfg)
    assert not os.path.exists(str(cfg_osnovni["izhod"]).replace(".pdf", ".dxf"))


def test_opombe_vsebujejo_omejitve_cnc(cfg_osnovni):
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_osnovni)
    doc = ezdxf.readfile(pot)
    besedila = " ".join(e.plain_text() for e in doc.modelspace().query("MTEXT"))
    assert "G-code" in besedila
    assert "kompenzacije" in besedila
    assert "M-ELEM-CONT, M-STEB-CONT, M-ODPR-CONT" in besedila


def test_naslovni_blok_in_layout(cfg_osnovni):
    pot, _ = dxf_izvoz.izvozi_dxf(cfg_osnovni)
    doc = ezdxf.readfile(pot)
    imena = [l.name for l in doc.layouts]
    assert any("A3" in ime for ime in imena)
    layout = next(l for l in doc.layouts if "A3" in l.name)
    besedila = " ".join(e.plain_text() for e in layout.query("MTEXT"))
    assert "MERILO: 1:1" in besedila
    assert "RISBA ŠT." in besedila

def test_skupna_dolzina_je_vsota_sirin_brez_risalnih_razmikov(tmp_path):
    # F1 (issue #5, O1): skupna dolžina = 2400 + 2000 = 4400 mm;
    # risalni razmak 1000 mm med segmentoma NI del ograje (prej 5400).
    cfg = {
        "ime": "Dolzina", "izhod": str(tmp_path / "D-001.pdf"),
        "segmenti": [
            {"ime": "S1", "tip": "ograja",
             "mere": {"sirina": 2400, "visina": 2300, "odcep": 60}},
            {"ime": "S2", "tip": "ograja",
             "mere": {"sirina": 2000, "visina": 2300, "odcep": 60}},
        ],
    }
    pot, _ = dxf_izvoz.izvozi_dxf(cfg)
    doc = ezdxf.readfile(pot)
    besedila = [e.plain_text() for layout in doc.layouts
                for e in layout.query("MTEXT")]
    zadetki = [b for b in besedila if "Skupna dolžina" in b]
    assert zadetki, "naslovni blok nima skupne dolžine"
    assert any("4400" in b for b in zadetki), zadetki


def test_sloji_iso_13567_struktura():
    """Plan 2: vsi sloji imajo ISO 13567 strukturo (discipline-major-minor),
    legacy imena se prevedejo in so idempotentna."""
    import re
    for ime in dxf_izvoz.PLASTI:
        assert re.match(r"^M-[A-Z]{4}-[A-Z]{4}$", ime), ime
    assert set(dxf_izvoz.LEGACY_SLOJI.values()) == set(dxf_izvoz.PLASTI)
    assert dxf_izvoz._sloj("OUTLINE") == "M-ELEM-CONT"
    assert dxf_izvoz._sloj("M-ELEM-CONT") == "M-ELEM-CONT"
