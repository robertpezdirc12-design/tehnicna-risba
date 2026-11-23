# -*- coding: utf-8 -*-
"""Poenostavljen statični PREGLED ograje (Plan 6) — informativno.

*** TO NI STATIČNI IZRAČUN IN NI NADOMESTILO ZA POOBLAŠČENEGA INŽENIRJA. ***

Kaj modul JE:
- izračun POTOVANJA („demand“): upogibni moment, zahtevani uporni prerezi
  W in vztrajnostni moment I za ročaj/stebre pri dani obtežbi;
- primerjalne obtežbe iz standardov Z NAVEDENIMI VIRI.

Kaj modul NI (iskreno):
- NE preverja ZMOGLJIVOSTI (capacity) konkretnega profila — tega brez
  certificiranih lastnosti materiala, varnostnih faktorjev (γ), sidranja,
  spojev in utrujenosti NI mogoče pošteno izračunati;
- ne upošteva dinamičnih obtežb, lokalnih učinkov, spojev, sidranja v
  podlago in nacionalnih dodatkov (SI NA) — vrednosti obtežb so iz
  tujih virov (spodaj), SLOVENSKEGA NA nismo preverjali.

Fizika (enostavna, zapisana tukaj za revizijo):
- ročaj kot preprosto podrt nosilec s črtno obtežbo q:
    M = q·L²/8;   W_pot = M / f;   I_pot (uklon L/200) = 5·q·L³·200 / (384·E)
- steber kot konsolno nosilo s silo F = q·L na višini ročaja h:
    M = F·h;   W_pot = M / f
Mere v mm, sile v N (q v N/mm, M v Nmm → W v mm³, I v mm⁴).
"""

# Prag uklona (običajna vrednost za ograje — L/200 ročaja).
PRAG_UKLONA = 200.0

# Primerjalne obtežbe Z VIRI (ne izmišljeno!):
# - BS 6180:2011 tabela 2 (prek Balconette tehnične specifikacije):
#   bivalno 0.74 kN/m / 1.0 kN/m² / 0.5 kN; javno 1.5 / 1.5 / 1.5
# - DIN EN 1991-1-1/NA (nemški NA, prek ChallengingGlass): 0.5 / 1.0 /
#   2.0 kN/m po kategoriji uporabe
# - PD 6688-1-1 tabela 3 (UK/IE NA): A(i) 0.36 (IE 0.50), A(ii–iii) 0.74,
#   C1–C2 1.50 kN/m
OBTEZBE: dict = {
    "bivalno": {
        "crta_kN_m": 0.74,
        "udl_kN_m2": 1.0,
        "tocka_kN": 0.5,
        "vir": "BS 6180:2011 tab. 2 (bivalne kategorije) / PD 6688-1-1",
    },
    "javno": {
        "crta_kN_m": 1.5,
        "udl_kN_m2": 1.5,
        "tocka_kN": 1.5,
        "vir": "BS 6180:2011 tab. 2 (javne kategorije) / PD 6688-1-1 C1–C2",
    },
    "nemski_na": {
        "crta_kN_m": 1.0,
        "udl_kN_m2": 1.0,
        "tocka_kN": 1.0,
        "vir": "DIN EN 1991-1-1/NA (srednja vrednost 0.5/1.0/2.0 po "
               "kategoriji) — PREVERI slovenski NA!",
    },
}

OPOZORILO = (
    "INFORMATIVNI PREGLED — NI STATIČNI IZRAČUN in NI nadomestilo za "
    "pooblaščenega inženirja. Ne upošteva varnostnih faktorjev, dinamike, "
    "utrujenosti, spojev, sidranja in nacionalnih dodatkov. "
    "Vrednosti obtežb so iz tujih virov (BS 6180 / EN 1991-1-1 NA) — "
    "preveri slovenski nacionalni dodatek."
)

