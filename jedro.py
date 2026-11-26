# -*- coding: utf-8 -*-
"""Jedro (core) — geometrija, konfiguracija, validacija, pomožne funkcije.

F2 (issue #5): izločeno iz monolita risba.py BREZ spremembe vedenja;
risba.py javno API ohranja prek re-exportov. Brez risanja (matplotlib).
"""
import math
import os
import re
import sys
from typing import Any

import yaml

from razrez import kos_iz_vira

import vrata as vrat

BARVA_LAMEL = "#3e4a5e"  # privzeta barva lamel (iz risba.konstante)

PRIVZETO: dict[str, Any] = {
    "predloga": "ograja",
    "ime": "BALKONSKA OGRAJA",
    "risba_st": "BO-001",
    "izdelal": "R. Pezdirc",
    "stranka": "",            # naročnik (glava + montažni list)
    "objekt": "",             # lokacija objekta (glava + montažni list)
    "uporabi_ostanke": False,  # privzeto NE uporabi skladišča (varno); vklop porabe je izrecen
    "dolzine_deske": [5800],  # tovarniške dolžine (npr. 5800, 4000, 2200)
    "dolzina_deske": 5800,    # (združljivost — posamezna dolžina)
    "dolzina_palice": 6000,   # tovarniška dolžina alu profila
    "kerf": 3.0,              # širina rezila (mm) — upoštevana v rezalnem načrtu
    "podjetje": "",           # ime podjetja v naslovnem bloku (neobvezno)
    "pregledal": "",          # neobvezno
    "odobril": "",            # neobvezno
    "revizije": None,         # ali [[rev, datum, opis, izdelal], ...]
    "datum": "",
    "merilo": "auto",
    "format": "A3",
    "izhod": "BO-001.pdf",
    "foto": "",
    "barva": "Antracit",      # ime iz WPC_BARVE ali #hex
    "profil": "ROMB 67",      # ime/dimenzija WPC deske (WoodCore)
    "material": "Aluminij (prašno barvano)",
    "material_lamel": "WPC lesni kompozit",
    "podlaga": "",            # beton / zid / les / jeklo — prilagodi vijake
    "pritrditev": "bočno",    # bočno (v fasado) ali vrh (v ploščo)
    "vijak_lamela": "",       # pritrditev lamela↔profil (prazno = privzeti)
    "vijak_nosilec": "",      # pritrditev nosilec↔podlaga (prazno = privzeti)
    "deli": None,
    "opombe": None,
    # dimenzije profilov/konstrukcijskih delov (issue #6: trdo zapisane
    # dimenzije so odstranjene iz generatorjev — to so privzete vrednosti)
    "profil_zg_dim": "80×40×3",   # zgornji alu profil (prečna)
    "profil_sp_dim": "60×40×3",   # spodnji alu profil (prečna)
    "nosilec_dim": "50×50×5",     # nosilni nosilec (prečna)
    "osnova_dim": "90×90×6",      # osnova stebra (pokončna)
    "mere": {"sirina": 3000, "visina": 1200, "globina": 1200,
             "odcep": 60, "profil_v": 40, "lamela_v": 60,
             "debelina": 20, "lamele": 13, "razmak_nosilcev": 1000,
             # predloga "pokončna":
             "deska_sirina": 100, "deska_debelina": 20, "vrzel": 20,
             "rocaj_v": 40, "razmak_stebrov": 1500,
             "steber_sirina": 60, "steber_debelina": 40},
}

def odsteni(hexbarva, faktor):
    """Osvetli (faktor > 1) ali potemni (faktor < 1) barvo v zapisu #rrggbb."""
    h = hexbarva.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    f = lambda c: max(0, min(255, int(c * faktor)))
    return f"#{f(r):02x}{f(g):02x}{f(b):02x}"


# Poimenovane barve desek (približki — natančni odtenek vedno po vzorcu
# proizvajalca, WoodCore WPC ne deluje po sistemu RAL)
WPC_BARVE = {
    "Antracit": "#3e4a5e",
    "RAL 7016 (prašno barvanje)": "#383e42",
    "Siva": "#8d939c",
    "Teak": "#a9764f",
    "Rustic Oak": "#9c6b43",
    "Rustic Walnut": "#6e4a33",
    "Kava": "#5d4433",
    "Bež": "#c3b394",
}


def barva_hex(vrednost):
    """Prevede ime barve (WPC_BARVE) ali #hex v #rrggbb."""
    if not vrednost:
        return BARVA_LAMEL
    vrednost = str(vrednost).strip()
    if vrednost.startswith("#"):
        return vrednost
    return WPC_BARVE.get(vrednost, BARVA_LAMEL)


