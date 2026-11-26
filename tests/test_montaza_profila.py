# -*- coding: utf-8 -*-
"""Montaža profila ROMB DESKA-67 (jedro.MONTAZA_ROMB) — pravila proizvajalca.

En vir resnice: `jedro.MONTAZA_ROMB`. Pravila:
- L-kotnik LEVO in DESNO na vsakem stebričku → razmak ≤ 1450 mm;
- 1450–1800 mm: vmesna povezava IZ ZGORNJE cevi (NI privijačena v tla) —
  vklopi se z 'vmesna_povezava: true';
- ≥ 1800 mm: vmesna povezava ne zadošča — dodatni stebriček;
- vrtanje: Ø3,2 skozi romb + alu cev, nato luknja v rombu Ø4,2–4,5
  (kompozit se razteza — luknja vedno večja od vijaka);
- romb BREZ alu cevi v sredini NI mogoče montirati.
"""
from conftest import osnovni_cfg, cfg_pokoncna

import jedro
import proizvodnja
import risba


def test_romb_montaza_prepozna_profil():
    assert jedro.romb_montaza("ROMB 67") is jedro.MONTAZA_ROMB
    assert jedro.romb_montaza("ROMB DESKA-67") is jedro.MONTAZA_ROMB
    assert jedro.romb_montaza("POLNA DESKA 128") is None
    assert jedro.romb_montaza("") is None
    assert jedro.romb_montaza(None) is None


def test_alu_cev_je_pogoj_montaze():
    """Opozorilo iz navodil: brez alu cevi montaža NI mogoča."""
    assert jedro.MONTAZA_ROMB["alu_cev_obvezna"] is True
    assert jedro.MONTAZA_ROMB["vmesna_povezava_v_tla"] is False


def test_romb_zaklucek_normalizacija():
    assert jedro.romb_zaklucek("čepi") == "cepi"
    assert jedro.romb_zaklucek("CEPI") == "cepi"
    assert jedro.romb_zaklucek("s čepi") == "cepi"
    assert jedro.romb_zaklucek("letvica") == "letvica"
    assert jedro.romb_zaklucek("z letvico") == "letvica"
    assert jedro.romb_zaklucek("") == ""
    assert jedro.romb_zaklucek(None) == ""
    assert jedro.romb_zaklucek("neki") == ""


def test_preveri_cfg_zaklucek_mora_biti_poznan():
    cfg = osnovni_cfg("x.pdf")
    cfg["zaklucek"] = "neki"
    nap = jedro.preveri_cfg(cfg)
    assert any("zaklucek" in n for n in nap), nap
    cfg["zaklucek"] = "letvica"
    assert jedro.preveri_cfg(cfg) == []
    cfg["zaklucek"] = "čepi"
    assert jedro.preveri_cfg(cfg) == []


def test_montazni_list_zaklucek_letvica(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list,
                           zaklucek="letvica")
    assert "Zaključna letvica (WPC)" in bes
    assert "IZ STRANI v romb" in bes
    assert "1 vidni vijak na lamelo" in bes


def test_montazni_list_zaklucek_cepi(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list,
                           zaklucek="cepi")
    assert "Čepi za romb profile" in bes
    assert "Čepi za stebričke" in bes
    assert "Zaključna letvica" not in bes


def test_montazni_list_zaklucek_neizbrano_ponudi_obe_izvedbi(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list)
    assert "s čepi" in bes
    assert "zaključno letvico" in bes


def test_narocilo_zaklucek_letvica():
    cfg = osnovni_cfg("x.pdf")
    cfg["zaklucek"] = "letvica"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Zaključna letvica (WPC)" in k["narocilo"]
    assert "Vijaki za zaključno letvico" in k["narocilo"]
    assert any("Zaključna letvica" in p[0] for p in k["postavke"])


def test_narocilo_zaklucek_cepi():
    cfg = osnovni_cfg("x.pdf")
    cfg["zaklucek"] = "cepi"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Čepi za romb profile" in k["narocilo"]
    assert "Čepi za stebričke" in k["narocilo"]


def test_vrtanje_uposteva_raztezanje_kompozita():
    m = jedro.MONTAZA_ROMB
    assert m["vrtina_romb_od_mm"] > m["vrtina_vijak_mm"]
    assert m["vrtina_romb_do_mm"] >= m["vrtina_romb_od_mm"]
    assert m["vrtina_predrta_mm"] < m["vrtina_vijak_mm"]


def test_razmak_do_1450_je_dovoljen():
    assert jedro.preveri_razmak_stebriki(1450, False, "ROMB 67") == []


def test_razmak_cez_1450_brez_vmesne_povezave_je_napaka():
    nap = jedro.preveri_razmak_stebriki(1500, False, "ROMB 67")
    assert len(nap) == 1
    assert "vmesna_povezava" in nap[0]


def test_razmak_cez_1450_z_vmesno_povezavo_je_dovoljen():
    assert jedro.preveri_razmak_stebriki(1500, True, "ROMB 67") == []
    assert jedro.preveri_razmak_stebriki(1799, True, "ROMB 67") == []


def test_razmak_1800_zahteva_dodatni_stebriček():
    nap = jedro.preveri_razmak_stebriki(1800, True, "ROMB 67")
    assert len(nap) == 1
    assert "stebriček" in nap[0]


def test_profil_izven_kataloga_nima_omejitev_razmika():
    assert jedro.preveri_razmak_stebriki(2500, False, "POLNA DESKA 200") == []
    assert jedro.preveri_razmak_stebriki(2500, False, "LES 100") == []


def test_preveri_cfg_romb_sporoci_razmak_in_resitev():
    # sirina 5000 + meja 2000 → dejanski razmak 1600 mm (> 1450 mm)
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"] = dict(cfg["mere"], sirina=5000, razmak_nosilcev=2000)
    nap = jedro.preveri_cfg(cfg)
    assert any("vmesna_povezava" in n for n in nap), nap
    cfg["vmesna_povezava"] = True
    assert jedro.preveri_cfg(cfg) == []


