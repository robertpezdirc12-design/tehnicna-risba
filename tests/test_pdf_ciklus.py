# -*- coding: utf-8 -*-
"""A1 (P0): celovit življenjski cikel PdfPages — regresijski testi.

Napaka (matplotlib >= 3.10.7): savefig po zaprtju PdfPages TIHO prepise
datoteko v 0 B / 0 strani. Zato testi preverjajo DEJANSKO število strani
s PDF parserjem (pypdf) in vsebino posameznih strani, ne le odsotnost
izjem.
"""
import os

from conftest import stevilo_strani, besedilo_strani, osnovni_cfg, cfg_pokoncna

import risba


CENE_PRIMER = {"wpc_deska_m": 24.5, "vijak_kos": 0.35, "fasadni_kos": 1.2,
               "osnova_kos": 12.0, "nosilec_kos": 9.5, "alu_m": 18.0,
               "dela_ure": 12, "dela_ur_cena": 35.0}


def test_pdf_brez_predracuna_ima_3_strani(cfg_ograja):
    izhod, png, dodatni, kolicine = risba.generiraj(cfg_ograja)
    assert os.path.getsize(izhod) > 0
    # risba + montažni list + nalepke (predračuna brez cenika ni)
    assert stevilo_strani(izhod) == 3
    assert kolicine is not None and kolicine.get("kosovnica")


def test_pdf_s_predracunom_ima_4_strani(tmp_path):
    cfg = osnovni_cfg(tmp_path / "s-cenami.pdf", cene=dict(CENE_PRIMER))
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    assert stevilo_strani(izhod) == 4          # risba, mont., predračun, nalepke


def test_nalepke_ne_odstranijo_ostalih_strani(tmp_path):
    """Točno ta regresija: nalepke (fig4) so bile shranjene PO zaprtju
    PdfPages in so TIHO prepisale celoten PDF v 0 strani."""
    cfg = osnovni_cfg(tmp_path / "nalepke.pdf", cene=dict(CENE_PRIMER))
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    assert os.path.getsize(izhod) > 1000
    assert stevilo_strani(izhod) == 4
    # strani so resnično tam in v pravem vrstnem redu
    assert "MONTA" in besedilo_strani(izhod, 1).upper()
    assert "PREDRA" in besedilo_strani(izhod, 2).upper()
    assert "NALEP" in besedilo_strani(izhod, 3).upper()
    # kosovnica in naročilo sta izvožena
    koncnice = [os.path.splitext(p)[1] for p in dodatni]
    assert ".csv" in koncnice and ".txt" in koncnice


def test_pdf_za_obe_predlogi(tmp_path):
    for ime, cfg in (("ograja", osnovni_cfg(tmp_path / "og.pdf")),
                     ("pokoncna", cfg_pokoncna(tmp_path / "pk.pdf"))):
        izhod, png, dodatni, kolicine = risba.generiraj(cfg)
        assert stevilo_strani(izhod) == 3, ime   # risba, mont., nalepke
        assert os.path.getsize(izhod) > 1000, ime
        assert kolicine.get("kosovnica"), ime


def test_stran_1_je_risba_in_ne_prazna(cfg_ograja):
    izhod, png, dodatni, kolicine = risba.generiraj(cfg_ograja)
    t = besedilo_strani(izhod, 0).upper()
    assert "PO-009" in t                     # oznaka naloge na listu 1
    assert "2500" in t                       # kotirana širina


def test_kosovnica_csv_vsebuje_vse_kose(cfg_ograja):
    izhod, png, dodatni, kolicine = risba.generiraj(cfg_ograja)
    csv = [p for p in dodatni if p.endswith("-kosovnica.csv")]
    assert csv
    with open(csv[0], encoding="utf-8-sig") as f:
        vrstice = [v for v in f.read().splitlines() if v.strip()]
    n = cfg_ograja["mere"]["lamele"]
    assert len(vrstice) == n + 1             # glava + n kosov


def test_zavrnitev_ne_pusti_pokvarjenega_pdfja(cfg_ograja, tmp_path):
    """Pri napaki v konfiguraciji PDF sploh ne nastane oziroma je zavrnitev
    jasna — nikoli ne nastane tiho pokvarjen dokument (A1)."""
    cfg = osnovni_cfg(tmp_path / "napaka.pdf")
    cfg["dolzine_deske"] = [1200]            # sirina 2500 se ne izide
    try:
        risba.generiraj(cfg)
        assert False, "pričakovana zavrnitev (preveri_cfg)"
    except ValueError as e:
        assert "Kontrola pravilnosti" in str(e)
    assert not os.path.exists(str(tmp_path / "napaka.pdf"))


def test_opozorila_so_vidna_ce_montazni_list_pade(cfg_ograja, monkeypatch,
                                                  tmp_path):
    """Če montažni list pade, mora biti to jasno zapisano (opozorilo),
    dokument pa ne sme biti tiho označen kot popoln (A1)."""
    def napacen(*a, **k):
        raise RuntimeError("testni padec")
    monkeypatch.setattr(risba, "narisi_montazni_list", napacen)
    cfg = osnovni_cfg(tmp_path / "padec.pdf")
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    assert risba.ZADNJA_OPOZORILA, "padec mora biti zabeležen"
    assert any("Montažni list" in o for o in risba.ZADNJA_OPOZORILA)
    assert stevilo_strani(izhod) == 1         # samo risba (kolicine = nič)
    assert os.path.getsize(izhod) > 1000

def test_status_dokumenta_v_naslovnem_bloku(tmp_path):
    """Plan 2 (ISO 7200): STATUS se izpiše v naslovnem bloku."""
    cfg = osnovni_cfg(tmp_path / "status.pdf")
    cfg["status_dokumenta"] = "ZA POTRDITEV"
    izhod, _png, _dod, _k = risba.generiraj(cfg)
    assert "STATUS: ZA POTRDITEV" in besedilo_strani(izhod, 0)


def test_status_dokumenta_privzeto_v_delu(tmp_path):
    cfg = osnovni_cfg(tmp_path / "status2.pdf")
    izhod, _png, _dod, _k = risba.generiraj(cfg)
    assert "STATUS: V DELU" in besedilo_strani(izhod, 0)
