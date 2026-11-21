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
OBTEZBE = {
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


if __name__ == "__main__":
    import sys
    L = float(sys.argv[1]) if len(sys.argv) > 1 else 1500.0
    h = float(sys.argv[2]) if len(sys.argv) > 2 else 1100.0
    print(povzetek(L, h))