# ── Montaža WPC profilov (navodila proizvajalca) — EN vir resnice ──────────
# Vir: navodila proizvajalca za montažo (ROMB DESKA-67, DESKA-150, DESKA-128).
# Uporabljajo: preveri_cfg (razmiki stebričkov), proizvodnja (naročilo) in
# risba (montažni koraki, opombe, DETAJL 2 — LAMELE).
# OPOZORILO (romb): BREZ alu cevi v sredini NI mogoče montirati — nevidno
# pritrjevanje gre skozi to cev, zato nakup desk brez alu cevi NI možen!
MONTAZE_PROFILAV = {
    "ROMB 67": {
        "ime": "ROMB 67",
        "tip": "romb",
        "sirina_profila_mm": 67,        # širina profila romb
        "dimenzija_mm": (67, 26),
        "uporaba": ("pokončna", "prečna"),
        "st_barv": 7,                   # barvni odtenki romba
        "barve": ("Amazon wood", "Ash wood", "Golden teak", "Burma teak",
                  "Oak wood", "Rustic oak", "Rustic walnut"),   # Klasik + Rustik
        "nakupne_dolzine_mm": (5800,),  # reže se po meri
        "alu_cev_obvezna": True,        # pogoj montaže (nevidno pritrjevanje)
        "kotniki_na_stebriku": 2,       # L-kotnik LEVO in DESNO na stebričku
        "razmak_max_stebriki_mm": 1450.0,  # z L-kotnikoma levo in desno
        "razmak_max_vmesna_povezava_mm": 1800.0,  # več → dodatni stebriček
        "vmesna_povezava_v_tla": False,  # povezava IZ ZGORNJE cevi, ne v tla
        # Prečna montaža desk (prečne ograje/pregradne stene): 145 cm
        # z L-kotnikoma levo in desno (vir: prečne strani).
        "razmak_max_stebriki_precna_mm": 1450.0,
        # Pokončna montaža desk: stebrički do 150 cm; vertikalni
        # nosilci do 100 cm (samo s kotnikom ali ploščatim aluminijem
        # na vsakem nosilcu) — vir: pokončne pregradne stene.
        "razmak_max_stebriki_pokoncna_mm": 1500.0,
        "razmak_max_vertikalni_nosilci_mm": 1000.0,
        "vijak": "kniping RF vijak 3,9",
        "vrtina_vijak_mm": 3.9,
        "vrtina_predrta_mm": 3.2,       # skozi romb + alu cev (eno vrtanje)
        "vrtina_romb_od_mm": 4.2,       # luknja v rombu se poveča na …
        "vrtina_romb_do_mm": 4.5,       # … (kompozit se razteza > vijak)
        # Zaključek ograje (konec ograje) — dve dovoljeni izvedbi:
        #   "cepi"    — čepi zaprejo odprte konce romb desk in stebričkov;
        #   "letvica" — zaključna letvica se PRIVIJA IZ STRANI v romb profile
        #               (vidni vijaki, 1 na lamelo) in skrije odprte konce.
        "zakljucki": ("cepi", "letvica"),
        "zaklucek_letvica_vijakov_na_lamelo": 1,
        # Čepi so LEVI in DESNI — za vsak konec lamele potrebujemo par
        # (levi + desni čep). Letvica je opcija za zaključevanje PREČNE
        # romb ograje.
        "zaklucek_cepi_levi_in_desni": True,
        # Čepe sicer imamo, vendar so dražji in NE garantirajo, da voda
        # kljub temu ne bo prišla v profil — priporočen je zaključek,
        # ki zakrije odprtine (deske niso polne in imajo odprtine).
        "zaklucek_cepi_opomba": (
            "Čepi so dražji in ne garantirajo, da voda kljub temu ne bo "
            "prišla v profil — priporočamo zaključek, ki zakrije odprtine."),
        # Pokončna postavitev z razmaki med deskami: alu cev v sredini
        # profila je vidna — vsako desko zapri s čepi ali reši v detajlu.
        "opomba_alu_vidna_pokoncno": (
            "Pri pokončni postavitvi z razmaki med deskami je vidna "
            "aluminijasta cev v sredini profila — za estetski zaključek "
            "vsako desko zapri s čepi ali to reši v detajlu konstrukcije."),
        # Votel profil s prekati — potrebne drenažne luknje (WOODCORE).
        "drenazne_luknje": True,
        # Pokončna ograja (navodila): razmak med vodoravnima cevema največ
        # 110 cm; na vodoravne cevi se zmontira kotnik, skozi katerega se
        # pritrjuje romb (skrito vijačenje).
        "pokoncna": {
            "razmak_max_vodoravne_cevi_mm": 1100.0,
            "skrito_vijacenje": True,
            "kotnik_na_vodoravne_cevi": True,
        },
    },
    "DESKA-150": {
        "ime": "DESKA-150",
        "tip": "deska",
        "sirina_profila_mm": 150,          # terasna deska
        "dimenzija_mm": (150, 25),
        "st_barv": 7,                   # barvni odtenki
        "st_povrsin": 3,                # 3 površine (Klasik, Rustik …)
        "barve": ("Amazon wood", "Ash wood", "Golden teak", "Burma teak",
                  "Oak wood", "Rustic oak", "Rustic walnut"),
        # Dvostranska: ena stran rebra bolj na gosto, druga na široko;
        # Rustic: ena stran gladka, druga gosto rebričena.
        "dvostranska_rebra": True,
        # Votel terasni profil s prekati — drenažne luknje (WOODCORE);
        # konce zapira zaključni pokrovček.
        "drenazne_luknje": True,
        "zakljucki": ("zaključni pokrovček",),
        "nakupne_dolzine_mm": (4000, 2200),  # odžaga se po meri
        "pritrditev_od_spredaj": True,     # skozi desko — vijaki VIDNI na licu
        "vrtina_odmik_mm": 1.0,            # predvrtje: luknja = vijak + 1 mm
        "lega_vijaka": "v sredino deske, kjer je rebro v profilu",
        "razmak_max_stebriki_mm": 1400.0,
        "razmak_opomba": "133–140 cm",     # navodila: „maksimalna razdalja“
        # Prečna montaža desk: 133–140 cm (povzetek strani navaja
        # 130 cm — ohranjeno 133–140 cm).
        "razmak_max_stebriki_precna_mm": 1400.0,
    },
    "DESKA-128": {
        "ime": "DESKA-128",
        "tip": "deska",
        "sirina_profila_mm": 128,          # polna deska
        # 16,5 mm (stran Pregradne stene); drug vir navaja 16 mm.
        "dimenzija_mm": (128, 16.5),
        "uporaba": ("pokončna", "prečna"),  # pokončno ALI prečno
        "st_barv": 6,                   # barvni odtenki (slika: 6; besedilo strani: 5)
        "barve": ("Amazon wood", "Ash wood", "Burma teak", "Oak wood",
                  "Rustic oak", "Rustic walnut"),
        # POLNA deska — BREZ prekatov (potrjeno s fotografijo profila),
        # zato drenažne luknje NE veljajo.
        "nakupne_dolzine_mm": (2200,),     # odžaga se po meri
        "pritrditev_od_spredaj": True,     # skozi desko — vijaki VIDNI na licu
        "vrtina_odmik_mm": 1.0,            # predvrtje: luknja = vijak + 1 mm
        "lega_vijaka": "v sredino deske",
        # Vodoravna ograja: razmak stebričkov 180 cm do 150 cm višine
        # ograje; pri višjih ograjah največ 150 cm.
        "razmak_max_stebriki_mm": 1800.0,
        "razmak_max_stebriki_visoke_mm": 1500.0,
        "visina_meja_stebriki_mm": 1500.0,
        "razmak_opomba": "180 cm do 150 cm višine / 150 cm višje",
        # Prečna montaža desk: 110 cm (vir: prečne ograje + prečne
        # pregrade) — POKONČNA montaža uporablja 180/150 zgoraj.
        "razmak_max_stebriki_precna_mm": 1100.0,
        # Pokončna ograja: razmak med vodoravnima cevema največ 100 cm.
        "pokoncna": {"razmak_max_vodoravne_cevi_mm": 1000.0},
    },
    "POLNA DESKA 57/32": {
        "ime": "POLNA DESKA 57/32",
        "tip": "deska",
        "sirina_profila_mm": 57,           # montira se na širino 57 ALI 32
        "montazne_sirine_mm": (57, 32),
        "nakupne_dolzine_mm": (5800,),     # dolžina 5,8 m
        "skrito_vijacenje": True,          # obe širini — skrito vijačenje
        "dimenzija_mm": (57, 32),
        "uporaba": ("pokončna",),          # deske za POKONČNO ograjo
        "st_barv": 4,                   # barvni odtenki (slika: 4; besedilo strani: 3)
        "barve": ("Amazon wood", "Oak wood", "Rustic oak", "Rustic walnut"),
        "vijak": "RF vijak skozi cev iz zadnje strani",
        "vijak_dolzina_opis": "približno 2/3 globine profila",
        # POSEBNOST vrtanja (obratno kot pri DESKA-100/128!):
        #   v KOMPOZIT luknja MANJŠA od vijaka (vijak se zareže v material),
        #   v KONSTRUKCIJO luknja VEČJA od vijaka (raztezanje materiala).
        "vrtina_kompozit_manjsa": True,
        "vrtina_konstrukcija_vecja": True,
        # Vodoravna ograja: razmak stebričkov največ 150 cm NE GLEDE na
        # višino ograje; nosilci (vodoravne cevi) največ 100 cm (pokončna).
        "razmak_max_stebriki_mm": 1500.0,
        "razmak_opomba": "150 cm (ne glede na višino)",
        # Pokončna ograja: razmak med vodoravnima cevema največ 100 cm.
        "pokoncna": {
            "razmak_max_vodoravne_cevi_mm": 1000.0,
            "skrito_vijacenje": True,
        },
    },
    "POLNA DESKA 100": {
        "ime": "POLNA DESKA 100",
        "tip": "deska",
        "sirina_profila_mm": 100,          # polna deska
        "dimenzija_mm": (100, 12),
        "uporaba": ("pokončna",),          # SAMO za pokončno ograjo!
        "st_barv": 8,                   # barvni odtenki
        "barve": ("Amazon wood", "Ash wood", "Golden teak", "Burma teak",
                  "Oak wood", "White", "Rustic oak", "Rustic walnut"),
        "nakupne_dolzine_mm": (5800,),     # dolžina 5,8 m
        "pritrditev_od_spredaj": True,     # skozi desko — vijaki VIDNI na licu
        "vrtina_odmik_mm": 1.0,            # predvrtje: luknja = vijak + 1 mm
        "lega_vijaka": "v sredino deske",
        # Vodoravna ograja: razmak stebričkov 180 cm do 150 cm višine
        # ograje; pri višjih ograjah največ 150 cm.
        "razmak_max_stebriki_mm": 1800.0,
        "razmak_max_stebriki_visoke_mm": 1500.0,
        "visina_meja_stebriki_mm": 1500.0,
        "razmak_opomba": "180 cm do 150 cm višine / 150 cm višje",
        # Pokončna ograja: razmak med vodoravnima cevema največ 80 cm.
        "pokoncna": {"razmak_max_vodoravne_cevi_mm": 800.0},
    },
    "KUBO 80/42": {
        "ime": "KUBO 80/42",
        "tip": "kubo",
        "sirina_profila_mm": 80,
        "dimenzija_mm": (80, 42),
        "uporaba": ("pokončna",),          # pokončne pregradne stene
        "st_barv": 4,
        "barve": ("Amazon wood", "Oak wood", "Rustic oak", "Rustic walnut"),
        "nakupne_dolzine_mm": (5800, 5000),  # 5000 samo Amazon Wood /
                                          # Rustic Walnut
        "skrito_vijacenje": True,          # pritrditev z zadnje strani
        # Montaža na vidno širino 80 mm ali 42 mm.
        "montazne_sirine_mm": (80, 42),
        # V kubo profil se vstavi surova ali ELOKSIRANA alu cev; za
        # montažo na prostem je obvezna eloksirana (zgornji pokrovček
        # sam ne zaščiti pred vdorom vlage). Izbira vpliva na ceno in
        # razpon konstrukcije.
        "alu_cevi_mm": ((20, 60, 2), (25, 25, 2), (20, 20, 2)),
        "alu_opomba": (
            "Za montažo na prostem obvezno ELOKSIRANA alu cev — zgornji "
            "pokrovček sam ne zagotovi zaščite pred vdorom vlage."),
        # Konstrukcija je lahko vpetja samo zgoraj in spodaj (brez
        # sredinske horizontalne povezave) ob pravilni izbiri ojačitve:
        "razpon_brez_ojacitve_mm": 1200,   # do 120 cm brez ojačitve
        "razpon_ojacitev_20x60x2_mm": 2600.0,  # 120–260 cm → 20×60×2
        "razpon_opomba": (
            "Nad 260 cm močnejša aluminijasta ali rostfrei cev — izbira "
            "glede na razpon in izvedbo konstrukcije."),
        # Razmak med kubo letvicami je poljuben (po želenem videzu);
        # razmak med vodoravnima cevema je odvisen od vrste alu cevi.
        "razmak_letvic": "poljuben (po želenem videzu pregrade)",
    },
}
MONTAZA_ROMB = MONTAZE_PROFILAV["ROMB 67"]  # združljivost — isti vir podatkov

