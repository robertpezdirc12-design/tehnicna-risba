# -*- coding: utf-8 -*-
"""Plan 16: statična priloga (PDF) — revizijsko sledljiv izračunski list.

Priloga je INFORMATIVNI pregled povpraševanja (demand) + kontrolni seznam
za pooblaščenega inženirja — NI statični izračun in ne trdi o zmogljivosti
profila, sidranja ali veternega bremena.
"""
import copy
import json

import pytest

import statika

CFG = {
    "ime": "BALKONSKA OGRAJA",
    "risba_st": "BO-100",
    "stranka": "Ana Novak",
    "objekt": "Radovljica",
    "izdelal": "R. Pezdirc",
    "datum": "01.06.2026",
    "mere": {"sirina": 2450, "visina": 950, "odcep": 50, "razmak_nosilcev": 900},
    "pritrditev": "bočno",
    "podlaga": "beton",
    "vijak_lamela": "Inox vijak 6×60",
    "vijak_nosilec": "Vijak M10×90",
}


def test_podatki_struktura_in_glava():
    p = statika.priloga_podatki(CFG)
    for kljuc in ("opozorilo", "glava", "geometrija", "material", "obtezbe",
                  "zahteve", "formule", "odprto_za_inzenirja", "pritrdila",
                  "podpis"):
        assert kljuc in p
    assert p["glava"] == {
        "projekt": "BALKONSKA OGRAJA", "risba_st": "BO-100",
        "stranka": "Ana Novak", "objekt": "Radovljica",
        "izdelal": "R. Pezdirc", "datum": "01.06.2026"}
    # geometrija: h ročaja = visina − odcep (kot v GUI statičnega pregleda)
    assert p["geometrija"]["razmak_stebrov_mm"] == 900
    assert p["geometrija"]["visina_rocaja_mm"] == 900
    assert p["odprto_za_inzenirja"] and p["formule"]
    assert p["podpis"]["pregledal"] == "" and p["podpis"]["odobril"] == ""


def test_zahtevo_ustrezajo_rocnima_izracunoma():
    p = statika.priloga_podatki(CFG)
    assert [z["kategorija"] for z in p["zahteve"]] == ["bivalno", "javno"]
    for z, q in zip(p["zahteve"], (0.74, 1.5)):
        assert z["q_kN_m"] == q
        r = statika.pregled_rocaj(900.0, q, 235.0, 210000.0)
        s = statika.pregled_steber(900.0, q, 900.0, 235.0)
        assert z["rocaj"]["M_kNm"] == pytest.approx(r["M_kNm"])
        assert z["rocaj"]["W_pot_cm3"] == pytest.approx(r["W_pot_cm3"])
        assert z["rocaj"]["I_pot_cm4"] == pytest.approx(r["I_pot_cm4"])
        assert z["steber"]["F_kN"] == pytest.approx(s["F_kN"])
        assert z["steber"]["W_pot_cm3"] == pytest.approx(s["W_pot_cm3"])


def test_veter_uporabnikov_tlak_je_le_vhod():
    cfg = copy.deepcopy(CFG)
    cfg["statika"] = {"veter_kN_m2": 0.5}
    p = statika.priloga_podatki(cfg)
    assert len(p["obtezbe"]) == 3
    veter = p["obtezbe"][-1]
    # q [kN/m] = p [kN/m²] · h [m] = 0.5 · 0.9
    assert veter["q_kN_m"] == pytest.approx(0.45)
    assert "NI izračun po EN 1991-1-4" in veter["vir"]
    assert "uporabnikov tlak" in veter["kategorija"]


def test_veter_napacen_vhod():
    cfg = copy.deepcopy(CFG)
    cfg["statika"] = {"veter_kN_m2": -1}
    with pytest.raises(ValueError):
        statika.priloga_podatki(cfg)


def test_material_opozarja_na_privzeti_s235():
    p = statika.priloga_podatki(CFG)
    assert "PRIVZETO S235" in p["material"]["opomba"]
    p2 = statika.priloga_podatki(CFG, f_MPa=60.0)   # aluminij
    assert "vneseno" in p2["material"]["opomba"]
    assert p2["material"]["f_MPa"] == 60.0


def test_pripis_vsebuje_opozorilo_vire_in_kontrolni_seznam():
    besedilo = statika.pripis_priloge(statika.priloga_podatki(CFG))
    assert "NI STATIČNI IZRAČUN" in besedilo
    assert "BS 6180" in besedilo
    assert "POTOVANJE" in besedilo and "demand" in besedilo
    assert "ODPRTO ZA POOBLAŠČENEGA INŽENIRJA" in besedilo
    assert "[ ]" in besedilo
    assert "Pregledal (pooblaščeni inženir)" in besedilo
    assert "Inox vijak 6×60" in besedilo          # pritrdila iz konfiguracije
    assert "W ≥" in besedilo                      # minimum, ne zmogljivost


def test_porocilo_je_json_prijazno():
    p = statika.priloga_podatki(CFG)
    assert json.loads(json.dumps(p, ensure_ascii=False))["glava"]["risba_st"] == "BO-100"


def test_priloga_pdf_ima_eno_stran(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    pot = str(tmp_path / "STAT-BO-100-priloga.pdf")
    statika.narisi_prilogo(pot, CFG)
    assert len(pypdf.PdfReader(pot).pages) == 1