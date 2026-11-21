# -*- coding: utf-8 -*-
"""F5 (issue #5): CNC/proizvodni izvoz — seznami rezov za tračno/kapno žago.

Zgrajeno na razrez.kosov (isti model reza B — ENA resnica o razrezu).
- izvozi_cutlist: CSV s položaji rezov (trak, kos, x-zacetek, x-konec)
- izvozi_gcode: preprost G-code (mm, absolutne koordinate) za žago z
  linearnim pomikom — odprte poti = ČRTE REZA (issue #5: DXF/CNC);

Varnost: G-code je informativen; pred uporabo na stroju ga PREVERI
operater! Program ne pozna zavor, orodja ali realne mehanike žage.
"""
import csv

from razrez import razrez_kosov


def _polozaji(traki, kerf):
    """Iz trakov razreza izračuna položaje kosov (od začetka traku).

    Med kosi je reža kerf (model B: Σd + (n−1)·kerf ≤ B).
    Vrne [(st_traku, B, [(oznaka, dolzina, x_zac, x_kon), ...]), ...]
    """
    izhod = []
    for i, (B, kosi) in enumerate(traki, start=1):
        x = 0.0
        kos_polozaji = []
        for j, (oznaka, dol) in enumerate(kosi):
            kos_polozaji.append((oznaka, dol, x, x + dol))
            x += dol + (kerf if j < len(kosi) - 1 else 0.0)
        izhod.append((i, B, kos_polozaji))
    return izhod


def izvozi_cutlist(kosi, dolzine_zaloge, kerf, pot_csv, barva="", profil=""):
    """CSV seznami rezov (odprte poti = črte reza)."""
    r = razrez_kosov(kosi, dolzine_zaloge, kerf, barva=barva, profil=profil)
    with open(pot_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["trak", "dolzina_traku_mm", "kos", "dolzina_kosa_mm",
                    "x_zacetek_mm", "x_konec_mm"])
        for st, B, kos_polozaji in _polozaji(r["traki"], kerf):
            for oznaka, dol, x0, x1 in kos_polozaji:
                w.writerow([st, f"{B:.1f}", oznaka, f"{dol:.1f}",
                            f"{x0:.1f}", f"{x1:.1f}"])
    return pot_csv, r


def izvozi_gcode(kosi, dolzine_zaloge, kerf, pot_nc, hitrost=300.0,
                 barva="", profil=""):
    """Preprost G-code za žago (mm, G90 absolutno; odprte poti = rezi).

    Za vsak trak: pomik na x-reza (G0), rez (M3/M5 okoli reza), med traki
    pavza (M0). Format je informativen — operater ga mora prilagoditi
    svoji žagi (ni univerzalnega standarda za tračne žage!).
    """
    r = razrez_kosov(kosi, dolzine_zaloge, kerf, barva=barva, profil=profil)
    vrstice = [
        "(TEHNICNA RISBA — CNC izvoz razreza)",
        "(POZOR: informativni G-code — pred uporabo PREVERI operater!)",
        "G21 (mm)",
        "G90 (absolutne koordinate)",
        f"F{float(hitrost):.1f}",
    ]
    for st, B, kos_polozaji in _polozaji(r["traki"], kerf):
        vrstice.append(f"(TRAK {st}: B = {B:.1f} mm)")
        for oznaka, dol, x0, x1 in kos_polozaji:
            # rezi na začetku in koncu kosa (odprte črte reza)
            vrstice.append(f"(KOS {oznaka}: {dol:.1f} mm)")
            vrstice.append(f"G0 X{x0:.3f}")
            vrstice.append("M3 (zacni rez)")
            vrstice.append(f"G1 X{x1:.3f}")
            vrstice.append("M5 (konec reza)")
        vrstice.append("M0 (zamenjaj trak)")
    vrstice.append("M30 (konec)")
    with open(pot_nc, "w", encoding="utf-8") as f:
        f.write("\n".join(vrstice) + "\n")
    return pot_nc, r