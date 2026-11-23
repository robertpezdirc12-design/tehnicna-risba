"""photo_fence_proposal — robova kontrola lamelnega ritma (scikit-image).

Profilni estimator (``rektifikacija.lamelni_ritem``) temelji na 1-D povprečju
svetlosti; ta modul doda NEODVISEN estimator na podlagi ROBOV (scikit-image
Canny + avtokorelacija profila robov) in kontrolni mehanizem:

- soglasje obeh estimatorjev -> ritem je bolj trden;
- NESOGLASJE -> rezultat je eksplicitno oznacen ("nesoglasje") in se NE
  upošteva tiho — klicajoc dolja statuse mer na OCENJENO.

Namenjeno predlogu mer (potrditev na objektu), ne samodejni avtoriteti.
Sklepni status vedno doloci klicajoc (avtomatska_skica / uporabnik).

Zakaj avtokorelacija in ne tekovi: fuga na sliki ustvari DVA robova (levi in
desni), zato bi tekovi robov dajali polovicno periodo. Avtokorelacija vrne
periodo neodvisno od tega, koliko robov ima ena fuga.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from skimage.feature import canny

import rektifikacija


def _prazen(vir="robovi"):
    return {"n_lamel": 0, "pitch_px": None, "debelina_px": None,
            "vrzel_px": None, "nepravilnost": None, "vir": vir}


def _sivinska(slika):
    """Sivinska kopija v [0, 1] (percentilna skala — robustna na osvetlitev)."""
    g = (slika[:, :, 0] * 0.114 + slika[:, :, 1] * 0.587
         + slika[:, :, 2] * 0.299) if slika.ndim == 3 else slika.astype(float)
    g = g.astype(float)
    spodaj = float(np.percentile(g, 2))
    zgoraj = float(np.percentile(g, 98))
    if zgoraj - spodaj < 1e-6:
        return np.zeros_like(g)
    return np.clip((g - spodaj) / (zgoraj - spodaj), 0.0, 1.0)


def _perioda(prof):
    """Perioda 1-D signala prek avtokorelacije (lag prvega pomembnega max).

    Vrne lag v pikah ali None, ce signala ni periodicnega. Prag M >= 0.5
    je NAMERNO konservativen: izmerjeno na sintetičnih slikah ima pravi
    ritem M ≈ 0,93, okna hrupa pa M <= 0,45 z lažnimi lag-i — kontrolni
    estimator raje javi "ni zaznano" kot napačen predlog.
    """
    p = prof - float(prof.mean())
    n = p.size
    if n < 16:
        return None
    ac = np.correlate(p, p, mode="full")[n - 1:]
    if ac[0] <= 1e-12:
        return None
    ac = ac / ac[0]
    min_lag = max(6, n // 20)
    zgoraj = n // 2
    if zgoraj - min_lag < 4:
        return None
    M = float(ac[min_lag:zgoraj].max())
    if M < 0.5:
        return None                       # ni prepričljive periodicnosti
    # prvi lokalni max z visino >= 0.7 * M -> osnovna perioda (ne harmonik)
    for lag in range(min_lag + 1, zgoraj - 1):
        if ac[lag] >= ac[lag - 1] and ac[lag] >= ac[lag + 1] \
                and ac[lag] >= 0.7 * M:
            return float(lag)
    return float(min_lag + int(np.argmax(ac[min_lag:zgoraj])))


def _sredisca_fug(prof, pitch):
    """Sredisca fug = zdruzeni lokalni max profila robov (par robov = fuga)."""
    if pitch is None or pitch < 4 or prof.size < 8:
        return []
    prag = float(np.percentile(prof, 75)) * 0.5
    kandidati = [i for i in range(1, prof.size - 1)
                 if prof[i] >= prof[i - 1] and prof[i] >= prof[i + 1]
                 and prof[i] >= prag]
    sredisca: list[float] = []
    za = 0.4 * pitch                        # par robov iste fuge
    for i in kandidati:
        if sredisca and i - sredisca[-1] <= za:
            sredisca[-1] = (sredisca[-1] + i) / 2.0
        else:
            sredisca.append(float(i))
    return sredisca


def _sirina_fug(prof_intenzitete, sredisca, pitch):
    """Povprecna sirina TEMNEGA pasu okoli vsakega sredisca fuge (px).

    Fuga je temna; prag je sredina med 10. in 90. percentilom okna.
    """
    if not sredisca:
        return None
    nizko = float(np.percentile(prof_intenzitete, 10))
    visoko = float(np.percentile(prof_intenzitete, 90))
    if visoko - nizko < 1e-6:
        return None
    meja = nizko + 0.5 * (visoko - nizko)
    sirine = []
    for c in sredisca:
        c = int(round(c))
        a = c
        b = c
        while a > 0 and prof_intenzitete[a - 1] < meja:
            a -= 1
        while b < prof_intenzitete.size - 1 and prof_intenzitete[b + 1] < meja:
            b += 1
        sirine.append(float(b - a + 1))
    return float(np.mean(sirine)) if sirine else None


def _ritem_okna(prof, prof_intenzitete, smer):
    """Ritem enega okna profila robov (fuge = zdruzeni robovi).

    Vrne dict (n_lamel, pitch_px, debelina_px, vrzel_px, nepravilnost,
    pas_px) ali None. Fizikalni preizkus je za FUGE: fuga/pitch je tipicno
    0.05–0.75 (fuga tanjsa od deske, pri odprtih ograjah tudi do 0.75).
    """
    pitch = _perioda(prof)
    if pitch is None:
        return None
    sredisca = _sredisca_fug(prof, pitch)
    if len(sredisca) < 2:
        return None
    razmiki = np.diff(np.array(sredisca))
    povp = float(razmiki.mean())
    std = float(razmiki.std()) if razmiki.size >= 2 else 0.0
    # ce so sredisc vec (perioda avtokorelacije je lahko tudi 2x), poravnaj
    if razmiki.size >= 2 and abs(povp - pitch) > 0.25 * pitch:
        pitch = povp
    vrzel = _sirina_fug(prof_intenzitete, sredisca, pitch)
    if vrzel is None:
        return None
    kandidat = {"n_lamel": len(sredisca), "pitch_px": float(pitch),
                "debelina_px": max(float(pitch) - vrzel, 0.0),
                "vrzel_px": max(vrzel, 0.0),
                "nepravilnost": std / max(povp, 1e-9),
                "pas_px": int(prof.size), "smer": smer}
    if razmiki.size < 3:
        kandidat["nepravilnost"] += 0.1   # premalo razmikov za zanesljiv std
    razmerje = vrzel / max(float(pitch), 1e-9)
    if not (0.05 <= razmerje <= 0.75):
        kandidat["nepravilnost"] += 1.0
        kandidat["sumljivo_razmerje"] = True
    return kandidat


def robni_ritem(slika_rect, pas=(0.05, 0.98)):
    """Ritem lamel iz ROBOV (scikit-image Canny) na rektificirani sliki.

    Vrne dict v isti obliki kot ``rektifikacija.lamelni_ritem`` (n_lamel,
    pitch_px, debelina_px, vrzel_px, nepravilnost, smer, y0) + ``vir``.
    Pri nezaznanem ritmu so vrednosti None/0 (isti dogovor kot profilni).
    """
    g = _sivinska(slika_rect)
    h, w = g.shape
    if h < 16 or w < 16:
        return _prazen()
    y0, y1 = int(h * pas[0]), int(h * pas[1])
    if y1 - y0 < 8:
        return _prazen()
    robovi = canny(g, sigma=1.5, low_threshold=0.1, high_threshold=0.3)
    kandidati = []
    for smer, prof, prof_i, rob, kon in (
            ("navpicno",
             gaussian_filter1d(robovi[y0:y1, :].mean(axis=0), 1.5),
             g[y0:y1, :].mean(axis=0),
             int(w * 0.02), int(w * 0.98)),
            ("vodoravno",
             gaussian_filter1d(robovi[:, :].mean(axis=1), 1.5),
             g.mean(axis=1),
             int(h * 0.02), int(h * 0.98))):
        dolzina = kon - rob
        for dele in (0.45, 0.30, 0.20):
            vel = int(dolzina * dele)
            if vel < 16:
                continue
            for zac in range(rob, max(rob + 1, kon - vel + 1),
                             max(1, vel // 3)):
                r = _ritem_okna(prof[zac:zac + vel], prof_i[zac:zac + vel],
                                smer)
                if r:
                    r["y0"] = zac
                    kandidati.append(r)
    if not kandidati:
        return _prazen()
    normalni = [r for r in kandidati
                if not r.get("sumljivo_razmerje") and r["n_lamel"] >= 5]
    if normalni:
        kandidati = normalni
    naj = min(kandidati, key=lambda r: r["nepravilnost"])
    izhod = dict(naj)
    izhod["vir"] = "robovi"
    return izhod


def soglasje(ritem_a, ritem_b, prag=0.10):
    """Primerjava dveh estimatorjev ritma.

    Soglasje: pitch-a se razlikujeta za <= ``prag`` (relativno) in stevili
    zaznanih enot se razlikujeta za najvec max(2, 30 %) — okna imata lahko
    razlicno dolzino, zato je stevilo le grob nadzor. Vrne dict
    {"soglasje": bool, "odstopanje": float | None, "razlog": str} — razlog
    vedno navaja obe meritvi pitch (sledljivost, ne le "narobe").
    """
    pa = ritem_a.get("pitch_px")
    pb = ritem_b.get("pitch_px")
    if not pa or not pb:
        return {"soglasje": False, "odstopanje": None,
                "razlog": "eden od estimatorjev ni nasel ritma"}
    odstopanje = abs(float(pa) - float(pb)) / max(float(pa), float(pb))
    na = int(ritem_a.get("n_lamel") or 0)
    nb = int(ritem_b.get("n_lamel") or 0)
    stevili_ok = abs(na - nb) <= max(2, int(round(0.3 * max(na, nb))))
    deli = [f"pitch: {pa:.1f} / {pb:.1f} px"]
    if odstopanje > prag:
        deli.append(f"odstopanje {odstopanje * 100:.1f} % presega "
                    f"{prag * 100:.0f} %")
    if not stevili_ok:
        deli.append(f"stevili enot se razlikujeta ({na} / {nb})")
    soglasje_v = (odstopanje <= prag) and stevili_ok
    if soglasje_v:
        deli.append("v toleranci")
    return {"soglasje": soglasje_v, "odstopanje": odstopanje,
            "razlog": " — ".join(deli)}


def lamelni_ritem_kontrolirano(slika_rect):
    """Profilni + robovi estimator in kontrola soglasja (brez tihe izbire).

    Vrne osnovni slovar ``rektifikacija.lamelni_ritem`` (dogovor ohranjen)
    z dodatkoma:

    - ``kontrola``: {"pitch_profil_px", "pitch_rob_px", "soglasje", "razlog",
      "vir"} — sledljivost obeh meritev;
    - ``nesoglasje``: True, ce se estimatorja NE strinjata. V tem primeru
      se vrednosti NE izberejo tiho: klicajoc MORA doljati statuse mer
      (avtomatska_skica to stori za ritemske mere) in uporabnika opozori.

    Ce robovni estimator ritma ne najde, ``nesoglasje`` ostane False —
    odsotnost drugega mnenja ni nestrinjanje.
    """
    profil = rektifikacija.lamelni_ritem(slika_rect)
    rob = robni_ritem(slika_rect)
    s = soglasje(profil, rob)
    oba = bool(profil.get("pitch_px")) and bool(rob.get("pitch_px"))
    nesoglasje = oba and not s["soglasje"]
    izhod = dict(profil)
    izhod["kontrola"] = {
        "pitch_profil_px": profil.get("pitch_px"),
        "pitch_rob_px": rob.get("pitch_px"),
        "soglasje": s["soglasje"],
        "razlog": s["razlog"],
        "vir": "profil (povprecje) + robovi (scikit-image Canny)",
    }
    izhod["nesoglasje"] = nesoglasje
    if nesoglasje:
        izhod["nepravilnost"] = (profil.get("nepravilnost") or 0.0) + 1.0
    return izhod