# Zapisane formule (revizijsko) — iste kot v funkcijah spodaj.
FORMULE = [
    "ročaj (preprosto podrt nosilec): M = q·L²/8; W_pot = M/f",
    "ročaj (uklon L/200): I_pot = 5·q·L³·200 / (384·E)",
    "steber (konsolno nosilo): F = q·L; M = F·h; W_pot = M/f",
    "veter (uporabnikov tlak p): q [kN/m] = p [kN/m²] · h [m] — enaka "
    "obravnava kot ročaj",
]

# Kontrolni seznam — kaj priloga NE izračuna in mora preveriti inženir.
ODPRTO_ZA_INZENIRJA = [
    "Zmogljivost dejanskega prereza (W, I) proti zahtevanemu minimumu — "
    "po katalogu proizvajalca / certificiranih lastnostih materiala.",
    "Varnostni faktorji (γ) in kombinacije obtežb po EN 1990 / SI NA.",
    "Sidranje v podlago: nosilnost sidra, robne razdalje, vrsta podlage "
    "(beton/les/jeklo) — ETA/izračun.",
    "Veterno breme EN 1991-1-4 (q_p(z)) — NI avtomatizirano; vneseni tlak "
    "je le uporabnikov vhod, ne izračun po standardu.",
    "Dinamika, utrujenost, lokalni učinki, spoji in prečke.",
    "Slovenski nacionalni dodatek (SI NA) — uporabljene obtežbe so iz "
    "tujih virov (BS 6180 / PD 6688 / EN 1991-1-1 NA).",
    "Dejanski razmak stebrov potrdi na risbi in na objektu.",
]


def pregled_rocaj(dolzina_polja_mm, q_kN_m, f_MPa, E_MPa=210000.0):
    """Povpraševanje ročaja: upogibni moment, W_pot in I_pot (uklon L/200).

    ``dolzina_polja_mm`` = razpon ročaja med podporami (stebri),
    ``q_kN_m`` = črtna obtežba (kN/m), ``f_MPa`` = meja plastičnosti
    materiala (npr. 235 za S235; za aluminij VNESI pravo vrednost!),
    ``E_MPa`` = elastični modul (privzeto jeklo 210 000 MPa).

    Vrne dict z M_kNm, W_pot_cm3, I_pot_cm4 + uporabljene enote.
    """
    if dolzina_polja_mm <= 0 or q_kN_m < 0 or f_MPa <= 0 or E_MPa <= 0:
        raise ValueError("Neveljavni vhodi za pregled ročaja.")
    L = float(dolzina_polja_mm)          # mm
    q = float(q_kN_m)                    # kN/m = N/mm
    f = float(f_MPa)                     # N/mm²
    M = q * L * L / 8.0                  # Nmm
    W_pot = M / f                        # mm³
    I_pot = 5.0 * q * L ** 3 * PRAG_UKLONA / (384.0 * E_MPa)   # mm⁴
    return {
        "M_kNm": M / 1e6,
        "W_pot_cm3": W_pot / 1000.0,
        "I_pot_cm4": I_pot / 1e4,
        "L_mm": L, "q_kN_m": float(q_kN_m), "f_MPa": f, "E_MPa": E_MPa,
    }


def pregled_steber(visina_mm, q_kN_m, dolzina_polja_mm, f_MPa):
    """Povpraševanje stebra kot konsolnega nosilca.

    Sila F = q·L (tributarna obtežba polja) deluje na višini ročaja h;
    M = F·h; W_pot = M/f. Ne preverja sidranja in lokalnih učinkov!
    """
    if visina_mm <= 0 or dolzina_polja_mm <= 0 or q_kN_m < 0 or f_MPa <= 0:
        raise ValueError("Neveljavni vhodi za pregled stebra.")
    h = float(visina_mm)
    L = float(dolzina_polja_mm)
    q = float(q_kN_m)
    F = q * L                           # N
    M = F * h                           # Nmm
    return {
        "F_kN": F / 1000.0,
        "M_kNm": M / 1e6,
        "W_pot_cm3": (M / float(f_MPa)) / 1000.0,
        "h_mm": h, "L_mm": L, "q_kN_m": float(q_kN_m), "f_MPa": float(f_MPa),
    }


