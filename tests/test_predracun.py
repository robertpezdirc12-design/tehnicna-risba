# -*- coding: utf-8 -*-
"""A8: predračun z neveljavnim/praznim cenikom ne sme zavajati.

Z „0.00“ PRIMER cenikom dokument ostane (informacije o količinah),
mora pa biti jasno označen kot INFORMATIVEN, brez zneskov „0,00 EUR“.
"""
from conftest import osnovni_cfg, stevilo_strani, besedilo_strani

import risba

import pytest

# Počasnejši testi (večstransko generiranje PDF) — hitra zanka: -m "not pocasi"
pytestmark = pytest.mark.pocasi


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


def test_predracun_vrata_brez_cenovnega_kluca(tmp_path):
    """Uporabniška najdba (USER-1): izdelani vratni kosi nimajo cenovnega
    ključa (None) — predračun NE SME pasti, temveč jih prikaže kot
    'cena po dogovoru' (brez izmišljenih cen) in jih ne šteje v SKUPAJ."""
    from conftest import osnovni_cfg, besedilo_strani
    cfg = osnovni_cfg(tmp_path / "vrata.pdf")
    cfg["cene"] = {"wpc_deska_m": 24.5, "alu_m": 18.0, "rocaj_kos": 45.0,
                   "nosilec_kos": 12.0, "vijak_kos": 0.9, "fasadni_kos": 1.2,
                   "anker_kos": 1.5, "osnova_kos": 15.0}
    cfg["vrata"] = [{"tip": "enokrilna", "x": 200, "sirina": 900,
                     "visina": 950, "smer": "desno-navzven"}]
    izhod, _png, _dod, _k = risba.generiraj(cfg)
    from pypdf import PdfReader
    assert len(PdfReader(izhod).pages) == 4      # vključno s predračunom
    txt = besedilo_strani(izhod, 2)
    assert "po dogovoru" in txt
    assert "PREDRAČUN" in txt


def test_predracun_znesek_brez_kluca():
    """predracun_znesek vrne vrstico 'po dogovoru' brez napake."""
    import proizvodnja
    postavke = [("Kos A", "2", "kos", "vijak_kos", 2),
                ("Izdelan kos", "1", "kos", None, 1)]
    z = proizvodnja.predracun_znesek({"vijak_kos": 0.9}, postavke)
    assert abs(z["skupaj"] - 1.8) < 1e-9
    assert any("po dogovoru" in str(v[2]) for v in z["vrstice"])
    assert z["manjkajoce_cene"] == []