# Značilnosti pritrjevanja desk na konstrukcijo (navodila proizvajalca):
# odmik vijaka od ROBA REZA. Velja za vse profile.
Pritrditev_DESK = {
    "odmik_vijak_min_mm": 30.0,             # minimalen odmik od roba reza
    "odmik_vijak_max_na_plosco_mm": 150.0,  # konstrukcija montirana NA
    # ploščo (balkon, dvoriščna ograja)
    "odmik_vijak_max_bocno_mm": 100.0,      # konstrukcija montirana BOČNO
    # na ploščo (balkon)
}

# Ročaji za WoodCore ograje (elementi). Samostojna prodaja ročajev NI
# možna — ročaj gre vedno skupaj z ograjo.
ROCAJI: dict = {
    "standardni": {
        "ime": "Ročaj za ograjo",
        "dimenzija_mm": (95, 45, 5800),
        "opomba": "na zalogi samo še v WHITE odtenku; ostali odtenki so "
                  "na voljo v polnem profilu",
    },
    "polni": {
        "ime": "Ročaj za ograjo – poln profil (WPC)",
        "dimenzija_mm": (92, 45, 5800),
        "notranja_dimenzija_mm": (55, 30),
    },
    "samostojna_prodaja": False,
    # Vijaki: skozi ročaj v nosilno cev/konstrukcijo od zgoraj navzdol,
    # v razmaku 50 cm; vijak je viden. V ročaj predvrtaj 1 mm večjo
    # luknjo od vijaka (material se razteza).
    "vijak_razmak_mm": 500.0,
    "vrtina_odmik_mm": 1.0,
    "vijak_lega": "od zgoraj navzdol skozi ročaj v konstrukcijo " 
                  "(vijak viden)",
}

# Skladiščenje WPC desk (navodila proizvajalca + FAQ) — pred montažo.
SKLADISCENJE_OPOMBA = (
    "Deske pred montažo hranite v suhem in zračnem prostoru; podlaga naj "
    "bo ravna in čista, deske na odlagalni podlagi po celotni dolžini in "
    "širini, podprte na največ 50 cm. Začasno skladiščenje zunaj mora biti "
    "obvezno pokrito (tveganje zastajanja vlage in plesni). V primeru "
    "neustreznega skladiščenja se reklamacija ne upošteva.")

# WoodCore navodila za montažo (Roksal — WOODCORE_navodila_za_montazo-sl.pdf,
# 9 strani): splošna pravila za VSE WPC elemente (en vir resnice).
WOODCORE: dict = {
    "vir": ("WOODCORE navodila za montažo (Roksal), 9 strani; O materialu; "
            "FAQ"),
    "material": "60 % bambusovih vlaken, 30 % polietilena (HDPE), 10 % aditivov",
    "garancija_let": 15,
    "garancija_izjeme": (
        "težke obremenitve in udarci niso kriti; posvetlitev 5–10 % in "
        "barvne variacije niso krite; neupoštevanje navodil montaže izniči "
        "garancijo"),
    "posvetlitev_prvo_leto": "5–10 % (nato barva ostane enaka)",
    "barve_opomba_dobave": (
        "Zaradi dodajanja naravnega materiala med barvanjem barvni odtenek "
        "med posameznimi dobavami malenkost varira in se lahko razlikuje "
        "od vzorca."),
    "montazna_temp_min_c": 5.0,     # montaža pod 5 °C ni primerna (O materialu)
    "barve_opomba_rustic": (
        "Pri odtenkih Rustic Oak in Rustic Walnut, ki imata večbarvni "
        "videz, lahko odtenek in razpored lis med deskami in serijami "
        "opazneje variirata."),
    "nosilnost_opozorilo": (
        "WoodCore desk se ne sme uporabljati za nosilce, tramove, "
        "podporne stebre ali druge gradbene elemente — neupoštevanje "
        "lahko izniči garancijo."),
    # Drenažne luknje v votlih deskah (voda ne sme zastajati — zmrzne
    # in desko poči).
    "drenazne_luknje": {
        "fi_mm": 4.2,
        "odmik_od_roba_mm": 50,        # cca 5 cm od roba
        "polozaj": "s spodnje strani, v vsak prekat",
        "namen": "voda ne sme zastajati (zmrzne in desko poči)",
    },
    "orodja": (
        "Baterijski vrtalnik (ročni izvijač ne pride v poštev — WPC je "
        "pretrd); rezila Widia (HM); brusni papir granulacija 40 za "
        "praske in poškodovane robove; glavo vijaka ugreznite z grezilom."),
    "vijaki": (
        "Priporočeni so nerjaveči vijaki; dovoljeni tudi drugi standardni "
        "RF vijaki, odporni na rjo in korozijo."),
    "odmik_od_sten_mm": 6,             # min. odmik deske od vseh sten
    "raztezek_na_4m_mm": 12,           # FAQ: 12 mm (-30…+40 °C); PDF: cca 10
    # Razmak med deskami [mm] po temperaturi montaže in dolžini deske.
    # Vir: tabela »Zahteva za zahodno in Vzhodno Evropo« (stran 6).
    # OPOMBA: pri -25 °C je v viru za 1 m tiskano »2,27« — očitna
    # tipkarska napaka za 2,75 (5,5 = 2×2,75; 8,25 = 3×2,75; 11 = 4×2,75).
    # Vrstici 40 °C in 45 °C sta v viru prazni — podatkov ni.
    "tabela_razmakov_mm": (
        (-25, (2.75, 5.5, 8.25, 11.0, 11.0)),
        (-20, (2.5, 5.0, 7.5, 10.0, 10.0)),
        (-15, (2.5, 5.0, 7.5, 10.0, 10.0)),
        (-10, (2.25, 4.5, 6.75, 9.0, 9.0)),
        (-5, (2.0, 4.0, 6.0, 8.0, 8.0)),
        (0, (1.75, 3.5, 5.25, 7.0, 7.0)),
        (5, (1.75, 3.5, 5.25, 7.0, 7.0)),
        (10, (1.5, 3.0, 4.5, 6.0, 6.0)),
        (15, (1.25, 2.5, 3.75, 5.0, 5.0)),
        (20, (1.25, 2.5, 3.75, 5.0, 5.0)),
        (25, (1.0, 2.0, 3.0, 4.0, 4.0)),
        (30, (1.0, 1.5, 2.25, 3.0, 3.0)),
        (35, (1.0, 1.5, 1.8, 2.0, 2.0)),
    ),
}


def razmak_desk_mm(temp_c, dolzina_m):
    """Razmak med WPC deskami [mm] po tabeli WoodCore.

    ``temp_c`` = temperatura montaže (°C) — najbližja vrstica tabele
    (korak 5 °C); ``dolzina_m`` = dolžina deske (m) — linearna
    interpolacija med stolpci 1–5 m, nad 5 m vrednost za 5 m.
    Za temperature zunaj tabele (< -25 °C ali > 35 °C) vrne vrednost
    najbližje vrstice (vir za 40/45 °C nima podatkov).
    """
    tabela = WOODCORE["tabela_razmakov_mm"]
    _temp, vrstica = min(tabela, key=lambda t: abs(t[0] - temp_c))
    if dolzina_m <= 1:
        return float(vrstica[0])
    if dolzina_m >= 5:
        return float(vrstica[4])
    for i in range(4):
        d0, d1 = float(i + 1), float(i + 2)
        if dolzina_m <= d1:
            del_ = (dolzina_m - d0) / (d1 - d0)
            return round(vrstica[i] + del_ * (vrstica[i + 1] - vrstica[i]), 2)
    return float(vrstica[4])


