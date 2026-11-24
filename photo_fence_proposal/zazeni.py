"""photo_fence_proposal — samostojen zagon (CLI).

Uporaba:
    python zazeni.py --fotografija stara_ograja.jpg --izhod izhod/
        [--tip wpc_vodoravne_lamele] [--barva antracit]
        [--referenca razmak_stebrov=2000] [--visina 1800] [--dolzina 6000]
        [--vogali 'x1,y1;x2,y2;x3,y3;x4,y4']

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
import marker
import perioda
import vec_posnetkov
import vnos
import rektifikacija
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


def razcleni_vogale(niz: str) -> list[tuple[float, float]]:
    """"x1,y1;x2,y2;x3,y3;x4,y4" → [(x, y) × 4] (TL, TR, BR, BL).

    Razčlenjevanje je skupno z GUI-jem (`vnos.razcleni_kote`), da se
    oblika vnosa ne razlikuje med CLI in oknom.
    """
    return vnos.razcleni_kote(str(niz).replace("\n", ";"))


def _preveri_vogale(tocke: list[tuple[float, float]], sirina: int,
                    visina: int) -> None:
    """Koti morajo biti znotraj slike in ne smejo biti degenerirani."""
    if len(tocke) != 4:
        raise ValueError("za poravnavo so potrebni natanko 4 koti")
    for x, y in tocke:
        if not (0 <= x < sirina and 0 <= y < visina):
            raise ValueError(
                f"kot ({x:.0f}, {y:.0f}) je zunaj slike "
                f"{sirina}×{visina} px — označi kote ograje na fotografiji")
    vogali = [(float(x), float(y)) for x, y in tocke]
    ploscina = 0.0
    for i in range(4):
        x1, y1 = vogali[i]
        x2, y2 = vogali[(i + 1) % 4]
        ploscina += x1 * y2 - x2 * y1
    if abs(ploscina) / 2.0 < 0.01 * sirina * visina:
        raise ValueError("označeni koti pokrivajo premajhno površino "
                         "(manj kot 1 % slike) — označi celotno ograjo")


MIN_RAZMAK_STEBROV_MM = 300.0   # ožje ni steber, ampak letev/prečka
MAX_RAZMAK_STEBROV_MM = 5000.0
RAZMAK_PRIVZET_MM = 2000.0      # privzet razmak, kadar ni zaznan


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


def _uskladi_polja(rezultat: Rezultat, dolzina_mm: float) -> None:
    """Polja in stebri morajo slediti ROČNO potrjeni dolžini, ne zaznavi.

    Zaznava na tujih fotografijah rada prešteje letve (19 »stebrov« na
    4 m ograji): če uporabnik poda --dolzina, velja ta meritev.
    """
    from model import Mera, OCENJENO

    razmak = rezultat.mere.get("razmak_stebrov")
    rm = razmak.vrednost_mm if razmak and razmak.vrednost_mm else None
    vir = "zaznan"
    if not (MIN_RAZMAK_STEBROV_MM <= (rm or 0.0) <= MAX_RAZMAK_STEBROV_MM):
        rm, vir = RAZMAK_PRIVZET_MM, "privzet"
    n_polj = max(1, int(round(dolzina_mm / rm)))
    prej = rezultat.mere.get("stevilo_polj")
    rezultat.mere["stevilo_polj"] = Mera(
        float(n_polj), OCENJENO,
        f"iz ročno potrjene dolžine in razmaka {rm:.0f} mm ({vir})")
    rezultat.mere["stevilo_stebrov"] = Mera(
        float(n_polj + 1), OCENJENO,
        "polja + 1 (iz ročno potrjene dolžine)")
    if prej and prej.vrednost_mm and int(prej.vrednost_mm) != n_polj:
        rezultat.opozorila.append(
            f"Zaznava je našla {int(prej.vrednost_mm) + 1} stebrov, kar ne gre "
            f"skupaj z ročno dolžino {dolzina_mm:.0f} mm — uporabljena je "
            "ročna meritev.")


def _mere_iz_markerja(rezultat: Rezultat, slika, vogali,
                      velikost_markerja_mm: float,
                      visina_mm: float | None,
                      dolzina_mm: float | None) -> None:
    """Dolžina in višina iz natisnjenega markerja v ravnini ograje."""
    from model import Mera, IZRACUNANO

    koti = marker.zaznaj_marker(slika)
    if koti is None:
        rezultat.opozorila.append(
            "Na fotografiji ni najdenega markerja, zato širine iz samih "
            "kotov NI mogoče izračunati (pravokotnik 6:1 od daleč in 3:1 "
            "pod drugim kotom dasta isto sliko). Natisni marker "
            "(`python marker.py --izhod marker.png`), ga prilepi v "
            "ravnino ograje in ponovi postopek — ali pa vnesi --dolzina "
            "ročno.")
        return
    stran = marker.stranica_px(koti)
    if stran < marker.DOBRA_STRANICA_PX:
        rezultat.opozorila.append(
            f"Marker je v sliki velik le {stran:.0f} px (priporočeno "
            f"{marker.DOBRA_STRANICA_PX:.0f}+); meritev je zato lahko "
            "nenatančna (±3 % ali več).")
    mere = marker.izmeri_kvadrilateral(vogali, koti, velikost_markerja_mm)
    if mere is None:
        rezultat.opozorila.append(
            "Meritve iz markerja ni bilo mogoče izračunati (neveljavna "
            "geometrija) — mere ostanejo neznane.")
        return
    sirina, visina = mere
    if dolzina_mm and abs(sirina - dolzina_mm) > 0.05 * dolzina_mm:
        rezultat.opozorila.append(
            f"Marker kaže dolžino {sirina:.0f} mm, ročni vnos "
            f"{dolzina_mm:.0f} mm — uporabljen je ROČNI vnos.")
    elif not dolzina_mm:
        rezultat.mere["dolzina_ograje"] = Mera(
            sirina, IZRACUNANO,
            f"iz markera {velikost_markerja_mm:.0f} mm "
            f"({stran:.0f} px) v ravnini ograje")
    if visina_mm and abs(visina - visina_mm) > 0.05 * visina_mm:
        rezultat.opozorila.append(
            f"Marker kaže višino {visina:.0f} mm, ročni vnos "
            f"{visina_mm:.0f} mm — uporabljen je ROČNI vnos.")
    elif not visina_mm:
        rezultat.mere["visina_ograje"] = Mera(
            visina, IZRACUNANO,
            f"iz markera {velikost_markerja_mm:.0f} mm "
            f"({stran:.0f} px) v ravnini ograje")


def _prestej_elemente(rezultat: Rezultat, slika) -> None:
    """Periodično štetje elementov na poravnani (rektificirani) sliki."""
    from model import Mera, IZRACUNANO

    per = perioda.prestej(perioda.pas_ograje(slika))
    if per is None or per.stevilo < 2:
        rezultat.opozorila.append(
            "Periodičnega ritma na poravnani sliki ni bilo mogoče "
            "zanesljivo določiti — število stebrov ostaja ocena zaznave.")
        return
    n = int(per.stevilo)
    popolno = abs(n - per.pricakovano) <= max(1, int(round(
        0.08 * per.pricakovano)))
    from model import OCENJENO
    status = IZRACUNANO if popolno else OCENJENO
    rezultat.mere["stevilo_polj"] = Mera(
        float(n - 1), status,
        f"periodično štetje na poravnani sliki (razmak "
        f"{per.perioda_px:.0f} px, zanesljivost {per.zanesljivost:.2f})")
    rezultat.mere["stevilo_stebrov"] = Mera(
        float(n), status, "periodično štetje (polja + 1)")
    if not popolno:
        rezultat.opozorila.append(
            f"Periodično štetje je našlo {n} elementov, geometrija pa jih "
            f"predvideva {per.pricakovano} — del elementov je zakritih ali "
            "slabo viden; število je ocena, potrdi ga ročno.")
    dol = rezultat.mere.get("dolzina_ograje")
    if dol and dol.vrednost_mm and n > 1:
        rezultat.mere["razmak_stebrov"] = Mera(
            dol.vrednost_mm / (n - 1), IZRACUNANO,
            "dolžina / število polj (poravnana slika)")
    if popolno:
        rezultat.opozorila.append(
            f"Število elementov ({n}) je izračunano periodično po "
            "celotni širini; pri močni perspektivi je lahko za ±1 "
            "napačno — pred ponudbo preveri na objektu.")

def _soglasje_posnetkov(rezultat: Rezultat, pot_fotografije: str, vogali,
                        dodatni, velikost_markerja_mm: float,
                        visina_mm: float | None,
                        dolzina_mm: float | None) -> None:
    """Meritev iz več posnetkov: nesoglasje razkrije napako posameznika.

    Soglasje PREVZAME mero iz enega posnetka (če se posnetki ujemajo) —
    soglasje je močnejši dokaz kot en sam posnetek. Ob nesoglasju se
    mera NE spremeni in uporabnik dobi opozorilo z razponom.
    """
    from model import Mera, IZRACUNANO

    meritve = [vec_posnetkov.izmeri(pot_fotografije, vogali,
                                    velikost_markerja_mm)]
    for pot_d, koti_d in dodatni:
        meritve.append(vec_posnetkov.izmeri(pot_d, koti_d,
                                            velikost_markerja_mm))
    sog = vec_posnetkov.soglasje(meritve)
    for o in sog.opozorila:
        if o not in rezultat.opozorila:
            rezultat.opozorila.append(o)
    if not sog.dovolj:
        return
    n = sum(1 for m in meritve if m.dolzina_mm and m.visina_mm)
    opis = (f"soglasje {n} posnetkov (razpršenost "
            f"{sog.razprsenost * 100:.2f} %)")
    if not dolzina_mm and sog.dolzina_mm:
        rezultat.mere["dolzina_ograje"] = Mera(sog.dolzina_mm, IZRACUNANO,
                                                opis)
    if not visina_mm and sog.visina_mm:
        rezultat.mere["visina_ograje"] = Mera(sog.visina_mm, IZRACUNANO,
                                              opis)


def _uporabi_maske(rezultat: Rezultat, pot: str) -> None:
    """AI maske NE določajo mere same: potrdijo ali ovržejo naše štetje.

    Ujemanje dveh neodvisnih metod je dokaz; nesoglasje je opozorilo.
    Vrednost AI nikoli ne prevzame tiho in ne dvigne statusa.
    """
    from model import Mera, OCENJENO

    import maske_ai

    try:
        maske = maske_ai.preberi(pot)
    except ValueError as e:
        rezultat.opozorila.append(f"Masek ni mogoče uporabiti: {e}")
        return
    n_m = maske_ai.prestej_stebre(maske)
    mera = rezultat.mere.get("stevilo_stebrov")
    n_z = int(mera.vrednost_mm) if (mera and mera.vrednost_mm) else None
    if n_z is None:
        rezultat.mere["stevilo_stebrov"] = Mera(
            float(n_m), OCENJENO,
            f"iz AI mask ({n_m}; AI ni del izdelka — ocena, ne meritev)")
        rezultat.opozorila.append(
            f"Število stebrov ({n_m}) je iz AI mask; naše periodično "
            "štetje ni uspelo, zato vrednost ostaja OCENJENA.")
        return
    primerjava = maske_ai.primerjaj(n_z, maske)
    if primerjava.ujemanje:
        rezultat.mere["stevilo_stebrov"] = Mera(
            float(n_z), mera.status,
            f"{mera.opis} — potrjeno z AI maskami ({n_m})")
        return
    rezultat.mere["stevilo_stebrov"] = Mera(
        float(n_z), OCENJENO,
        f"{mera.opis}; AI maske: {n_m} — nesoglasje")
    for o in primerjava.opozorila:
        if o not in rezultat.opozorila:
            rezultat.opozorila.append(o)


def pozeni(pot_fotografije: str, izhod: str, parametri: ParametriNove,
           referenca: tuple[str, float] | None = None,
           visina_mm: float | None = None,
           dolzina_mm: float | None = None,
           cene_pot: str | None = None, stranka: str = "",
           podjetje: str = "", objekt: str = "",
           vogali: list[tuple[float, float]] | None = None,
           velikost_markerja_mm: float = marker.STRANICA_MM,
           dodatni: list[tuple[str, list[tuple[float, float]]]]
           | None = None,
           maske_pot: str | None = None) -> Rezultat:
    os.makedirs(izhod, exist_ok=True)

    # 1) poravnava v čelni pogled (4 koti, ki jih označi uporabnik)
    _, izvirnik = zaznavanje.nalozi_sliko(pot_fotografije)
    bgr = izvirnik
    poravnano = False
    if vogali:
        _preveri_vogale(vogali, bgr.shape[1], bgr.shape[0])
        bgr, _homografija, _meta = rektifikacija.iz_vogalov(izvirnik,
                                                          vogali)
        poravnano = True
        cv2.imwrite(os.path.join(izhod, "00-poravnano.png"), bgr)

    # 2) zaznavanje (klasični OpenCV)
    zaznava = zaznavanje.zaznaj(pot_fotografije,
                                slika_bgr=bgr if poravnano else None)
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
        _uskladi_polja(rezultat, dolzina_mm)

    # 3b) opozorila zaznave (zavržene mere, negotova zaznava) morajo priti
    # v dokument — sicer uporabnik ne vidi, ZAKAJ je mera neznana
    rezultat.opozorila.extend(o for o in zaznava.opozorila
                               if o not in rezultat.opozorila)
    if poravnano:
        _mere_iz_markerja(rezultat, izvirnik, vogali, velikost_markerja_mm,
                          visina_mm, dolzina_mm)
        if dodatni:
            _soglasje_posnetkov(rezultat, pot_fotografije, vogali, dodatni,
                                velikost_markerja_mm, visina_mm, dolzina_mm)
        _prestej_elemente(rezultat, bgr)
    if maske_pot:
        _uporabi_maske(rezultat, maske_pot)
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
    p.add_argument("--marker-mm", type=float, default=marker.STRANICA_MM,
                   help=f"stranica natisnjenega markerja v mm "
                        f"(privzeto {marker.STRANICA_MM:.0f}); list "
                        "pripravi `python marker.py --izhod marker.png`")
    p.add_argument("--vogali", default=None,
                   help="4 koti ograje za poravnavo v čelni pogled: "
                        "'x1,y1;x2,y2;x3,y3;x4,y4' (TL, TR, BR, BL) — "
                        "dolžina/višina se nato izračunata iz homografije")
    p.add_argument("--dodatna", action="append", default=None,
                   metavar="POT|KOTI",
                   help="dodatni posnetek iste ograje za soglasje mer: "
                        "'pot|x,y;x,y;x,y;x,y' (lahko večkrat); "
                        "zahteva --vogali prve fotografije")
    p.add_argument("--maske", default=None, metavar="MASKE.JSON",
                   help="maske elementov iz zunanjega AI orodja "
                        "(Grounded SAM 2); AI NI del izdelka — maske "
                        "lahko le potrdijo naše štetje")
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

    vogali = None
    if args.vogali:
        try:
            vogali = razcleni_vogale(args.vogali)
        except ValueError as e:
            print(f"NAPAKA: --vogali: {e}", file=sys.stderr)
            return 2

    dodatni: list[tuple[str, list[tuple[float, float]]]] = []
    if args.dodatna:
        if not vogali:
            print("NAPAKA: --dodatna zahteva --vogali (kote prve "
                  "fotografije).", file=sys.stderr)
            return 2
        for niz in args.dodatna:
            try:
                dodatni.append(vec_posnetkov.razcleni_dodatno(niz))
            except ValueError as e:
                print(f"NAPAKA: --dodatna: {e}", file=sys.stderr)
                return 2

    parametri = ParametriNove(tip=args.tip, barva=args.barva)
    try:
        rezultat = pozeni(args.fotografija, args.izhod, parametri,
                          referenca, args.visina, args.dolzina,
                          cene_pot=cene_pot, stranka=args.stranka,
                          podjetje=args.podjetje, objekt=args.objekt,
                          vogali=vogali,
                          velikost_markerja_mm=args.marker_mm,
                          dodatni=dodatni or None,
                          maske_pot=args.maske)
    except ValueError as e:
        print(f"NAPAKA: {e}", file=sys.stderr)
        return 1

    print(za_konzolo(rezultat.povzetek()))
    print(f"\nIzpisi v: {args.izhod}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())