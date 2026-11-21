# -*- coding: utf-8 -*-
"""A2/A6/A10: validacija konfiguracije — regresijski testi.

A2: kontrola dolžine kosa mora preverjati DEJANSKO dolžino kosa po predlogi
(prečna ograja: širina ograje; pokončna: višina desk = visina - rocaj_v -
odcep), ne katerekoli mere.
"""
import pytest

from conftest import osnovni_cfg, cfg_pokoncna

import risba
from razrez import kos_iz_vira


# ------------------------------------------------------------ A2: dolžina kosa
def test_ograja_kos_je_sirina_ne_lamela(tmp_path):
    """Lamela je kratka (120), kos pa je dolg 2500 (širina) — dolžine desk
    1200 mm ne smejo zadostovati."""
    cfg = osnovni_cfg(tmp_path / "a2.pdf", dolzine_deske=[1200],
                      dolzina_deske=1200)
    napake = risba.preveri_cfg(cfg)
    assert any("Nobena nabavna dolžina" in n for n in napake), napake


def test_ograja_zadostna_dolzina_nima_napake(tmp_path):
    cfg = osnovni_cfg(tmp_path / "ok.pdf", dolzine_deske=[5800])
    assert risba.preveri_cfg(cfg) == []


def test_pokoncna_kos_vkljucuje_rocaj_in_odcep(tmp_path):
    """visina 1150 - rocaj 100 - odcep 50 = 1000 mm; palica 1000 mm
    zadošča. Če bi formula pozabila ročaj (kos 1100 mm), bi jo zavrnila."""
    cfg = cfg_pokoncna(tmp_path / "p.pdf", dolzine_deske=[1000],
                       dolzina_deske=1000)
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"].update({"visina": 1150, "rocaj_v": 100, "odcep": 50,
                        "lamele": 4, "vrzel": 20})
    napake = risba.preveri_cfg(cfg)
    assert not any("Nobena nabavna" in n for n in napake), napake
    # ko kos preseže palico, mora biti napaka
    cfg["dolzine_deske"] = [990]
    assert any("Nobena nabavna" in n for n in risba.preveri_cfg(cfg))


def test_pokoncna_kos_manjsa_od_palice_je_napaka(tmp_path):
    cfg = cfg_pokoncna(tmp_path / "p2.pdf", dolzine_deske=[990])
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"].update({"visina": 1150, "rocaj_v": 100, "odcep": 50,
                        "lamele": 4, "vrzel": 20})
    assert kos_iz_vira(990, 1000, 3) == 0
    assert any("Nobena nabavna" in n for n in risba.preveri_cfg(cfg))


# ------------------------------------------------------- A2: kerf in dolžine
def test_negativen_kerf_je_napaka(tmp_path):
    cfg = osnovni_cfg(tmp_path / "k.pdf", kerf=-1)
    assert any("Kerf" in n for n in risba.preveri_cfg(cfg))


def test_prazen_seznam_dolzin_je_napaka(tmp_path):
    cfg = osnovni_cfg(tmp_path / "d.pdf", dolzine_deske=[])
    assert any("dolžin" in n.lower() for n in risba.preveri_cfg(cfg))


def test_neveljavna_dolzina_deske_je_napaka(tmp_path):
    cfg = osnovni_cfg(tmp_path / "d2.pdf", dolzine_deske=["abc", 5800])
    assert any("dolžin" in n.lower() for n in risba.preveri_cfg(cfg))


def test_negativna_dolzina_deske_je_napaka(tmp_path):
    cfg = osnovni_cfg(tmp_path / "d3.pdf", dolzine_deske=[-5800])
    assert any("dolžin" in n.lower() for n in risba.preveri_cfg(cfg))


def test_prazna_mera_je_napaka(tmp_path):
    cfg = osnovni_cfg(tmp_path / "m.pdf")
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"]["sirina"] = 0
    assert any("sirina" in n.lower() or "> 0" in n
               for n in risba.preveri_cfg(cfg))


def test_rocaj_presega_palico_je_napaka(tmp_path):
    """Zaključni profil/ročaj (širina ograje) ne sme presegati palice."""
    cfg = osnovni_cfg(tmp_path / "r.pdf", dolzina_palice=2000)
    napake = risba.preveri_cfg(cfg)
    assert any("palice" in n for n in napake), napake


def test_steber_presega_palico_je_napaka(tmp_path):
    cfg = cfg_pokoncna(tmp_path / "r2.pdf", dolzina_palice=1500)
    napake = risba.preveri_cfg(cfg)
    assert any("palice" in n for n in napake), napake