def odmik_vijak_max(pritrditev):
    """Največji odmik vijaka od roba reza za tip konstrukcije (mm).

    'vrh' = konstrukcija montirana NA ploščo (balkon, dvoriščna ograja);
    'bočno' = konstrukcija montirana BOČNO na ploščo (balkon).
    None, če tip konstrukcije ni znan (dokumenti navedejo obe možnosti).
    """
    p = str(pritrditev or "").strip().lower()
    if "bo" in p:                      # bočno
        return Pritrditev_DESK["odmik_vijak_max_bocno_mm"]
    if "vr" in p or "plo" in p:        # vrh / na ploščo
        return Pritrditev_DESK["odmik_vijak_max_na_plosco_mm"]
    return None


def opomba_kratkih_kosov(kosi):
    """Opozorila za kose, v katere ne prideta 2 vijaka (min odmik od roba).

    kosi: iterable terk (oznaka, dolzina_mm, ...); vrne seznam vrstic.
    """
    min_dol = 2 * Pritrditev_DESK["odmik_vijak_min_mm"]
    nap = []
    for k in kosi:
        try:
            ozn, dol = k[0], float(k[1])
        except (IndexError, TypeError, ValueError):
            continue
        if dol < min_dol - 1e-9:
            nap.append(
                f"- OPOZORILO: kos {ozn} ({fmt(dol)} mm) je krajši od "
                f"{fmt(min_dol)} mm — minimalen odmik vijaka od roba reza "
                f"{fmt(Pritrditev_DESK['odmik_vijak_min_mm'])} mm, zato 2 "
                "vijaka ne prideta v kos.")
    return nap


def montaza_profila(profil):
    """Spec montaže iz MONTAZE_PROFILAV za profil; None, če ni v katalogu."""
    p = str(profil or "").upper().replace("-", " ").replace("/", " ")
    if "ROMB" in p:
        return MONTAZE_PROFILAV["ROMB 67"]
    if "KUBO" in p:
        return MONTAZE_PROFILAV["KUBO 80/42"]
    if "57" in p and "32" in p:
        return MONTAZE_PROFILAV["POLNA DESKA 57/32"]
    if "DES" in p or "POLN" in p:          # WoodCore deske
        if "DESKA" in p and "150" in p:
            return MONTAZE_PROFILAV["DESKA-150"]
        if "128" in p:
            return MONTAZE_PROFILAV["DESKA-128"]
        if "100" in p:
            return MONTAZE_PROFILAV["POLNA DESKA 100"]
    return None


def romb_montaza(profil):
    """Spec montaže SAMO za romb (specifična pravila); None za ostale profile."""
    spec = montaza_profila(profil)
    return spec if spec and spec.get("tip") == "romb" else None


def deska_montaza(profil):
    """Spec montaže SAMO za deske (DESKA-150/128, POLNA DESKA …)."""
    spec = montaza_profila(profil)
    return spec if spec and spec.get("tip") == "deska" else None


def pokoncna_pravila(profil):
    """Pravila pokončne ograje iz MONTAZE_PROFILAV; None, če jih ni."""
    spec = montaza_profila(profil)
    return (spec or {}).get("pokoncna") or None


def st_vodoravnih_cevi(deska_h_mm, profil):
    """Najmanjše število vodoravnih cevi (montažnih letev) na polje.

    Navodila (MONTAZE_PROFILAV): razmak med vodoravnima cevema največ
    `razmak_max_vodoravne_cevi_mm`. Cevi so enakomerno razporejene po
    višini desk, tako da so VSE nepodprte razdalje (tudi robovi desk) ≤
    ta razmak: n cevi deli višino na n + 1 razmakov. Brez pravila za
    profil ostane najmanj 2 cevi na polje (doslejšnja izvedba).
    """
    pr = pokoncna_pravila(profil)
    if not pr or not deska_h_mm or deska_h_mm <= 0:
        return 2
    s = float(pr["razmak_max_vodoravne_cevi_mm"])
    return max(2, math.ceil(deska_h_mm / s) - 1)


def romb_zaklucek(vrednost):
    """Normalizira izbiro zaključka ograje: 'cepi', 'letvica' ali '' (ni izbrano)."""
    v = str(vrednost or "").strip().lower()
    if v in ("čepi", "cepi", "s čepi", "s cepi"):
        return "cepi"
    if v in ("letvica", "z letvico", "z letvica"):
        return "letvica"
    return ""


def preveri_razmak_stebriki(razmak_mm, vmesna_povezava=False, profil=None,
                            visina_mm=None, pokoncna=False):
    """Pravila razmika stebričkov iz MONTAZE_PROFILAV; [] če je vse OK.

    Usmerjenost montaže desk je ODLOČILNA — domnevni spor 110 cm proti
    180/150 cm je usmerjenostni (oba podatka sta uradna):
      * prečna ('razmak_max_stebriki_precna_mm'): romb ≤ 1450 mm z
        L-kotnikom LEVO in DESNO; 1450–1800 mm z vmesno povezavo IZ
        ZGORNJE cevi (NI privijačena v tla — 'vmesna_povezava: true');
        ≥ 1800 mm dodatni stebriček. DESKA-128 ≤ 1100 mm; DESKA-150
        ≤ 1400 mm (133–140 cm).
      * pokončna ('razmak_max_stebriki_pokoncna_mm' oziroma
        'razmak_max_stebriki_mm'): 57/32 1500 mm ne glede na višino;
        100/128 1800 mm do 150 cm višine, 1500 mm višje; romb 1500 mm.
    Vmesna povezava je predvidena samo za romb pri prečni montaži.
    """
    spec = montaza_profila(profil)
    if spec is None or razmak_mm is None:
        return []
    if pokoncna:
        limit = spec.get("razmak_max_stebriki_pokoncna_mm",
                         spec.get("razmak_max_stebriki_mm"))
    else:
        limit = spec.get("razmak_max_stebriki_precna_mm",
                         spec.get("razmak_max_stebriki_mm"))
    if limit is None:
        return []  # profil nima pravila za razmak stebričkov
    visoke = (spec.get("razmak_max_stebriki_visoke_mm")
              if pokoncna else None)
    meja = spec.get("visina_meja_stebriki_mm")
    if (visoke is not None and meja is not None
            and visina_mm is not None and visina_mm > meja):
        limit = visoke
    nap = []
    max_vmesna = (spec.get("razmak_max_vmesna_povezava_mm")
                  if not pokoncna else None)
    if max_vmesna is not None:
        if razmak_mm >= max_vmesna:
            nap.append(
                f"Razmak stebričkov {razmak_mm:.0f} mm ≥ "
                f"{max_vmesna:.0f} mm: vmesna povezava ne zadošča — "
                "dodajte še en stebriček.")
        elif razmak_mm > limit and not vmesna_povezava:
            nap.append(
                f"Razmak stebričkov {razmak_mm:.0f} mm presega "
                f"{limit:.0f} mm (dovoljeno z "
                "L-kotnikom levo in desno na stebričku): zmanjšajte razmak "
                "ali vklopite 'vmesna_povezava: true' (vmesna povezava IZ "
                "ZGORNJE cevi, ni privijačena v tla — dovoljeno do "
                f"{max_vmesna:.0f} mm).")
    elif razmak_mm > limit:
        if visina_mm is not None:
            nap.append(
                f"Razmak stebričkov {razmak_mm:.0f} mm presega največji "
                f"dovoljeni {fmt(limit)} mm za {spec['ime']} "
                f"({spec.get('razmak_opomba') or ''}) pri višini ograje "
                f"{fmt(visina_mm)} mm — zmanjšajte razmak (vmesna povezava "
                "za ta profil ni predvidena).")
        else:
            nap.append(
                f"Razmak stebričkov {razmak_mm:.0f} mm presega največji "
                f"dovoljeni za {spec['ime']} "
                f"({spec.get('razmak_opomba') or fmt(limit) + ' mm'}) "
                "— zmanjšajte razmak (vmesna povezava za ta profil ni "
                "predvidena).")
    return nap



def fmt(v):
    """Število brez odvečnih decimalk (2500.0 -> 2500, 47.5 -> 47.5)."""
    return f"{v:g}"


def fmt_vejica(v):
    """Število z decimalko Z VEJICO (slovenski zapis: 4,2 mm)."""
    return f"{v:g}".replace(".", ",")


#: Domača (neuradna) poimenovanja odtenkov, ki jih preverjanje konfiguracije
#: prepozna in preslika na kataloško ime iz ``barve``.
BARVE_ALIAS = {
    "antracit": "Amazon wood",
    "amazon": "Amazon wood",
    "bel": "White",
    "bela": "White",
    "bela barva": "White",
    "hrast": "Oak wood",
    "oak": "Oak wood",
    "jesen": "Ash wood",
    "ash": "Ash wood",
    "oreh": "Rustic walnut",
    "rustik oreh": "Rustic walnut",
    "rustik walnut": "Rustic walnut",   # stran uporablja tudi zapis "Rustik"
    "rustik hrast": "Rustic oak",
}