def povzetek(razmak_stebrov_mm, visina_rocaja_mm, f_MPa=235.0,
             kategorije=("bivalno", "javno")):
    """Besedilni povzetek za prikaz (GUI/CLI) — vse kategorije + opozorilo.

    f_MPa privzeto 235 (S235) — za aluminij/kompozit VNESI pravo vrednost;
    privzeta številka NI trditev o materialu ograje!
    """
    vrstice = [OPOZORILO, ""]
    for kat in kategorije:
        o = OBTEZBE.get(kat)
        if not o:
            continue
        q = o["crta_kN_m"]
        r = pregled_rocaj(razmak_stebrov_mm, q, f_MPa)
        s = pregled_steber(visina_rocaja_mm, q, razmak_stebrov_mm, f_MPa)
        vrstice.append(
            f"[{kat.upper()}] q = {q} kN/m ({o['vir']})")
        vrstice.append(
            f"  ročaj (L={razmak_stebrov_mm:.0f} mm): "
            f"M = {r['M_kNm']:.3f} kNm → W ≥ {r['W_pot_cm3']:.2f} cm³, "
            f"I ≥ {r['I_pot_cm4']:.2f} cm⁴ (uklon L/{PRAG_UKLONA:.0f})")
        vrstice.append(
            f"  steber (h={visina_rocaja_mm:.0f} mm): "
            f"F = {s['F_kN']:.2f} kN → M = {s['M_kNm']:.3f} kNm, "
            f"W ≥ {s['W_pot_cm3']:.2f} cm³")
        vrstice.append("")
    vrstice.append(f"Material: f = {f_MPa} MPa (vneseno/privzeto S235).")
    vrstice.append("Zahtevani W/I sta POTREBNI minimum — preveri, da jih "
                   "tvoj profil presega (katalog proizvajalca).")
    return "\n".join(vrstice)


# ---------- Statčna priloga (plan 16): revizijsko sledljiv izračunski list ----------

def _zahteva(kategorija, q_kN_m, razmak, h_rocaja, f_MPa, E_MPa):
    """Povpraševanje (demand) za eno obtežbeno kategorijo."""
    r = pregled_rocaj(razmak, q_kN_m, f_MPa, E_MPa)
    s = pregled_steber(h_rocaja, q_kN_m, razmak, f_MPa)
    return {
        "kategorija": kategorija,
        "q_kN_m": float(q_kN_m),
        "rocaj": {"M_kNm": r["M_kNm"], "W_pot_cm3": r["W_pot_cm3"],
                  "I_pot_cm4": r["I_pot_cm4"]},
        "steber": {"F_kN": s["F_kN"], "M_kNm": s["M_kNm"],
                   "W_pot_cm3": s["W_pot_cm3"]},
    }


# ---------- Pritrdila iz kataloga mechanical/ (dimenzije Z dokazilom) ----------

# Znane dimenzije -> kratke oznake; ostalo se izpiše surovo (brez ugibanja).
_OZNAKE_DIMENZIJ = {
    "thread_pitch_P_mm": "P",
    "width_across_flats_s_mm": "s",
    "head_height_k_mm": "k",
    "width_across_corners_e_mm": "e",
}


def _mera(vrednost):
    """Eno dimenzijo kataloga v berljiv zapis (nominal/min/max, številka, niz)."""
    if isinstance(vrednost, dict):
        for kljuc, predpona in (("nominal", ""), ("min", "min"), ("max", "max")):
            if isinstance(vrednost.get(kljuc), (int, float)):
                return ("%s %g" % (predpona, vrednost[kljuc])).strip()
        return "; ".join("%s=%s" % (k, vrednost[k]) for k in sorted(vrednost))
    if isinstance(vrednost, (int, float)):
        return "%g" % vrednost
    return str(vrednost)