def test_preveri_cfg_dejanski_razmak_pod_1450_je_tih():
    # meja 1500, a dejanski razmak (1150 mm) ostane pod 1450 mm — brez napake
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"] = dict(cfg["mere"], sirina=2500, razmak_nosilcev=1500)
    assert jedro.preveri_cfg(cfg) == []


def test_preveri_cfg_1800_je_napaka_tudi_z_vmesno_povezavo():
    # sirina 6000 + meja 2000 → dejanski razmak 1933 mm (≥ 1800 mm)
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"] = dict(cfg["mere"], sirina=6000, razmak_nosilcev=2000)
    cfg["vmesna_povezava"] = True
    nap = jedro.preveri_cfg(cfg)
    assert any("stebriček" in n for n in nap), nap


def test_preveri_cfg_vmesna_povezava_mora_biti_bool():
    cfg = osnovni_cfg("x.pdf")
    cfg["vmesna_povezava"] = "da"
    nap = jedro.preveri_cfg(cfg)
    assert any("vmesna_povezava" in n for n in nap), nap


def test_narocilo_vsebuje_l_kotnike_in_opozorilo():
    cfg = osnovni_cfg("x.pdf")
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "L-kotnik za pritrditev romba" in k["narocilo"]
    assert "levo in desno" in k["narocilo"]
    assert "BREZ alu cevi" in k["narocilo"]
    assert any("L-kotnik" in p[0] for p in k["postavke"])


def test_narocilo_vmesna_povezava_ko_je_vklopljena():
    cfg = osnovni_cfg("x.pdf")
    cfg["mere"] = dict(cfg["mere"], sirina=5000, razmak_nosilcev=2000)
    cfg["vmesna_povezava"] = True
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Vmesna povezava (iz zgornje cevi)" in k["narocilo"]
    assert "NI privijačena v tla" in k["narocilo"]


def _narisi_in_zberi(tmp_path, narisi, **spremembe):
    """Nariše v nov list in vrne vsa besedila na risbi."""
    cfg = osnovni_cfg(str(tmp_path / "x.pdf"))
    cfg.update(spremembe)
    c = risba.zdruzi(cfg)
    fig, ax = risba.nov_list()
    try:
        narisi(ax, c)
        return " ".join(" ".join(t.get_text().split()) for t in ax.texts)
    finally:
        risba.plt.close(fig)


def test_montazni_koraki_opisujejo_vrtanje_in_nevidno_pritrditev(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list)
    assert "L-kotnik LEVO in DESNO" in bes
    assert "Z ZADNJE STRANI" in bes          # vijak ni viden s sprednje strani
    assert "3,2" in bes and "4,2" in bes and "4,5" in bes  # vrtanje
    assert "BREZ alu cevi" in bes
    assert "L-kotnik za pritrditev romba" in bes   # potrebščine


def test_montazni_koraki_brez_romba_ostanejo_splosni(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list,
                           profil="LES 100")
    assert "predrtje Ø + 1 mm" in bes
    assert "L-kotnik LEVO in DESNO" not in bes


def test_montazni_list_vmesna_povezava_ko_je_potrebna(tmp_path):
    mere = dict(osnovni_cfg("x.pdf")["mere"], sirina=5000, razmak_nosilcev=2000)
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list,
                           mere=mere, vmesna_povezava=True)
    assert "Vmesna povezava (iz zgornje cevi)" in bes
    assert "NI privijačena v tla" in bes


def test_opombe_na_a3_listu_opisujejo_romb_pravila(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_ogrado)
    assert "OBVEZNA alu cev" in bes
    assert "L-kotnik levo in desno" in bes
    assert "največ 1450 mm" in bes
    assert "Zaključek ograje:" in bes


def test_opombe_na_a3_listu_upostevajo_izbiro_zaključka(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_ogrado,
                           zaklucek="letvica")
    assert "Zaključek ograje: z letvico, privito iz strani v romb." in bes

# --- DESKA-150 / DESKA-128 (pritrditev od spredaj, vidni vijaki) -----------

def test_montaza_profila_katalog_vseh_profilov():
    assert jedro.montaza_profila("ROMB 67") is jedro.MONTAZE_PROFILAV["ROMB 67"]
    assert jedro.montaza_profila("ROMB 67") is jedro.MONTAZA_ROMB
    assert jedro.montaza_profila("DESKA-150")["ime"] == "DESKA-150"
    assert jedro.montaza_profila("DESKA 150")["ime"] == "DESKA-150"
    assert jedro.montaza_profila("POLNA DESKA 128")["ime"] == "DESKA-128"
    assert jedro.montaza_profila("POLNA DESKA 200") is None
    assert jedro.montaza_profila("LES") is None


def test_deska_montaza_samo_za_deske():
    assert jedro.deska_montaza("DESKA-150")["tip"] == "deska"
    assert jedro.deska_montaza("ROMB 67") is None
    assert jedro.romb_montaza("DESKA-150") is None


def test_deska_vrtanje_luknja_1_mm_vecja():
    for kljuc in ("DESKA-150", "DESKA-128"):
        spec = jedro.MONTAZE_PROFILAV[kljuc]
        assert spec["vrtina_odmik_mm"] == 1.0
        assert spec["pritrditev_od_spredaj"] is True


def test_deska_150_razmak_133_140():
    assert jedro.preveri_razmak_stebriki(1400, False, "DESKA-150") == []
    nap = jedro.preveri_razmak_stebriki(1450, False, "DESKA-150")
    assert len(nap) == 1
    assert "133" in nap[0] and "140" in nap[0]


