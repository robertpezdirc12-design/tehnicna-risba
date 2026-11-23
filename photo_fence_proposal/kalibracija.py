"""photo_fence_proposal — kalibracija in izpeljava mer s statusi.

Ena znana referenčna mera uporabnika (npr. "razmak stebrov je 2000 mm")
pretvori slike v milimetre. Vse ostalo je izpeljano (IZRACUNANO) ali
ocenjeno (OCENJENO) ali NEZNANO — nikoli tiho izmišljeno.

OMEJITEV (izpisano v izhodu): single-view kalibracija predpostavlja čeln
pogled; pod kotom je napaka lahko večja — zato je napaka navedena kot
ocena in dokument ostane informativen, dokler uporabnik ne potrdi mer.
"""
from __future__ import annotations

import numpy as np

from model import (Kalibracija, Mera, Zaznava, ParametriNove,
                   NEZNANO, OCENJENO, IZMERJENO, IZRACUNANO)

# Fizično verodostojne meje za mere ograje (klasični QC, brez AI). Če
# kalibrirana vrednost pade ven, zaznava ali referenca NE drži — mera se
# NE izpiše kot izmerjena, ampak se JAVNO zavrže z opozorilom (nikoli tiho
# izmišljena številka).
MEJE_VERODOSTOJNOSTI_MM = {
    "dolzina_ograje": (300.0, 200000.0),
    "visina_ograje": (300.0, 6000.0),
    "razmak_stebrov": (100.0, 15000.0),
}


def _preveri_verodostojnost(ime: str, mera: Mera, zaznava: Zaznava) -> Mera:
    """Zavrži fizično neverodostojne izračune (glasno, ne tiho)."""
    spodaj, zgoraj = MEJE_VERODOSTOJNOSTI_MM[ime]
    if mera.vrednost_mm is not None and not spodaj <= mera.vrednost_mm <= zgoraj:
        zavrzena = f"{mera.vrednost_mm:.0f} mm"
        zaznava.opozorila.append(
            f"{ime}: izračunana vrednost {zavrzena} ni fizično verodostojna "
            f"(pričakovano {spodaj:.0f}–{zgoraj:.0f} mm) — zaznava ali "
            "referenca je napačna; mera je ZAVRŽENA, potreben ročni vnos.")
        return Mera(None, NEZNANO,
                    f"izračunana vrednost {zavrzena} ni fizično verodostojna "
                    "— zavržena (zaznava ali referenca napačna)")
    return mera


def _x_sredine_stebrov(zaznava: Zaznava) -> list:
    return sorted(t[0] for e in zaznava.elementi if e.vrsta == "steber"
                  for t in e.tocke_px[:1])


def razdalje_stebrov_px(zaznava: Zaznava) -> list:
    """Razmaki med sosednjimi zaznanimi stebri v slikovnih pikah."""
    x_stebri = _x_sredine_stebrov(zaznava)
    return [x_stebri[i + 1] - x_stebri[i] for i in range(len(x_stebri) - 1)]


def visina_ograje_px(zaznava: Zaznava) -> float | None:
    """Višina ograje v pikah.

    Merjeno iz ZANESLJIVIH referenc, ne iz bbox-a vseh elementov:
    - če sta vsaj 2 ločeni vodoravni letvi (zgoraj in spodaj): razpon med
      njunima središčema (dejanska višina ograje — stebri segajo prek nje
      navzgor/navzdol in bi bbox sistematično PREVELIČAL višino),
    - sicer fallback: razpon zaznanega območja (bbox) — negotovo.
    """
    if not zaznava.obmocje_ograje_px:
        return None
    # središča zaznanih letvi; robovi iste letve se zgručijo skupaj
    sredine = sorted(sum(p[1] for p in e.tocke_px) / len(e.tocke_px)
                     for e in zaznava.elementi
                     if e.vrsta == "precka" and len(e.tocke_px) >= 2)
    prag_locevanja = max(4.0, 0.02 * zaznava.slika.visina_px)
    gruce: list = []
    for y in sredine:
        if gruce and y - gruce[-1][-1] <= prag_locevanja:
            gruce[-1].append(y)
        else:
            gruce.append([y])
    sredisci = [sum(g) / len(g) for g in gruce]
    if (len(sredisci) >= 2
            and sredisci[-1] - sredisci[0] >= 0.05 * zaznava.slika.visina_px):
        return sredisci[-1] - sredisci[0]
    bbox_ys = [t[1] for t in zaznava.obmocje_ograje_px]
    return max(bbox_ys) - min(bbox_ys)


