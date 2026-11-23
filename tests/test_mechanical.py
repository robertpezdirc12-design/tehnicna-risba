# -*- coding: utf-8 -*-
"""F0/F1 — mehansko katalogsko jedro: resolver, BOM, validate (brez ograjnega uvoza).

Izhodni kriterij F1 (docs/f1-specifikacija.md, razdelek 5):

- resolver vrne citirane vrednosti za ciljne katalogske vrstice (test proti
  tabelam/provenanci),
- BOM iz primera vrne 6 vrstic z ustreznim vrstnim redom in oznakami,
- `validate` poroča manjkajoča polja za poz. 1–2 in spoštuje gating,
- brez ograjnega importa / brez posega v obstoječo ograjno kodo.
"""
import copy
import json
import os

import pytest

import mechanical
from mechanical import (
    ManjkajocaVarianta,
    NapakaBOM,
    NapakaKataloga,
    NeznanProfil,
    NeznanStandard,
    derive_bom,
    izpelji_bom,
    nalozi_dokument,
    nalozi_katalog,
    preveri,
    razresi,
    resolve,
    validate,
)

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIMER = os.path.join(KOREN, "mechanical", "examples", "vijacnik.yaml")


@pytest.fixture
def dok():
    """Primer vijacnik.yaml — vsak test dobi svoj globok prepis."""
    return copy.deepcopy(nalozi_dokument(PRIMER))


# ---------- resolver: citirane vrednosti za ciljne vrstice ----------

def test_resolve_iso_4032_m10_citirane_vrednosti():
    vrstica = resolve("M10", "ISO 4032", "iso")
    dim = vrstica["dimenzije"]
    s = dim["width_across_flats_s_mm"]
    assert (s["nominal"], s["min"], s["max"]) == (16, 15.73, 16.00)
    m = dim["height_m_mm"]
    assert (m["nominal"], m["min"], m["max"]) == (8.40, 8.04, 8.40)
    assert dim["width_across_corners_e_mm"]["min"] == 17.77
    assert dim["thread_pitch_P_mm"] == 1.5
    vir = vrstica["provenenca"][0]
    assert "wermac" in vir["name"].lower()
    assert vir["accessed"] == "2026-04-11"
    assert "wermac.org" in (vir["url"] or "")


def test_resolve_iso_4017_m10x35_citirane_vrednosti():
    vrstica = resolve("M10x35", "ISO 4017", "iso")
    dim = vrstica["dimenzije"]
    assert dim["width_across_flats_s_mm"]["nominal"] == 16
    k = dim["head_height_k_mm"]
    assert (k["nominal"], k["min_A"], k["max_A"]) == (6.4, 6.22, 6.58)
    assert dim["width_across_corners_e_mm"]["min"] == 17.77
    assert dim["thread_pitch_P_mm"] == 1.5
    assert dim["thread"] == "full"
    assert dim["point_chamfer_a_mm"]["max"] == 4.5
    assert vrstica["length_mm"] == 35
    assert len(vrstica["provenenca"]) == 2   # Fuller + fasteners.eu


def test_resolve_legacy_din_citirane_vrednosti():
    matica = resolve("M10", "DIN 934", "legacy_din")
    assert matica["dimenzije"]["width_across_flats_s_mm"] == 17
    assert matica["dimenzije"]["height_m_mm"] == 8
    vijak = resolve("M10x35", "DIN 933", "legacy_din")
    assert vijak["dimenzije"]["width_across_flats_s_mm"] == 17
    assert vijak["dimenzije"]["head_height_k_mm"] == 6.4
    assert vijak["length_mm"] == 35


def test_strogo_locevanje_profilov():
    with pytest.raises(NeznanStandard):
        resolve("M10", "DIN 934", "iso")
    with pytest.raises(NeznanStandard):
        resolve("M10", "ISO 4032", "legacy_din")
    iso = resolve("M10", "ISO 4032", "iso")
    assert iso["dimenzije"]["width_across_flats_s_mm"]["nominal"] == 16  # ne 17


def test_napake_brez_ugibanja():
    with pytest.raises(NeznanProfil):
        resolve("M10", "ISO 4032", "din")
    with pytest.raises(NeznanStandard):
        resolve("M10", "ISO 1234", "iso")
    with pytest.raises(ManjkajocaVarianta) as napaka:
        resolve("M10x20", "ISO 4017", "iso")
    assert "M10x35" in str(napaka.value)   # javi, kaj je na voljo


def test_normalizacija_zapisa_oznake_in_profila():
    assert resolve("M10\u00d735", "iso 4017", "ISO") == resolve("M10x35", "ISO 4017", "iso")


