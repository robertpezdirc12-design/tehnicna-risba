# -*- coding: utf-8 -*-
"""Testi 3D sloja: mreža, izvoz STL/OBJ/GLB, sestav, licenčna pravila.

Ključna trditev, ki jo testi dokazujejo: 3D izvoz deluje **brez ene same
nove odvisnosti** in brez copyleft kode (cadquery/OCP/casadi se ne
uvažajo v paket). Prostornina zaprte mreže je preverjena z izrekom o
divergenci, ne z zaupanjem v risalnik.
"""

from __future__ import annotations

import ast
import pathlib
import struct
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tridim import izvoz  # noqa: E402
from conftest import osnovni_cfg  # noqa: E402
from tridim.mreza import Mreza, kvader, prizma, trianguliraj  # noqa: E402
from tridim.sestav import (  # noqa: E402
    deli_pokoncne, model_ograde, model_pokoncne,
)


# ------------------------------------------------------------------ mreža


def test_kvader_je_zaprt_in_ima_pravilno_prostornino():
    m = kvader(0, 0, 0, 10, 20, 30)
    assert len(m.trikotniki) == 12
    assert m.prostornina() == pytest.approx(6000.0)
    assert m.povrsina() == pytest.approx(2 * (10 * 20 + 10 * 30 + 20 * 30))
    assert m.je_zaprta()
    assert m.preveri() == []


def test_kvader_odmik_in_meje():
    m = kvader(100, -50, 200, 10, 10, 10)
    spodaj, zgoraj = m.meje()
    assert spodaj == (100, -50, 200)
    assert zgoraj == (110, -40, 210)


def test_kvader_zavrne_nicelne_dimenzije():
    with pytest.raises(ValueError, match="pozitivne"):
        kvader(0, 0, 0, 0, 10, 10)


def test_prizma_l_profil_prostornina():
    # L-profil s ploščino 300 mm²: 20×20 minus 10×10 izrez
    profil = [(0, 0), (20, 0), (20, 10), (10, 10), (10, 20), (0, 20)]
    m = prizma(profil, 50)
    assert m.prostornina() == pytest.approx(300.0 * 50.0)
    assert m.je_zaprta()
    assert m.preveri() == []


@pytest.mark.parametrize("os", ["x", "y", "z"])
def test_prizma_je_enaka_po_vseh_oseh(os):
    profil = [(0, 0), (30, 0), (30, 10), (0, 10)]
    m = prizma(profil, 70, os=os)
    assert m.prostornina() == pytest.approx(300.0 * 70.0)
    assert m.je_zaprta()
    assert m.preveri() == []


def test_prizma_oznaka_osi_in_dolzine():
    with pytest.raises(ValueError, match="os"):
        prizma([(0, 0), (1, 0), (1, 1)], 5, os="q")
    with pytest.raises(ValueError, match="dolžina"):
        prizma([(0, 0), (1, 0), (1, 1)], 0)


def test_trianguliraj_kvadrat_in_konkavni_poligon():
    kvadrat = [(0, 0), (10, 0), (10, 10), (0, 10)]
    tri = trianguliraj(kvadrat)
    assert len(tri) == 2
    assert {i for t in tri for i in t} == {0, 1, 2, 3}

    konka = [(0, 0), (20, 0), (20, 10), (10, 10), (10, 20), (0, 20)]
    tri_k = trianguliraj(konka)
    assert len(tri_k) == len(konka) - 2


def test_trianguliraj_degeneriran_ne_vrze():
    # vse točke kolinearne — pahljača, nikoli izjema
    tri = trianguliraj([(0, 0), (5, 0), (10, 0), (15, 0)])
    assert len(tri) == 2
    assert trianguliraj([(0, 0), (1, 1)]) == []


def test_preveri_odkrije_odprto_mrezo():
    m = kvader(0, 0, 0, 5, 5, 5)
    odprta = Mreza(m.tocke, m.trikotniki[:-1])
    assert not odprta.je_zaprta()
    assert any("zaprta" in t for t in odprta.preveri())


def test_preveri_odkrije_obratno_orientacijo():
    m = kvader(0, 0, 0, 5, 5, 5)
    obrnjen = Mreza(m.tocke, tuple((a, c, b) for a, b, c in m.trikotniki))
    assert obrnjen.prostornina() == pytest.approx(-125.0)
    assert any("orientacija" in t for t in obrnjen.preveri())