def test_deska_128_razmak_visinsko_odvisen():
    # POKONČNA montaža: 180 cm do 150 cm višine ograje; pri višjih 150 cm
    assert jedro.preveri_razmak_stebriki(1800, False, "POLNA DESKA 128",
                                         1500, pokoncna=True) == []
    nap = jedro.preveri_razmak_stebriki(1850, False, "POLNA DESKA 128",
                                        1500, pokoncna=True)
    assert len(nap) == 1 and "180" in nap[0]
    # PREČNA montaža: 110 cm ne glede na višino (rešitev domnevnega
    # spora — 110 velja za prečno, 180/150 za pokončno montažo)
    assert jedro.preveri_razmak_stebriki(1100, False, "POLNA DESKA 128",
                                         1800) == []
    nap2 = jedro.preveri_razmak_stebriki(1150, False, "POLNA DESKA 128",
                                         1800)
    assert len(nap2) == 1 and "110" in nap2[0]


def test_deska_nima_vmesne_povezave():
    nap = jedro.preveri_razmak_stebriki(1450, True, "DESKA-150")
    assert len(nap) == 1
    assert "ni predvidena" in nap[0]


def test_preveri_cfg_deska_trda_meja_razmika():
    # sirina 5000 + meja 2500 → dejanski razmak 2400 mm (> 1400 mm)
    cfg = osnovni_cfg("x.pdf")
    cfg["profil"] = "DESKA-150"
    cfg["mere"] = dict(cfg["mere"], sirina=5000, razmak_nosilcev=2500)
    nap = jedro.preveri_cfg(cfg)
    assert any("133" in n for n in nap), nap
    cfg["vmesna_povezava"] = True      # pri deskah vmesna povezava NE pomaga
    assert any("133" in n for n in jedro.preveri_cfg(cfg))


def test_montazni_list_deska_pritrditev_od_spredaj(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list,
                           profil="DESKA-150")
    assert "od SPREDAJ skozi desko" in bes
    assert "VIDNI na licu" in bes
    assert "vijak + 1 mm" in bes                # predvrtje
    assert "sredino deske" in bes
    assert "L-kotnik LEVO in DESNO" not in bes  # ni romb
    assert "BREZ alu cevi" not in bes


def test_opombe_na_a3_listu_deska(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_ogrado, profil="DESKA-150")
    assert "DESKA-150" in bes
    assert "VIDNI na licu" in bes
    assert "133–140 cm" in bes
    assert "OBVEZNA alu cev" not in bes         # velja samo za romb


def test_narocilo_deska_128_opisuje_montazo():
    cfg = osnovni_cfg("x.pdf")
    cfg["profil"] = "POLNA DESKA 128"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "DESKA-128" in k["narocilo"]
    assert "VIDNI na licu" in k["narocilo"]
    assert "L-kotnik" not in k["narocilo"]


def test_narocilo_opozori_na_nekataloske_dolzine():
    cfg = osnovni_cfg("x.pdf")
    cfg["profil"] = "POLNA DESKA 128"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "niso kataloške" in k["narocilo"]
    assert "2200" in k["narocilo"]


def test_narocilo_brez_opozorila_pri_kataloskih_dolzinah():
    cfg = osnovni_cfg("x.pdf")
    cfg["profil"] = "POLNA DESKA 128"
    cfg["mere"] = dict(cfg["mere"], sirina=2000)
    cfg["dolzine_deske"] = [2200]
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "niso kataloške" not in k["narocilo"]


def test_narocilo_romb_ne_opozarja_na_dolzine():
    # za romb so dovoljene tudi druge tovarniške dolžine (razrez čez več dolžin)
    cfg = osnovni_cfg("x.pdf")
    cfg["dolzine_deske"] = [5800, 4000, 2200]
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "niso kataloške" not in k["narocilo"]


# --- Pokončna ograja: razmak med vodoravnima cevema (MONTAZE_PROFILAV) -----

def _narisi_pokoncno_in_zberi(tmp_path, narisi, profil, **mere):
    """Nariše pokončno risbo v nov list in vrne vsa besedila na risbi."""
    cfg = cfg_pokoncna(str(tmp_path / "p.pdf"))
    cfg["profil"] = profil
    if mere:
        cfg["mere"] = dict(cfg["mere"], **mere)
    c = risba.zdruzi(cfg)
    fig, ax = risba.nov_list()
    try:
        narisi(ax, c)
        return " ".join(" ".join(t.get_text().split()) for t in ax.texts)
    finally:
        risba.plt.close(fig)


def test_katalog_pokoncna_pravila():
    assert (jedro.pokoncna_pravila("ROMB 67")
            ["razmak_max_vodoravne_cevi_mm"]) == 1100
    assert (jedro.pokoncna_pravila("POLNA DESKA 57/32")
            ["razmak_max_vodoravne_cevi_mm"]) == 1000
    assert (jedro.pokoncna_pravila("POLNA DESKA 100")
            ["razmak_max_vodoravne_cevi_mm"]) == 800
    assert (jedro.pokoncna_pravila("POLNA DESKA 128")
            ["razmak_max_vodoravne_cevi_mm"]) == 1000
    assert jedro.pokoncna_pravila("DESKA-150") is None
    assert jedro.pokoncna_pravila("LES") is None


def test_katalog_57_32_skrito_vijacenje_in_sirini():
    spec = jedro.montaza_profila("POLNA DESKA 57/32")
    assert spec["skrito_vijacenje"] is True
    assert spec["montazne_sirine_mm"] == (57, 32)
    assert jedro.montaza_profila("POLNA DESKA 32/57") is spec
    assert jedro.pokoncna_pravila("POLNA DESKA 57/32")["skrito_vijacenje"] \
        is True


def test_romb_pokoncna_kotnik_in_skrito():
    pr = jedro.pokoncna_pravila("ROMB 67")
    assert pr["kotnik_na_vodoravne_cevi"] is True
    assert pr["skrito_vijacenje"] is True