def _povzetek_dimenzij(vrstica):
    """Kratek povzetek mer katalogske vrstice — LE podatki iz kataloga."""
    deli = []
    if vrstica.get("nominal_diameter"):
        deli.append(str(vrstica["nominal_diameter"]))
    if vrstica.get("length_mm") is not None:
        deli.append("L %g mm" % vrstica["length_mm"])
    dim = vrstica.get("dimenzije") or {}
    for kljuc in _OZNAKE_DIMENZIJ:
        if kljuc in dim:
            deli.append("%s %s mm" % (_OZNAKE_DIMENZIJ[kljuc], _mera(dim[kljuc])))
    for kljuc in sorted(dim):
        if kljuc not in _OZNAKE_DIMENZIJ:
            deli.append("%s %s" % (kljuc, _mera(dim[kljuc])))
    return "; ".join(deli) or "—"


def _provenenca_vrstic(vrstica):
    """Provenenca katalogske vrstice za prilogo (vir + datum dostopa)."""
    return [{"name": v.get("name"), "url": v.get("url"),
             "accessed": v.get("accessed")}
            for v in vrstica.get("provenenca") or []]


def _pritrdila_iz_kataloga(vnosi):
    """Razreši ``cfg["pritrdila_katalog"]`` prek ``mechanical.resolver``.

    Vsak vnos: ``designation``, ``standard``, ``profil`` (+ neobvezna ``vloga``).
    Neznana/manjkajoča vrstica je EKSPlicitna napaka (``NapakaKataloga``) —
    dimenzije pritrdil se nikoli ne izmislijo.
    """
    from mechanical.resolver import NapakaKataloga, razresi   # leniv uvoz

    izhod = []
    for i, vnos in enumerate(vnosi or []):
        if not isinstance(vnos, dict):
            raise NapakaKataloga(
                "pritrdila_katalog[%d]: vnos mora biti objekt z "
                "polji designation/standard/profil" % i)
        vloga = vnos.get("vloga") or "—"
        manjkajoce = [k for k in ("designation", "standard", "profil")
                      if not vnos.get(k)]
        if manjkajoce:
            raise NapakaKataloga(
                "pritrdila_katalog[%d] (vloga %r): manjkajo polja %s"
                % (i, vloga, ", ".join(manjkajoce)))
        try:
            vrstica = razresi(vnos["designation"], vnos["standard"], vnos["profil"])
        except NapakaKataloga as napaka:
            raise type(napaka)(
                "pritrdila_katalog[%d] (vloga %r): %s" % (i, vloga, napaka)
            ) from napaka
        izhod.append({
            "vloga": vloga,
            "profil": vrstica["profil"],
            "standard": vrstica["standard"],
            "designation": vrstica["designation"],
            "mere": _povzetek_dimenzij(vrstica),
            "provenenca": _provenenca_vrstic(vrstica),
            "status": vrstica["status"],
            "vir": vrstica["vir"],
        })
    return izhod


