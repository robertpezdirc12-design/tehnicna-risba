# -*- coding: utf-8 -*-
"""UI/UX Plan G: dokument ponudbe (Good/Better/Best).

POŠTENOST: brez cenika variante NI izmišljene številke — znesek je
„cena po dogovoru“. Testi to izrecno preverjajo.
"""

from conftest import osnovni_cfg

import ponudba
import proizvodnja


def test_brez_variant_je_cena_po_dogovoru(tmp_path):
    """Brez cenikov osnovna/premium NI številk — samo priporočena."""
    cfg = osnovni_cfg(tmp_path / "o.pdf", cene={"wpc_deska_m": 12.5})
    m = ponudba.sestavi_moznosti(cfg)
    assert [x["ime"] for x in m] == ["OSNOVNA", "PRIPOROČENA", "PREMIUM"]
    assert m[0]["znesek"] is None and "po dogovoru" in m[0]["oznaka"]
    assert m[2]["znesek"] is None and "po dogovoru" in m[2]["oznaka"]
    # priporočena je izračunana iz glavnega cenika
    assert m[1]["znesek"] is not None
    assert "EUR" in m[1]["oznaka"]


def test_z_variantami_je_znesek_iz_cenika(tmp_path):
    cfg = osnovni_cfg(
        tmp_path / "o.pdf",
        cene={"wpc_deska_m": 12.0},
        cene_osnovna={"wpc_deska_m": 10.0},
        cene_premium={"wpc_deska_m": 15.0})
    m = ponudba.sestavi_moznosti(cfg)
    # zneski morajo slediti razmerju cenikov (ročno preverjeno)
    osnovna, priporocena, premium = (x["znesek"] for x in m)
    assert osnovna < priporocena < premium
    kol = proizvodnja.izracunaj_kolicine(cfg)
    wpc = [n for (_a, _b, _c, k, n) in kol["postavke"] if k == "wpc_deska_m"]
    assert abs(priporocena - sum(wpc) * 12.0) < 1e-6


def test_ponudba_pdf_vsebina(tmp_path):
    cfg = osnovni_cfg(tmp_path / "o.pdf", cene={"wpc_deska_m": 12.5})
    pot = str(tmp_path / "ponudba.pdf")
    ponudba.narisi_ponudbo(pot, cfg)
    from pypdf import PdfReader
    t = PdfReader(pot).pages[0].extract_text()
    assert "PONUDBA" in t
    assert "OSNOVNA" in t and "PRIPOROČENA" in t and "PREMIUM" in t
    assert "BREZ DDV" in t
    assert "po dogovoru" in t          # pošteno označene opcije brez cenika
    assert "NI statični izračun" in t  # omejitev odgovornosti ostane


def test_ponudba_brez_cenika_sploh_nima_zneskov(tmp_path):
    """Brez kakršnegakoli cenika nobena opcija nima številke."""
    cfg = osnovni_cfg(tmp_path / "o.pdf")
    m = ponudba.sestavi_moznosti(cfg)
    assert all(x["znesek"] is None for x in m)

def test_ponudba_brez_dvojne_enote(tmp_path):
    """'m m' v ponudbi (ista napaka kot prej v predračunu, a v ponudba.py)."""
    from pypdf import PdfReader
    import ponudba
    from conftest import osnovni_cfg
    c = osnovni_cfg(str(tmp_path / "R.pdf"))
    c["cene"] = {"lamele_m": 10.0}
    pot = str(tmp_path / "ponudba.pdf")
    ponudba.narisi_ponudbo(pot, c)
    bes = "".join((pg.extract_text() or "") for pg in PdfReader(pot).pages)
    # vzorec ' m m' (presledek+m+presledek+m) — NE 'premiuM Materiali'
    assert " m m" not in bes, "ponudba ne sme podvajati enote ('75.4 m m')"
    assert "IZVEDBENE MOŽNOSTI" in bes
