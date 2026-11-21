"""photo_fence_proposal — samostojen zagon (CLI).

Uporaba:
    python zazeni.py --fotografija stara_ograja.jpg --izhod izhod/
        [--tip wpc_vodoravne_lamele] [--barva antracit]
        [--referenca razmak_stebrov=2000] [--visina 1800] [--dolzina 6000]

Vse se obdela LOKALNO (CPU, brez GPU in brez omrežja). Brez AI modelov.

Izhodne datoteke v --izhod:
    01-zaznava.png        fotografija z označenimi zaznanimi elementi
    02-vizualni-predlog.png  vizualizacija nove ograje (A)
    03-tehniska-risba.pdf    tehnična risba s kotiranjem in statusi (B)
    04-kosovnica.csv         kosovnica / material
    05-povzetek.json         mere s statusi + opozorila (strojno berljivo)
    06-povzetek.txt          človeku prijazen povzetek
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import cv2

from model import ParametriNove, Rezultat
import zaznavanje
import kalibracija
import material
import predlog
import tehniska_risba


def izvozi_kosovnico_csv(rezultat: Rezultat, pot: str) -> str:
    with open(pot, "w", encoding="utf-8", newline="") as f:
        p = csv.writer(f)
        p.writerow(["Naziv", "Material", "Dimenzija", "Kolicina", "Enota",
                    "Status mer", "Opomba"])
        for postavka in rezultat.kosovnica:
            p.writerow([postavka.naziv, postavka.material, postavka.dimenzija,
                        f"{postavka.kolicina:.0f}", postavka.enota,
                        postavka.status_mer, postavka.opomba])
        if rezultat.razrez:
            p.writerow([])
            p.writerow(["RAZREZ (informativen)", "", "", "", "", "", ""])
            for r in rezultat.razrez:
                p.writerow([f"Palica {r['palica_mm']:.0f} mm", "",
                            f"kosi {r['dolzina_kosa_mm']:.0f} mm",
                            f"{r['kosov']}", "kos", "ocenjeno", ""])
            p.writerow(["Odpad (ocena)", "", "",
                        f"{rezultat.odpad_mm:.0f}" if rezultat.odpad_mm
                        is not None else "??", "mm", "ocenjeno", ""])
    return pot


def pozeni(pot_fotografije: str, izhod: str, parametri: ParametriNove,
           referenca: tuple[str, float] | None = None,
           visina_mm: float | None = None,
           dolzina_mm: float | None = None) -> Rezultat:
    os.makedirs(izhod, exist_ok=True)

    # 1) zaznavanje (klasični OpenCV)
    zaznava = zaznavanje.zaznaj(pot_fotografije)
    slika, bgr = zaznavanje.nalozi_sliko(pot_fotografije)
    oznacena = zaznavanje.oznaci_sliko(zaznava, bgr)
    cv2.imwrite(os.path.join(izhod, "01-zaznava.png"), oznacena)

    # 2) kalibracija (najmanjši ročni poseg: ena referenčna mera)
    kal = None
    if referenca:
        kal = kalibracija.kalibriraj_referenca(zaznava, referenca[0],
                                               referenca[1])

    # 3) mere s statusi
    rezultat = Rezultat(zaznava=zaznava, parametri=parametri)
    rezultat.mere = kalibracija.izpelji_mere(zaznava, parametri, kal)

    # ročni potrjeni vnosi (če jih uporabnik poda — štejejo kot IZMERJENO)
    from model import Mera, IZMERJENO
    if visina_mm:
        rezultat.mere["visina_ograje"] = Mera(visina_mm, IZMERJENO,
                                              "potrdil uporabnik (ročni vnos)")
    if dolzina_mm:
        rezultat.mere["dolzina_ograje"] = Mera(dolzina_mm, IZMERJENO,
                                               "potrdil uporabnik (ročni vnos)")

    # 4) material + razrez
    material.izracunaj_material(rezultat)

    # 5) izpisi (A + B)
    predlog.narisi_predlog(rezultat, pot_fotografije,
                           os.path.join(izhod, "02-vizualni-predlog.png"), bgr)
    tehniska_risba.narisi_tehnisko_risbo(rezultat,
                                         os.path.join(izhod, "03-tehniska-risba.pdf"))
    izvozi_kosovnico_csv(rezultat, os.path.join(izhod, "04-kosovnica.csv"))
    with open(os.path.join(izhod, "05-povzetek.json"), "w",
              encoding="utf-8") as f:
        f.write(rezultat.v_json())
    with open(os.path.join(izhod, "06-povzetek.txt"), "w",
              encoding="utf-8") as f:
        f.write(rezultat.povzetek())
    return rezultat


def main(argv=None):
    p = argparse.ArgumentParser(prog="photo_fence_proposal",
                                description="Predlog nove ograje iz fotografije "
                                            "stare (brez AI modelov, lokalno)")
    p.add_argument("--fotografija", required=True, help="fotografija stare ograje")
    p.add_argument("--izhod", default="izhod_pfp", help="izhodna mapa")
    p.add_argument("--tip", default="wpc_vodoravne_lamele",
                   choices=("wpc_vodoravne_lamele", "wpc_pokoncne_deske"))
    p.add_argument("--barva", default="antracit",
                   choices=("antracit", "rjava", "siva", "bela"))
    p.add_argument("--referenca", default=None,
                   help="kalibracija: razmak_stebrov=2000 ali visina_ograje=1800")
    p.add_argument("--visina", type=float, default=None,
                   help="ročno potrjena višina ograje v mm")
    p.add_argument("--dolzina", type=float, default=None,
                   help="ročno potrjena dolžina ograje v mm")
    args = p.parse_args(argv)

    referenca = None
    if args.referenca:
        try:
            kaj, vrednost = args.referenca.split("=")
            referenca = (kaj.strip(), float(vrednost))
        except ValueError:
            print(f"NAPAKA: --referenca mora biti oblike kaj=mm "
                  f"(prejeto: {args.referenca!r})", file=sys.stderr)
            return 2

    parametri = ParametriNove(tip=args.tip, barva=args.barva)
    try:
        rezultat = pozeni(args.fotografija, args.izhod, parametri,
                          referenca, args.visina, args.dolzina)
    except ValueError as e:
        print(f"NAPAKA: {e}", file=sys.stderr)
        return 1

    print(rezultat.povzetek())
    print(f"\nIzpisi v: {args.izhod}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())