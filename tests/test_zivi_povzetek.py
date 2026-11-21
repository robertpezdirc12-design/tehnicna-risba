# -*- coding: utf-8 -*-
"""UI/UX Plan A: živi povzetek — čisti izračun količin in cene.

Dokazi:
1. `proizvodnja.izracunaj_kolicine` vrne NATANČNO iste količine, kot jih
   vrne `risba.generiraj` (izločitev brez spremembe številk — issue #6).
2. `proizvodnja.predracun_znesek` šteje pravilno (ročno preverjen seštevek).
3. GUI živi povzetek se osveži brez sesutja tudi ob neveljavnem vnosu.
"""
import pytest

from conftest import osnovni_cfg, cfg_pokoncna

import proizvodnja
import risba


def _generiraj_kolicine(cfg, tmp_path, ime):
    izhod = str(tmp_path / ime)
    _p, _png, _dod, kolicine = risba.generiraj(
        {**cfg, "izhod": izhod}, dpi_png=60)
    return kolicine


# ---------------------------------------------------------------- enakovrednost
def test_izracunaj_kolicine_je_enako_generiraji_ograda(tmp_path):
    cfg = osnovni_cfg(tmp_path / "o.pdf")
    k1 = proizvodnja.izracunaj_kolicine(cfg)
    k2 = _generiraj_kolicine(cfg, tmp_path, "o2.pdf")
    assert k1["postavke"] == k2["postavke"]
    assert k1["narocilo"] == k2["narocilo"]
    assert k1["kosovnica"] == k2["kosovnica"]
    assert k1["ostanki_posodobitev"] == k2["ostanki_posodobitev"]


def test_izracunaj_kolicine_je_enako_generiraji_pokoncna(tmp_path):
    cfg = cfg_pokoncna(tmp_path / "p.pdf")
    k1 = proizvodnja.izracunaj_kolicine(cfg)
    k2 = _generiraj_kolicine(cfg, tmp_path, "p2.pdf")
    assert k1["postavke"] == k2["postavke"]
    assert k1["narocilo"] == k2["narocilo"]
    assert k1["kosovnica"] == k2["kosovnica"]


def test_izracunaj_kolicine_z_vrati_je_enako_generiraji(tmp_path):
    cfg = osnovni_cfg(
        tmp_path / "v.pdf",
        vrata=[{"tip": "enokrilna", "x": 200, "sirina": 900, "visina": 1500,
                "smer": "desno-navzven"}])
    k1 = proizvodnja.izracunaj_kolicine(cfg)
    k2 = _generiraj_kolicine(cfg, tmp_path, "v2.pdf")
    assert k1["postavke"] == k2["postavke"]
    assert k1["narocilo"] == k2["narocilo"]


# ---------------------------------------------------------------- predracun
def test_predracun_znesek_rocni_primer():
    postavke = [
        ("A", "10", "m", "wpc_deska_m", 10.0),
        ("B", "5", "kos", "vijak_kos", 5.0),
        ("C", "2", "kos", "manjka_kos", 2.0),     # brez cene -> opozorilo
    ]
    cene = {"wpc_deska_m": 12.5, "vijak_kos": 0.4}
    z = proizvodnja.predracun_znesek(cene, postavke)
    assert abs(z["skupaj"] - (10 * 12.5 + 5 * 0.4)) < 1e-9   # 127.00
    assert z["manjkajoce_cene"] == ["manjka_kos"]
    # manjkajoča cena = delni seštevek (NI vštet) — to je pravilno vedenje
    assert not z["vse_nic"] and z["delno"]
    # vrstica z manjkajočo ceno je v tabeli vidna (ni tiho izpuščena)
    assert any("CENA MANJKA" in r[2] for r in z["vrstice"])


def test_predracun_znesek_vse_primer():
    z = proizvodnja.predracun_znesek(
        {"wpc_deska_m": 0.0}, [("A", "10", "m", "wpc_deska_m", 10.0)])
    assert z["vse_nic"]
    assert z["skupaj"] == 0.0


# ---------------------------------------------------------------- GUI
tk = pytest.importorskip("tkinter")


@pytest.fixture
def datoteka_zadnje(tmp_path, monkeypatch):
    import vmesnik
    p = str(tmp_path / "zadnje.yaml")
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", p)
    return p


def _app():
    import vmesnik
    try:
        app = vmesnik.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    return app


def test_zivi_povzetek_se_osvezi(datoteka_zadnje):
    app = _app()
    try:
        app.v["sirina"].set("2500")
        app.v["visina"].set("1850")
        app._zivi_osvezi()
        txt = app.zivi_cena.cget("text")
        assert ("EUR" in txt) or ("ni obračunano" in txt), txt
        assert app.zivi_platno.find_all(), "shematski prikaz je prazen"
        assert "WPC" in app.zivi_vrstice.cget("text")
    finally:
        app.destroy()


def test_zivi_povzetek_neveljaven_vnos_ne_sesuje(datoteka_zadnje):
    app = _app()
    try:
        app.v["sirina"].set("NI ŠTEVILO")
        app._zivi_osvezi()                       # ne sme vreči izjeme
        assert "Vnos ni veljaven" in app.zivi_status.cget("text")
    finally:
        app.destroy()