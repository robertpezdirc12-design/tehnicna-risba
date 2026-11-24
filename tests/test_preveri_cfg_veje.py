# -*- coding: utf-8 -*-
"""Vsaka veja `preveri_cfg` mora biti dosegljiva — in povedati, kaj je narobe.

Revizijska vrzel (P2/P3): „preveri_cfg B1–B7“ ni imel testov za vse veje.
Merjenje pokritosti je pokazalo ~20 neizvedenih vej; tu vsako pokrijemo z
minimalno konfiguracijo. Pravilo ostaja: slaba vrednost je NAPAKA v seznamu,
nikoli izjema — zato vsak test prebere seznam, ne pričakuje sledi sklada.
"""
import pytest

from conftest import osnovni_cfg, cfg_pokoncna

import jedro


def _napake(cfg, *podnizi):
    nap = jedro.preveri_cfg(cfg)
    for p in podnizi:
        assert any(p in n for n in nap), (p, nap)
    return nap


@pytest.mark.parametrize("kljuc", ["brez_optimizacije",
                                   "brez_zdruzevanja_rezov"])
def test_izklop_optimizacije_ni_podprt(kljuc):
    """A6: neoptimiziranega izpisa ni dovoljeno prikazati kot optimiranega."""
    cfg = osnovni_cfg("x.pdf")
    cfg[kljuc] = True
    _napake(cfg, f"Zahteva '{kljuc}' NI podprta")


@pytest.mark.parametrize("kljuc", ["optimizacija_rezov",
                                   "zdruzevanje_rezov"])
def test_izklop_z_false_ni_podprt(kljuc):
    cfg = osnovni_cfg("x.pdf")
    cfg[kljuc] = False
    _napake(cfg, f"'{kljuc}=false' NI podprta")


def test_status_dokumenta_mora_biti_dovoljen():
    cfg = osnovni_cfg("x.pdf")
    cfg["status_dokumenta"] = "KONČANO"
    _napake(cfg, "ni dovoljen")
    cfg["status_dokumenta"] = "v delu"
    assert jedro.preveri_cfg(cfg) == []


def test_revizije_slaba_oblika():
    cfg = osnovni_cfg("x.pdf")
    cfg["revizije"] = "A"
    _napake(cfg, "'revizije' mora biti seznam")

    cfg["revizije"] = [["A", "01.06.2026", "opis"]]
    _napake(cfg, "Revizija 1 mora biti")

    cfg["revizije"] = [[" ", "01.06.2026", "opis", "RP"]]
    _napake(cfg, "z izpolnjeno oznako")

    cfg["revizije"] = [["A", "01.06.2026", "prva izdaja", "RP"]]
    assert jedro.preveri_cfg(cfg) == []


def test_pokoncna_rocaj_in_odcep_presegata_visino():
    cfg = cfg_pokoncna("x.pdf", mere={"visina": 1500, "odcep": 1200,
                                      "rocaj_v": 400})
    _napake(cfg, "presega skupno višino")


def test_pokoncna_deska_sirsa_od_razpona_ni_tiho_skrcena():
    cfg = cfg_pokoncna("x.pdf", mere={"deska_sirina": 3000})
    _napake(cfg, "je širša kot razpon")


def test_pokoncna_razmak_stebrov_mora_presegati_steber():
    cfg = cfg_pokoncna("x.pdf", mere={"razmak_stebrov": 60})
    _napake(cfg, "večji od širine stebra")


def test_ograja_cona_profilov_in_odcepa():
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"].update({"visina": 1000, "odcep": 400, "profil_v": 400})
    _napake(cfg, "Višina profilov in odcepa presega")


def test_ograja_lamele_se_ne_prilegajo_v_cona():
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"].update({"visina": 1800, "odcep": 100, "profil_v": 40,
                        "lamele": 11, "lamela_v": 150})
    _napake(cfg, "Lamele se ne prilegajo")


def test_negativen_kerf_je_napaka():
    cfg = osnovni_cfg("x.pdf")
    cfg["kerf"] = -1
    _napake(cfg, "Kerf")


def test_dolzina_deske_brez_seznama_je_veljavna():
    """Starejši zapis `dolzina_deske: 5800` (brez seznama) mora delovati."""
    cfg = osnovni_cfg("x.pdf")
    cfg.pop("dolzine_deske")
    cfg["dolzina_deske"] = 5800
    assert jedro.preveri_cfg(cfg) == []


@pytest.mark.parametrize("vrednost", [5800, []])
def test_dolzine_deske_morajo_biti_neprazen_seznam(vrednost):
    cfg = osnovni_cfg("x.pdf")
    cfg["dolzine_deske"] = vrednost
    _napake(cfg, "morajo biti seznam števil")


def test_neveljavna_dolzina_v_seznamu():
    cfg = osnovni_cfg("x.pdf")
    cfg["dolzine_deske"] = [5800, -5]
    _napake(cfg, "Dolžina deske -5")


def test_nobena_deska_ni_dovolj_dolga():
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"]["sirina"] = 6000
    _napake(cfg, "Nobena nabavna dolžina desk ni dovolj velika")


def test_palica_prekratka_za_profil():
    cfg = osnovni_cfg("x.pdf")
    cfg["dolzina_palice"] = 1000
    _napake(cfg, "presega tovarniško dolžino palice")


def test_palica_prekratka_za_steber():
    cfg = cfg_pokoncna("x.pdf")
    cfg["dolzina_palice"] = 1000
    _napake(cfg, "Steber (")


def test_geometrija_pokoncne_ki_vrze_drugo_izjemo_ne_sesuje(monkeypatch):
    """Defenzivna veja: nepričakovana izjema geometrije ne sme pasti ven.

    Manjkajoče mere že javijo zgornje preverbe; če `razpored_pokoncna`
    vseeno vrže KeyError/TypeError, `preveri_cfg` vrne seznam napak.
    """
    def _sesuje(_m):
        raise KeyError("nepricakovano")
    monkeypatch.setattr(jedro, "razpored_pokoncna", _sesuje)
    cfg = cfg_pokoncna("x.pdf")
    assert isinstance(jedro.preveri_cfg(cfg), list)


def test_brez_merila_ni_napake():
    """`merilo` je neobvezen; odsotnost pomeni 'auto' — ne napake."""
    cfg = osnovni_cfg("x.pdf")
    cfg.pop("merilo")
    assert jedro.preveri_cfg(cfg) == []


def test_foto_ki_ne_obstaja(tmp_path):
    cfg = osnovni_cfg("x.pdf")
    cfg["foto"] = str(tmp_path / "ni-take.png")
    _napake(cfg, "Fotografija ne obstaja")


def test_segmenti_niso_seznam():
    cfg = osnovni_cfg("x.pdf")
    cfg["segmenti"] = {"tip": "ograja"}
    _napake(cfg, "'segmenti' mora biti seznam segmentov")


def test_vrata_podatki_ki_vrzejo_so_napaka_ne_izjema(monkeypatch):
    def _sesuje(_cfg):
        raise ValueError("pokvarjen vnos")
    monkeypatch.setattr(jedro, "vrata_podatki", _sesuje)
    cfg = osnovni_cfg("x.pdf")
    cfg["vrata"] = [{"tip": "ograda", "sirina": 900, "visina": 1200}]
    _napake(cfg, "Vrata/prehodi: pokvarjen vnos")
