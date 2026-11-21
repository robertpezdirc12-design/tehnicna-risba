# -*- coding: utf-8 -*-
"""B1: skladišče ostankov — regresijski testi.

Regresija 1 (dvojno odštevanje): po porazdelitvi je bil ostanek prikazan
0 mm, čeprav je bilo pravilno 994 mm (3000 − 2 × (1000 + 3)).
"""
import os

import yaml

import razrez
from razrez import (nalozi_ostanke, shrani_ostanke, porazdeli_z_ostanki,
                    razrez_podatki, MIN_OSTANKA)


def _skladisce(ostanki):
    shrani_ostanke(ostanki)
    return nalozi_ostanke()


# --------------------------------------------------------------- regresija 1
def test_ostanek_se_odstete_samo_enkrat():
    """3000 mm ostanek, 2 kosa × 1000 mm, kerf 3 -> ostanek 994, NE 0."""
    _skladisce([{"dolzina": 3000, "barva": "Antracit", "profil": "ROMB 67"}])
    c = {"kerf": 3.0, "barva": "Antracit", "profil": "ROMB 67",
         "dolzine_deske": [5800], "uporabi_ostanke": True}
    rp = razrez_podatki(1000, 2, c, oznaka="L", glava="LAMELE ŠT.")
    # iz ostankega traku je izdelanih 2 kosov
    assert rp["iz_ost_kos"] == 2
    # v tabeli je ostanek po rezu 994 mm (ne 0)
    vrstica = [r for r in rp["rez_rows"] if r[0].startswith("OSTANEK #1")]
    assert vrstica, rp["rez_rows"]
    assert vrstica[0][3] == "994"
    # posodobljeno skladišče hrani 994 mm
    pos = rp["ostanki_posodobitev"]
    assert pos and abs(pos[0]["dolzina"] - 994) < 1e-6


def test_vhodni_seznam_ostankov_se_ne_mutira():
    ost = [{"dolzina": 3000, "barva": "Antracit", "profil": "ROMB 67"}]
    kopija = [dict(o) for o in ost]
    iz_ost, preost, posodobljeno = porazdeli_z_ostanki(
        1000, 2, ost, 3.0, "Antracit", "ROMB 67")
    assert ost == kopija                     # B1: brez mutacije vhoda
    assert iz_ost[0][2] == 994               # ostanek po rezu
    assert posodobljeno[0]["dolzina"] == 994


def test_ostanek_se_porabi_najvec_enkrat():
    """Ostanek 2000 mm, 4 kosi × 950 mm (kerf 3) -> največ 2 kosa iz ostanka."""
    _skladisce([{"dolzina": 2000, "barva": "Antracit", "profil": "ROMB 67"}])
    c = {"kerf": 3.0, "barva": "Antracit", "profil": "ROMB 67",
         "dolzine_deske": [5800], "uporabi_ostanke": True}
    rp = razrez_podatki(950, 4, c)
    assert rp["iz_ost_kos"] == 2             # (2000+3)//953 = 2
    # preostala 2 kosa iz nabave
    assert sum(k for _, k in rp["traki"]) == 2


# ------------------------------------------------------- B1: izolacija po barvi
def test_ostanek_druge_barve_se_ne_uporabi():
    _skladisce([{"dolzina": 3000, "barva": "Siva", "profil": "ROMB 67"}])
    c = {"kerf": 3.0, "barva": "Antracit", "profil": "ROMB 67",
         "dolzine_deske": [5800], "uporabi_ostanke": True}
    rp = razrez_podatki(1000, 2, c)
    assert rp["iz_ost_kos"] == 0             # ni uporabljen
    pos = rp["ostanki_posodobitev"]
    assert any(abs(o["dolzina"] - 3000) < 1e-6 for o in pos)   # ostane


def test_ostanek_drugega_profila_se_ne_uporabi():
    _skladisce([{"dolzina": 3000, "barva": "Antracit", "profil": "GLADKA 70"}])
    c = {"kerf": 3.0, "barva": "Antracit", "profil": "ROMB 67",
         "dolzine_deske": [5800], "uporabi_ostanke": True}
    rp = razrez_podatki(1000, 2, c)
    assert rp["iz_ost_kos"] == 0


