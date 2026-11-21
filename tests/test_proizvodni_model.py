# -*- coding: utf-8 -*-
"""Kanonični proizvodni model količin (issue #6, §3).

Vse tabele (SEZNAM SESTAVNIH DELOV), montažni list, količine, kosovnica
in naročilo morajo šteti iz ENEGA modela (risba.proizvodni_model).
Pričakovane vrednosti so ročno izračunane (glej komentarje) in
preverjene tudi z NEODVISNIM štetjem: (n_kosov, n_stikov, vijaki = 2·stikov).

Napaka iz HEAD: tabela je štela n_desk·n_stebrov·2 = 120 vijakov,
količine pa 4/desko = 80 (testni primer: 20 desk, 3 stebri).
"""
import pytest

from conftest import osnovni_cfg, cfg_pokoncna, besedilo_strani

import risba


# ročni izračun (T2): 20 desk ima po 2 robova (2 stika) → 40 stikov
# → 2 vijaka na stik = 80 vijakov; 3 stebri → 3 osnove → 6 ankerjev.
PRICAKOVANO_POK = {"n_kosov": 20, "n_stikov": 40, "vijaki_element": 80,
                   "n_nosilcev": 3, "pritrdila_nosilec": 6}

# ročni izračun (T7): 11 lamel × 4 nosilca = 44 parov × 2 vijaka = 88;
# 4 nosilci → 8 pritrdil nosilca.
PRICAKOVANO_PREC = {"n_kosov": 11, "n_stikov": 44, "vijaki_element": 88,
                    "n_nosilcev": 4, "pritrdila_nosilec": 8}


def _preveri_model(m, pricakovano):
    for kljuc, vrednost in pricakovano.items():
        assert m[kljuc] == vrednost, kljuc
    # neodvisna kontrola: vijaki = 2 na stik
    assert m["vijaki_element"] == 2 * m["n_stikov"]
    assert m["pritrdila_nosilec"] == 2 * m["n_nosilcev"]


def test_t2_pokoncna_brez_odprtin(tmp_path):
    c = cfg_pokoncna(tmp_path / "t2.pdf")
    _preveri_model(risba.proizvodni_model(c), PRICAKOVANO_POK)


def test_t3_pokoncna_z_odprtino_430_1330(tmp_path):
    """Odprtina [430, 1330]: deske 175/295 nedotaknjeni (2+2 stika), 415 →
    kos 1 stik, 6 desk v celoti v odprtini (0 stikov), 1255 → kos 1 stik,
    polje 2: 10 desk × 2 = 20 → n_kosov=14, n_stikov=26, vijaki=52."""
    c = cfg_pokoncna(tmp_path / "t3.pdf", vrata=[
        {"tip": "enokrilna", "x": 430, "sirina": 900, "visina": 1400,
         "smer": "desno-navzven"}])
    _preveri_model(risba.proizvodni_model(c),
                   {"n_kosov": 14, "n_stikov": 26, "vijaki_element": 52,
                    "n_nosilcev": 3, "pritrdila_nosilec": 6})


def test_t4_pokoncna_z_ozkim_prehodom_400_600(tmp_path):
    """Prehod [400, 600]: deske 415 in 515 odpadeta, 535…635 → kos (600,635)
    z 1 stikom, ostalo 18 desk po 2 stika → n_kosov=19, n_stikov=37, vijaki=74.
    (Prehod namesto vrat: krilo širine 200 mm bi bilo manjše od profilov.)"""
    c = cfg_pokoncna(tmp_path / "t4.pdf", prehodi=[
        {"tip": "prehodna", "x": 400, "sirina": 200, "visina": 1400}])
    _preveri_model(risba.proizvodni_model(c),
                   {"n_kosov": 19, "n_stikov": 37, "vijaki_element": 74,
                    "n_nosilcev": 3, "pritrdila_nosilec": 6})


def test_t7_prečna_brez_odprtin(tmp_path):
    c = osnovni_cfg(tmp_path / "t7.pdf")
    _preveri_model(risba.proizvodni_model(c), PRICAKOVANO_PREC)


def test_t8_prečna_z_odprtino_800_1700(tmp_path):
    """Odprtina [800, 1700]: vsaka lamela → kosa (0,800) in (1700,2500) →
    22 kosov, 22 stikov (le zunanja robova), 44 vijakov; nosilca 866,67 in
    1633,33 padeta v odprtino → brez vijakov na njiju."""
    c = osnovni_cfg(tmp_path / "t8.pdf", vrata=[
        {"tip": "enokrilna", "x": 800, "sirina": 900, "visina": 1500,
         "smer": "desno-navzven"}])
    _preveri_model(risba.proizvodni_model(c),
                   {"n_kosov": 22, "n_stikov": 22, "vijaki_element": 44,
                    "n_nosilcev": 4, "pritrdila_nosilec": 8})


def test_t11_neznana_predloga_ne_pade_tiho_v_prečno_vejo(tmp_path):
    """ASCII 'pokoncna' mora vrniti jasno napako, ne napačnih količin."""
    c = cfg_pokoncna(tmp_path / "t11.pdf", predloga="pokoncna")
    with pytest.raises(ValueError, match="predloga"):
        risba.proizvodni_model(c)


def test_t12_strani_pdf_kazejo_enake_kolicine(tmp_path):
    """Križanje izpisov: tabela (stran 1) in montažni list (stran 2)
    morata za testni primer (T2) vsebovati 80 vijakov — NE 120."""
    c = cfg_pokoncna(tmp_path / "t12.pdf")
    izhod, _png, _dod, kolicine = risba.generiraj(c)
    s1 = besedilo_strani(izhod, 0)
    s2 = besedilo_strani(izhod, 1)
    for s in (s1, s2):
        assert "120 kos" not in s
    assert "80 kos" in s1 and "80 kos" in s2
    # natančna vrstica vijakov v naročilu (ne vakuumska "80" — QA najdba #2)
    nar = kolicine["narocilo"]
    assert "- RF M8×70 Inox — 80 kos" in nar
    assert "120 kos" not in nar


def test_narocilo_prečne_vsebuje_obe_sekciji_profila_in_nosilce(tmp_path):
    """Naročilo mora ločeno navesti zgornji in spodnji alu profil ter
    nosilce (issue #6: prej so manjkali spodnji profil in nosilci)."""
    c = osnovni_cfg(tmp_path / "nar.pdf")
    _izhod, _png, _dod, kolicine = risba.generiraj(c)
    nar = kolicine["narocilo"]
    assert "80×40×3" in nar and "60×40×3" in nar
    assert "Nosilni nosilec" in nar
    # vsaka sekcija profila ima svojo nabavo (1 kos × 2500 mm)
    assert nar.count("2500 mm") >= 2

def test_montazne_letve_pokoncne_v_modelu(tmp_path):
    # F1 (issue #5, O3): montažne letve za deskami (2 na polje) so del
    # proizvodnega modela — prej sploh niso bile v modelu/BOM.
    cfg = osnovni_cfg(tmp_path / "ml.pdf", predloga="pokončna")
    m = risba.proizvodni_model(cfg)
    assert m["tip"] == "pokoncna"
    assert m["montazne_letve"] == 2 * len(
        risba.razpored_pokoncna(cfg["mere"])["polja"])
    assert m["montazne_letve"] > 0