def dolzina_ograje_px(zaznava: Zaznava) -> float | None:
    """Dolžina ograje v pikah.

    Merjeno iz razpona skrajnih središč stebrov (teka ograje), ne iz bbox-a
    vseh elementov — Hough daljice in robovi stebrov segajo prek ograje in bi
    bbox sistematično PREVELIČAL dolžino. Fallback (manj kot 2 stebra):
    razpon zaznanega območja (bbox) — negotovo.
    """
    x_stebri = _x_sredine_stebrov(zaznava)
    if len(x_stebri) >= 2:
        return x_stebri[-1] - x_stebri[0]
    if not zaznava.obmocje_ograje_px:
        return None
    xs = [t[0] for t in zaznava.obmocje_ograje_px]
    return max(xs) - min(xs)


def kalibriraj_referenca(zaznava: Zaznava, kaj: str, vrednost_mm: float
                         ) -> Kalibracija:
    """Uporabnikova referenčna mera → kalibracija.

    kaj: "razmak_stebrov" (povprečje zaznanih razmakov) ali "visina_ograje".
    """
    if vrednost_mm <= 0:
        raise ValueError("Referenčna mora biti pozitivna")
    if kaj == "razmak_stebrov":
        razmaki = razdalje_stebrov_px(zaznava)
        if not razmaki:
            raise ValueError("Ni zaznanih stebrov — kalibracije z razmakom ni "
                             "mogoče izvesti; uporabite 'visina_ograje'")
        dolzina_px = float(np.mean(razmaki))
    elif kaj == "visina_ograje":
        v = visina_ograje_px(zaznava)
        if not v:
            raise ValueError("Višine ograje ni mogoče zaznati")
        dolzina_px = float(v)
    else:
        raise ValueError(f"Neznana referenca {kaj!r} — dovoljeni: "
                         "'razmak_stebrov', 'visina_ograje'")
    return Kalibracija(dolzina_px=dolzina_px, dolzina_mm=vrednost_mm,
                       opis=f"{kaj} = {vrednost_mm:.0f} mm (potrdil uporabnik)")