def priloga_podatki(cfg=None, f_MPa=None, E_MPa=None,
                    kategorije=("bivalno", "javno")):
    """Sestavi podatke statične priloge iz konfiguracije projekta (JSON-prijazno).

    ``cfg`` je običajna konfiguracija projekta (mere, stranka, objekt …).
    Neobvezen blok ``cfg["statika"]``: ``f_MPa``, ``E_MPa`` in
    ``veter_kN_m2`` (tlak, ki ga VNESE uporabnik — NI izračun po EN 1991-1-4).
    Neobvezni seznam ``cfg["pritrdila_katalog"]``: vnosi z
    ``designation``/``standard``/``profil`` (+ ``vloga``), razrešeni prek
    ``mechanical.resolver`` → dimenzije pritrdil Z dokazilom (vir + datum).
    """
    cfg = cfg or {}
    m = cfg.get("mere") or {}
    razmak = float(m.get("razmak_stebrov") or m.get("razmak_nosilcev") or 1500.0)
    visina = float(m.get("visina", 1100.0))
    odcep = float(m.get("odcep", 0.0) or 0.0)
    h_rocaja = max(visina - odcep, 1.0)
    nastavitve = cfg.get("statika") or {}
    vnesen_f = f_MPa is not None or "f_MPa" in nastavitve
    f = float(f_MPa if f_MPa is not None else nastavitve.get("f_MPa", 235.0))
    E = float(E_MPa if E_MPa is not None else nastavitve.get("E_MPa", 210000.0))

    obtezbe, zahteve = [], []
    for kat in kategorije:
        o = OBTEZBE.get(kat)
        if not o:
            continue
        q = float(o["crta_kN_m"])
        obtezbe.append({"kategorija": kat, "q_kN_m": q, "vir": o["vir"]})
        zahteve.append(_zahteva(kat, q, razmak, h_rocaja, f, E))

    veter = nastavitve.get("veter_kN_m2")
    if veter:
        p = float(veter)
        if p <= 0:
            raise ValueError("statika.veter_kN_m2 mora biti > 0.")
        q_v = p * h_rocaja / 1000.0   # p [kN/m²] · h [m] → kN/m
        oznaka = "veter (uporabnikov tlak %.2f kN/m²)" % p
        obtezbe.append({
            "kategorija": oznaka, "q_kN_m": q_v,
            "vir": "uporabnikov vhod p·h — NI izračun po EN 1991-1-4",
        })
        zahteve.append(_zahteva(oznaka, q_v, razmak, h_rocaja, f, E))

    return {
        "opozorilo": OPOZORILO,
        "glava": {
            "projekt": cfg.get("ime") or "—",
            "risba_st": cfg.get("risba_st") or "—",
            "stranka": cfg.get("stranka") or "—",
            "objekt": cfg.get("objekt") or "—",
            "izdelal": cfg.get("izdelal") or "—",
            "datum": cfg.get("datum") or "",
        },
        "geometrija": {
            "razmak_stebrov_mm": razmak,
            "visina_rocaja_mm": h_rocaja,
            "visina_ograje_mm": visina,
            "odcep_mm": odcep,
            "vir_mer": "vnos uporabnika (mere ograje) — preveri na objektu",
        },
        "material": {
            "f_MPa": f, "E_MPa": E,
            "opomba": ("PRIVZETO S235 JEKLO; za aluminij/kompozit vnesi "
                       "pravo vrednost!" if not vnesen_f
                       else "vneseno — preveri z dokumentacijo materiala"),
        },
        "obtezbe": obtezbe,
        "zahteve": zahteve,
        "formule": list(FORMULE),
        "odprto_za_inzenirja": list(ODPRTO_ZA_INZENIRJA),
        "pritrdila": {
            "pritrditev": cfg.get("pritrditev") or "—",
            "podlaga": cfg.get("podlaga") or "—",
            "vijak_lamela": cfg.get("vijak_lamela") or "privzeti",
            "vijak_nosilec": cfg.get("vijak_nosilec") or "privzeti",
            "katalog": _pritrdila_iz_kataloga(cfg.get("pritrdila_katalog")),
        },
        "podpis": {"izdelal": cfg.get("izdelal") or "—",
                   "pregledal": "", "odobril": ""},
    }