def test_zdruzi_in_premakni():
    a = kvader(0, 0, 0, 10, 10, 10)
    b = kvader(20, 0, 0, 10, 10, 10)
    skupaj = a.zdruzi(b)
    assert skupaj.prostornina() == pytest.approx(2000.0)
    assert skupaj.je_zaprta()
    premaknjen = a.premakni(5, 0, 0)
    assert premaknjen.meje()[0] == (5, 0, 0)


# ------------------------------------------------------------------ izvoz


def test_stl_roundtrip(tmp_path):
    m = kvader(0, 0, 0, 10, 20, 30)
    pot = izvoz.shrani_stl(m, tmp_path / "a.stl")
    surovo = pot.read_bytes()
    assert surovo[:6] == b"tehnic"
    (stevilo,) = struct.unpack_from("<I", surovo, 80)
    assert stevilo == 12
    assert len(surovo) == 80 + 4 + 12 * 50          # 84 + 50/trikotnik

    nazaj = izvoz.preberi_stl(pot)
    assert len(nazaj.trikotniki) == 12
    assert nazaj.prostornina() == pytest.approx(6000.0, abs=1e-3)
    assert nazaj.meje()[1] == pytest.approx((10, 20, 30), abs=1e-4)


def test_stl_okrnjen_in_prazna_mreza(tmp_path):
    pot = tmp_path / "b.stl"
    pot.write_bytes(b"x" * 40)
    with pytest.raises(ValueError):
        izvoz.preberi_stl(pot)
    with pytest.raises(ValueError, match="prazne"):
        izvoz.shrani_stl(Mreza((), ()), tmp_path / "c.stl")


def test_obj_roundtrip(tmp_path):
    m = kvader(1, 2, 3, 4, 5, 6)
    pot = izvoz.shrani_obj(m, tmp_path / "a.obj")
    besedilo = pot.read_text(encoding="ascii")
    assert besedilo.count("\nv ") == 8
    assert besedilo.count("\nf ") == 12
    nazaj = izvoz.preberi_obj(pot)
    assert len(nazaj.tocke) == 8
    assert nazaj.prostornina() == pytest.approx(120.0)
    assert nazaj.je_zaprta()


def test_glb_je_veljaven_gltf2(tmp_path):
    m = kvader(0, 0, 0, 10, 20, 30)
    pot = izvoz.shrani_glb(m, tmp_path / "a.glb", ime="ograda")
    surovo = pot.read_bytes()
    magic, razlicica, skupaj = struct.unpack_from("<III", surovo, 0)
    assert magic == 0x46546C67 and razlicica == 2 and skupaj == len(surovo)

    dokument, nazaj = izvoz.preberi_glb(pot)
    assert dokument["asset"]["version"] == "2.0"
    assert dokument["accessors"][0]["count"] == len(m.tocke)
    assert dokument["accessors"][1]["count"] == 36
    assert dokument["accessors"][0]["min"] == [0.0, 0.0, 0.0]
    assert dokument["accessors"][0]["max"] == [10.0, 20.0, 30.0]
    assert len(nazaj.trikotniki) == 12
    assert nazaj.prostornina() == pytest.approx(6000.0)


def test_glb_napacna_magija(tmp_path):
    pot = tmp_path / "x.glb"
    pot.write_bytes(b"\0" * 40)
    with pytest.raises(ValueError, match="magija"):
        izvoz.preberi_glb(pot)


def test_shrani_po_koncnici(tmp_path):
    m = kvader(0, 0, 0, 1, 1, 1)
    for ime, velikost in (("a.stl", 84 + 12 * 50), ("a.obj", None)):
        pot = izvoz.shrani(m, tmp_path / ime)
        assert pot.is_file()
        if velikost:
            assert pot.stat().st_size == velikost
    with pytest.raises(ValueError, match="nepodprt zapis"):
        izvoz.shrani(m, tmp_path / "a.step")


# --------------------------------------------------------------- sestav


