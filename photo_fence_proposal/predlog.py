"""photo_fence_proposal — vizualni predlog nove ograje na fotografiji (A).

Risba NOVE ograje čez zaznano območje stare ograje na fotografiji.
Vedno označeno kot VIZUALIZACIJA — ni dokaz mer ali konstrukcijske varnosti.
Lokalno (PIL), brez zunanjih storitev.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from model import Rezultat, BARVE_BGR

NAPIS_VIZUALIZACIJA = ("VIZUALIZACIJA — ni dokaz mer ali konstrukcijske "
                       "varnosti")


def _barva_rgb(barva: str) -> tuple:
    bgr = BARVE_BGR.get(barva, (63, 63, 70))
    return (bgr[2], bgr[1], bgr[0])  # RGB


def _korak_px(rezultat: Rezultat, kljuc_mere: str, dolzina_px: float,
              korak_mm: float) -> float:
    """Korak risanja lamel/desk v slikovnih pikah.

    Če je ustrezna mera kalibrirana, korak sledi razmerju mm/pika (prikaz
    ustreza kosovnici); sicer informativni prikaz px ≈ mm — vizualizacija
    ni dokaz mer.
    """
    mera = (rezultat.mere or {}).get(kljuc_mere)
    if mera is not None and mera.vrednost_mm and dolzina_px > 0:
        return max(3.0, korak_mm * dolzina_px / mera.vrednost_mm)
    return max(4.0, korak_mm)


def narisi_predlog(rezultat: Rezultat, pot_slike: str, pot_izhoda: str,
                   original_bgr=None) -> str:
    """Vizualni predlog: fotografija + nova ograja + oznaka.

    Če original_bgr ni podan, slika se naloži s pot_slike.
    """
    if original_bgr is not None:
        slika = Image.fromarray(original_bgr[:, :, ::-1])  # BGR → RGB
    else:
        slika = Image.open(pot_slike).convert("RGB")
    narisi = ImageDraw.Draw(slika, "RGBA")

    quad = rezultat.zaznava.obmocje_ograje_px
    if len(quad) != 4:
        # brez zaznanega območja: predloga se ne more umestiti na fotografijo
        return _zakljuci(slika, pot_izhoda,
                         [NAPIS_VIZUALIZACIJA,
                          "Območje ograje ni zaznano — predloga ni mogoče "
                          "umestiti na fotografijo."])

    xs = [t[0] for t in quad]
    ys = [t[1] for t in quad]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    sirina, visina = x1 - x0, y1 - y0

    barva = _barva_rgb(rezultat.parametri.barva)

    # polosnovna maska območja (75 % preglednost)
    narisi.rectangle([x0, y0, x1, y1], fill=barva + (190,))

    korak_mm = (rezultat.parametri.sirina_lamele_mm
                + rezultat.parametri.razmak_mm)
    if rezultat.parametri.tip == "wpc_vodoravne_lamele":
        korak = _korak_px(rezultat, "visina_ograje", visina, korak_mm)
        y = y0
        while y < y1:
            narisi.line([x0, y, x1, y], fill=(255, 255, 255, 90), width=1)
            y += korak
        # vmesni stebri
        for el in rezultat.zaznava.elementi:
            if el.vrsta == "steber":
                x = el.tocke_px[0][0]
                narisi.rectangle([x - 3, y0, x + 3, y1],
                                 fill=(30, 30, 30, 230))
    else:  # pokončne deske
        korak = _korak_px(rezultat, "dolzina_ograje", sirina, korak_mm)
        x = x0
        while x < x1:
            narisi.line([x, y0, x, y1], fill=(255, 255, 255, 90), width=1)
            x += korak

    return _zakljuci(slika, pot_izhoda,
                     [NAPIS_VIZUALIZACIJA,
                      f"Predloga: {rezultat.parametri.tip.replace('_', ' ')} — "
                      f"{rezultat.parametri.barva}",
                      rezultat.oznaka_dokumenta])


def _zakljuci(slika: Image.Image, pot_izhoda: str, napisi: list) -> str:
    narisi = ImageDraw.Draw(slika)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_velik = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
        font_velik = font
    visina = slika.size[1]
    y = visina - 24 - 26 * len(napisi)
    # svetlo ozadje za berljivost
    narisi.rectangle([0, y - 10, slika.size[0], visina], fill=(255, 255, 255, 210))
    for i, napis in enumerate(napisi):
        f = font_velik if i == 0 else font
        narisi.text((12, y + 26 * i), napis, fill=(150, 0, 0) if i == 0
                    else (20, 20, 20), font=f)
    slika.save(pot_izhoda)
    return pot_izhoda