def pripis_priloge(podatki):
    """Človeško berljiv izpis statične priloge (kopiranje/pregled/revizija)."""
    g, geo, mat = podatki["glava"], podatki["geometrija"], podatki["material"]
    vrstice = [
        "STATIČNA PRILOGA — INFORMATIVNI PREGLED",
        podatki["opozorilo"],
        "",
        "PROJEKT: %s | Št.: %s | Stranka: %s | Objekt: %s | Datum: %s"
        % (g["projekt"], g["risba_st"], g["stranka"], g["objekt"],
           g["datum"] or "—"),
        "GEOMETRIJA: L (razmak stebrov) = %.0f mm; h (višina ročaja) = %.0f mm; "
        "višina ograje = %.0f mm; odcep = %.0f mm"
        % (geo["razmak_stebrov_mm"], geo["visina_rocaja_mm"],
           geo["visina_ograje_mm"], geo["odcep_mm"]),
        "  vir mer: %s" % geo["vir_mer"],
        "MATERIAL: f = %.0f MPa, E = %.0f MPa — %s"
        % (mat["f_MPa"], mat["E_MPa"], mat["opomba"]),
        "",
        "OBLIKOVNE OBTEŽBE:",
    ]
    for o in podatki["obtezbe"]:
        vrstice.append("  [%s] q = %.2f kN/m — vir: %s"
                       % (o["kategorija"].upper(), o["q_kN_m"], o["vir"]))
    vrstice.append("")
    vrstice.append("ZAHTEVE (POTOVANJE — demand; NI zmogljivost profila!):")
    for z in podatki["zahteve"]:
        vrstice.append("  [%s] q = %.2f kN/m"
                       % (z["kategorija"].upper(), z["q_kN_m"]))
        vrstice.append("    ročaj: M = %.3f kNm → W ≥ %.2f cm³, I ≥ %.2f cm⁴ (uklon L/%.0f)"
                       % (z["rocaj"]["M_kNm"], z["rocaj"]["W_pot_cm3"],
                          z["rocaj"]["I_pot_cm4"], PRAG_UKLONA))
        vrstice.append("    steber: F = %.2f kN → M = %.3f kNm, W ≥ %.2f cm³"
                       % (z["steber"]["F_kN"], z["steber"]["M_kNm"],
                          z["steber"]["W_pot_cm3"]))
    vrstice.append("")
    vrstice.append("FORMULE:")
    vrstice.extend("  " + f_ for f_ in podatki["formule"])
    vrstice.append("")
    vrstice.append("ODPRTO ZA POOBLAŠČENEGA INŽENIRJA:")
    vrstice.extend("  [ ] " + o for o in podatki["odprto_za_inzenirja"])
    p = podatki["pritrdila"]
    vrstice.append("")
    vrstice.append("PRITRDILA (prosta konfiguracija — brez kataloškega vira): "
                   "pritrditev %s; podlaga %s; "
                   "vijak lamela↔profil: %s; vijak nosilec↔podlaga: %s"
                   % (p["pritrditev"], p["podlaga"], p["vijak_lamela"],
                      p["vijak_nosilec"]))
    vrstice.append("")
    if p.get("katalog"):
        vrstice.append("PRITRDILA (katalog mechanical/ — dimenzije Z dokazilom):")
        for vr in p["katalog"]:
            vrstice.append("  • %s: %s %s — %s"
                           % (vr["vloga"], vr["standard"], vr["designation"],
                              vr["mere"]))
            for vir in vr["provenenca"]:
                vrstice.append("    vir: %s (dostopano %s)%s"
                               % (vir["name"], vir["accessed"],
                                  "; %s" % vir["url"] if vir.get("url") else ""))
            vrstice.append("    status: %s (katalog: %s)"
                           % (vr["status"], vr["vir"]))
    else:
        vrstice.append("PRITRDILA (katalog): brez kataloških vrstic — "
                       "dimenzije pritrdil so brez kataloškega vira.")
    pod = podatki["podpis"]
    vrstice.append("")
    vrstice.append("PODPISI: Izdelal: %s | Pregledal (pooblaščeni inženir): "
                   "____________ | Odobril: ____________" % pod["izdelal"])
    return "\n".join(vrstice)