def izpelji_mere(zaznava: Zaznava, parametri: ParametriNove,
                 kalibracija: Kalibracija | None) -> dict:
    """Iz zaznave (+ kalibracije) sestavi mere s statusi.

    Poštenost (test z realnimi fotografijami, balkoni): če je zaznava
    negotova (neenakomerni razmaki stebrov, ...), izpeljane mere NISO
    'izmerjeno' — demovane so v 'ocenjeno', ker izhajajo iz zgrešene
    zaznave (npr. dolžina 17329 mm namesto ~6200 mm).
    """
    mere: dict[str, Mera] = {}
    negotova = any(("negotov" in o.lower()) or ("neenakomern" in o.lower())
                   for o in zaznava.opozorila)
    # referenčna višina (uporabnik jo je potrdil) ostane 'izmerjeno';
    # vse ostalo iz negotove zaznave je le 'ocenjeno'
    ref_visina = bool(kalibracija and
                      kalibracija.opis.startswith("visina_ograje"))

    def _status(je_referenca):
        if not negotova:
            return IZMERJENO
        return IZMERJENO if je_referenca else OCENJENO

    def _opis(osnova, je_referenca):
        if negotova and not je_referenca:
            return osnova + " (zaznava NEGOTOVA — ocena, ne natančna meritev)"
        return osnova

    # Dolžina ograje (razpon skrajnih središč stebrov — glej dolzina_ograje_px)
    dolz_px = dolzina_ograje_px(zaznava)
    if dolz_px and kalibracija:
        mere["dolzina_ograje"] = _preveri_verodostojnost(
            "dolzina_ograje",
            kalibracija.v_mere(
                dolz_px, _opis("teka ograje (razpon skrajnih središč stebrov; "
                              "fallback: območje zaznave)", False),
                status=_status(False)),
            zaznava)
    elif dolz_px:
        mere["dolzina_ograje"] = Mera(
            None, NEZNANO, "zaznana širina v pikah, brez kalibracije",
            vir=f"{dolz_px:.0f} px")
    else:
        mere["dolzina_ograje"] = Mera(None, NEZNANO, "območje ograje ni zaznano")

    # Višina ograje (razpon zunanjih letvi — glej visina_ograje_px)
    vis_px = visina_ograje_px(zaznava)
    if vis_px and kalibracija:
        mere["visina_ograje"] = _preveri_verodostojnost(
            "visina_ograje",
            kalibracija.v_mere(
                vis_px, _opis("višina ograje (razpon središč zunanjih letvi; "
                             "fallback: območje zaznave)", ref_visina),
                status=_status(ref_visina)),
            zaznava)
    elif vis_px:
        mere["visina_ograje"] = Mera(
            None, NEZNANO, "zaznana višina v pikah, brez kalibracije",
            vir=f"{vis_px:.0f} px")
    else:
        mere["visina_ograje"] = Mera(None, NEZNANO, "višina ograje ni zaznana")

    # Število polj / stebrov (štetje je zanesljivo tudi brez kalibracije)
    st_stebrov = len({round(t[0], 1) for e in zaznava.elementi
                      if e.vrsta == "steber" for t in e.tocke_px[:1]})
    if st_stebrov >= 2:
        mere["stevilo_stebrov"] = Mera(float(st_stebrov), IZMERJENO,
                                       "prešteti zaznani stebri",
                                       vir="zaznavanje", enota="kos")
        mere["stevilo_polj"] = Mera(float(st_stebrov - 1), IZRACUNANO,
                                    "polja med stebri", vir="štetje", enota="kos")
    else:
        mere["stevilo_stebrov"] = Mera(None, NEZNANO,
                                       "stebri niso zanesljivo zaznani")

    # Razmak stebrov
    razmaki = razdalje_stebrov_px(zaznava)
    if razmaki and kalibracija:
        mere["razmak_stebrov"] = _preveri_verodostojnost(
            "razmak_stebrov",
            kalibracija.v_mere(
                float(np.mean(razmaki)), "povprečni razmak stebrov",
                status=IZRACUNANO),
            zaznava)
    elif razmaki:
        mere["razmak_stebrov"] = Mera(
            None, NEZNANO, "razmak v pikah, brez kalibracije",
            vir=f"{np.mean(razmaki):.0f} px")

    # Parametri nove ograje — OCENJENO, dokler uporabnik ne potrdi
    mere["sirina_lamele"] = Mera(parametri.sirina_lamele_mm, OCENJENO,
                                 "standardna širina lamele (ni izmerjena)",
                                 vir="parametri")
    mere["razmak_lamel"] = Mera(parametri.razmak_mm, OCENJENO,
                                "razmak med lamelami (izbira uporabnika)",
                                vir="parametri")
    return mere


def napaka_na_testni_sliki(mere: dict, resni: dict) -> dict:
    """Za testne slike z ZNANIMI merami: izračunaj napako kalibriranih mer.

    Uporabljeno samo v testih (Faza 4) — resni vrednosti prideta iz
    generatorja testnih slik, ne iz fotografije.
    """
    napake = {}
    for ime, resnicna in resni.items():
        m = mere.get(ime)
        if m and m.vrednost_mm is not None:
            napake[ime] = abs(m.vrednost_mm - resnicna)
    return napake