# -*- coding: utf-8 -*-
"""B2/B3/B4: pokončna predloga — geometrija polj, vrzel, količine.

Regresija 3 (vijaki): 2 vijaka na stik × 2 sosednja stebra = 4 na desko;
stara formula n_d × n_s × 2 je preštevala (20 desk × 3 stebri → 120 namesto 80).
"""
import pytest

from conftest import cfg_pokoncna, osnovni_cfg

import razrez
import risba
from razrez import stevilo_palic


# ------------------------------------------------------------- B2: vrzel
def test_vrzel_je_natancno_uporabnikova_mera(cfg_pok):
    """Primer iz poročila: 3000 / 3×60 / 20×100 / vrzel 20 -> 20, NE 43.16."""
    p = risba.razpored_pokoncna(cfg_pok["mere"])
    assert abs(p["vrzel"] - 20.0) < 1e-9
    # deske so zares razporejene z natanko to vrzeljo v vsakem polju
    for polje in p["polja"]:
        xs = polje["deske_x"]
        if len(xs) > 1:
            razmiki = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
            for r in razmiki:
                assert abs(r - (cfg_pok["mere"]["deska_sirina"] + 20.0)) < 1e-6


def test_vrzel_mora_iti_cez_preverbo_konfiguracije(cfg_pok):
    """Vhodni podatki (vrzel 20) morajo priti skozi validacijo nespremenjeni."""
    napake = risba.preveri_cfg(cfg_pok)
    assert napake == []


def test_ce_se_deske_ne_prilegajo_je_jasna_napaka(tmp_path):
    cfg = cfg_pokoncna(tmp_path / "x.pdf")
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"]["vrzel"] = 200          # neizvedljivo velika vrzel
    napake = risba.preveri_cfg(cfg)
    assert any("ne prilegajo" in n for n in napake), napake


def test_polja_ne_prekrijejo_stebrov(cfg_pok):
    p = risba.razpored_pokoncna(cfg_pok["mere"])
    for polje in p["polja"]:
        for x in polje["deske_x"]:
            assert polje["levo"] - 1e-6 <= x
            assert x + cfg_pok["mere"]["deska_sirina"] <= polje["desno"] + 1e-6


def test_stebri_in_polja_ustrezajo_sirini(cfg_pok):
    p = risba.razpored_pokoncna(cfg_pok["mere"])
    sir = cfg_pok["mere"]["sirina"]
    assert p["centri"][0] == pytest.approx(cfg_pok["mere"]["steber_sirina"] / 2)
    assert p["centri"][-1] == pytest.approx(
        sir - cfg_pok["mere"]["steber_sirina"] / 2)
    skupaj = sum(len(f["deske_x"]) for f in p["polja"])
    assert skupaj == cfg_pok["mere"]["lamele"]


# --------------------------------------------------- regresija 3: vijaki
def test_vijaki_4_na_desko(tmp_path):
    """20 desk × 3 stebri -> 80 vijakov (4 na desko), NE 120."""
    cfg = cfg_pokoncna(tmp_path / "v.pdf")
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"]["razmak_stebrov"] = 1500       # 3 stebri pri 3000 mm
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    vijaki = [p for p in kolicine["postavke"] if p[3] == "vijak_kos"]
    assert vijaki, kolicine["postavke"]
    n_d = cfg["mere"]["lamele"]
    assert vijaki[0][4] == n_d * 4
    # tudi v naročilu je ta količina
    assert f"{n_d * 4} kos" in kolicine["narocilo"]


def test_vijaki_v_risbi_in_kolicinah_se_skladata(tmp_path):
    cfg = cfg_pokoncna(tmp_path / "v2.pdf")
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    vijaki = [p for p in kolicine["postavke"] if p[3] == "vijak_kos"][0]
    assert vijaki[4] == cfg["mere"]["lamele"] * 4


# -------------------------------------------------- B3: kolicine / palice
def test_palice_s_za_stebre():
    """9 stebrov × 1200 mm iz palic 6000 mm -> 3 palice."""
    assert stevilo_palic(1200, 9, 6000, 3) == 3


def test_montazni_pokoncna_palice_in_stebri(tmp_path):
    cfg = cfg_pokoncna(tmp_path / "p.pdf")
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"].update({"sirina": 3000, "razmak_stebrov": 400, "visina": 1200,
                        "odcep": 50, "rocaj_v": 40, "vrzel": 20,
                        "lamele": 8, "deska_sirina": 100})
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    n_s = 9                          # ceil((3000-60)/400)+1 = 9
    stebri = [p for p in kolicine["postavke"] if p[3] == "alu_m"]
    assert stebri, kolicine["postavke"]
    # palice = ceil(9 / 3) = 3 (NE ceil(9×1203/6000) = 2)
    assert stebri[0][1].startswith("3 kos"), stebri
    # kosovnica vsebuje 8 desk
    assert len(kolicine["kosovnica"]) == 8


def test_visina_stebra_je_polna_visina(tmp_path):
    """Steber meri višino ograje (0..visina), ne višino desk."""
    cfg = cfg_pokoncna(tmp_path / "p2.pdf")
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    nar = kolicine["narocilo"]
    assert "stebri" in nar
    assert f"{cfg['mere']['visina']:g} mm" in nar.replace(".0", "")


def test_vrzel_izven_obmocja_opozori(tmp_path, capsys):
    cfg = cfg_pokoncna(tmp_path / "o.pdf")
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"]["vrzel"] = 2            # pod priporočenim območjem
    risba.razpored_pokoncna(cfg["mere"])
    zajeto = capsys.readouterr()
    assert "OPOZORILO" in zajeto.err