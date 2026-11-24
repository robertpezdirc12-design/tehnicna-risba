"""photo_fence_proposal — zaznavanje geometrije stare ograje (klasični OpenCV).

BREZ AI modelov: kolonski temni profil (stebri) + sivinska slika → CLAHE →
zameglitev → Canny → HoughLinesP (vodoravne letvi). Vse lokalno (CPU).

Poštene omejitve: zaznavanje deluje najbolje na čelnih posnetkih z vidno
kontrastno ograjo. Perspektiva, sence in zakritja slabšajo rezultat — vse
negotovosti gredo v opozorila in statuse mer, nikoli v izmišljene mere.
"""
from __future__ import annotations

import cv2
import numpy as np

from model import Slika, Element, Zaznava


def nalozi_sliko(pot: str) -> tuple[Slika, np.ndarray]:
    """Naloži fotografijo (lokalno). Vrne opis + BGR matriko."""
    slika = cv2.imread(pot, cv2.IMREAD_COLOR)
    if slika is None:
        raise ValueError(f"Slike ni mogoče prebrati: {pot}")
    visina, sirina = slika.shape[:2]
    return Slika(pot=pot, sirina_px=sirina, visina_px=visina), slika


def _predobdelava(slika_bgr: np.ndarray) -> np.ndarray:
    """Sivinska slika z izravnavo kontrasta in zameglitvijo — robustni robovi."""
    siva = cv2.cvtColor(slika_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    siva = clahe.apply(siva)
    return cv2.GaussianBlur(siva, (5, 5), 0)


def _robovi(siva: np.ndarray) -> np.ndarray:
    return cv2.Canny(siva, 40, 120)


def _hough_crte(robovi: np.ndarray, min_dolzina: float) -> list:
    """HoughLinesP → seznami daljic [(x1, y1, x2, y2), ...]."""
    crte = cv2.HoughLinesP(robovi, rho=1, theta=np.pi / 180,
                           threshold=60, minLineLength=min_dolzina,
                           maxLineGap=20)
    if crte is None:
        return []
    return [tuple(int(v) for v in crta[0]) for crta in crte]


def _kot_stopinje(x1, y1, x2, y2) -> float:
    return abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) % 180.0


def _vodoravne(crte: list, toleranca: float = 12.0) -> list:
    return [c for c in crte if _kot_stopinje(*c) <= toleranca
            or abs(_kot_stopinje(*c) - 180.0) <= toleranca]


def _stebri_po_profilu(siva: np.ndarray) -> list:
    """Stebri iz kolonskega profila temnih slikovnih pik (klasično, brez AI).

    Stebri so ŠIRŠE temne pokončne pasove kot deske — zato se združujejo
    kolone z veliko temnimi pikami in ločujejo po širini (>= 6 px).
    Vrne [(x_sredina, y_vrh, y_dno), ...].
    """
    visina = siva.shape[0]
    prag = float(np.mean(siva)) * 0.65
    temne = (siva < prag).astype(np.uint8)
    profil = temne.sum(axis=0)
    if profil.max() == 0:
        return []
    aktivne = profil > 0.35 * profil.max()
    pasovi = []
    zacetek = None
    for x, a in enumerate(aktivne):
        if a and zacetek is None:
            zacetek = x
        elif not a and zacetek is not None:
            pasovi.append((zacetek, x - 1))
            zacetek = None
    if zacetek is not None:
        pasovi.append((zacetek, len(aktivne) - 1))
    stebri = []
    for x0, x1 in pasovi:
        sirina = x1 - x0 + 1
        if sirina < 6 or sirina > 0.2 * siva.shape[1]:
            continue  # preozko (deska) ali preširoko (senca/objekt)
        stolpci = temne[:, x0:x1 + 1].any(axis=1)
        ys = np.where(stolpci)[0]
        if len(ys) < 0.12 * visina:
            continue  # ne sega čez dovolj slike — ni steber
        stebri.append((float((x0 + x1) / 2.0), float(ys.min()), float(ys.max())))
    return stebri


