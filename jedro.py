# -*- coding: utf-8 -*-
"""Jedro (core) — geometrija, konfiguracija, validacija, pomožne funkcije.

F2 (issue #5): izločeno iz monolita risba.py BREZ spremembe vedenja;
risba.py javno API ohranja prek re-exportov. Brez risanja (matplotlib).
"""
import math
import re
import sys

import yaml

from razrez import kos_iz_vira

import vrata as vrat

BARVA_LAMEL = "#3e4a5e"  # privzeta barva lamel (iz risba.konstante)

PRIVZETO = {
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



def fmt(v):
    """Število brez odvečnih decimalk (2500.0 -> 2500, 47.5 -> 47.5)."""
    return f"{v:g}"


def traki_nabava(traki):
    """Število NABAVNIH trakov (desk) po dolžinah: [(dolžina, št. trakov)]."""
    agg = {}
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
    H_o = vis - odcep
    izhod = {"vrata": [], "prehodi": [], "odprtine": [], "elementi": [],
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


def zdruzi(cfg):
    izhod = dict(PRIVZETO)
    izhod.update(cfg or {})
    izhod["mere"] = {**PRIVZETO["mere"], **(cfg or {}).get("mere", {})}
    return izhod


def nalozi_konf(pot):
    with open(pot, "r", encoding="utf-8") as f:
        podatki = yaml.safe_load(f) or {}
    return zdruzi(podatki)


def preveri_cfg(cfg):
    """Kontrola pravilnosti PRED izvozom. Vrne seznam napak (prazno = OK)."""
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
    for k in ("sirina", "visina"):
        v = m.get(k)
        if not isinstance(v, (int, float)) or v <= 0:
            nap.append(f"Mera '{k}' mora biti pozitivno število.")
    odcep = m.get("odcep", 0)
    if not isinstance(odcep, (int, float)) or odcep < 0:
        nap.append("Mera 'odcep' ne sme biti negativna.")
    if cfg.get("predloga") == "pokončna":
        raz = m.get("razmak_stebrov", 1500)
        if not isinstance(raz, (int, float)) or raz <= 0:
            nap.append("Razmak stebrov mora biti pozitiven.")
        ds = m.get("deska_sirina", 0)
        if not isinstance(ds, (int, float)) or ds <= 0:
            nap.append("Širina deske mora biti pozitivno število.")
    else:
        for klj, napis in (("lamela_v", "Višina lamel"),
                           ("debelina", "Debelina lamel")):
            v = m.get(klj)
            if not isinstance(v, (int, float)) or v <= 0:
                nap.append(f"Mera '{napis}' mora biti pozitivno število.")
        raz = m.get("razmak_nosilcev", 1000)
        if not isinstance(raz, (int, float)) or raz <= 0:
            nap.append("Razmak nosilcev mora biti pozitiven.")
    if cfg.get("predloga") == "pokončna":
        rv = m.get("rocaj_v", 40)
        cona = m.get("visina", 0) - odcep - rv
        if cona <= 0:
            nap.append("Višina ročaja in odcepa presega skupno višino.")
        ds = m.get("deska_sirina", 0)
        if ds > m.get("sirina", 0) - m.get("steber_sirina", 60):
            nap.append(f"Deska ({ds:.0f} mm) je širša kot razpon ograje "
                       "med stebroma.")
        if m.get("razmak_stebrov", 0) <= m.get("steber_sirina", 60):
            nap.append("Razmak stebrov mora biti večji od širine stebra.")
        if m.get("lamele", 0) < 1:
            nap.append("Število desk mora biti vsaj 1.")
        vrzel = m.get("vrzel", 20.0)
        if not isinstance(vrzel, (int, float)) or vrzel < 0:
            nap.append("Vrzel med deskami ne sme biti negativna.")
    else:
        cona = m.get("visina", 0) - odcep - 2 * m.get("profil_v", 40)
        if cona <= 0:
            nap.append("Višina profilov in odcepa presega skupno višino.")
        elif m.get("lamele", 0) * m.get("lamela_v", 0) > cona:
            nap.append(f"Lamele se ne prilegajo: {m.get('lamele')} × "
                       f"{m.get('lamela_v')} mm > cona {cona:.0f} mm.")
    kerf = cfg.get("kerf", 3.0)
    if not isinstance(kerf, (int, float)) or kerf < 0:
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
            if not isinstance(x, (int, float)) or x <= 0:
                nap.append(f"Dolžina deske {x!r} mora biti pozitivno število.")
    # dolžina kosa po predlogi — EN sam vir resnice (A2):
    #   prečna ograja: lamele se režejo na ŠIRINO ograje,
    #   pokončna: deske na višino desk (visina - rocaj_v - odcep).
    if cfg.get("predloga") == "pokončna":
        kos_dol = (m.get("visina", 0) - m.get("odcep", 0)
                   - m.get("rocaj_v", 40))
    else:
        kos_dol = m.get("sirina", 0)
    dl_ok = [x for x in dl
             if isinstance(x, (int, float))
             and kos_iz_vira(x, kos_dol, kerf) >= 1]
    if kos_dol > 0 and not dl_ok:
        nap.append(f"Nobena nabavna dolžina desk ni dovolj velika za kos "
                   f"{kos_dol:.0f} mm (kerf {kerf:g} mm).")

    # alu palice: ročaj/stebri/U-profili ne smejo presegati tovarniške dolžine
    dl_palice = cfg.get("dolzina_palice", 6000)
    if isinstance(dl_palice, (int, float)) and dl_palice > 0:
        preseganja = [(m.get("sirina", 0), "zaključni profil/ročaj")]
        if cfg.get("predloga") == "pokončna":
            preseganja.append((m.get("visina", 0), "steber"))
        for kosa, opis in preseganja:
            if isinstance(kosa, (int, float)) and kosa > dl_palice + 1e-9:
                nap.append(f"{opis.capitalize()} ({kosa:.0f} mm) presega "
                           f"tovarniško dolžino palice ({dl_palice:.0f} mm) "
                           "— potreben spoj ali druga dolžina palice.")

    # geometrija pokončne predloge: brez tihega prilagajanja proizvodnih
    # podatkov (B2) — če se deske ne prilegajo, je to napaka, ne popravek.
    if cfg.get("predloga") == "pokončna":
        try:
            razpored_pokoncna(m)
        except ValueError as e:
            nap.append(str(e))
        except (KeyError, TypeError):
            pass  # manjkajoče mere že javijo spodnji preverbi
    if cfg.get("foto") and not os.path.isfile(cfg["foto"]):
        nap.append(f"Fotografija ne obstaja: {cfg['foto']}")
    # vrata/prehodi (issue #3) — le če so prisotni (brez vrat ni dodatnih napak)
    if cfg.get("vrata") or cfg.get("prehodi"):
        try:
            nap += vrata_podatki(cfg)["napake"]
        except (TypeError, ValueError, KeyError) as e:
            nap.append(f"Vrata/prehodi: {e}")
    return nap