def test_vsaka_katalogska_vrstica_ima_provenenco():
    for vrstica in nalozi_katalog().values():
        assert vrstica["provenenca"], vrstica["vir"]
        for vir in vrstica["provenenca"]:
            assert vir["name"] and vir["accessed"]


def test_vrstica_brez_provenance_je_zavrnjena(tmp_path):
    (tmp_path / "slaba.yaml").write_text(
        "catalog: {profil: iso, standard: ISO 4032, designation: M12}\n"
        "dimensions: {width_across_flats_s_mm: 18}\n", encoding="utf-8")
    with pytest.raises(NapakaKataloga):
        nalozi_katalog(str(tmp_path))


# ---------- BOM: 6 vrstic, vrstni red, oznake ----------

def test_bom_vijacnik_sest_vrstic_in_skladnost_z_primerom(dok):
    izpeljan = izpelji_bom(dok)
    assert izpeljan["source_assembly_ref"] == "ASM-VIJ-001"
    assert [vrstica["find_no"] for vrstica in izpeljan["rows"]] == [1, 2, 3, 4, 5, 6]
    # izpeljane vrstice so enake ročno zapisanim v primeru
    assert izpeljan["rows"] == dok["bom"]["rows"]


def test_bom_vrstni_red_custom_pred_standardnimi(dok):
    vrstice = izpelji_bom(dok)["rows"]
    assert [vrstica["part_ref"] for vrstica in vrstice] == ["1", "2", "3", "4", "5", "6"]
    prve_stiri = vrstice[:4]
    assert all(vrstica["standard"] is None for vrstica in prve_stiri)
    assert [vrstica["standard"] for vrstica in vrstice[4:]] == [
        "ISO 4032 M10", "ISO 4017 M10x35"]


def test_bom_oznake_vrstic(dok):
    vrstice = {vrstica["find_no"]: vrstica for vrstica in izpelji_bom(dok)["rows"]}
    assert vrstice[1]["note"] == "placeholder/incomplete"
    assert vrstice[2]["note"] == "placeholder/incomplete"
    assert vrstice[5]["note"] == "ob razrešitvi"
    assert vrstice[6]["note"] == "ob razrešitvi"
    assert vrstice[3]["note"] == "Odprto: konvencija dolžine L100 (potrebna potrditev/razjasnitev)."
    assert all(vrstica["mass"] is None for vrstica in vrstice.values())


def test_bom_agregacija_instanc_dela(dok):
    dok["assembly"]["items"].append({
        "instance_id": "I3b", "part_ref": "3", "quantity": 2,
        "find_no": 3, "transform": None, "overrides": {}})
    vrstice = izpelji_bom(dok)["rows"]
    assert len(vrstice) == 6
    trojka = [vrstica for vrstica in vrstice if vrstica["part_ref"] == "3"][0]
    assert trojka["qty"] == 3


def test_bom_nedvoumen_find_no_je_napaka(dok):
    dok["assembly"]["items"].append({
        "instance_id": "I3b", "part_ref": "3", "quantity": 1,
        "find_no": 9, "transform": None, "overrides": {}})
    with pytest.raises(NapakaBOM):
        izpelji_bom(dok)


def test_bom_neznan_del_je_napaka(dok):
    dok["assembly"]["items"][0]["part_ref"] = "99"
    with pytest.raises(NapakaBOM):
        izpelji_bom(dok)


# ---------- validate: manjkajoča polja, gating, standardi ----------

def test_validate_vijacnik_brez_napak(dok):
    porocilo = validate(dok)
    assert porocilo["napake"] == []
    assert porocilo["ok"] is True


def test_validate_poroca_manjkajoca_polja_za_poz_1_in_2(dok):
    porocilo = validate(dok)
    assert porocilo["deli"]["1"]["manjkajoce"] == [
        "gabariti", "izvrtine", "navojni sedež", "rebra", "tolerance", "datum/csys"]
    druga = porocilo["deli"]["2"]["manjkajoce"]
    for polje in ("skupna dolžina in/ali dolžina stožca", "premeri",
                  "navoj (oznaka, dolžina)", "konec za ročico", "tolerance",
                  "datum/csys"):
        assert polje in druga
    besedilo = mechanical.pripis_clovek(porocilo)
    for polje in ("gabariti", "izvrtine", "navojni sedež", "rebra", "tolerance",
                  "datum/csys"):
        assert polje in besedilo


def test_validate_spozituje_gating_matriko(dok):
    porocilo = validate(dok)
    assert porocilo["deli"]["1"]["detajl"] == "blokiran"
    assert porocilo["deli"]["2"]["detajl"] == "blokiran"
    assert porocilo["deli"]["3"]["detajl"] == "dovoljen"
    assert porocilo["deli"]["5"]["detajl"] == "dovoljen"
    assert porocilo["gating"] == {
        "detajl_dovoljen": ["3", "4", "5", "6"],
        "detajl_blokiran": ["1", "2"],
        "oznaceni_placeholder": ["1", "2"],
    }