def zaznaj(pot: str, slika_bgr: np.ndarray | None = None) -> Zaznava:
    """Glavna funkcija: fotografija → zaznani elementi + opozorila.

    Deterministično: ista slika → isti rezultat. Kombinacija:
    kolonski temni profil (stebri) + Canny/Hough (vodoravne letvi).

    slika_bgr: že naložena (in morebiti poravnana) matrika; če je podana,
    se datoteka ne bere znova.
    """
    slika, bgr = nalozi_sliko(pot)
    if slika_bgr is not None:
        bgr = slika_bgr
        slika = Slika(pot=pot, sirina_px=int(bgr.shape[1]),
                      visina_px=int(bgr.shape[0]))
    visina, sirina = bgr.shape[:2]
    zaznava = Zaznava(slika=slika)
    siva = _predobdelava(bgr)
    robovi = _robovi(siva)
    min_dolzina = max(40.0, 0.08 * min(sirina, visina))

    # --- stebri: temni široki pasovi (primarno) ---
    stebri_prof = _stebri_po_profilu(siva)
    for x, y_vrh, y_dno in stebri_prof:
        zaznava.elementi.append(Element(
            vrsta="steber", tocke_px=[(x, y_vrh), (x, y_dno)],
            zaupanje=0.7, opis="širok temen pas (kolonski profil)"))

    # rezervna pot: Hough pokončne črte, če profil ni našel stebrov
    if not stebri_prof:
        crte = _hough_crte(robovi, min_dolzina)
        pok = [c for c in crte
               if abs(_kot_stopinje(*c) - 90.0) <= 12.0]
        for c in pok[:20]:
            zaznava.elementi.append(Element(
                vrsta="steber",
                tocke_px=[(float(c[0]), float(c[1])),
                          (float(c[2]), float(c[3]))],
                zaupanje=0.4, opis="pokončna črta (Hough, rezervno)"))
        if not pok:
            zaznava.opozorila.append(
                "Ni zaznanih stebrov — fotografija je preveč nejasna ali "
                "ograja ni vidna. Potreben ročni vnos mer.")
            return zaznava

    # --- vodoravne letvi: Hough ---
    vod = _vodoravne(_hough_crte(robovi, min_dolzina))
    for c in sorted(vod, key=lambda c: -abs(c[2] - c[0]))[:8]:
        zaznava.elementi.append(Element(
            vrsta="precka", tocke_px=[(float(c[0]), float(c[1])),
                                      (float(c[2]), float(c[3]))],
            zaupanje=0.5, opis="vodoravna črta (Hough)"))

    # --- območje ograje: iz dejanskih razsežnosti elementov ---
    xs = [t[0] for e in zaznava.elementi for t in e.tocke_px]
    ys = [t[1] for e in zaznava.elementi for t in e.tocke_px]
    if xs and ys:
        zaznava.obmocje_ograje_px = [
            (min(xs), min(ys)), (max(xs), min(ys)),
            (max(xs), max(ys)), (min(xs), max(ys))]
    else:
        zaznava.opozorila.append("Območja ograje ni bilo mogoče zaznati.")

    # --- polja med stebri ---
    x_stebri = sorted({round(t[0], 1) for e in zaznava.elementi
                       if e.vrsta == "steber" for t in e.tocke_px[:1]})
    y_v = min((t[1] for e in zaznava.elementi if e.vrsta == "steber"
               for t in e.tocke_px[:1]), default=0.0)
    y_d = max(ys, default=0.0)
    for i in range(len(x_stebri) - 1):
        zaznava.elementi.append(Element(
            vrsta="polje",
            tocke_px=[(x_stebri[i], y_v), (x_stebri[i + 1], y_v),
                      (x_stebri[i + 1], y_d), (x_stebri[i], y_d)],
            zaupanje=0.4, opis="med sosednjima stebroma"))

    if len(x_stebri) < 2:
        zaznava.opozorila.append(
            "Zaznanih je manj kot 2 stebra — geometrija ograje ni zanesljivo "
            "določljiva; mere ostajajo neznane.")
    elif len(x_stebri) < 3:
        zaznava.opozorila.append(
            "Zaznana sta samo 2 stebra — zaznava je ŠIBKA in je lahko lažna "
            "(tudi tehnična risba ali drug motiv namesto fotografije ograje); "
            "štetje stebrov in vse mere potrdi ročno.")
    else:
        x_sez = sorted(x_stebri)
        razmaki = [x_sez[i + 1] - x_sez[i] for i in range(len(x_sez) - 1)]
        mediana = float(np.median(razmaki))
        if mediana > 0 and max(abs(r - mediana) for r in razmaki) > 0.35 * mediana:
            zaznava.opozorila.append(
                "Razmaki med zaznanimi stebri so zelo neenakomerni — zaznava "
                "stebrov je negotova (možne lažne zaznave); mere potrdi ročno.")
    if not vod:
        zaznava.opozorila.append(
            "Ni zaznanih vodoravnih letvi — višina ograje je manj zanesljiva "
            "in zahteva potrditev.")
    zaznava.opozorila.append(
        "Zaznavanje je izvedeno s klasičnimi algoritmi (kolonski profil + "
        "Canny + Hough) brez AI modelov; pri pogledu pod kotom so mere manj "
        "zanesljive in zahtevajo potrditev.")
    return zaznava


def oznaci_sliko(zaznava: Zaznava, bgr: np.ndarray) -> np.ndarray:
    """Nariše zaznane elemente čez izvirno fotografijo (dokaz zaznavanja)."""
    slika = bgr.copy()
    barve = {"steber": (0, 255, 0), "precka": (255, 160, 0),
             "polje": (255, 0, 255), "letv": (0, 200, 255), "rob": (200, 200, 0)}
    for el in zaznava.elementi:
        barva = barve.get(el.vrsta, (180, 180, 180))
        tocke = [(int(x), int(y)) for x, y in el.tocke_px]
        if el.vrsta == "polje" and len(tocke) == 4:
            cv2.polylines(slika, [np.array(tocke, dtype=np.int32)], True,
                          barva, 1, cv2.LINE_AA)
        else:
            for i in range(len(tocke) - 1):
                cv2.line(slika, tocke[i], tocke[i + 1], barva, 2, cv2.LINE_AA)
    if zaznava.obmocje_ograje_px:
        quad = np.array([(int(x), int(y)) for x, y in zaznava.obmocje_ograje_px],
                        dtype=np.int32)
        cv2.polylines(slika, [quad], True, (0, 255, 255), 2, cv2.LINE_AA)
    return slika