def ujemanje_barve(barva, spec):
    """Vrne kanonsko ime odtenka iz kataloga za vpisano barvo (ali ``None``).

    Primerjava ne upošteva velikosti črk; prepoznana so tudi domača
    poimenovanja iz :data:`BARVE_ALIAS` (npr. ``"Antracit"`` → ``"Amazon wood"``).
    Odtenek mora biti na voljo za ta profil (npr. ``White`` samo pri POLNI DESKI 100).
    """
    if not barva or not spec or not spec.get("barve"):
        return None
    norm = " ".join(str(barva).split()).casefold()
    for ime in spec["barve"]:
        if ime.casefold() == norm:
            return ime
    zadetek = BARVE_ALIAS.get(norm)
    if zadetek and zadetek in spec["barve"]:
        return zadetek
    return None


def traki_nabava(traki):
    """Število NABAVNIH trakov (desk) po dolžinah: [(dolžina, št. trakov)]."""
    agg: dict = {}
    for B, _ in traki:
        agg[B] = agg.get(B, 0) + 1
    return sorted(agg.items())


def pritrdilo_material(naziv):
    """Material pritrdila iz naziva (Inox / Pocinkano / —)."""
    vz = (naziv or "").lower()
    if "inox" in vz or "a2" in vz or "a4" in vz:
        return "Inox"
    if "pocink" in vz or "galvan" in vz or "verzink" in vz:
        return "Pocinkano"
    return "—"


def vijak_dim(naziv, priv="M8×70"):
    """Dimenzija pritrdila iz naziva (M8×70, Ø8×80, anker M10, M10 …)."""
    vz = naziv or ""
    najdi = (re.search(r"(M\d+\s*[×xX]\s*\d+|Ø\d+\s*[×xX]\s*\d+)", vz)
             or re.search(r"anker\s*(M\d+)", vz, re.IGNORECASE)
             or re.search(r"(M\d+)", vz))
    return (najdi.group(1).replace("x", "×").replace("X", "×")
            .replace(" ", "")) if najdi else priv


# Priporočena sidranja po podlagi (načrt 8) — EDO vir resnice za tabelo
# na montažnem listu in za DETAJL 1 — SIDRANJE na risbi.
# Vrednosti so ≈/OCENJENO („priporočeno — potrdi strokovnjak"),
# NIKOLI „izmerjeno" — nosilnost preveri statik (opomba NI statični izračun).
SIDRANJA_PODLAGE = (
    (("beton",), "Beton C20/25", "anker M10", 60),
    (("zid", "opek", "silikat"), "Zid (opeka/silikat)", "fasadni Ø8", 70),
    (("les", "jeklo"), "Les / jeklo", "vijak Ø8", 40),
)


def priporoceno_sidranje(podlaga):
    """Priporočeno sidranje za podlago (načrt 8).

    Vrne (vrsta_podlage, sidro, globina_mm); za nepoznano ali prazno
    podlago (None, None, None) — brez izmišljanja vrednosti.
    """
    vz = (podlaga or "").strip().lower()
    if not vz:
        return None, None, None
    for kljuci, vrsta, sidro, globina in SIDRANJA_PODLAGE:
        if any(k in vz for k in kljuci):
            return vrsta, sidro, globina
    return None, None, None