def narisi_prilogo(pot_pdf, cfg=None, podatki=None):
    """Nariši A4 statično prilogo (PDF) — ena stran, revizijsko sledljiva."""
    import textwrap

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    podatki = podatki if podatki is not None else priloga_podatki(cfg)
    g, geo, mat = podatki["glava"], podatki["geometrija"], podatki["material"]

    fig = plt.figure(figsize=(8.27, 11.69))          # A4 pokončno
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, 210)
    ax.set_ylim(0, 297)
    ax.axis("off")

    def zavij(x, y, besedilo, max_zn, fs=7.0, barva="#333333", **kw):
        for vrstica in textwrap.wrap(besedilo, width=max_zn) or [""]:
            ax.text(x, y, vrstica, fontsize=fs, ha="left", va="top",
                    color=barva, **kw)
            y -= fs * 0.52
        return y

    # ---- glava ----
    ax.add_patch(plt.Rectangle((12, 266), 186, 22, facecolor="#eceff1",
                               edgecolor="#90a4ae", lw=0.8))
    ax.text(16, 282, "STATIČNA PRILOGA — INFORMATIVNI PREGLED",
            fontsize=12, fontweight="bold", va="center")
    ax.text(16, 273.5, "%s | Št.: %s | %s"
            % (g["projekt"], g["risba_st"], g["datum"] or "—"),
            fontsize=8.5, va="center", color="#37474f")
    ax.text(194, 282, "Stranka: %s" % g["stranka"], fontsize=8,
            ha="right", va="center")
    ax.text(194, 274.5, "Objekt: %s" % g["objekt"], fontsize=8,
            ha="right", va="center")

    # ---- opozorilo (rdeče) ----
    y = zavij(12, 259, podatki["opozorilo"], 108, fs=7.0, barva="#b71c1c")

    # ---- vhodni podatki ----
    y -= 3
    ax.text(12, y, "VHODNI PODATKI:", fontsize=9, fontweight="bold")
    y -= 5
    y = zavij(14, y, "Geometrija: L (razmak stebrov) = %.0f mm; h (višina ročaja) "
                    "= %.0f mm; višina ograje = %.0f mm; odcep = %.0f mm. %s"
              % (geo["razmak_stebrov_mm"], geo["visina_rocaja_mm"],
                 geo["visina_ograje_mm"], geo["odcep_mm"], geo["vir_mer"]),
              112, fs=7.2)
    y = zavij(14, y - 1, "Material: f = %.0f MPa, E = %.0f MPa — %s"
              % (mat["f_MPa"], mat["E_MPa"], mat["opomba"]), 112, fs=7.2)

    # ---- obtežbe + zahteve ----
    y -= 3
    ax.text(12, y, "OBLIKOVNE OBTEŽBE IN ZAHTEVE (POTOVANJE — demand):",
            fontsize=9, fontweight="bold")
    y -= 5.5
    for z in podatki["zahteve"]:
        vir = next((o["vir"] for o in podatki["obtezbe"]
                    if o["kategorija"] == z["kategorija"]), "")
        y = zavij(14, y, "[%s] q = %.2f kN/m — %s"
                  % (z["kategorija"].upper(), z["q_kN_m"], vir), 112,
                  fs=7.2, barva="#1565c0")
        y = zavij(16, y, "ročaj: M = %.3f kNm → W ≥ %.2f cm³, I ≥ %.2f cm⁴ "
                        "(uklon L/%.0f)"
                  % (z["rocaj"]["M_kNm"], z["rocaj"]["W_pot_cm3"],
                     z["rocaj"]["I_pot_cm4"], PRAG_UKLONA), 112, fs=7.0)
        y = zavij(16, y, "steber: F = %.2f kN → M = %.3f kNm, W ≥ %.2f cm³"
                  % (z["steber"]["F_kN"], z["steber"]["M_kNm"],
                     z["steber"]["W_pot_cm3"]), 112, fs=7.0)
        y -= 1.2

    # ---- formule ----
    y -= 1
    ax.text(12, y, "FORMULE (revizijsko):", fontsize=9, fontweight="bold")
    y -= 4.5
    for f_ in podatki["formule"]:
        y = zavij(14, y, f_, 118, fs=6.8, barva="#455a64")

    # ---- kontrolni seznam ----
    y -= 2
    ax.text(12, y, "ODPRTO ZA POOBLAŠČENEGA INŽENIRJA:", fontsize=9,
            fontweight="bold")
    y -= 5
    for o in podatki["odprto_za_inzenirja"]:
        y = zavij(14, y, "[ ] " + o, 108, fs=7.0)
        y -= 0.6

    # ---- pritrdila (prosta konfiguracija + katalog mechanical/) ----
    p = podatki["pritrdila"]
    y -= 2
    y = zavij(12, y, "PRITRDILA (prosta konfiguracija — brez kataloškega vira): "
                    "pritrditev %s; podlaga %s; "
                    "vijak lamela↔profil: %s; vijak nosilec↔podlaga: %s"
              % (p["pritrditev"], p["podlaga"], p["vijak_lamela"],
                 p["vijak_nosilec"]), 118, fs=6.8, barva="#455a64")
    if p.get("katalog"):
        y = zavij(12, y - 1,
                  "PRITRDILA (katalog mechanical/ — dimenzije Z dokazilom):",
                  118, fs=6.8, barva="#455a64")
        for vr in p["katalog"]:
            y = zavij(14, y, "%s: %s %s — %s"
                      % (vr["vloga"], vr["standard"], vr["designation"],
                         vr["mere"]), 118, fs=6.6, barva="#455a64")
            for vir in vr["provenenca"]:
                y = zavij(16, y, "vir: %s (dostopano %s)"
                          % (vir["name"], vir["accessed"]), 118, fs=6.2,
                          barva="#607d8b")
    else:
        y = zavij(12, y - 1, "PRITRDILA (katalog): brez kataloških vrstic — "
                             "dimenzije pritrdil so brez kataloškega vira.",
                  118, fs=6.8, barva="#455a64")

    # ---- opombe inženirja (prostor za ročne zapise) ----
    y -= 5
    ax.text(12, y, "OPOMBE INŽENIRJA:", fontsize=9, fontweight="bold")
    y -= 6
    while y > 40:
        ax.plot([14, 196], [y, y], color="#cfd8dc", lw=0.6)
        y -= 8

    # ---- podpisni blok ----
    ax.text(12, 28, "Izdelal: %s" % podatki["podpis"]["izdelal"], fontsize=8.5)
    ax.text(12, 18, "Pregledal (pooblaščeni inženir): ______________________",
            fontsize=8.5)
    ax.text(120, 18, "Odobril: ______________________", fontsize=8.5)

    with PdfPages(pot_pdf) as pdf:
        pdf.savefig(fig)
    plt.close(fig)
    return pot_pdf


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Poenostavljen statični pregled ograje — informativno "
                    "(NI statični izračun!).")
    parser.add_argument("L", nargs="?", type=float, default=1500.0,
                        help="razmak stebrov/polja (mm)")
    parser.add_argument("h", nargs="?", type=float, default=1100.0,
                        help="višina ročaja (mm)")
    parser.add_argument("--priloga", metavar="PROJEKT_YAML",
                        help="sestavi A4 statično prilogo iz konfiguracije projekta")
    parser.add_argument("-o", "--izhod", metavar="PDF",
                        help="izhodna PDF datoteka priloge "
                             "(privzeto STAT-priloga.pdf)")
    argumenti = parser.parse_args()
    if argumenti.priloga:
        import yaml

        with open(argumenti.priloga, encoding="utf-8") as dat:
            konfiguracija = yaml.safe_load(dat) or {}
        pot = argumenti.izhod or "STAT-priloga.pdf"
        narisi_prilogo(pot, konfiguracija)
        print(pripis_priloge(priloga_podatki(konfiguracija)))
        print("\nPriloga zapisana: %s" % pot)
    else:
        print(povzetek(argumenti.L, argumenti.h))