def test_st_vodoravnih_cevi():
    # n cevi deli višino desk na n + 1 nepodprtih razdalj (tudi robovi
    # desk) — vse morajo biti ≤ razmak_max_vodoravne_cevi_mm.
    assert jedro.st_vodoravnih_cevi(1560, "ROMB 67") == 2        # 520 ≤ 1100
    assert jedro.st_vodoravnih_cevi(1560, "POLNA DESKA 100") == 2  # 520 ≤ 800
    assert jedro.st_vodoravnih_cevi(2500, "POLNA DESKA 100") == 3  # 625 ≤ 800
    assert jedro.st_vodoravnih_cevi(3001, "POLNA DESKA 128") == 3  # 750 ≤ 1000
    assert jedro.st_vodoravnih_cevi(4000, "POLNA DESKA 57/32") == 3  # natanko 1000
    assert jedro.st_vodoravnih_cevi(4001, "POLNA DESKA 57/32") == 4  # 800,2 ≤ 1000
    assert jedro.st_vodoravnih_cevi(1560, "DESKA-150") == 2      # brez pravila
    assert jedro.st_vodoravnih_cevi(None, "ROMB 67") == 2


def test_preveri_cfg_57_32_montazna_sirina():
    cfg = cfg_pokoncna("x.pdf", mere={"deska_sirina": 40, "lamele": 15})
    cfg["profil"] = "POLNA DESKA 57/32"
    nap = jedro.preveri_cfg(cfg)
    assert any("montira na širino" in n for n in nap), nap
    for sir in (57, 32):
        cfg["mere"] = dict(cfg["mere"], deska_sirina=sir)
        assert not any("montira na širino" in n
                       for n in jedro.preveri_cfg(cfg))


def test_montazne_letve_pokoncne_sledijo_pravilu():
    cfg = cfg_pokoncna("x.pdf")
    cfg["profil"] = "POLNA DESKA 100"
    polja = len(risba.razpored_pokoncna(cfg["mere"])["polja"])
    m = risba.proizvodni_model(cfg)
    assert m["montazne_letve"] == 2 * polja       # 1560/3 = 520 ≤ 800
    cfg["mere"] = dict(cfg["mere"], visina=3000)  # h = 2710 → 3 na polje
    m2 = risba.proizvodni_model(cfg)
    assert m2["montazne_letve"] == 3 * polja


def test_narocilo_pokoncna_vodoravne_cevi():
    cfg = cfg_pokoncna("x.pdf")
    cfg["profil"] = "POLNA DESKA 100"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "MONTAŽA POKONČNO (POLNA DESKA 100)" in k["narocilo"]
    assert "razmak med vodoravnima cevema največ 800 mm" in k["narocilo"]


def test_narocilo_romb_pokoncna_kotniki():
    cfg = cfg_pokoncna("x.pdf")                   # privzeti profil ROMB 67
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "L-kotniki na vodoravnih ceveh" in k["narocilo"]
    assert "skrito vijačenje" in k["narocilo"]
    assert "1100" in k["narocilo"]


def test_opombe_pokoncna_57_32_skrito(tmp_path):
    bes = _narisi_pokoncno_in_zberi(tmp_path, risba.narisi_pokoncna,
                                    "POLNA DESKA 57/32",
                                    deska_sirina=57, lamele=18)
    assert "skrito vijačenje" in bes
    assert "montaža na širino" in bes
    assert "Razmak vodoravnih cevi" in bes
    assert "1000" in bes


def test_opombe_pokoncna_romb_kotnik(tmp_path):
    bes = _narisi_pokoncno_in_zberi(tmp_path, risba.narisi_pokoncna,
                                    "ROMB 67")
    assert "kotnik" in bes
    assert "Razmak vodoravnih cevi" in bes
    assert "1100" in bes


def test_montazni_pokoncna_pot_in_koraki(tmp_path):
    bes = _narisi_pokoncno_in_zberi(tmp_path, risba.narisi_montazni_pokoncna,
                                    "POLNA DESKA 100")
    assert "vodoravne cevi" in bes
    assert "razmak ≤ 800 mm" in bes
    bes_romb = _narisi_pokoncno_in_zberi(
        tmp_path, risba.narisi_montazni_pokoncna, "ROMB 67")
    assert "L-kotnik (na vodoravni cevi)" in bes_romb
    assert "zmontiraj kotnike" in bes_romb


# --- Odmiki vijaka od roba reza + dopolnjena pravila profilov --------------

def test_pritrditev_desk_odmiki_min_max():
    assert jedro.Pritrditev_DESK["odmik_vijak_min_mm"] == 30
    assert jedro.Pritrditev_DESK["odmik_vijak_max_na_plosco_mm"] == 150
    assert jedro.Pritrditev_DESK["odmik_vijak_max_bocno_mm"] == 100


def test_odmik_vijak_max_po_tipu_konstrukcije():
    assert jedro.odmik_vijak_max("vrh") == 150
    assert jedro.odmik_vijak_max("bočno") == 100
    assert jedro.odmik_vijak_max("na ploščo") == 150
    assert jedro.odmik_vijak_max("neki") is None
    assert jedro.odmik_vijak_max(None) is None


def test_opomba_kratkih_kosov():
    nap = jedro.opomba_kratkih_kosov([("D1", 2000), ("V1-1", 55), ("D2", 60)])
    assert len(nap) == 1
    assert "V1-1" in nap[0] and "55" in nap[0] and "30" in nap[0]


def test_deska_100_razmak_visinsko_odvisen():
    assert jedro.preveri_razmak_stebriki(1800, False, "POLNA DESKA 100",
                                         1200, pokoncna=True) == []
    assert jedro.preveri_razmak_stebriki(1500, False, "POLNA DESKA 128",
                                         1501, pokoncna=True) == []
    nap = jedro.preveri_razmak_stebriki(1550, False, "POLNA DESKA 128",
                                        1501, pokoncna=True)
    assert len(nap) == 1 and "150" in nap[0]


def test_deska_57_32_razmak_150_neodvisno_od_visini():
    assert jedro.preveri_razmak_stebriki(1500, False, "POLNA DESKA 57/32",
                                         2500, pokoncna=True) == []
    nap = jedro.preveri_razmak_stebriki(1550, False, "POLNA DESKA 57/32",
                                        1000, pokoncna=True)
    assert len(nap) == 1 and "150" in nap[0]