def test_model_pokoncne_osnovno(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    model = model_pokoncne(cfg)
    m = model["mreza"]
    assert m.preveri() == []

    mere = model["mere"]
    assert mere["stebrov"] == 4          # 2500 mm / 1200 mm -> 4 stebri
    assert mere["desk"] == 11

    (x0, y0, z0), (x1, y1, z1) = m.meje()
    # osnovne plošče 90 mm segajo prek stebra 60 mm — zato je obseg širši
    assert x0 <= 0.0 and x0 >= -45.0
    assert x1 >= cfg["mere"]["sirina"] - 1e-6
    assert z0 == pytest.approx(0.0)
    # pritrditev "vrh" + osnova 90×90×6 -> vrh 6 mm nad visino ograje
    assert z1 == pytest.approx(cfg["mere"]["visina"] + 6.0)

    # prostornina združene mreže = vsota prostornin delov (brez presekov)
    vsota = sum(d.mreza.prostornina() for d in model["deli"])
    assert m.prostornina() == pytest.approx(vsota)
    assert len(model["deli"]) == 4 + 11 + 1 + 4


def test_model_pokoncne_brez_osnov(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    cfg["pritrditev"] = "bočno"
    model = model_pokoncne(cfg)
    assert len(model["deli"]) == 4 + 11 + 1
    assert any("pritrditev ni" in o for o in model["opombe"])
    assert model["mreza"].preveri() == []


def test_model_pokoncne_napacna_osnova(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    cfg["osnova_dim"] = "nečitljivo"
    model = model_pokoncne(cfg)
    assert len(model["deli"]) == 4 + 11 + 1
    assert any("osnove niso berljive" in o for o in model["opombe"])


def test_model_pokoncne_brez_ugibanja_pri_presirokih_deskah(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    cfg["mere"]["vrzel"] = 200           # ne prilega se v polje
    with pytest.raises(ValueError, match="ne prilegajo"):
        model_pokoncne(cfg)


def test_deli_pokoncne_vraca_kvadre(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    podatki = deli_pokoncne(cfg)
    assert len(podatki["kvadri"]) == 20
    for k in podatki["kvadri"]:
        assert min(k.dx, k.dy, k.dz) > 0
    assert podatki["kvadri"][0].ime.startswith("steber")


def test_precna_predloga_je_zavrnjena(tmp_path):
    """Prečna ograja ima drugačno geometrijo — 3D izvoz je ne ugiba."""
    cfg = osnovni_cfg(tmp_path / "x.pdf")          # privzeto "ograja"            # predloga "ograja"
    with pytest.raises(ValueError, match="pokončna"):
        model_pokoncne(cfg)


def test_izvoz_se_ujema_s_3d_predogledom(monkeypatch, tmp_path):
    """Izvoz (mreža) in obstoječi predogled (matplotlib) morata uporabiti
    ISTI razpored desk — dva 3D pogleda, ena geometrija."""
    import tridimenzionalno as t3

    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    model = model_pokoncne(cfg)
    z0, z1 = cfg["mere"]["odcep"], cfg["mere"]["odcep"] + model["mere"]["deska_h"]

    klici: list[tuple] = []
    orig = t3._skatla

    def vohun(kol, ax0, ax1, ay0, ay1, az0, az1, barva):
        klici.append((round(ax0, 3), round(ax1, 3),
                      round(az0, 3), round(az1, 3)))
        return orig(kol, ax0, ax1, ay0, ay1, az0, az1, barva)

    monkeypatch.setattr(t3, "_skatla", vohun)
    t3.sestavi_3d(cfg)

    # prednje deske (x > 0); predogled doda še stranski krak (x ≈ 0), ker
    # je globina > 0 — izvoz tega namenoma ne modelira (glej opombe)
    deske_predogled = [k for k in klici
                       if (k[2], k[3]) == (z0, z1) and k[0] >= 0]
    stranski = [k for k in klici
                if (k[2], k[3]) == (z0, z1) and k[0] < 0 < k[1]]
    assert len(stranski) == 1
    assert any("Stranski segment" in o for o in model["opombe"])
    assert len(deske_predogled) == model["mere"]["desk"] == 11
    # izvoz uporablja isto cono desk
    deske_izvoz = [d for d in model["deli"] if d.ime.startswith("deska")]
    assert len(deske_izvoz) == 11
    (dx0, _dy0, dz0), (_dx1, _dy1, dz1) = deske_izvoz[0].mreza.meje()
    assert dz0 == pytest.approx(z0) and dz1 == pytest.approx(z1)
    # širina ograje je v obeh enaka
    assert max(k[1] for k in deske_predogled) <= cfg["mere"]["sirina"]
    assert model["mreza"].meje()[1][0] >= cfg["mere"]["sirina"]


# --------------------------------------------------------------- licenca


def _uvozi(pot: pathlib.Path) -> set[str]:
    """Koreni vseh uvoženih modulov v datoteki (AST, ne iskanje besed)."""
    drevo = ast.parse(pot.read_text(encoding="utf-8"), filename=str(pot))
    koreni: set[str] = set()
    for vozel in ast.walk(drevo):
        if isinstance(vozel, ast.Import):
            koreni.update(alias.name.split(".")[0] for alias in vozel.names)
        elif isinstance(vozel, ast.ImportFrom) and vozel.module:
            koreni.add(vozel.module.split(".")[0])
    return koreni


def test_paket_ne_uvaža_copyleft_knjižnic():
    """Copyleft se sme uvoziti SAMO v neobveznem mostu step.py."""
    prepovedano = {"cadquery", "OCP", "casadi", "gmsh", "pymeshlab",
                   "pythonocc", "paddleocr", "transformers", "torch"}
    najdbe: dict[str, set[str]] = {}
    for pot in sorted((REPO / "tridim").glob("*.py")):
        zadetki = _uvozi(pot) & prepovedano
        if zadetki:
            najdbe[pot.name] = zadetki
    assert set(najdbe) <= {"step.py"}, f"copyleft tudi zunaj step.py: {najdbe}"
    assert najdbe.get("step.py") == {"cadquery"}
    step = (REPO / "tridim" / "step.py").read_text(encoding="utf-8")
    assert "LGPL" in step              # most mora povedati, zakaj ni vgrajen


def test_uvoz_paketa_ne_nalozi_cadqueryja():
    koda = ("import sys; import tridim; "
            "print('cadquery' in sys.modules, 'OCP' in sys.modules)")
    izhod = subprocess.run([sys.executable, "-c", koda], cwd=str(REPO),
                           capture_output=True, text=True, timeout=120)
    assert izhod.returncode == 0, izhod.stderr
    assert izhod.stdout.strip() == "False False"


def test_step_brez_cadqueryja_pove_kaj_manjka(tmp_path):
    from tridim import step

    if step.na_voljo():
        pytest.skip("cadquery je nameščen — ta test velja za okolje brez njega")
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    with pytest.raises(step.ManjkaKnjiznica) as informacija:
        step.izvozi_step(cfg, tmp_path / "x.step")
    sporočilo = str(informacija.value)
    assert "cadquery" in sporočilo and "LGPL" in sporočilo
    assert "STL" in sporočilo            # pove, kaj dela brez njega


# ------------------------------------------------------------------ CLI


def test_cli_izvozi_glb(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf", predloga="pokončna")
    vhod = tmp_path / "projekt.yaml"
    vhod.write_text(cfg_v_yaml(cfg), encoding="utf-8")
    izhod = tmp_path / "model.glb"
    dokoncan = subprocess.run(
        [sys.executable, "-m", "tridim", "--vhod", str(vhod),
         "--izhod", str(izhod)],
        cwd=str(REPO), capture_output=True, text=True, timeout=300)
    assert dokoncan.returncode == 0, dokoncan.stderr
    assert "Zapisano" in dokoncan.stdout
    assert "opomba" in dokoncan.stdout
    dokument, mreza = izvoz.preberi_glb(izhod)
    assert dokument["asset"]["version"] == "2.0"
    assert len(mreza.trikotniki) == 20 * 12


def test_cli_napacna_pot(tmp_path):
    dokoncan = subprocess.run(
        [sys.executable, "-m", "tridim", "--vhod", str(tmp_path / "ni.yaml"),
         "--izhod", str(tmp_path / "m.stl")],
        cwd=str(REPO), capture_output=True, text=True, timeout=120)
    assert dokoncan.returncode == 2
    assert "NAPAKA" in dokoncan.stderr


def cfg_v_yaml(cfg: dict) -> str:
    """Zapiše konfiguracijo v YAML brez odvisnosti od yamla v testu."""
    import yaml

    return yaml.safe_dump(cfg, allow_unicode=True)


# ------------------------------------------------- prečna (vodoravne lamele)


def test_model_precne_osnovno(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")          # predloga "ograja"
    cfg["mere"]["globina"] = 0                     # brez stranskega kraka
    model = model_ograde(cfg)
    assert model["mreza"].preveri() == []
    assert model["mere"]["lamel"] == cfg["mere"]["lamele"]

    (x0, _y0, z0), (x1, _y1, z1) = model["mreza"].meje()
    assert x0 <= 0.0 and x1 >= cfg["mere"]["sirina"]
    assert z1 == pytest.approx(cfg["mere"]["visina"])
    assert z0 >= 0.0
    # tla iz predogleda niso del modela
    assert any("Tla iz 3D predogleda" in o for o in model["opombe"])


def test_model_precne_z_vrati_pusti_odprtino(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf",
                      vrata=[{"tip": "enokrilna", "x": 300, "sirina": 900,
                              "visina": 1600, "smer": "levo-navzven"}])
    model = model_ograde(cfg)
    assert model["mreza"].preveri() == []
    odprtina = (300.0, 1200.0)

    def prerez(kos):
        (ax, _ay, _az), (bx, _by, _bz) = kos.mreza.meje()
        return ax, bx

    for del_ in model["deli"]:
        if not del_.ime.startswith("lamela"):
            continue
        ax, bx = prerez(del_)
        assert bx <= odprtina[0] + 1e-6 or ax >= odprtina[1] - 1e-6, \
            f"{del_.ime} seka odprtino {ax:.1f}..{bx:.1f}"

    imena = {d.ime for d in model["deli"]}
    assert {"okvir V1 levo", "okvir V1 desno", "okvir V1 precka"} <= imena


def test_model_precne_se_ujema_s_predogledom(monkeypatch, tmp_path):
    """Iste lamele kot v shematskem predogledu (isti razpored iz jedro)."""
    import tridimenzionalno as t3

    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["mere"]["globina"] = 0
    model = model_ograde(cfg)
    deb = float(cfg["mere"]["debelina"])

    klici: list[tuple] = []
    orig = t3._skatla

    def vohun(kol, ax0, ax1, ay0, ay1, az0, az1, barva):
        klici.append((round(az0, 3), round(az1, 3),
                      round(ay0, 3), round(ay1, 3)))
        return orig(kol, ax0, ax1, ay0, ay1, az0, az1, barva)

    monkeypatch.setattr(t3, "_skatla", vohun)
    t3.sestavi_3d(cfg)

    prednje = [k for k in klici
               if k[2] == pytest.approx(-deb / 2) and k[3] == pytest.approx(deb / 2)]
    izvoz = sorted((round(d.mreza.meje()[0][2], 3), round(d.mreza.meje()[1][2], 3))
                   for d in model["deli"] if d.ime.startswith("lamela"))
    assert sorted((k[0], k[1]) for k in prednje) == izvoz
    assert len(izvoz) == model["mere"]["lamel"] == 11


def test_dispecer_predlog(tmp_path):
    cfg_pok = osnovni_cfg(tmp_path / "a.pdf", predloga="pokončna")
    assert "desk" in model_ograde(cfg_pok)["mere"]
    cfg_prec = osnovni_cfg(tmp_path / "b.pdf")
    assert "lamel" in model_ograde(cfg_prec)["mere"]

    cfg_prec["predloga"] = "neznana"
    with pytest.raises(ValueError, match="neznana predloga"):
        model_ograde(cfg_prec)


def test_cli_precna_predloga(tmp_path):
    cfg = osnovni_cfg(tmp_path / "x.pdf")
    cfg["mere"]["globina"] = 0
    vhod = tmp_path / "projekt.yaml"
    vhod.write_text(cfg_v_yaml(cfg), encoding="utf-8")
    izhod = tmp_path / "precna.stl"
    dokoncan = subprocess.run(
        [sys.executable, "-m", "tridim", "--vhod", str(vhod),
         "--izhod", str(izhod)],
        cwd=str(REPO), capture_output=True, text=True, timeout=300)
    assert dokoncan.returncode == 0, dokoncan.stderr
    assert "lamele" in dokoncan.stdout
    nazaj = izvoz.preberi_stl(izhod)
    assert len(nazaj.trikotniki) == 12 * len(model_ograde(cfg)["deli"])