# ---------------------------------------------------------------- geometrija ograje
def razpored(m):
    """Vrne (zgornji_profil, spodnji_profil, lamele od spodaj, vrzel, n).

    Profili: (z0, z1) v mm od tal; lamele: seznam (z0, z1).
    Če se lamele ne prilegajo v cono, se število samodejno prilagodi.
    """
    cona = m["visina"] - m["odcep"] - 2 * m["profil_v"]
    n, lv = m["lamele"], m["lamela_v"]
    if n * lv > cona:
        n_nova = max(1, int((cona - 8) // (lv + 8)))
        print(f"[OPOZORILO] {n} lamel × {lv} mm se ne prilega v cono "
              f"{cona:.0f} mm — prilagojeno na {n_nova} lamel.")
        n = n_nova
    if n * lv > cona:
        raise ValueError("Lamele se ne prilegajo v cono — zmanjšaj število "
                         "ali višino lamel.")
    vrzel = (cona - n * lv) / (n - 1) if n > 1 else 0
    zg = (m["visina"] - m["profil_v"], m["visina"])
    sp = (m["odcep"], m["odcep"] + m["profil_v"])
    lamele = []
    z = zg[0]                      # od zgoraj navzdol
    for _ in range(n):
        lamele.append((z - lv, z))
        z -= lv + vrzel
    lamele.reverse()
    return zg, sp, lamele, vrzel, n


def pozicije_nosilcev(sir, raz):
    """Dejanske lege nosilcev (skupni izračun — risba, montažni list,
    kosovnica in količine pritrdil se morajo ujemati, A4/A5).

    Vrne (pozicije [mm], dejanski razmak [mm]). `raz` je največji
    dovoljeni razmak (omejitev, ne kota) — kotira se DEJANSKI razmak.
    """
    n = max(2, math.ceil(sir / raz) + 1)
    rob = min(100.0, sir * 0.1)          # odmik od roba (varen tudi za ozke ograje)
    pozicije = [rob + i * (sir - 2 * rob) / (n - 1) for i in range(n)]
    dejanski = (sir - 2 * rob) / (n - 1)
    return pozicije, dejanski


def razdeli_po_odprtinah(x0, x1, odprtine):
    """Intervali [x0, x1] brez odprtin (odprtine: [(ox0, ox1, oznaka)])."""
    intervali = [(float(x0), float(x1))]
    for odprtina in odprtine:
        ox0, ox1 = odprtina[0], odprtina[1]
        novi = []
        for a, b in intervali:
            if ox1 <= a or ox0 >= b:
                novi.append((a, b))
            else:
                if a < ox0:
                    novi.append((a, ox0))
                if ox1 < b:
                    novi.append((ox1, b))
        intervali = novi
    return [(a, b) for a, b in intervali if b - a > 1e-6]


BARVA_OKOVJA = "#8a8a8a"


# ---------------------------------------------------------------- predloga: pokončna
# KONSTRUKCIJSKA GEOMETRIJA (dokumentirana odločitev — B2; F1/issue #5, O3):
#   - stebri stojijo v enakomernih legah (prvi/zadnji ob robovih ograje),
#   - deske potekajo po POLJIH med stebri (se NE prekrivajo s stebri) in so
#     pritrjene na MONTAŽNE LETVE za deskami (2 na polje), ki so na koncih
#     prišraufane na stebre (2 vijaka na rob deske = 4 na desko),
#   - `vrzel` je uporabnikova zahtevana mera in se uporabi NATANČNO;
#     če se deske s to vrzeljo ne prilegajo v polje, funkcija vrne jasno
#     napako (brez tihega prilagajanja proizvodnega podatka).
def razpored_pokoncna(m):
    """Razpored pokončne ograje: stebri (lega), deske po poljih, višine.

    Vrne dict s centri stebrov, polji (in legami desk po poljih),
    višino desk (visina - rocaj_v - odcep) in natanko uporabnikovo vrzeljo.
    """
    sir, vis = m["sirina"], m["visina"]
    odcep, rv = m["odcep"], m["rocaj_v"]
    ss = m["steber_sirina"]
    ds = m["deska_sirina"]
    vrzel, n = float(m["vrzel"]), int(m["lamele"])
    raz = m["razmak_stebrov"]

    n_stebrov = max(2, math.ceil((sir - ss) / raz) + 1)
    centri = [ss / 2 + i * (sir - ss) / (n_stebrov - 1)
              for i in range(n_stebrov)]

    # polja med stebri
    n_polj = n_stebrov - 1
    sirine_polj = [(sir - ss) / n_polj - ss for _ in range(n_polj)]
    osn = n // n_polj
    dod = n % n_polj
    st_desk_polje = [(osn + 1 if i < dod else osn) for i in range(n_polj)]

    polja = []
    deske_x = []
    for i in range(n_polj):
        levo = centri[i] + ss / 2
        desno = centri[i + 1] - ss / 2
        sirina_polja = sirine_polj[i]
        n_f = st_desk_polje[i]
        potrebno = n_f * ds + max(0, n_f - 1) * vrzel
        if potrebno > sirina_polja + 1e-6:
            raise ValueError(
                f"Deske se ne prilegajo v polje med stebroma "
                f"(polje {i + 1}: {fmt(sirina_polja)} mm) pri {n_f} deskah "
                f"× {fmt(ds)} mm in vrzeli {fmt(vrzel)} mm — potrebnih "
                f"{fmt(potrebno)} mm. Zmanjšaj število desk, vrzel ali "
                "širino desk.")
        rob = (sirina_polja - potrebno) / 2
        x_polje = [levo + rob + j * (ds + vrzel) for j in range(n_f)]
        deske_x.extend(x_polje)
        polja.append({"levo": levo, "desno": desno, "sirina": sirina_polja,
                      "rob": rob, "deske_x": x_polje,
                      "stebri": (centri[i], centri[i + 1])})

    if n > 1 and (vrzel < 5 or vrzel > 30):
        print(f"OPOZORILO: Vrzel med deskami {fmt(vrzel)} mm je izven "
              f"priporočenega območja proizvajalca (5–30 mm).",
              file=sys.stderr)
    deske_h = vis - rv - odcep
    return {"centri": centri, "polja": polja, "deske_x": deske_x,
            "deske_h": deske_h, "vrzel": vrzel, "n_stebrov": n_stebrov,
            "n_desk": n, "rocaj": (vis - rv, vis),
            "deske_z": (odcep, odcep + deske_h)}


# --------------------------------------------------- vrata in prehodi (issue #3)
def vrata_podatki(c):
    """Geometrija in količine vrat/prehodov iz cfg (vir resnice: vrata.py).

    Vrne {vrata, prehodi, odprtine, elementi, napake, opozorila}; uporabljata
    jo obe predlogi (ograda + pokončna), količine, montažni list in DXF.
    """
    m = c.get("mere") or {}
    odcep = m.get("odcep", 0) or 0
    sir = m.get("sirina", 0) or 0
    vis = m.get("visina", 0) or 0
    izhod: dict = {"vrata": [], "prehodi": [], "odprtine": [], "elementi": [],
             "napake": [], "opozorila": []}
    if not (c.get("vrata") or c.get("prehodi")):
        return izhod
    for i, v in enumerate(c.get("vrata") or [], start=1):
        ozn = f"V{i}"
        H_o_v = float(v.get("visina") or 0)
        if H_o_v + odcep > vis + 1e-9:
            izhod["napake"].append(
                f"{ozn}: višina vrat ({fmt(H_o_v)}) z odcepom ({fmt(odcep)}) "
                f"presega višino ograje ({fmt(vis)}).")
            continue
        try:
            g = vrat.geometrija_vrat(v, v.get("sirina", 900), H_o_v)
        except ValueError as e:
            izhod["napake"].append(f"Vrata {i}: {e}")
            continue
        izhod["vrata"].append({"oznaka": ozn, "g": g, "vnos": v,
                               "kosovnica": vrat.kosovnica_vrat(g, ozn)})
        x = g["x"]
        izhod["odprtine"].append((x, x + g["odprtina"]["sirina"], ozn))
        for vr, pod, plast in vrat.elementi_vrat(g):
            if vr == "kvadrat":
                px, py, pw, ph = pod
                izhod["elementi"].append(
                    ("kvadrat", (px + x, py + odcep, pw, ph), plast, ozn))
            elif vr == "crta":
                x1, y1, x2, y2 = pod
                izhod["elementi"].append(
                    ("crta", (x1 + x, y1 + odcep, x2 + x, y2 + odcep), plast, ozn))
            elif vr == "krog":
                cx, cy, dd = pod
                izhod["elementi"].append(
                    ("krog", (cx + x, cy + odcep, dd), plast, ozn))
    for i, p in enumerate(c.get("prehodi") or [], start=1):
        ozn = f"P{i}"
        H_o_p = float(p.get("visina") or 0)
        if H_o_p + odcep > vis + 1e-9:
            izhod["napake"].append(
                f"{ozn}: višina prehoda ({fmt(H_o_p)}) z odcepom ({fmt(odcep)}) "
                f"presega višino ograje ({fmt(vis)}).")
            continue
        try:
            g = vrat.geometrija_prehoda(p, p.get("sirina", 1000), H_o_p)
        except ValueError as e:
            izhod["napake"].append(f"Prehod {i}: {e}")
            continue
        izhod["prehodi"].append({"oznaka": ozn, "g": g, "vnos": p,
                                 "kosovnica": vrat.kosovnica_prehoda(g)})
        x = g["x"]
        izhod["odprtine"].append((x, x + g["odprtina"]["sirina"], ozn))
        for vr, pod, plast in vrat.elementi_prehoda(g):
            px, py, pw, ph = pod
            izhod["elementi"].append(
                ("kvadrat", (px + x, py + odcep, pw, ph), plast, ozn))
    # trki odprtin z nosilci/stebri -> opozorilo (ne blokira)
    lege = []
    if sir > 0 and vis > 0:
        try:
            if (c.get("predloga") or "ograja") == "pokončna":
                ss_p = (m.get("steber_sirina", 60) or 60) / 2.0
                lege = [(x - ss_p, x + ss_p)
                        for x in razpored_pokoncna(m)["centri"]]
            else:
                poz, _razmk = pozicije_nosilcev(
                    sir, m.get("razmak_nosilcev", 1000) or 1000)
                lege = [(x - 40.0, x + 40.0) for x in poz]
        except (ValueError, TypeError, KeyError):
            lege = []
    for a, b, oz in izhod["odprtine"]:
        for pa, pb in lege:
            if pa < b - 1e-9 and pb > a + 1e-9:
                izhod["opozorila"].append(
                    f"{oz}: odprtina seka nosilec/steber "
                    f"({fmt(pa)}–{fmt(pb)} mm) — preveri izvedbo.")
                break
    # issue #6: višino odprtine preverimo DEJANSKO (ne višino ograje)
    visine_odprtin = {e["oznaka"]: e["g"]["odprtina"]["visina"]
                      for e in izhod["vrata"] + izhod["prehodi"]}
    izhod["napake"] += vrat.preveri_odprtine(
        [(a, b - a, visine_odprtin.get(oz, vis), oz)
         for a, b, oz in izhod["odprtine"]], sir, vis)
    return izhod


def privzeto_stevilo_lamel(m):
    """Prilagojeno privzeto število lamel (prečna predloga) — MORA se
    prilegati coni.

    Statična privzeta vrednost (13) je preračunana za privzete mere; ko
    uporabnik spremeni mere, dobi napako za številko, ki je NI vnesel.
    Zato se privzeta vrednost izračuna iz mer — ISTI prag kot razpored.
    """
    try:
        cona = (float(m.get("visina", 0) or 0) - float(m.get("odcep", 0) or 0)
                - 2 * float(m.get("profil_v", 0) or 0))
        lv = float(m.get("lamela_v", 0) or 0)
    except (TypeError, ValueError):
        return 1
    if cona <= 0 or lv <= 0:
        return 1
    return max(1, int((cona - 8) // (lv + 8)))


def normaliziraj_predlogo(v):
    """Ena oblika imena predloge za validacijo in izris ("ograda" = "ograja")."""
    p = str(v or "ograja").strip().lower()
    return "ograja" if p == "ograda" else p


def zdruzi(cfg):
    if cfg is not None and not isinstance(cfg, dict):
        raise ValueError("Konfiguracija mora biti slovar (ključ: vrednost).")
    izhod = dict(PRIVZETO)
    izhod.update(cfg or {})
    pred = normaliziraj_predlogo(izhod.get("predloga"))
    if pred in ("ograja", "pokončna"):
        izhod["predloga"] = pred
    surove = (cfg or {}).get("mere")
    if surove is None:
        surove = {}
    if isinstance(surove, dict):
        mere = {**PRIVZETO["mere"], **surove}
        # Če uporabnik NI podal števila lamel, se privzeta vrednost izračuna
        # iz mer (statična 13 se ob spremembi mer ne prilega in bi uporabnika
        # blokirala s številko, ki je ni vnesel). Če jo podal, ostane njegova
        # vrednost — ta se strogo preveri (brez tihega spreminjanja vhodov).
        if "lamele" not in surove:
            if (izhod.get("predloga") or "ograja") == "ograja":
                mere["lamele"] = privzeto_stevilo_lamel(mere)
    else:
        # preveri_cfg javi jasno napako; tu ne tiho popravljamo
        mere = surove
    izhod["mere"] = mere
    return izhod


def nalozi_konf(pot):
    with open(pot, "r", encoding="utf-8") as f:
        podatki = yaml.safe_load(f)
    if podatki is None:
        podatki = {}
    if not isinstance(podatki, dict):
        raise ValueError("Projektna datoteka mora vsebovati sliko "
                         "(ključ: vrednost), ne seznama.")
    return zdruzi(podatki)


DOVOLJENI_STATUSI = ("V DELU", "ZA POTRDITEV", "IZVEDENO")


def preveri_cfg(cfg):
    """Kontrola pravilnosti PRED izvozom. Vrne seznam napak (prazno = OK).

    Nikoli ne sproži izjeme zaradi slabih tipov: napačna vrednost je
    napaka v seznamu, ne sesutje. YAML namreč lahko npr.
    ``deska_sirina: "100"`` prebere kot niz, uporabnik pa mora dobiti
    jasno napako namesto sledi sklada.
    """
    if not isinstance(cfg, dict):
        return ["Konfiguracija mora biti slovar (ključ: vrednost)."]

    def _num(v):
        """Vrne v, če je realno število (ne bool), sicer None."""
        return v if (isinstance(v, (int, float))
                     and not isinstance(v, bool)
                     and math.isfinite(v)) else None

    def _poz(v):
        """Vrne v, če je pozitivno realno število, sicer None."""
        v = _num(v)
        return v if v is not None and v > 0 else None

    nap = []
    # A6: izklop optimizacije NI podprt — optimiziranega rezultata ni
    # dovoljeno zamenjati z neoptimiziranim ali prikriti.
    for kljuc in ("brez_optimizacije", "brez_zdruzevanja_rezov"):
        if cfg.get(kljuc):
            nap.append(f"Zahteva '{kljuc}' NI podprta: razrez se vedno "
                       "optimizira in združuje reze; neoptimiziranega "
                       "izpisa ne označimo kot optimiziranega.")
    for kljuc in ("optimizacija_rezov", "zdruzevanje_rezov"):
        if cfg.get(kljuc) is False:
            nap.append(f"Zahteva '{kljuc}=false' NI podprta: razrez se vedno "
                       "optimizira; neoptimiziranega izpisa ne označimo "
                       "kot optimiziranega.")
    m = cfg.get("mere", {})
    if not isinstance(m, dict):
        nap.append("'mere' mora biti objekt s številkami "
                   "(npr. sirina: 2500).")
        m = {}
    for k in ("sirina", "visina"):
        if _poz(m.get(k)) is None:
            nap.append(f"Mera '{k}' mora biti pozitivno število.")
    sirina = _poz(m.get("sirina"))
    visina = _poz(m.get("visina"))
    # Merilo se v risbi razčleni z int(...) in deli z njim; "1:0" ali
    # "abc" bi sicer sesul risanje namesto jasne napake.
    if "merilo" in cfg:
        merilo = str(cfg.get("merilo")).strip()
        deli = merilo.split(":")
        kos = deli[-1].strip()
        if (merilo.lower() != "auto"
                and (len(deli) > 2 or not kos.isascii()
                     or not kos.isdecimal() or len(kos) > 9
                     or int(kos) <= 0)):
            nap.append("'merilo' mora biti 'auto' ali '1:N' s pozitivnim "
                       "celim N.")

    # ISO 7200 (Plan 2): status dokumenta — dovoljeni trije statusi;
    # „IZVEDENO" se sme uporabiti šele po terenski potrditvi.
    status = str(cfg.get("status_dokumenta") or "").strip()
    if status and status.upper() not in DOVOLJENI_STATUSI:
        nap.append(f"Status dokumenta '{status}' ni dovoljen — dovoljeni: "
                   + ", ".join(DOVOLJENI_STATUSI) + ".")
    # Načrt 7: revizije — oblika [[rev, datum, opis, izdelal], ...]
    revizije = cfg.get("revizije")
    if revizije is not None:
        if not isinstance(revizije, list):
            nap.append("'revizije' mora biti seznam revizijskih vnosov.")
        else:
            for i, v in enumerate(revizije):
                if (not isinstance(v, (list, tuple)) or len(v) != 4
                        or not str(v[0] or "").strip()):
                    nap.append(
                        f"Revizija {i + 1} mora biti [oznaka, datum, opis, "
                        "izdelal] z izpolnjeno oznako.")
                    break
    odcep = _num(m.get("odcep", 0))
    if odcep is None or odcep < 0:
        nap.append("Mera 'odcep' mora biti nenegativno število.")
        odcep = None
    pokoncna = normaliziraj_predlogo(cfg.get("predloga")) == "pokončna"
    # uporaba profila po navodilih (npr. POLNA DESKA 100 je SAMO za
    # pokončno ograjo, DESKA-128 za pokončno ali prečno)
    spec_up = montaza_profila(cfg.get("profil"))
    if spec_up and spec_up.get("uporaba"):
        if pokoncna and "pokončna" not in spec_up["uporaba"]:
            nap.append(f"Profil {spec_up['ime']} ni namenjen pokončni "
                       "ograji.")
        elif not pokoncna and "prečna" not in spec_up["uporaba"]:
            nap.append(
                f"Profil {spec_up['ime']} je po navodilih proizvajalca samo "
                "za POKONČNO ograjo — uporabite predlogo 'pokončna'.")
    raz = ds = None
    if pokoncna:
        raz = _poz(m.get("razmak_stebrov", 1500))
        if raz is None:
            nap.append("Razmak stebrov mora biti pozitiven.")
        ds = _poz(m.get("deska_sirina", 0))
        if ds is None:
            nap.append("Širina deske mora biti pozitivno število.")
        # navodila: POLNA DESKA 57/32 se montira na širino 57 ALI 32 mm
        spec = montaza_profila(cfg.get("profil"))
        if spec and spec.get("montazne_sirine_mm") and ds is not None:
            dovoljene = spec["montazne_sirine_mm"]
            if not any(abs(ds - float(d)) < 1e-6 for d in dovoljene):
                nap.append(
                    f"Profil {spec['ime']} se montira na širino "
                    + " ali ".join(f"{fmt(d)} mm" for d in dovoljene)
                    + f" — nastavite 'deska_sirina' (trenutno {fmt(ds)} mm).")
    else:
        for klj, napis in (("lamela_v", "Višina lamel"),
                           ("debelina", "Debelina lamel")):
            if _poz(m.get(klj)) is None:
                nap.append(f"Mera '{napis}' mora biti pozitivno število.")
        if _poz(m.get("razmak_nosilcev", 1000)) is None:
            nap.append("Razmak nosilcev mora biti pozitiven.")
        # romb: razmiki stebričkov po navodilih proizvajalca (MONTAZA_ROMB) —
        # preverja se DEJANSKI razmak med nosilci (razmak_nosilcev je le
        # zgornja meja, kotira se dejanski — enako kot na risbi).
        vmesna = cfg.get("vmesna_povezava")
        if vmesna is not None and not isinstance(vmesna, bool):
            nap.append("'vmesna_povezava' mora biti true ali false.")
            vmesna = bool(vmesna)
        razmak_nos = _poz(m.get("razmak_nosilcev", 1000))
        if razmak_nos is not None and sirina is not None:
            try:
                _xs, dejanski = pozicije_nosilcev(sirina, razmak_nos)
            except (ValueError, TypeError, ZeroDivisionError, OverflowError):
                dejanski = razmak_nos
            nap += preveri_razmak_stebriki(dejanski, bool(vmesna),
                                          cfg.get("profil"), visina)
        # zaključek ograje (MONTAZA_ROMB): 'cepi' ali 'letvica'
        if romb_montaza(cfg.get("profil")) and cfg.get("zaklucek") \
                and not romb_zaklucek(cfg.get("zaklucek")):
            nap.append("'zaklucek' mora biti 'cepi' ali 'letvica' "
                       "(zaključek ograje romb).")
    # letvica je opcija za zaključevanje PREČNE romb ograje
    if (pokoncna and romb_montaza(cfg.get("profil"))
            and romb_zaklucek(cfg.get("zaklucek")) == "letvica"):
        nap.append("Zaključna letvica je opcija za prečno romb ograjo — "
                   "za pokončno uporabite 'zaklucek: cepi'.")
    # Odtenek in barvna paleta (imena so kataloška z barvne lestvice).
    # Dovoljeni so tudi risalne barve iz WPC_BARVE in #hex zapis —
    # zavrnjeni so le neznani vnosi (tipkarske napake).
    barva = cfg.get("barva")
    spec_b = montaza_profila(cfg.get("profil"))
    if barva and spec_b and spec_b.get("barve"):
        norm_b = " ".join(str(barva).split()).casefold()
        risalne = {k.casefold() for k in WPC_BARVE}
        if (ujemanje_barve(barva, spec_b) is None
                and norm_b not in risalne
                and not str(barva).lstrip().startswith("#")):
            nap.append(
                f"'barva' {barva!r} ni med odtenki za {spec_b['ime']} "
                f"({', '.join(spec_b['barve'])}) niti med risalnimi "
                "barvami WPC_BARVE.")

    # tabela razmakov WoodCore velja za -25 … 35 °C (40/45 sta prazni)
    if cfg.get("montazna_temp_c") is not None:
        try:
            t_mont = float(cfg["montazna_temp_c"])
        except (TypeError, ValueError):
            nap.append("'montazna_temp_c' mora biti število (°C).")
        else:
            if not -25 <= t_mont <= 35:
                nap.append("'montazna_temp_c' mora biti med -25 in 35 °C "
                           "(tabela WoodCore nima podatkov zunaj tega "
                           "območja).")
    rv = profil_v = steber = None
    if pokoncna:
        rv = _poz(m.get("rocaj_v", 40))
        if rv is None:
            nap.append("Višina ročaja mora biti pozitivno število.")
        if visina is not None and odcep is not None and rv is not None:
            cona = visina - odcep - rv
            if cona <= 0:
                nap.append("Višina ročaja in odcepa presega skupno višino.")
        steber = _poz(m.get("steber_sirina", 60))
        if steber is None:
            nap.append("Širina stebra mora biti pozitivno število.")
        if ds is not None and sirina is not None and steber is not None:
            if ds > sirina - steber:
                nap.append(f"Deska ({ds:.0f} mm) je širša kot razpon ograje "
                           "med stebroma.")
        if raz is not None and steber is not None and raz <= steber:
            nap.append("Razmak stebrov mora biti večji od širine stebra.")
        lamele = _poz(m.get("lamele", 0))
        if lamele is None or lamele < 1:
            nap.append("Število desk mora biti vsaj 1.")
    else:
        profil_v = _poz(m.get("profil_v", 40))
        if profil_v is None:
            nap.append("Višina profila mora biti pozitivno število.")
        lamele = _poz(m.get("lamele", 0))
        if "lamele" in m and lamele is None:
            nap.append("Število lamel mora biti vsaj 1.")
        lamela_v = _poz(m.get("lamela_v", 0))
        if (profil_v is not None and visina is not None
                and odcep is not None):
            cona = visina - odcep - 2 * profil_v
            if cona <= 0:
                nap.append("Višina profilov in odcepa presega skupno višino.")
            elif (lamele is not None and lamela_v is not None
                  and lamele * lamela_v > cona):
                nap.append(f"Lamele se ne prilegajo: {m.get('lamele')} × "
                           f"{m.get('lamela_v')} mm > cona {cona:.0f} mm.")
    vrzel = _num(m.get("vrzel", 20.0))
    if vrzel is None or vrzel < 0:
        nap.append("Vrzel med deskami ne sme biti negativna.")
    kerf = _num(cfg.get("kerf", 3.0))
    if kerf is None or kerf < 0:
        nap.append("Kerf (širina rezila) ne sme biti negativen.")
        kerf = 0.0
    dl = cfg.get("dolzine_deske")
    if dl is None:
        dl = [cfg.get("dolzina_deske", 5800)]
    if not isinstance(dl, (list, tuple)) or not dl:
        nap.append("Dolžine desk morajo biti seznam števil "
                   "(npr. '5800; 4000; 2200').")
        dl = []
    else:
        for x in dl:
            if _num(x) is None or x <= 0:
                nap.append(f"Dolžina deske {x!r} mora biti pozitivno število.")
    # dolžina kosa po predlogi — EN sam vir resnice (A2):
    #   prečna ograja: lamele se režejo na ŠIRINO ograje,
    #   pokončna: deske na višino desk (visina - rocaj_v - odcep).
    if pokoncna:
        if visina is not None and odcep is not None and rv is not None:
            kos_dol = visina - odcep - rv
        else:
            kos_dol = None
    else:
        kos_dol = sirina
    dl_ok = [x for x in dl
             if _num(x) is not None and kos_dol is not None
             and kos_iz_vira(x, kos_dol, kerf) >= 1]
    if kos_dol is not None and kos_dol > 0 and not dl_ok:
        sporocilo = (f"Nobena nabavna dolžina desk ni dovolj velika za kos "
                     f"{kos_dol:.0f} mm (kerf {kerf:g} mm).")
        spec = montaza_profila(cfg.get("profil"))
        if spec and spec.get("nakupne_dolzine_mm"):
            sporocilo += (f" Nakupne dolžine za {spec['ime']}: "
                          + ", ".join(f"{fmt(d)} mm"
                                      for d in spec["nakupne_dolzine_mm"])
                          + " — nastavite 'dolzine_deske'.")
        nap.append(sporocilo)

    # alu palice: ročaj/stebri/U-profili ne smejo presegati tovarniške dolžine
    dl_palice = _num(cfg.get("dolzina_palice", 6000))
    if dl_palice is None or dl_palice <= 0:
        nap.append("Tovarniška dolžina alu palice mora biti pozitivno število.")
        dl_palice = None
    if dl_palice is not None:
        preseganja = []
        if sirina is not None:
            preseganja.append((sirina, "zaključni profil/ročaj"))
        if pokoncna and visina is not None:
            preseganja.append((visina, "steber"))
        for kosa, opis in preseganja:
            if kosa > dl_palice + 1e-9:
                nap.append(f"{opis.capitalize()} ({kosa:.0f} mm) presega "
                           f"tovarniško dolžino palice ({dl_palice:.0f} mm) "
                           "— potreben spoj ali druga dolžina palice.")

    # geometrija pokončne predloge: brez tihega prilagajanja proizvodnih
    # podatkov (B2) — če se deske ne prilegajo, je to napaka, ne popravek.
    if pokoncna and None not in (sirina, visina, odcep, rv, steber, ds,
                                 vrzel, lamele, raz):
        try:
            razpored_pokoncna(m)
        except ValueError as e:
            nap.append(str(e))
        except (KeyError, TypeError, ZeroDivisionError, OverflowError):
            pass  # manjkajoče/nejasne mere že javijo zgornje preverbe
    # razmak stebričkov (stebrov) po navodilih (MONTAZE_PROFILAV) za
    # POKONČNO montažo desk: romb 150 cm (vmesna povezava ni predvidena),
    # 57/32: 150 cm ne glede na višino; 100/128: 180 cm do 150 cm višine,
    # 150 cm višje.
    if (pokoncna and raz is not None and sirina is not None
            and steber is not None):
        try:
            n_st = max(2, math.ceil((sirina - steber) / raz) + 1)
            dejanski_s = (sirina - steber) / (n_st - 1)
        except (ZeroDivisionError, TypeError, ValueError, OverflowError):
            dejanski_s = raz
        nap += preveri_razmak_stebriki(dejanski_s, False,
                                      cfg.get("profil"), visina,
                                      pokoncna=True)
    foto = cfg.get("foto")
    if foto and not isinstance(foto, (str, os.PathLike)):
        nap.append("'foto' mora biti pot do datoteke.")
    elif foto and not os.path.isfile(foto):
        nap.append(f"Fotografija ne obstaja: {foto}")
    # shema v2: segmenti so del DXF izvoza; neznan tip ali slaba oblika
    # bi se sicer tiho izrisala kot pokončna (dxf_izvoz ima else vejo).
    segmenti = cfg.get("segmenti")
    if segmenti is not None:
        if not isinstance(segmenti, (list, tuple)):
            nap.append("'segmenti' mora biti seznam segmentov.")
        else:
            for i, s in enumerate(segmenti, 1):
                if not isinstance(s, dict):
                    nap.append(f"Segment {i} mora biti objekt (dict).")
                    continue
                tip = normaliziraj_predlogo(s.get("tip") or cfg.get("predloga"))
                if tip not in ("ograja", "pokončna"):
                    nap.append(f"Segment {i}: neznan tip {s.get('tip')!r} "
                               "(dovoljeno: ograja, pokončna).")
                mere_s = s.get("mere")
                if mere_s is not None and not isinstance(mere_s, dict):
                    nap.append(f"Segment {i}: 'mere' mora biti objekt.")

    # vrata/prehodi (issue #3) — le če so prisotni (brez vrat ni dodatnih napak)
    vrata = cfg.get("vrata") or []
    prehodi = cfg.get("prehodi") or []
    oblika_ok = True
    for klj, sez in (("vrata", vrata), ("prehodi", prehodi)):
        if not isinstance(sez, (list, tuple)):
            nap.append(f"'{klj}' mora biti seznam vnosov.")
            oblika_ok = False
        elif any(not isinstance(v, dict) for v in sez):
            nap.append(f"Vsak vnos v '{klj}' mora biti slika (dict).")
            oblika_ok = False
    if oblika_ok and (vrata or prehodi):
        try:
            nap += vrata_podatki(cfg)["napake"]
        except (TypeError, ValueError, KeyError, AttributeError) as e:
            nap.append(f"Vrata/prehodi: {e}")
    return nap