def test_validate_zahteva_ekspliciten_placeholder(dok):
    for instance in dok["assembly"]["items"]:
        instance.pop("placeholder", None)
    porocilo = validate(dok)
    assert porocilo["ok"] is False
    assert any("eksplicitnega placeholderja" in napaka for napaka in porocilo["napake"])


def test_validate_standard_razresen_s_provenenco(dok):
    porocilo = validate(dok)
    matica = porocilo["standardi"]["5"]
    assert matica["razreseno"] is True
    assert matica["dimenzije"]["width_across_flats_s_mm"]["nominal"] == 16
    assert matica["provenenca"][0]["accessed"]
    vijak = porocilo["standardi"]["6"]
    assert vijak["razreseno"] is True
    assert vijak["dimenzije"]["thread"] == "full"


def test_validate_neznana_velikost_je_napaka(dok):
    dok["parts"][4]["standard_ref"]["designation"] = "M12"
    porocilo = validate(dok)
    assert porocilo["ok"] is False
    assert any("ni razrešen" in napaka for napaka in porocilo["napake"])
    assert porocilo["standardi"]["5"]["razreseno"] is False


def test_validate_dolzina_se_ne_ujema_s_katalogom(dok):
    dok["parts"][5]["standard_ref"]["length"] = 30
    porocilo = validate(dok)
    assert any("ne ustreza katalogu" in napaka for napaka in porocilo["napake"])


def test_validate_profil_se_ne_sme_mezati(dok):
    dok["parts"][4]["standard_ref"]["profil"] = "legacy_din"
    porocilo = validate(dok)
    assert any("se ne ujema" in napaka for napaka in porocilo["napake"])


def test_validate_enote_morajo_biti_mm(dok):
    dok["parts"][2]["geometry"]["parametri"]["premer"]["enota"] = "cm"
    dok["parts"][2]["geometry"]["parametri"]["radij_konca"].pop("enota")
    porocilo = validate(dok)
    assert any("pričakovana mm" in napaka for napaka in porocilo["napake"])
    assert any("nima `enota`" in napaka for napaka in porocilo["napake"])


def test_validate_reference_sestava(dok):
    dok["assembly"]["items"][0]["part_ref"] = "99"
    porocilo = validate(dok)
    assert any("ne obstaja" in napaka for napaka in porocilo["napake"])


def test_validate_sklic_bom_na_listu(dok):
    dok["drawing_sheets"][0]["tables"]["bom_ref"] = "BOM-NAPACEN"
    porocilo = validate(dok)
    assert any("ne ustreza `bom.id`" in napaka for napaka in porocilo["napake"])


def test_validate_complete_brez_geometrije_je_napaka(dok):
    dok["parts"][2]["geometry"]["parametri"] = {}
    porocilo = validate(dok)
    assert any("status complete, a `parametri` so prazni" in napaka
               for napaka in porocilo["napake"])
    assert "gabariti" in porocilo["deli"]["3"]["ugotovljeno"]


def test_validate_porocilo_je_json_in_clovek(dok):
    porocilo = validate(dok)
    prepis = json.loads(json.dumps(porocilo, ensure_ascii=False))
    assert prepis["ok"] is True
    assert prepis["deli"]["1"]["detajl"] == "blokiran"
    besedilo = mechanical.pripis_clovek(porocilo)
    assert "Kontrola dokumenta VIJ-001" in besedilo
    assert "detajl: BLOKIRAN" in besedilo
    assert "razrešeno" in besedilo


# ---------- pogodba F1: brez ograjnega importa ----------

def test_brez_ograjnega_uvoza():
    mehansko = os.path.join(KOREN, "mechanical")
    prepovedani = ("jedro", "risba", "razrez", "vrata", "vmesnik", "merjenje",
                   "proizvodnja", "terenski_list", "dxf_izvoz")
    for ime in sorted(os.listdir(mehansko)):
        if not ime.endswith(".py"):
            continue
        with open(os.path.join(mehansko, ime), encoding="utf-8") as dat:
            vsebina = dat.read()
        for modul in prepovedani:
            assert "import %s" % modul not in vsebina, ime
            assert "from %s" % modul not in vsebina, ime


def test_anglezke_sopomenke_sledijo_specifikaciji():
    assert resolve is razresi
    assert derive_bom is izpelji_bom
    assert validate is preveri
    assert preveri is mechanical.preveri