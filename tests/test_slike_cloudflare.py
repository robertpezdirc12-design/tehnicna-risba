# -*- coding: utf-8 -*-
"""Testi za `scripts/slike_cloudflare.py` — BREZ omrežja (klic je nadomeščen).

Preverjamo vedenje, ki je pomembno za varnost in pošteno napako: manjkajoče
okolje pove KATERO spremenljivko, prazno povpraševanje ne kliče API-ja,
napaka Cloudflare se ne pojavi tiho, kvota ima razlago, zapis pa je res
slika (JPEG/PNG) in ne poljuben base64.
"""
from __future__ import annotations

import base64
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import slike_cloudflare as sc  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 32
OKOLJE = {"CLOUDFLARE_API_TOKEN": "zeton", "CLOUDFLARE_ACCOUNT_ID": "racun"}


def _odgovor(bajti: bytes) -> dict[str, object]:
    return {"success": True, "result": {"image": base64.b64encode(bajti).decode()}}


def test_manjkajoce_okolje_pove_katero_spremenljivko():
    with pytest.raises(sc.Napaka) as e:
        sc.preberi_okolje({})
    sporocilo = str(e.value)
    assert "CLOUDFLARE_API_TOKEN" in sporocilo
    assert "CLOUDFLARE_ACCOUNT_ID" in sporocilo


def test_okolje_odreze_presledke():
    zeton, racun = sc.preberi_okolje({
        "CLOUDFLARE_API_TOKEN": "  a  ",
        "CLOUDFLARE_ACCOUNT_ID": " b ",
    })
    assert (zeton, racun) == ("a", "b")


def test_prazno_povprasevanje_ne_kliče_api(monkeypatch):
    def ne_sme(url, zeton, telo, omejitev):
        raise AssertionError("prazno povpraševanje ne sme klicati API-ja")

    monkeypatch.setattr(sc, "_klic", ne_sme)
    with pytest.raises(sc.Napaka, match="prazno"):
        sc.ustvari("   ", okolje=OKOLJE)


def test_prevec_korakov_je_razlozeno():
    with pytest.raises(sc.Napaka, match="1–8"):
        sc.ustvari("ograja", koraki=9, okolje=OKOLJE)


def test_uspeh_vrne_bajte_slike(monkeypatch):
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: _odgovor(JPEG))
    assert sc.ustvari("ograja", okolje=OKOLJE) == JPEG


def test_shrani_ustvari_mapo_in_zapise(monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: _odgovor(JPEG))
    cilj = tmp_path / "globina" / "ograja.jpg"
    pot = sc.shrani("ograja", cilj, okolje=OKOLJE)
    assert pot == cilj and pot.is_file()
    assert pot.read_bytes() == JPEG


def test_napacna_koncnica_ne_zapise(monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: _odgovor(JPEG))
    with pytest.raises(sc.Napaka, match="Končnica"):
        sc.shrani("ograja", tmp_path / "ograja.txt", okolje=OKOLJE)
    assert not (tmp_path / "ograja.txt").exists()


def test_napaka_api_ni_tiha(monkeypatch):
    napaka = {"success": False, "errors": [{"message": "Invalid prompt"}]}
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: napaka)
    with pytest.raises(sc.Napaka, match="Invalid prompt"):
        sc.ustvari("ograja", okolje=OKOLJE)


def test_porabljena_kvota_dobi_razlago(monkeypatch):
    napaka = {
        "success": False,
        "errors": [{"message": "You have used up your daily free allocation of 10,000 neurons"}],
    }
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: napaka)
    with pytest.raises(sc.Napaka) as e:
        sc.ustvari("ograja", okolje=OKOLJE)
    assert "00:00 UTC" in str(e.value)


def test_neveljaven_base64_je_napaka(monkeypatch):
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: {"success": True, "result": {"image": "!!!"}})
    with pytest.raises(sc.Napaka, match="base64"):
        sc.ustvari("ograja", okolje=OKOLJE)


def test_vsebina_ki_ni_slika_je_napaka(monkeypatch):
    smeti = base64.b64encode(b"GIF89a" + b"0" * 16).decode()
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: {"success": True, "result": {"image": smeti}})
    with pytest.raises(sc.Napaka, match="JPEG ali PNG"):
        sc.ustvari("ograja", okolje=OKOLJE)


def test_ocena_nevronov_po_ceniku():
    # 1024x1024 = 4 ploščice; 4 koraki → 4*4,8 + 4*9,6 = 57,6
    assert sc.oceni_nevrone(1024, 1024, 4) == pytest.approx(57.6)
    assert sc.oceni_nevrone(512, 512, 4) == pytest.approx(43.2)
    assert sc.oceni_nevrone(700, 300, 1) == pytest.approx(2 * 4.8 + 9.6)


def test_ocena_nevronov_zavrne_neveljavne_velikosti():
    with pytest.raises(sc.Napaka):
        sc.oceni_nevrone(0, 512, 4)


def test_cli_brez_okolja_vrne_kodo_2(monkeypatch, capsys):
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    assert sc.main(["ograja"]) == 2
    assert "CLOUDFLARE_API_TOKEN" in capsys.readouterr().err


def test_cli_z_okoljem_shrani(monkeypatch, tmp_path):
    monkeypatch.setattr(sc, "_klic", lambda *a, **k: _odgovor(JPEG))
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "zeton")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "racun")
    cilj = tmp_path / "x.jpg"
    assert sc.main(["ograja", "--izhod", str(cilj), "--koraki", "2"]) == 0
    assert cilj.is_file()