# ------------------------------------------------------- A10: normalizacija
def test_generiraj_normalizira_konfiguracijo(tmp_path):
    """Manjkajoči kerf/dolzine_deske se dopolnijo iz PRIVZETO (A10)."""
    cfg = osnovni_cfg(tmp_path / "n.pdf")
    del cfg["dolzine_deske"]
    del cfg["kerf"]
    cfg["dolzina_deske"] = 3000
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    assert izhod and kolicine.get("kosovnica")


def test_privzeto_ne_uporablja_ostankov():
    """A3/A5: privzeta vrednost 'uporabi ostanke' je izklopljena."""
    assert risba.PRIVZETO["uporabi_ostanke"] is False


# ------------------------------------------------- A6: brez optimizacije
def test_brez_optimizacije_je_zavrnjeno(tmp_path):
    cfg = osnovni_cfg(tmp_path / "bo.pdf", brez_optimizacije=True)
    with pytest.raises(ValueError, match="NI podprta"):
        risba.generiraj(cfg)


def test_izklop_zdruzevanja_je_zavrnjen(tmp_path):
    cfg = osnovni_cfg(tmp_path / "bz.pdf", zdruzevanje_rezov=False)
    with pytest.raises(ValueError, match="NI podprta"):
        risba.generiraj(cfg)
    cfg2 = osnovni_cfg(tmp_path / "bz2.pdf", optimizacija_rezov=False)
    with pytest.raises(ValueError, match="NI podprta"):
        risba.generiraj(cfg2)


# ------------------------------------------------- napake so razumljive
def test_neznana_predloga_je_jasna_napaka(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="neznano")
    with pytest.raises(ValueError, match="Neznana predloga"):
        risba.generiraj(cfg)


def test_kontrola_zavrne_in_pove_zakaj(tmp_path):
    cfg = osnovni_cfg(tmp_path / "y.pdf")
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"]["visina"] = -5
    with pytest.raises(ValueError) as e:
        risba.generiraj(cfg)
    assert "Kontrola pravilnosti" in str(e.value)
    assert "-" in str(e.value)                 # izpisane posamezne napake

def test_status_dokumenta_nedovoljen(tmp_path):
    """Plan 2 (ISO 7200): nedovoljen status dokumenta je napaka."""
    cfg = osnovni_cfg(tmp_path / "status.pdf")
    cfg["status_dokumenta"] = "ZA GRADNJO"
    with pytest.raises(ValueError) as e:
        risba.generiraj(cfg)
    assert "Status dokumenta" in str(e.value)


def test_status_dokumenta_dovoljeni_ok(tmp_path):
    for status in ("V DELU", "ZA POTRDITEV", "IZVEDENO"):
        cfg = osnovni_cfg(tmp_path / f"status-{status.replace(' ', '_')}.pdf")
        cfg["status_dokumenta"] = status
        risba.generiraj(cfg)          # brez izjeme


def test_privzeto_stevilo_lamel_se_prilega_coni(tmp_path):
    """Uporabniška najdba (testiranje USER-1): vnos BREZ števila lamel
    ne sme pasti na privzeti vrednosti — ta se mora prilagoditi meram.
    Eksplicitno število uporabnika ostane strogo preverjeno."""
    import jedro
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["mere"] = dict(cfg["mere"])
    cfg["mere"].pop("lamele", None)          # uporabnik ga NI vnesel
    cfg["mere"].update({"visina": 1200, "odcep": 250, "profil_v": 40,
                        "lamela_v": 100})
    izhod = jedro.zdruzi(cfg)
    n = izhod["mere"]["lamele"]
    cona = 1200 - 250 - 2 * 40
    assert n * 100 <= cona, (n, cona)
    assert jedro.preveri_cfg(izhod) == []    # veljavno brez napake
    risba.generiraj(dict(izhod, izhod=str(tmp_path / "x.pdf")))  # brez izjeme

    # ekspliciten uporabnikov vrednost pa OSTANE strogo preverjena:
    cfg2 = osnovni_cfg(tmp_path / "y.pdf")
    cfg2["mere"] = dict(cfg2["mere"], lamele=13, visina=1200, odcep=250,
                        profil_v=40, lamela_v=100)
    with pytest.raises(ValueError) as e:
        risba.generiraj(cfg2)
    assert "Lamele se ne prilegajo" in str(e.value)


def test_privzeto_stevilo_lamel_robni_primeri():
    import jedro
    assert jedro.privzeto_stevilo_lamel({"visina": 0, "odcep": 0,
                                         "profil_v": 0, "lamela_v": 60}) == 1
    assert jedro.privzeto_stevilo_lamel({"visina": 100, "odcep": 0,
                                         "profil_v": 0, "lamela_v": 0}) == 1
    # privzete mere: cona 1060, lv 60 -> (1060-8)//68 = 15
    assert jedro.privzeto_stevilo_lamel(jedro.PRIVZETO["mere"]) == 15
