# -*- coding: utf-8 -*-
"""Testi ocenjevalnika — validacija BREZ modela (samo skripte).

Ključna zamisel: vsak razred izida izzove ponarejeni agent
(benchmark/ponarejeni_agent.py), zato je mogoče dokazati, da
ocenjevalnik pravilno loči uspeh, neuspeh, regresijo, uhajanje in
prekoračitev časa — brez klica kateregakoli AI modela.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
KOREN_NALOG = REPO / "benchmark" / "naloge"
AGENT = REPO / "benchmark" / "ponarejeni_agent.py"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from benchmark import naloge as bn  # noqa: E402
from benchmark import ocenjevanje, statistika  # noqa: E402
from benchmark.model import (  # noqa: E402
    NI_RESEN,
    NAPAKA_OKOLJA,
    ONESNAZENO,
    POKVARJEN,
    PREKORACEN_CAS,
    RESEN,
    Naloga,
    RezultatNaloge,
)


def ukaz(nacin: str) -> list[str]:
    return [sys.executable, str(AGENT), "--nacin", nacin]


def naloga(ime: str) -> Naloga:
    for n in bn.nalozi_vse(KOREN_NALOG):
        if n.id == ime:
            return n
    raise AssertionError(f"naloge {ime!r} ni")


def izvedi(nacin: str, ime: str = "vsota", **kwargs) -> RezultatNaloge:
    return ocenjevanje.izvedi_nalogo(naloga(ime), ukaz(nacin), KOREN_NALOG,
                                     **kwargs)


# --------------------------------------------------------- statistika


def test_pass_at_k_znane_vrednosti():
    assert statistika.pass_at_k(10, 5, 1) == pytest.approx(0.5)
    assert statistika.pass_at_k(200, 0, 1) == 0.0
    assert statistika.pass_at_k(10, 10, 5) == 1.0
    # n=4, c=1, k=2 -> 1 - C(3,2)/C(4,2) = 1 - 3/6
    assert statistika.pass_at_k(4, 1, 2) == pytest.approx(0.5)


def test_pass_at_k_neveljavni_vhodi():
    with pytest.raises(ValueError):
        statistika.pass_at_k(0, 0, 1)
    with pytest.raises(ValueError):
        statistika.pass_at_k(3, 1, 4)
    with pytest.raises(ValueError):
        statistika.pass_at_k(3, 5, 1)


def test_povprecni_pass_at_k():
    assert statistika.povprecni_pass_at_k([(2, 1), (2, 2)], 1) == pytest.approx(
        (0.5 + 1.0) / 2)


def test_wilson_interval_meje():
    spodnja, zgornja = statistika.wilson_interval(0, 10)
    assert spodnja == 0.0 and 0.0 < zgornja < 1.0
    spodnja, zgornja = statistika.wilson_interval(10, 10)
    assert 0.7 < spodnja < 1.0 and zgornja <= 1.0
    assert statistika.wilson_interval(0, 0) == (0.0, 1.0)


def test_mcnemar_tocne_vrednosti():
    # b=0, c=10: p = 2 * P(X <= 0) = 2/2^10
    assert statistika.mcnemar_exact(0, 10) == pytest.approx(2 / 2 ** 10)
    assert statistika.mcnemar_exact(7, 7) == 1.0
    assert statistika.mcnemar_exact(0, 0) == 1.0
    assert statistika.mcnemar_exact(1, 1) == pytest.approx(1.0)


def test_bootstrap_ponovljiv_in_nicen():
    assert statistika.bootstrap_razlika([1, 0, 1], [1, 0, 1]) == (0.0, 0.0, 0.0)
    prvi = statistika.bootstrap_razlika([1, 0, 1, 0], [0, 0, 1, 0], zrno=7)
    drugi = statistika.bootstrap_razlika([1, 0, 1, 0], [0, 0, 1, 0], zrno=7)
    assert prvi == drugi
    spodnja, zgornja, ocena = prvi
    assert spodnja <= ocena <= zgornja


def test_bootstrap_neujemanje_dolzin():
    with pytest.raises(ValueError):
        statistika.bootstrap_razlika([1, 0], [1])


def test_znakovni_test_pravila():
    assert statistika.znakovni_test([1, 0, 1], [1, 0, 1]) == 1.0
    assert statistika.znakovni_test([0, 0, 0, 0, 0], [1, 1, 1, 1, 1]) == pytest.approx(
        2 / 2 ** 5)
    p = statistika.znakovni_test([0] * 30, [1] * 30, zrno=1)
    assert p < 0.01


def test_primerjaj_kljuci():
    izid = statistika.primerjaj([True, False, True], [True, True, False])
    assert izid["samo_a"] == 1.0 and izid["samo_b"] == 1.0
    assert izid["n"] == 3.0
    assert 0.0 <= izid["p_mcnemar"] <= 1.0


# ------------------------------------------------------------- naloge


def test_nalozi_vse_tri_naloge():
    vse = bn.nalozi_vse(KOREN_NALOG)
    assert [n.id for n in vse] == ["orodja", "razlika", "vsota"]
    vsota = vse[2]
    assert vsota.canary == ("SKRIVNI-KANAR-VSOTA-7f3a",)
    assert vsota.pass_to_pass == ("test_obstojeca_funkcija",)


def _zapis(mapa: pathlib.Path, vsebina: str) -> pathlib.Path:
    mapa.mkdir(parents=True, exist_ok=True)
    pot = mapa / "task.yaml"
    pot.write_text(vsebina, encoding="utf-8")
    return pot


def test_naloga_neznano_polje(tmp_path):
    pot = _zapis(tmp_path, "id: a\nopis: b\npredloga: p\nfail_to_pass: [t]\n"
                            "neznano: 1\n")
    with pytest.raises(bn.NapakaNaloge, match="neznana polja"):
        bn.nalozi_nalogo(pot)


def test_naloga_brez_cilja(tmp_path):
    pot = _zapis(tmp_path, "id: a\nopis: b\npredloga: p\nfail_to_pass: []\n")
    with pytest.raises(bn.NapakaNaloge, match="ne sme biti prazen"):
        bn.nalozi_nalogo(pot)


def test_naloga_prekrivanje_testov(tmp_path):
    pot = _zapis(tmp_path, "id: a\nopis: b\npredloga: p\n"
                            "fail_to_pass: [t]\npass_to_pass: [t]\n")
    with pytest.raises(bn.NapakaNaloge, match="obeh seznamih"):
        bn.nalozi_nalogo(pot)


def test_naloga_neveljaven_cas(tmp_path):
    pot = _zapis(tmp_path, "id: a\nopis: b\npredloga: p\n"
                            "fail_to_pass: [t]\ncas_s: 0\n")
    with pytest.raises(bn.NapakaNaloge, match="pozitivno"):
        bn.nalozi_nalogo(pot)


def test_naloga_podvojeni_id(tmp_path):
    for ime in ("ena", "dve"):
        mapa = tmp_path / ime
        mapa.mkdir()
        (mapa / "task.yaml").write_text(
            "id: isti\nopis: b\npredloga: p\nfail_to_pass: [t]\n",
            encoding="utf-8")
    with pytest.raises(bn.NapakaNaloge, match="podvojeni id"):
        bn.nalozi_vse(tmp_path)


# ------------------------------------------------ ocenjevanje (brez AI)


def test_agent_ok_resi_vecdatotecno():
    rez = izvedi("ok", "orodja")
    assert rez.status == RESEN
    assert sorted(rez.fail_to_pass_ok) == ["test_povprecje_en_element",
                                          "test_povprecje_osnovno"]
    assert rez.pass_to_pass_ok == ["test_sestej_ostane"]


def test_agent_ok_resi_nalogo():
    rez = izvedi("ok")
    assert rez.status == RESEN
    assert sorted(rez.fail_to_pass_ok) == ["test_vsota_negativna",
                                          "test_vsota_osnovno"]
    assert rez.pass_to_pass_ok == ["test_obstojeca_funkcija"]
    assert rez.canary_zadet == []


def test_agent_napol_ni_resen():
    rez = izvedi("napol")
    assert rez.status == NI_RESEN
    assert rez.fail_to_pass_napaka
    assert rez.pass_to_pass_napaka == []


def test_agent_pokvari_regresijo():
    rez = izvedi("pokvari")
    assert rez.status == POKVARJEN
    assert rez.pass_to_pass_napaka == ["test_obstojeca_funkcija"]


def test_agent_uhajaj_onesnazi():
    zeton = naloga("vsota").canary[0]
    rez = izvedi("uhajaj", okolje_dodatno={"BENCHMARK_CANARY": zeton})
    assert rez.status == ONESNAZENO
    assert rez.canary_zadet == [zeton]


def test_agent_pocasi_prekoraci():
    rez = izvedi("pocasi", cas_agent_s=0.5)
    assert rez.status == PREKORACEN_CAS
    assert "presegel" in rez.sporočilo


def test_agent_sesuje_ni_resen():
    rez = izvedi("sesuje")
    assert rez.status == NI_RESEN
    assert rez.izhod_agenta == 2


def test_manjkajoca_predloga(tmp_path):
    n = Naloga(id="x", opis="o", predloga="ni-te-poti",
               fail_to_pass=("t",), pass_to_pass=())
    rez = ocenjevanje.izvedi_nalogo(n, ukaz("ok"), tmp_path)
    assert rez.status == NAPAKA_OKOLJA
    assert "predloga ne obstaja" in rez.sporočilo


def test_razcleni_ukaz():
    assert ocenjevanje.razcleni_ukaz('python -m mod --x "a b"') == [
        "python", "-m", "mod", "--x", "a b"]
    with pytest.raises(ValueError):
        ocenjevanje.razcleni_ukaz("   ")


def test_canary_iskanje(tmp_path):
    (tmp_path / "a.txt").write_text("vsebuje SKRIVNO-1 tukaj", encoding="utf-8")
    najdeno = ocenjevanje.poisci_canary(
        tmp_path, ["brez"], ("SKRIVNO-1", "SKRIVNO-2"))
    assert najdeno == ["SKRIVNO-1"]


def test_beri_junit_napaka(tmp_path):
    pot = tmp_path / "junit.xml"
    pot.write_text("to ni xml", encoding="utf-8")
    with pytest.raises(ValueError):
        ocenjevanje.beri_junit(pot)


# -------------------------------------------------------------- CLI


def test_cli_seznam():
    dokoncan = subprocess.run(
        [sys.executable, "-m", "benchmark.tek", "--seznam"],
        cwd=str(REPO), capture_output=True, text=True, timeout=120)
    assert dokoncan.returncode == 0, dokoncan.stderr
    for ime in ("vsota", "razlika", "orodja"):
        assert ime in dokoncan.stdout


def test_cli_serija_in_primerjava(tmp_path):
    pot = tmp_path / "rez.json"
    agent = f'"{sys.executable}" "{AGENT}" --nacin ok'
    dokoncan = subprocess.run(
        [sys.executable, "-m", "benchmark.tek", "--agent", agent,
         "--ponovitve", "1", "--izhod", str(pot)],
        cwd=str(REPO), capture_output=True, text=True, timeout=300)
    assert dokoncan.returncode == 0, dokoncan.stderr
    podatek = json.loads(pot.read_text(encoding="utf-8"))
    assert podatek["povzetek"]["uspesnih"] == 3
    assert podatek["povzetek"]["delez"] == 1.0
    assert podatek["povzetek"]["onesnazenih"] == 0
    okolje = podatek["okolje"]
    assert okolje["python"] and "platforma" in okolje
    assert okolje["git"] != "" and "umazano" in okolje

    # primerjava z samim seboj: razlika 0, interval vsebuje 0
    dokoncan = subprocess.run(
        [sys.executable, "-m", "benchmark.tek", "--primerjaj", str(pot), str(pot)],
        cwd=str(REPO), capture_output=True, text=True, timeout=120)
    assert dokoncan.returncode == 0, dokoncan.stderr
    assert "razlika B - A: +0.000" in dokoncan.stdout
    assert "interval zaupanja vsebuje 0" in dokoncan.stdout


# ------------------------------------------------ unit: povzetek in CLI


def _serija(uspehi: list[bool]) -> dict:
    return {"rezultati": [
        {"naloga": f"n{i}", "uspesna": u, "status": RESEN if u else NI_RESEN}
        for i, u in enumerate(uspehi)
    ]}


def test_povzetek_izracuna_deleze_in_pass_k():
    from benchmark import tek

    podatek = {
        "agent": "test", "zrno": 1, "ponovitve": 2,
        "serije": [_serija([True, False]), _serija([True, True])],
    }
    p = tek.povzetek(podatek)
    assert p["stevilo_izvedb"] == 4
    assert p["uspesnih"] == 3
    assert p["delez"] == pytest.approx(0.75)
    assert p["k"] == 2
    # n=2 za vsako nalogo: n0 (1/2), n1 (2/2) -> pass@2 = (1.0 + 1.0)/2
    assert p["pass_at_k"] == pytest.approx(1.0)
    assert p["po_nalogi"] == {"n0": 1.0, "n1": 0.5}


def test_povzetek_steje_onesnazene():
    from benchmark import tek

    podatek = {"agent": "t", "zrno": 0, "ponovitve": 1, "serije": [
        {"rezultati": [{"naloga": "a", "uspesna": True,
                        "status": ONESNAZENO}]}]}
    assert tek.povzetek(podatek)["onesnazenih"] == 1


def test_tek_main_seznam(capsys):
    from benchmark import tek

    assert tek.main(["--seznam"]) == 0
    izhod = capsys.readouterr().out
    assert "vsota" in izhod and "orodja" in izhod


def test_tek_primerjaj_zapiše_json(tmp_path):
    from benchmark import tek

    def zapis(ime: str, uspehi: list[bool]) -> pathlib.Path:
        pot = tmp_path / ime
        pot.write_text(json.dumps({
            "agent": ime, "zrno": 1, "ponovitve": 1,
            "serije": [{"rezultati": [
                {"naloga": f"n{i}", "uspesna": u, "status": RESEN}
                for i, u in enumerate(uspehi)]}],
        }), encoding="utf-8")
        return pot

    a = zapis("a.json", [True, False])
    b = zapis("b.json", [True, True])
    izhod = tmp_path / "primejava.json"
    tek.primerjaj(a, b, zrno=1, izhod=izhod)
    podatek = json.loads(izhod.read_text(encoding="utf-8"))
    assert podatek["skupne_naloge"] == ["n0", "n1"]
    assert podatek["razlika"] == pytest.approx(0.5)
    assert podatek["p_mcnemar"] == pytest.approx(1.0)
    assert podatek["dokazano"] is False


def test_ponarejeni_agent_main_v_procesu(tmp_path):
    import shutil

    from benchmark import ponarejeni_agent

    prostor = tmp_path / "p"
    shutil.copytree(REPO / "benchmark" / "primeri" / "knjiznica3", prostor)
    assert ponarejeni_agent.main(
        ["--nacin", "ok", "--prostor", str(prostor)]) == 0
    assert "return a + b" in (prostor / "vozlice.py").read_text(encoding="utf-8")
    assert "sum(vrednosti)" in (prostor / "orodja.py").read_text(encoding="utf-8")

    prostor2 = tmp_path / "q"
    shutil.copytree(REPO / "benchmark" / "primeri" / "knjiznica", prostor2)
    assert ponarejeni_agent.main(
        ["--nacin", "pokvari", "--prostor", str(prostor2)]) == 0
    assert 'return "pokvarjeno"' in (prostor2 / "vozlice.py").read_text(
        encoding="utf-8")