def test_57_32_obrnjeno_vrtanje_in_vijak():
    spec = jedro.montaza_profila("POLNA DESKA 57/32")
    assert spec["vrtina_kompozit_manjsa"] is True
    assert spec["vrtina_konstrukcija_vecja"] is True
    assert "2/3" in spec["vijak_dolzina_opis"]


def test_narocilo_odmiki_po_tipu_konstrukcije():
    cfg = cfg_pokoncna("x.pdf")
    cfg["profil"] = "POLNA DESKA 57/32"
    cfg["pritrditev"] = "bočno"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Odmik vijaka od roba reza" in k["narocilo"]
    assert "največ 100 mm" in k["narocilo"]
    assert "MANJŠA od vijaka" in k["narocilo"]
    assert "2/3 globine profila" in k["narocilo"]
    cfg["pritrditev"] = "vrh"
    k2 = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "največ 150 mm" in k2["narocilo"]


def test_narocilo_romb_vkljucena_alu_cev():
    cfg = osnovni_cfg("x.pdf")
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "vključena v ceno romb deske" in k["narocilo"]


def test_opombe_vsebujejo_odmike_in_vrzel(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_ogrado)
    assert "Odmik vijaka od roba reza" in bes
    assert "prekrivanje desk" in bes
    assert "obdelujejo kot les" in bes


def test_opombe_pokoncna_odmiki(tmp_path):
    bes = _narisi_pokoncno_in_zberi(tmp_path, risba.narisi_pokoncna,
                                    "POLNA DESKA 57/32",
                                    deska_sirina=57, lamele=18)
    assert "Odmik vijaka od roba reza" in bes
    assert "MANJŠA od vijaka" in bes
    assert "2/3" in bes


def test_montazni_list_samodejno_vsebuje_odmik_vijaka(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list)
    assert "Odmik vijaka od roba reza" in bes


# --- Dimenzije elementov, ročaji, uporaba profilov -------------------------

def test_katalog_dimenzije_elementov():
    assert jedro.montaza_profila("POLNA DESKA 57/32")["dimenzija_mm"] == (57, 32)
    assert jedro.montaza_profila("POLNA DESKA 100")["dimenzija_mm"] == (100, 12)
    assert jedro.montaza_profila("POLNA DESKA 128")["dimenzija_mm"] == (128,
                                                                      16.5)


def test_rocaj_specifikaciji():
    r1 = jedro.ROCAJI["standardni"]
    assert r1["dimenzija_mm"] == (95, 45, 5800)
    assert "WHITE" in r1["opomba"]
    r2 = jedro.ROCAJI["polni"]
    assert r2["dimenzija_mm"] == (92, 45, 5800)
    assert r2["notranja_dimenzija_mm"] == (55, 30)
    assert jedro.ROCAJI["samostojna_prodaja"] is False


def test_preveri_cfg_100_samo_za_pokoncno():
    cfg = osnovni_cfg("x.pdf")            # predloga 'ograja' (prečna)
    cfg["profil"] = "POLNA DESKA 100"
    nap = jedro.preveri_cfg(cfg)
    assert any("samo za POKONČNO ograjo" in n for n in nap), nap
    cfg_p = cfg_pokoncna("x.pdf")
    cfg_p["profil"] = "POLNA DESKA 100"
    assert jedro.preveri_cfg(cfg_p) == []


def test_preveri_cfg_57_32_tudi_samo_pokoncna():
    cfg = osnovni_cfg("x.pdf")
    cfg["profil"] = "POLNA DESKA 57/32"
    assert any("samo za POKONČNO ograjo" in n
               for n in jedro.preveri_cfg(cfg))
    # DESKA-128 velja za obe izvedbi (pokončno ali prečno)
    cfg["profil"] = "POLNA DESKA 128"
    assert not any("samo za POKONČNO" in n for n in jedro.preveri_cfg(cfg))


def test_pokoncna_razmak_stebrov_po_navodilih():
    cfg = cfg_pokoncna("x.pdf", mere={"sirina": 5000, "razmak_stebrov": 2500,
                                      "deska_sirina": 57, "lamele": 20})
    cfg["profil"] = "POLNA DESKA 57/32"
    # dejanski razmak stebrov = (5000 - 60) / 2 = 2470 mm > 150 mm
    nap = jedro.preveri_cfg(cfg)
    assert any("150" in n for n in nap), nap
    cfg["profil"] = "POLNA DESKA 100"
    cfg["mere"] = dict(cfg["mere"], deska_sirina=100)
    nap2 = jedro.preveri_cfg(cfg)
    assert any("180" in n or "150" in n for n in nap2), nap2


def test_pokoncna_razmak_stebrov_v_okviru():
    cfg = cfg_pokoncna("x.pdf")           # 3000 / 1500 → 1470 mm
    cfg["profil"] = "POLNA DESKA 100"
    assert jedro.preveri_cfg(cfg) == []


def test_narocilo_vsebuje_dimenzije_in_rocaj():
    cfg = cfg_pokoncna("x.pdf")
    cfg["profil"] = "POLNA DESKA 100"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Dimenzija profila: 100×12×5800 mm" in k["narocilo"]
    assert "samo za pokončno ograjo" in k["narocilo"]
    assert "Ročaj: 95×45×5800 mm" in k["narocilo"]
    assert "92×45×5800" in k["narocilo"]
    assert "55×30" in k["narocilo"]
    assert "Samostojna prodaja ročajev ni možna" in k["narocilo"]


def test_narocilo_57_32_naleganje():
    cfg = cfg_pokoncna("x.pdf")
    cfg["profil"] = "POLNA DESKA 57/32"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "57×32×5800 mm" in k["narocilo"]
    assert "naleganje na 57 ali 32" in k["narocilo"]


# --- Romb dimenzije, čepi levi/desni, barve, skladiščenje ------------------

def test_romb_dimenzija_in_uporaba():
    spec = jedro.montaza_profila("ROMB 67")
    assert spec["dimenzija_mm"] == (67, 26)
    assert spec["uporaba"] == ("pokončna", "prečna")


