# -*- coding: utf-8 -*-
"""A8: predračun z neveljavnim/praznim cenikom ne sme zavajati.

Z „0.00“ PRIMER cenikom dokument ostane (informacije o količinah),
mora pa biti jasno označen kot INFORMATIVEN, brez zneskov „0,00 EUR“.
"""
from conftest import osnovni_cfg, stevilo_strani, besedilo_strani

import risba


def test_predracun_z_primer_cenikom_je_informativen(tmp_path):
    cfg = osnovni_cfg(tmp_path / "pr.pdf",
                      cene={"wpc_deska_m": 0.0, "vijak_kos": 0.0,
                            "dela_ure": 12, "dela_ur_cena": 0.0})
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    assert stevilo_strani(izhod) == 4         # dokument ostane
    t = besedilo_strani(izhod, 2).upper()
    t_brez = t.replace(" ", "")
    assert "INFORMATIVEN" in t                # jasna oznaka
    assert "BREZ VELJAVNEGA CENIKA" in t
    # brez zavajajočih zneskov „0,00 EUR“ (upoštevaje presledke v PDF)
    assert "0.00EUR" not in t_brez and "0,00EUR" not in t_brez
    assert "NI OBRAČUNANO" in t or "NI OBRA" in t


def test_predracun_z_veljavnim_cenikom_ima_zneske(tmp_path):
    cfg = osnovni_cfg(tmp_path / "pv.pdf",
                      cene={"wpc_deska_m": 24.5, "vijak_kos": 0.35,
                            "dela_ure": 12, "dela_ur_cena": 35.0})
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    t = besedilo_strani(izhod, 2).upper()
    assert "ORIENTACIJSKI" in t
    assert "SKUPAJ" in t
    assert "EUR" in t


def test_predracun_delno_manjkajoce_cene_niso_skrite(tmp_path):
    cfg = osnovni_cfg(tmp_path / "pd.pdf",
                      cene={"wpc_deska_m": 24.5, "vijak_kos": 0.0})
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    t = besedilo_strani(izhod, 2).upper()
    assert "NI OBRAČUNANO" in t or "NI OBRA" in t
    assert "NI POPOLN" in t or "MANJKAJO" in t


def test_brez_cenikacni_strani_ni(tmp_path):
    """Brez ključa 'cene' predračuna sploh ne objavimo (3 strani:
    risba + montažni list + nalepke)."""
    cfg = osnovni_cfg(tmp_path / "bb.pdf")
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    assert stevilo_strani(izhod) == 3

def test_predracun_manjkajoca_cena_opozorjena_ne_tiha(tmp_path):
    # F1 (issue #5): manjkajoč ključ cene NE sme tiho izpustiti postavke.
    risba.ZADNJA_OPOZORILA.clear()
    cfg = osnovni_cfg(tmp_path / "pm.pdf",
                      cene={"wpc_deska_m": 24.5,
                            "dela_ure": 12, "dela_ur_cena": 35.0})
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    t = besedilo_strani(izhod, 2).upper()
    assert "CENA MANJKA" in t                  # vrstica NI izpuščena
    assert any("manjkajo cene" in o.lower() for o in risba.ZADNJA_OPOZORILA)
