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
    07-predracun.pdf         predračun iz kosovnice in cenika (neobvezno)
    08-predracun.csv         predračun, strojno berljivo

Predračun se izdela samo, če je cenik podan (--cene) ali najden v korenu
projekta (cene.yaml). Brez cenika se ne izmišljuje nobena cena.
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
import izracun
import material
import predlog
import tehniska_risba


ZAMENJAVE_KONZOLA = {"≈": "~", "³": "3", "×": "x", "Ø": "fi", "–": "-",
                     "—": "-", "·": "."}


def za_konzolo(besedilo: str) -> str:
    """Prilagodi besedilo kodni strani konzole (Windows cp1250).

    Zapis v datoteke ostane UTF-8; tu zamenjamo le znake, ki jih konzola
    ne zmore (≈, ×, —), da izpis ne pade z UnicodeEncodeError.
    """
    kod = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        besedilo.encode(kod)
        return besedilo
    except UnicodeEncodeError:
        for znak, nadomestek in ZAMENJAVE_KONZOLA.items():
            besedilo = besedilo.replace(znak, nadomestek)
        return besedilo.encode(kod, "replace").decode(kod, "replace")


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


MIN_RAZMAK_STEBROV_MM = 300.0   # ožje ni steber, ampak letev/prečka
MAX_RAZMAK_STEBROV_MM = 5000.0


def _preveri_razmak(rezultat: Rezultat) -> None:
    """Zaznani vertikalci z razmakom < 300 mm niso stebri ograje.

    Zaznavanje na poljubnih fotografijah (balkoni, okna, balustrade) rado
    prešteje letve/prečke kot stebre — takrat je treba to povedati glasno,
    ne pa izpeljati dolžine iz nesmiselnega razmaka.
    """
    razmak = rezultat.mere.get("razmak_stebrov")
    if not razmak or razmak.vrednost_mm is None:
        return
    if MIN_RAZMAK_STEBROV_MM <= razmak.vrednost_mm <= MAX_RAZMAK_STEBROV_MM:
        return
    rezultat.opozorila.append(
        f"Zaznani razmak vertikalnih elementov je {razmak.vrednost_mm:.0f} mm — "
        "to niso stebri ograje (običajno 1000–3000 mm), zato mere niso "
        "uporabne; potreben je ročni vnos mere (--dolzina/--visina).")


def pozeni(pot_fotografije: str, izhod: str, parametri: ParametriNove,
           referenca: tuple[str, float] | None = None,
           visina_mm: float | None = None,
           dolzina_mm: float | None = None,
           cene_pot: str | None = None, stranka: str = "",
           podjetje: str = "", objekt: str = "") -> Rezultat:
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

    # 3b) opozorila zaznave (zavržene mere, negotova zaznava) morajo priti
    # v dokument — sicer uporabnik ne vidi, ZAKAJ je mera neznana
    rezultat.opozorila.extend(o for o in zaznava.opozorila
                               if o not in rezultat.opozorila)
    _preveri_razmak(rezultat)

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
    povzetek = rezultat.povzetek()
    if cene_pot:
        cenik = izracun.preberi_cenik(cene_pot)
        predracun = izracun.sestavi(rezultat, cenik)
        izracun.narisi_predracun(
            predracun, rezultat, os.path.join(izhod, "07-predracun.pdf"),
            podjetje=podjetje, stranka=stranka, objekt=objekt)
        izracun.izvozi_csv(predracun, os.path.join(izhod, "08-predracun.csv"))
        povzetek += "\n\n" + predracun.povzetek()
    with open(os.path.join(izhod, "06-povzetek.txt"), "w",
              encoding="utf-8") as f:
        f.write(povzetek)
    return rezultat


def main(argv=None):
    # cevi ne znajo cp1250: ko izhod ni konzola, piši UTF-8 (konzola ostane
    # privzeto kodiranje — tam Python č/š/ž izpiše pravilno)
    if not sys.stdout.isatty():
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:      # pragma: no cover — <3.7
            pass
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
    p.add_argument("--cene", default=None,
                   help="cenik (cene.yaml); privzeto iz korena projekta")
    p.add_argument("--brez-predracuna", action="store_true",
                   help="ne izdelaj predračuna (samo risba + kosovnica)")
    p.add_argument("--podjetje", default="", help="izvajalec (glava ponudbe)")
    p.add_argument("--stranka", default="", help="stranka (glava ponudbe)")
    p.add_argument("--objekt", default="", help="objekt (glava ponudbe)")
    args = p.parse_args(argv)

    for ime_mere, vrednost in (("--visina", args.visina),
                              ("--dolzina", args.dolzina)):
        if vrednost is not None and vrednost <= 0:
            print(f"NAPAKA: {ime_mere} mora biti pozitivna vrednost v mm "
                  f"(prejeto: {vrednost})", file=sys.stderr)
            return 2
    referenca = None
    if args.referenca:
        try:
            kaj, vrednost = args.referenca.split("=")
            referenca = (kaj.strip(), float(vrednost))
        except ValueError:
            print(f"NAPAKA: --referenca mora biti oblike kaj=mm "
                  f"(prejeto: {args.referenca!r})", file=sys.stderr)
            return 2

    cene_pot: str | None = None
    if not args.brez_predracuna:
        if args.cene:
            if not os.path.isfile(args.cene):
                print(f"NAPAKA: cenik {args.cene!r} ne obstaja — predračuna "
                      "ni mogoče izdelati (brez --cene se ne izmišljuje cen).",
                      file=sys.stderr)
                return 2
            cene_pot = args.cene
        else:
            privzeti = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "cene.yaml")
            if os.path.isfile(privzeti):
                cene_pot = privzeti
            else:
                print("OPOZORILO: cenik cene.yaml ni najden — predračun ne bo "
                      "izdelan (uporabi --cene ali --brez-predracuna).",
                      file=sys.stderr)

    parametri = ParametriNove(tip=args.tip, barva=args.barva)
    try:
        rezultat = pozeni(args.fotografija, args.izhod, parametri,
                          referenca, args.visina, args.dolzina,
                          cene_pot=cene_pot, stranka=args.stranka,
                          podjetje=args.podjetje, objekt=args.objekt)
    except ValueError as e:
        print(f"NAPAKA: {e}", file=sys.stderr)
        return 1

    print(za_konzolo(rezultat.povzetek()))
    print(f"\nIzpisi v: {args.izhod}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())