def test_st_barv_po_profilih():
    assert jedro.montaza_profila("POLNA DESKA 57/32")["st_barv"] == 4
    assert jedro.montaza_profila("POLNA DESKA 100")["st_barv"] == 8
    assert jedro.montaza_profila("POLNA DESKA 128")["st_barv"] == 6
    assert jedro.montaza_profila("ROMB 67")["st_barv"] == 7


def test_narocilo_cepi_levi_in_desni():
    cfg = osnovni_cfg("x.pdf")
    cfg["zaklucek"] = "cepi"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "levi + desni" in k["narocilo"]
    assert "parov" in k["narocilo"]
    assert "Čepi za stebričke" in k["narocilo"]


def test_narocilo_letvica_je_opcija_prečne():
    cfg = osnovni_cfg("x.pdf")
    cfg["zaklucek"] = "letvica"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "opcija za zaključevanje prečne romb ograje" in k["narocilo"]


def test_narocilo_skladiscenje_in_barve():
    cfg = cfg_pokoncna("x.pdf")
    cfg["profil"] = "POLNA DESKA 100"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Skladiščenje" in k["narocilo"]
    assert "reklamacija" in k["narocilo"]
    assert "8 barv" in k["narocilo"]
    assert "White" in k["narocilo"]


def test_narocilo_romb_dimenzija():
    cfg = osnovni_cfg("x.pdf")
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Dimenzija profila: 67×26×5800 mm" in k["narocilo"]


def test_montazni_list_vsebuje_skladiscenje(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list)
    assert "Pred montažo" in bes and "suhem" in bes


def test_preveri_cfg_letvica_samo_prečna():
    cfg = cfg_pokoncna("x.pdf")            # pokončna, profil ROMB 67
    cfg["zaklucek"] = "letvica"
    nap = jedro.preveri_cfg(cfg)
    assert any("prečno romb ograjo" in n for n in nap), nap
    cfg_p = osnovni_cfg("x.pdf")           # prečna — letvica dovoljena
    cfg_p["zaklucek"] = "letvica"
    assert jedro.preveri_cfg(cfg_p) == []


# --- WoodCore navodila: tabela razmakov, drenaža, orodja ------------------

def test_tabela_razmakov_osnovne_vrednosti():
    assert jedro.razmak_desk_mm(20, 2.0) == 2.5
    assert jedro.razmak_desk_mm(-25, 4.0) == 11.0
    assert jedro.razmak_desk_mm(0, 3.0) == 5.25
    # 5 m stolpec = vrednost za 4 m (tako je v viru)
    assert jedro.razmak_desk_mm(-20, 5.0) == 10.0
    assert jedro.razmak_desk_mm(-20, 6.0) == 10.0


def test_tabela_razmakov_interpolacija_in_meje():
    # interpolacija dolžine: 2,5 m pri 20 °C = povprečje 2,5 in 3,75
    assert jedro.razmak_desk_mm(20, 2.5) == 3.12
    # pod 1 m → vrednost za 1 m
    assert jedro.razmak_desk_mm(25, 0.5) == 1.0
    # temperature zunaj tabele → najbližja vrstica (40/45 sta prazni)
    assert jedro.razmak_desk_mm(45, 2.0) == 1.5
    assert jedro.razmak_desk_mm(-30, 2.0) == 5.5


def test_preveri_cfg_montazna_temp():
    cfg = osnovni_cfg("x.pdf")
    cfg["montazna_temp_c"] = "toplo"
    assert any("montazna_temp_c" in n for n in jedro.preveri_cfg(cfg))
    cfg["montazna_temp_c"] = 50
    assert any("-25 in 35" in n for n in jedro.preveri_cfg(cfg))
    cfg["montazna_temp_c"] = 20
    assert jedro.preveri_cfg(cfg) == []


def test_narocilo_woodcore_pravila_brez_drenaze_pri_polni():
    cfg = cfg_pokoncna("x.pdf", profil="POLNA DESKA 100")  # polna deska
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "nosilce, tramove" in k["narocilo"]
    assert "nerjaveči" in k["narocilo"]
    assert "Baterijski vrtalnik" in k["narocilo"]
    # polna deska nima prekatov → brez drenažnih lukenj
    assert "Drenažne luknje" not in k["narocilo"]


def test_narocilo_drenazne_luknje_romb():
    cfg = osnovni_cfg("x.pdf")         # ROMB 67 — votel s prekati
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Drenažne luknje" in k["narocilo"]
    assert "4,2 mm" in k["narocilo"]
    assert "v vsak prekat" in k["narocilo"]


def test_narocilo_razmak_po_temperaturi():
    cfg = osnovni_cfg("x.pdf")
    cfg["montazna_temp_c"] = 20
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Razmak med deskami" in k["narocilo"]
    assert "tabela WoodCore" in k["narocilo"]
    assert "6 mm odmik" in k["narocilo"]


def test_montazni_list_orodja_in_drenaza(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list)  # ROMB
    assert "Baterijski vrtalnik" in bes
    assert "Drenažne luknje" in bes
    bes2 = _narisi_pokoncno_in_zberi(
        tmp_path, risba.narisi_montazni_pokoncna, "POLNA DESKA 100")
    assert "Baterijski vrtalnik" in bes2
    assert "Drenažne luknje" not in bes2   # POLNA DESKA 100 je polna


def test_montazni_list_dodatki_temp(tmp_path):
    bes = _narisi_in_zberi(tmp_path, risba.narisi_montazni_list,
                           montazna_temp_c=20)
    assert "tabeli WoodCore" in bes


# --- Pregradne stene (stran Roksal): profili, razmiki, pokrovček ----------

def test_pregradne_stene_razmiki_stebriki():
    # prečna montaža desk (razmak_max_stebriki_precna_mm)
    assert jedro.montaza_profila(
        "ROMB 67")["razmak_max_stebriki_precna_mm"] == 1450.0
    assert jedro.montaza_profila(
        "DESKA-128")["razmak_max_stebriki_precna_mm"] == 1100.0
    assert jedro.montaza_profila(
        "DESKA-150")["razmak_max_stebriki_precna_mm"] == 1400.0
    # pokončna montaža desk (romb): stebrički 150 cm, vertikalni
    # nosilci 100 cm
    r = jedro.montaza_profila("ROMB 67")
    assert r["razmak_max_stebriki_pokoncna_mm"] == 1500.0
    assert r["razmak_max_vertikalni_nosilci_mm"] == 1000.0