# --------------------------------------- B1: novi ostanki tudi brez uporabe
def test_novi_ostanki_iz_nabave_tudi_ko_uporaba_izklopljena():
    _skladisce([{"dolzina": 2500, "barva": "Antracit", "profil": "ROMB 67"}])
    c = {"kerf": 3.0, "barva": "Antracit", "profil": "ROMB 67",
         "dolzine_deske": [3000], "uporabi_ostanke": False}
    rp = razrez_podatki(1000, 2, c)
    assert rp["iz_ost_kos"] == 0             # stari ostanek NI porabljen
    pos = rp["ostanki_posodobitev"]
    # obstoječi ostanek ostane nedotaknjen, doda se nov (3000 − 2×1003 = 994)
    assert any(abs(o["dolzina"] - 2500) < 1e-6 for o in pos)
    assert any(abs(o["dolzina"] - 994) < 1e-6 for o in pos)


def test_generiraj_ne_pise_skladisca_samodejno(cfg_ograja):
    """Generiranje NIKOLI samodejno ne spremeni skladišča (B1)."""
    import risba
    _skladisce([{"dolzina": 2000, "barva": "Antracit", "profil": "ROMB 67"}])
    cfg = cfg_ograja
    cfg["uporabi_ostanke"] = True
    pot = razrez.pot_ostanki()
    pred = open(pot, encoding="utf-8").read()
    izhod, png, dodatni, kolicine = risba.generiraj(cfg)
    # datoteka ostane enaka do izrecnega odpisa
    po = open(pot, encoding="utf-8").read()
    assert po == pred


# --------------------------------------------------- B1: varno pisanje (B5)
def test_shranjevanje_naredi_backup_in_je_atomarno():
    _skladisce([{"dolzina": 1234, "barva": "A", "profil": "P"}])
    pot = razrez.pot_ostanki()
    nova_pot, backup = shrani_ostanke([{"dolzina": 2000, "barva": "A",
                                        "profil": "P"}])
    assert nova_pot == pot
    assert backup and os.path.exists(backup)
    with open(pot, encoding="utf-8") as f:
        vsebina = yaml.safe_load(f)
    assert vsebina[0]["dolzina"] == 2000


def test_majhni_ostanki_se_ne_hranijo():
    shrani_ostanke([{"dolzina": MIN_OSTANKA - 1, "barva": "A", "profil": "P"},
                    {"dolzina": 500, "barva": "A", "profil": "P"}])
    vse = nalozi_ostanke()
    assert len(vse) == 1
    assert vse[0]["dolzina"] == 500


def test_metapodatki_ostankov_se_ohranijo():
    _skladisce([{"dolzina": 1500, "barva": "Antracit", "profil": "ROMB 67",
                 "opomba": "teren"}])
    c = {"kerf": 3.0, "barva": "Antracit", "profil": "ROMB 67",
         "dolzine_deske": [5800], "uporabi_ostanke": True}
    rp = razrez_podatki(500, 1, c)
    pos = rp["ostanki_posodobitev"]
    ohranjeni = [o for o in pos if o.get("opomba") == "teren"]
    assert ohranjeni                        # B1: metapodatki se ne izgubijo
    assert ohranjeni[0]["barva"] == "Antracit"


def test_migracija_stare_lokacije(tmp_path, monkeypatch):
    """ostanki.yaml iz delovne mape se varno prekopira v uporabniško mapo."""
    delo = tmp_path / "delo"
    delo.mkdir()
    monkeypatch.chdir(delo)
    with open(delo / "ostanki.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump([{"dolzina": 700, "barva": "x", "profil": "y"}], f)
    vse = nalozi_ostanke()
    assert len(vse) == 1 and vse[0]["dolzina"] == 700
    # izvirna datoteka ostane nedotaknjena
    assert os.path.exists(delo / "ostanki.yaml")