# -*- coding: utf-8 -*-
"""Validacija ne sme sesuti na napačnih tipih (YAML nizi, null, seznam).

`preveri_cfg` je javni vmesnik: CLI, GUI in API pričakujejo SEZNAM napak,
ne izjeme. Pred popravkom je npr. `deska_sirina: "100"` vrgel TypeError
globoko v geometrijskih primerjavah.
"""
import pytest

from conftest import osnovni_cfg, cfg_pokoncna

import jedro
import risba


def _cfg(predloga, mere):
    cfg = (cfg_pokoncna("x.pdf") if predloga == "pokončna"
           else osnovni_cfg("x.pdf"))
    cfg["mere"] = dict(cfg["mere"], **mere)
    return cfg


@pytest.mark.parametrize("predloga, mere, besedilo", [
    ("pokončna", {"deska_sirina": "100"}, "Širina deske"),
    ("pokončna", {"razmak_stebrov": "1200"}, "Razmak stebrov"),
    ("pokončna", {"rocaj_v": "40"}, "ročaja"),
    ("pokončna", {"steber_sirina": "60"}, "stebra"),
    ("ograja", {"lamele": "11"}, "Število lamel"),
    ("ograja", {"lamela_v": "120"}, "Višina lamel"),
    ("ograja", {"debelina": None}, "Debelina lamel"),
    ("ograja", {"profil_v": "80"}, "profila"),
    ("ograja", {"razmak_nosilcev": "1000"}, "Razmak nosilcev"),
    ("ograja", {"odcep": "250"}, "odcep"),
    ("ograja", {"vrzel": "20"}, "Vrzel"),
])
def test_napacen_tip_je_napaka_ne_izjema(predloga, mere, besedilo):
    napake = jedro.preveri_cfg(_cfg(predloga, mere))
    assert any(besedilo in n for n in napake), napake


def test_mere_ni_objekt():
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"] = []
    napake = jedro.preveri_cfg(cfg)
    assert any("'mere'" in n for n in napake), napake


def test_foto_napacen_tip():
    cfg = osnovni_cfg("x.pdf")
    cfg["foto"] = 123
    napake = jedro.preveri_cfg(cfg)
    assert any("'foto'" in n for n in napake), napake


def test_generiraj_vrne_valueerror_ne_typeerror(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["mere"]["lamele"] = "11"
    with pytest.raises(ValueError, match="Kontrola pravilnosti"):
        risba.generiraj(cfg)


@pytest.mark.parametrize("predloga", ["ograja", "pokončna"])
def test_veljavna_konfiguracija_ostane_brez_napak(predloga):
    assert jedro.preveri_cfg(_cfg(predloga, {})) == []


def test_manjkajoce_lamele_ni_napaka_za_ograjo():
    """Združevanje manjkajoče lamele izračuna; preverjanje samo ne sme
    zahtevati vrednosti, ki je uporabnik ni podal."""
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"].pop("lamele")
    assert jedro.preveri_cfg(cfg) == []

def test_zdruzi_z_none_mere_uporabi_privzete():
    """`mere:` brez vrednosti v YAML je None, ne seznam — to ni napaka,
    ampak enako kot manjkajoče mere."""
    cfg = jedro.zdruzi({"mere": None, "izhod": "x.pdf"})
    assert isinstance(cfg["mere"], dict)
    assert cfg["mere"]["sirina"] == jedro.PRIVZETO["mere"]["sirina"]


def test_nalozi_konf_prazne_mere(tmp_path):
    """`mere:` v YAML se prebere kot None — nalaganje ne sme pasti."""
    pot = tmp_path / "p.yaml"
    pot.write_text("izhod: x.pdf\nmere:\n", encoding="utf-8")
    cfg = jedro.nalozi_konf(pot)
    assert cfg["mere"]["sirina"] == jedro.PRIVZETO["mere"]["sirina"]


def test_generiraj_brez_izhoda_ne_pise_v_cwd(tmp_path, monkeypatch):
    """Znana past: `generiraj({})` je tiho ustvaril BO-001.pdf v CWD."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="izhod"):
        risba.generiraj({})
    assert not (tmp_path / "BO-001.pdf").exists()
    assert [p.name for p in tmp_path.iterdir()] == ["data"]


def test_generiraj_mere_seznam_vrne_valueerror(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["mere"] = []
    with pytest.raises(ValueError, match="mere"):
        risba.generiraj(cfg)