def test_deska_128_je_polna_brez_drenaze():
    spec = jedro.montaza_profila("DESKA-128")
    assert spec["dimenzija_mm"] == (128, 16.5)
    assert not spec.get("drenazne_luknje")   # polna deska — brez prekatov


def test_deska_150_podatki():
    spec = jedro.montaza_profila("DESKA-150")
    assert spec["dimenzija_mm"] == (150, 25)
    assert spec["st_barv"] == 7
    assert spec["st_povrsin"] == 3
    assert spec["dvostranska_rebra"] is True
    assert spec["drenazne_luknje"] is True    # votel terasni profil
    assert "zaključni pokrovček" in spec["zakljucki"]


def test_woodcore_material_in_garancija():
    assert jedro.WOODCORE["garancija_let"] == 15
    assert "HDPE" in jedro.WOODCORE["material"]


def test_narocilo_128_polna_brez_drenaze():
    cfg = cfg_pokoncna("x.pdf", profil="DESKA-128",
                       mere={"deska_sirina": 128, "lamele": 18})
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Drenažne luknje" not in k["narocilo"]
    assert "Dimenzija profila: 128×16,5×2200 mm" in k["narocilo"]


def test_narocilo_150_drenazne_in_dimenzije():
    cfg = osnovni_cfg("x.pdf")
    cfg["profil"] = "DESKA-150"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Drenažne luknje" in k["narocilo"]
    assert "Dimenzija profila: 150×25×4000 / 2200 mm" in k["narocilo"]
    assert "3 površine" in k["narocilo"]


# --- KUBO 80/42, ročaj 50 cm, opombe (pokončne pregradne stene) ----------

def test_kubo_katalog():
    spec = jedro.montaza_profila("KUBO 80/42")
    assert spec is not None
    assert jedro.montaza_profila("kubo") is spec
    assert spec["dimenzija_mm"] == (80, 42)
    assert spec["uporaba"] == ("pokončna",)
    assert spec["st_barv"] == 4
    assert spec["montazne_sirine_mm"] == (80, 42)
    assert spec["skrito_vijacenje"] is True
    assert (20, 60, 2) in spec["alu_cevi_mm"]
    assert spec["razpon_brez_ojacitve_mm"] == 1200
    assert spec["razpon_ojacitev_20x60x2_mm"] == 2600.0
    assert "ELOKSIRANA" in spec["alu_opomba"]


def test_rocaj_vijaki_50cm():
    assert jedro.ROCAJI["vijak_razmak_mm"] == 500.0
    assert jedro.ROCAJI["vrtina_odmik_mm"] == 1.0
    assert "zgoraj navzdol" in jedro.ROCAJI["vijak_lega"]


def test_narocilo_rocaj_50cm():
    cfg = osnovni_cfg("x.pdf")
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "razmaku 50 cm" in k["narocilo"]
    assert "1 mm večje od vijaka" in k["narocilo"]


def test_narocilo_spoji_na_stebriku_samo_prečna():
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(osnovni_cfg("x.pdf")))
    assert "obvezno na stebričku" in k["narocilo"]
    kp = proizvodnja.izracunaj_kolicine(
        jedro.zdruzi(cfg_pokoncna("x.pdf")))
    assert "obvezno na stebričku" not in kp["narocilo"]


def test_narocilo_cepi_opomba_voda():
    cfg = osnovni_cfg("x.pdf")
    cfg["zaklucek"] = "cepi"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "ne garantirajo" in k["narocilo"]
    assert "zakrije odprtine" in k["narocilo"]


def test_narocilo_pokoncna_romb_alu_viden():
    cfg = cfg_pokoncna("x.pdf")         # ROMB 67 pokončno
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "aluminijasta cev v sredini profila" in k["narocilo"]
    assert "zapri s čepi" in k["narocilo"]


def test_narocilo_rustic_opomba():
    cfg = osnovni_cfg("x.pdf")
    cfg["barva"] = "Rustic Oak"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Rustic Oak in Rustic Walnut" in k["narocilo"]
    assert "variirata" in k["narocilo"]
    cfg2 = osnovni_cfg("x.pdf")
    cfg2["barva"] = "Antracit"
    k2 = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg2))
    assert "variirata" not in k2["narocilo"]


def test_preveri_cfg_romb_pokoncna_150():
    cfg = cfg_pokoncna("x.pdf")         # ROMB 67 pokončno
    # 2 stebrica → dejanski razmak 2940 mm > 1500 mm (pokončno pravilo)
    cfg["mere"] = dict(cfg["mere"], razmak_stebrov=3000)
    nap = jedro.preveri_cfg(cfg)
    assert any("150" in n and "stebrič" in n for n in nap), nap


# --- barvni odtenki (barvna lestvica WoodCore, imena prebrana s slik) --- #

def test_barve_romb_po_imenih():
    b = jedro.MONTAZA_ROMB["barve"]
    assert b == ("Amazon wood", "Ash wood", "Golden teak", "Burma teak",
                 "Oak wood", "Rustic oak", "Rustic walnut")


def test_barve_100_vkljucuje_white():
    b = jedro.deska_montaza("POLNA DESKA 100")["barve"]
    assert "White" in b and len(b) == 8


def test_barve_128_brez_golden_teak():
    b = jedro.deska_montaza("DESKA-128")["barve"]
    assert "Golden teak" not in b and len(b) == 6


def test_barve_5732_in_kubo_so_enake():
    assert (jedro.deska_montaza("POLNA DESKA 57/32")["barve"]
            == jedro.montaza_profila("KUBO 80/42")["barve"])


def test_barve_150_vkljucuje_rustik():
    b = jedro.deska_montaza("DESKA-150")["barve"]
    assert "Rustic oak" in b and "Rustic walnut" in b and len(b) == 7


def test_ujemanje_barve_prepozna_ime():
    assert jedro.ujemanje_barve(
        "Rustic Oak", jedro.MONTAZA_ROMB) == "Rustic oak"


def test_ujemanje_barve_prepozna_antracit_kot_amazon():
    assert jedro.ujemanje_barve(
        "Antracit", jedro.MONTAZA_ROMB) == "Amazon wood"


def test_ujemanje_barve_ne_zamenja_odtenka_izven_palete():
    # White je na voljo samo pri POLNI DESKI 100
    assert jedro.ujemanje_barve("White", jedro.MONTAZA_ROMB) is None
    assert jedro.ujemanje_barve(
        "White", jedro.deska_montaza("POLNA DESKA 100")) == "White"


def test_ujemanje_barve_neznan_vrne_none():
    assert jedro.ujemanje_barve("Roza", jedro.MONTAZA_ROMB) is None


def test_preveri_cfg_barva_neznana_je_napaka():
    cfg = osnovni_cfg("x.pdf")
    cfg["barva"] = "Roza"
    nap = jedro.preveri_cfg(jedro.zdruzi(cfg))
    assert any("ni med odtenki" in n for n in nap)


def test_preveri_cfg_barva_antracit_in_rustic_sprejeti():
    cfg = osnovni_cfg("x.pdf")
    cfg["barva"] = "Antracit"
    assert not any("ni med odtenki" in n
                   for n in jedro.preveri_cfg(jedro.zdruzi(cfg)))
    cfg["barva"] = "Rustic Oak"
    assert not any("ni med odtenki" in n
                   for n in jedro.preveri_cfg(jedro.zdruzi(cfg)))


def test_narocilo_barvna_paleta_po_imenih():
    cfg = osnovni_cfg("x.pdf")
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Barvna paleta (7 barv): Amazon wood" in k["narocilo"]
    assert "Rustic walnut" in k["narocilo"]


def test_narocilo_barvni_odtenek_je_kataloski():
    cfg = osnovni_cfg("x.pdf")
    cfg["barva"] = "Rustic Oak"
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Barvni odtenek: Rustic oak." in k["narocilo"]


def test_narocilo_vsebuje_variacije_dobav_in_posvetlitev():
    cfg = osnovni_cfg("x.pdf")
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "dobavami malenkost varira" in k["narocilo"]
    assert "Posvetlitev prvo leto: 5–10 %" in k["narocilo"]


def test_narocilo_vsebuje_garancijske_izjeme():
    cfg = osnovni_cfg("x.pdf")
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "Garancija 15 let" in k["narocilo"]
    assert "težke obremenitve in udarci niso kriti" in k["narocilo"]


def test_narocilo_opozori_montaza_pod_5():
    cfg = osnovni_cfg("x.pdf")
    cfg["montazna_temp_c"] = 0
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "POZOR: montaža pod 5 °C" in k["narocilo"]


def test_narocilo_brez_opozorila_pri_15():
    cfg = osnovni_cfg("x.pdf")
    cfg["montazna_temp_c"] = 15
    k = proizvodnja.izracunaj_kolicine(jedro.zdruzi(cfg))
    assert "POZOR: montaža pod 5" not in k["narocilo"]


def test_montazni_list_opozori_montaza_pod_5(tmp_path):
    cfg = cfg_pokoncna(str(tmp_path / "x.pdf"))
    cfg["montazna_temp_c"] = 0
    c = risba.zdruzi(cfg)
    fig, ax = risba.nov_list()
    try:
        risba.narisi_montazni_pokoncna(ax, c)
        besedilo = " ".join(" ".join(t.get_text().split()) for t in ax.texts)
    finally:
        risba.plt.close(fig)
    assert "POZOR: montaža pod 5 °C ni primerna!" in besedilo


# --- material in skladiščenje (O materialu + FAQ) --- #

def test_material_je_60_30_10():
    assert jedro.WOODCORE["material"] == (
        "60 % bambusovih vlaken, 30 % polietilena (HDPE), 10 % aditivov")


def test_posvetlitev_prvo_leto():
    assert "5–10 %" in jedro.WOODCORE["posvetlitev_prvo_leto"]


def test_raztezek_je_12_mm_na_4m():
    assert jedro.WOODCORE["raztezek_na_4m_mm"] == 12


def test_montazna_temp_min_je_5():
    assert jedro.WOODCORE["montazna_temp_min_c"] == 5


def test_garancija_ima_izjeme():
    izjeme = jedro.WOODCORE["garancija_izjeme"]
    assert "udarci" in izjeme and "posvetlitev" in izjeme


def test_skladisce_podpore_na_50_cm_in_pokrito():
    s = jedro.SKLADISCENJE_OPOMBA
    assert "največ 50 cm" in s
    assert "obvezno pokrito" in s


def test_preveri_cfg_risalne_barve_wpc_barve_sprejete():
    # risalne barve (WPC_BARVE) veljajo tudi, če niso kataloški odtenki
    for b in ("Teak", "Siva", "Kava", "RAL 7016 (prašno barvanje)"):
        cfg = osnovni_cfg("x.pdf")
        cfg["barva"] = b
        assert not any("ni med odtenki" in n
                       for n in jedro.preveri_cfg(jedro.zdruzi(cfg))), b


def test_preveri_cfg_hex_barva_sprejeta():
    cfg = osnovni_cfg("x.pdf")
    cfg["barva"] = "#a9764f"
    assert not any("ni med odtenki" in n
                   for n in jedro.preveri_cfg(jedro.zdruzi(cfg)))


def test_preveri_cfg_res_neznana_barva_je_se_vedno_napaka():
    # tipkarska napaka izven vseh poznanih besedišč mora pasti
    cfg = osnovni_cfg("x.pdf")
    cfg["barva"] = "Rožnata"
    assert any("ni med odtenki" in n
               for n in jedro.preveri_cfg(jedro.zdruzi(cfg)))
