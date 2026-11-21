# -*- coding: utf-8 -*-
"""Rektifikacija ravnine ograje + lamelni ritem (avtomatska skica).

Fizikalna omejitev (pošteno): absolutne mere iz ENE fotografije brez
znanega merila so nemogoče. Zato:
- rektificiramo ravnino ograje (homografija) → ortogonalni pogled;
- izmerimo RITEM lamel v pikah (štetje + pitch);
- skalo določi: (a) referenca uporabnika (status izmerjeno) ali
  (b) standardna dimenzija lamel (status OCENJENO — nikoli izmišljeno).

Omejitve: vhodna fotografija naj bo čim bolj čelna; pri močni perspektivi
ali zgrešeni zaznavi so mere slabše — zato so vsi izpisi označeni.
"""
import numpy as np
import cv2

from model import Mera, IZMERJENO, OCENJENO, NEZNANO

# Standardne višine WPC lamel (mm) — uporabljeno SAMO kot ocena skale.
STANDARDNE_VISINE_LAMEL = (67.0, 70.0, 100.0, 140.0, 165.0)


def rektificiraj(slika, obmocje_px, sirina_izhoda=1400):
    """Perspektivna rektifikacija ravnine ograje v ortogonalni pogled.

    Najprej poskusi METRIČNO rektifikacijo iz točk izginjanja (deluje
    tudi pri močni perspektivi); sicer homografija iz vogalov (TL, TR,
    BR, BL). Če nič ne deluje, vrne izvirno sliko z opozorilom.
    """
    opozorila = []
    # --- 1) metrična rektifikacija iz točk izginjanja ---
    H_vp, meta_vp = homografija_pogleja(slika)
    if H_vp is not None:
        h, w = slika.shape[:2]
        rect = cv2.warpPerspective(slika, H_vp, (w * 2, h * 2))
        # območje ograje prenesi v isto geometrijo in obreži
        if obmocje_px is not None and len(obmocje_px) == 4:
            q = np.float32(obmocje_px).reshape(-1, 1, 2)
            q2 = cv2.perspectiveTransform(q, H_vp).reshape(-1, 2)
            x0, y0 = np.floor(q2.min(axis=0)).astype(int)
            x1, y1 = np.ceil(q2.max(axis=0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0)
            rect = rect[y0:max(y1, y0 + 8), x0:max(x1, x0 + 8)]
        if rect.size == 0 or rect.shape[0] < 8 or rect.shape[1] < 8:
            rect = cv2.warpPerspective(slika, H_vp, (w * 2, h * 2))
        Hh, Ww = rect.shape[:2]
        if Ww != sirina_izhoda and Ww > 8:
            faktor = sirina_izhoda / float(Ww)
            rect = cv2.resize(rect, (int(sirina_izhoda),
                                     max(8, int(Hh * faktor))))
        return rect, H_vp, {"opozorila": opozorila, "rektificirano": True,
                            "nacin": "tocke_izginjanja", **meta_vp}

    # --- 2) homografija iz vogalov (TL, TR, BR, BL) ---
    if obmocje_px is None or len(obmocje_px) != 4:
        opozorila.append("Ravnina ograje ni zaznana — brez rektifikacije.")
        return slika, None, {"opozorila": opozorila, "rektificirano": False}

    src = np.float32(obmocje_px)
    # cilj: pravokotnik z enakim razmerjem stranic kot povprečje vhodnih
    sirina = float(np.mean([np.linalg.norm(src[1] - src[0]),
                            np.linalg.norm(src[2] - src[3])]))
    visina = float(np.mean([np.linalg.norm(src[3] - src[0]),
                            np.linalg.norm(src[2] - src[1])]))
    if sirina < 8 or visina < 8:
        opozorila.append("Območje ograje je premajhno za rektifikacijo.")
        return slika, None, {"opozorila": opozorila, "rektificirano": False}

    W = int(max(8, sirina_izhoda))
    H = int(max(8, round(W * visina / sirina)))
    dst = np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]])
    H_mat = cv2.getPerspectiveTransform(src, dst)
    rect = cv2.warpPerspective(slika, H_mat, (W, H))
    return rect, H_mat, {"opozorila": opozorila, "rektificirano": True,
                         "sirina_px": W, "visina_px": H}


def _teki(maska):
    """Zaporedni intervali True v 1-D maski."""
    out = []
    zac = None
    for i, t in enumerate(maska):
        if t and zac is None:
            zac = i
        elif not t and zac is not None:
            if i - zac > 1:
                out.append((zac, i))
            zac = None
    if zac is not None:
        out.append((zac, len(maska)))
    return out


def _ritem_profila(prof):
    """Najbolj reden ritem v 1-D profilu svetlosti (ali None).

    Poskusi več pragov (kvantili) — en sam prag pogosto zgreši vzorec
    na zapletenih prizorih (kombinacija ograje, korit, oken).
    """
    if len(prof) < 12:
        return None
    k = max(1, int(len(prof) * 0.01) | 1)
    sm = np.convolve(prof, np.ones(k) / k, mode="same")
    najboljse = None
    for kvantil in (0.35, 0.5, 0.65):
        meja = float(np.quantile(sm, kvantil))
        for tip, maska in (("temne", sm < meja), ("svetle", sm >= meja)):
            teki = _teki(maska)
            if not (2 <= len(teki) <= 200):
                continue
            zacetki = [a for a, _b in teki]
            pitch = np.diff(np.array(zacetki, dtype=float))
            if pitch.size == 0:
                continue
            povp = float(pitch.mean())
            std = float(pitch.std())
            nepr = std / max(povp, 1e-9)
            if tip == "temne":
                deb = float(np.mean([b - a for a, b in teki]))
                vrz = float(np.mean([teki[i + 1][0] - teki[i][1]
                                     for i in range(len(teki) - 1)]))
            else:
                vrz = float(np.mean([b - a for a, b in teki]))
                deb = float(np.mean([teki[i + 1][0] - teki[i][1]
                                     for i in range(len(teki) - 1)]))
            kandidat = {"n_lamel": len(teki), "pitch_px": povp,
                        "debelina_px": deb, "vrzel_px": max(vrz, 0.0),
                        "nepravilnost": nepr, "pas_px": len(prof)}
            # Fizikalna verjetnost: pri ograjah je debelina lamele tipično
            # 0.35–0.9 pitcha (deska večja od fuge). Če je razmerje izven
            # tega, je verjetno zamenjava deska↔fuga ali zgrešena zaznava.
            razmerje = deb / max(povp, 1e-9)
            if not (0.35 <= razmerje <= 0.9):
                kandidat["nepravilnost"] += 1.0
                kandidat["sumljivo_razmerje"] = True
            if najboljse is None or kandidat["nepravilnost"] < najboljse["nepravilnost"]:
                najboljse = kandidat
    return najboljse


def lamelni_ritem(slika_rect, pas=(0.05, 0.98)):
    """Na rektificirani sliki izmeri navpični ritem lamel v pikah.

    Izbira NAJBOLJ REDEN pas (drseča okna) — slika pogosto vsebuje več
    vzorcev (cvetlična korita, senčila, tla); ritem ograje je tisti z
    najbolj redno periodiko.

    Vrne dict: n_lamel, pitch_px, debelina_px, vrzel_px, nepravilnost
    (0 = popolnoma redno). Ritem merimo PO VIŠINI (vodoravne lamele).
    """
    g = (cv2.cvtColor(slika_rect, cv2.COLOR_BGR2GRAY)
         if slika_rect.ndim == 3 else slika_rect)
    h, w = g.shape
    y0, y1 = int(h * pas[0]), int(h * pas[1])
    if y1 - y0 < 8:
        return {"n_lamel": 0, "pitch_px": None, "debelina_px": None,
                "vrzel_px": None, "nepravilnost": None}
    obseg = g[:, int(w * 0.15):int(w * 0.85)].mean(axis=1)

    kandidati = []
    # drobna drseča okna (45/30/20 % višine) čez celotno sliko —
    # enotni pasovi (ograjа) se ločijo od detajlov (korita, okna)
    for dele in (0.45, 0.30, 0.20):
        vel = int((y1 - y0) * dele)
        if vel < 12:
            continue
        for zac in range(y0, max(y0 + 1, y1 - vel + 1), max(1, vel // 3)):
            r = _ritem_profila(obseg[zac:zac + vel])
            if r:
                r["y0"] = zac
                kandidati.append(r)
    if not kandidati:
        return {"n_lamel": 0, "pitch_px": None, "debelina_px": None,
                "vrzel_px": None, "nepravilnost": None}
    # Izbor: najprej verjetni kandidati (deske večje od fug, dovolj
    # lamel) — sicer tudi sumljivi. Nato: rednost + število lamel,
    # nagrajen z VIŠINO PASU (ograja je večja od posameznih detajlov,
    # npr. reber cvetličnih korit).
    normalni = [r for r in kandidati
                if not r.get("sumljivo_razmerje") and r["n_lamel"] >= 5]
    if normalni:
        kandidati = normalni

    def _ocena(r):
        pas = pas_ograje(slika_rect, r["pitch_px"])
        visina = (pas[1] - pas[0]) if pas else 0
        r["pas"] = pas
        return r["nepravilnost"] + 2.0 / max(r["n_lamel"], 1) \
            - 0.002 * visina

    kandidati.sort(key=_ocena)
    return kandidati[0]


def skala_mm(ritem, referenca=None, visina_slike_px=None):
    """Določi mm/pik iz referenca uporabnika ali standardne lamelе.

    ``referenca``: (kaj, vrednost_mm) — kaj ∈ {"visina_ograje"}.
    Pri referenci višine se skala računa čez celotno višino slike
    (visina_slike_px), NE čez okno ritma — okno je le vzorec lamel.
    Vrne (mm_na_px, Mera_skale) — status je POŠTEN:
    referenca -> izmerjeno; standard lamel -> ocenjeno.
    """
    if referenca is not None:
        kaj, vrednost_mm = referenca
        if kaj == "visina_ograje" and visina_slike_px:
            return (float(vrednost_mm) / float(visina_slike_px),
                    Mera(vrednost_mm, IZMERJENO,
                         "višina ograje (referenca uporabnika)"))
    # ocena iz standardne višine lamel
    if ritem.get("debelina_px"):
        naj = min(STANDARDNE_VISINE_LAMEL,
                  key=lambda s: abs(s - 67.0))   # privzeti ROMB 67×20
        return (naj / ritem["debelina_px"],
                Mera(naj, OCENJENO,
                     "standardna višina lamel (NI izmerjena — ocena skale)"))
    return (None, Mera(None, NEZNANO, "skale ni mogoče določiti"))

# ------------------------------------------------- metrična rektifikacija (VP)
def _linije(slika, min_dolzina=None):
    """HoughLinesP -> dve družini smerei: (navpične, vodoravne)."""
    g = (cv2.cvtColor(slika, cv2.COLOR_BGR2GRAY)
         if slika.ndim == 3 else slika.copy())
    g = cv2.GaussianBlur(g, (3, 3), 0)
    robovi = cv2.Canny(g, 40, 120)
    h, w = g.shape
    min_dolzina = min_dolzina or max(20, int(min(h, w) * 0.08))
    crte = cv2.HoughLinesP(robovi, 1, np.pi / 180, 60,
                           minLineLength=min_dolzina,
                           maxLineGap=max(8, min_dolzina // 4))
    navp, vod = [], []
    for c in (crte if crte is not None else []):
        x1, y1, x2, y2 = c[0]
        d = np.array([x2 - x1, y2 - y1], dtype=float)
        norm = np.linalg.norm(d)
        if norm < 1e-6:
            continue
        d /= norm
        kot = abs(np.degrees(np.arctan2(d[1], d[0])))
        p = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0])
        if kot < 25 or kot > 155:            # vodoravne
            vod.append((p, d))
        elif 65 < kot < 115:                 # navpične
            navp.append((p, d))
    return navp, vod


def _iscisce_unicenja(linije):
    """Najmanjši kvadrati: točka izginjanja družine premic."""
    if len(linije) < 2:
        return None
    A = np.zeros((2, 2))
    b = np.zeros(2)
    for p, d in linije:
        P = np.eye(2) - np.outer(d, d)      # projekcija na normalo
        A += P
        b += P @ p
    try:
        v = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return None
    if not np.all(np.isfinite(v)) or np.linalg.norm(v) > 1e7:
        return None
    return v


def homografija_pogleja(slika):
    """Metrična rektifikacija ravnine iz dveh pravokotnih točk izginjanja.

    Vrne (H 3×3 ali None, meta). H = K·R·K⁻¹ premakne ravnino ograje v
    čeln pogled (do podobnosti). Deluje tudi pri močni perspektivi.
    """
    navp, vod = _linije(slika)
    vh = _iscisce_unicenja(vod)
    vv = _iscisce_unicenja(navp)
    meta = {"st_vodoravnih": len(vod), "st_navpicnih": len(navp)}
    if vh is None or vv is None:
        meta["opozorilo"] = "Premoč malo premic za točke izginjanja."
        return None, meta
    h, w = slika.shape[:2]
    c = np.array([w / 2.0, h / 2.0])
    # gorišče iz pravokotnih točk izginjanja: f² = -(vh-c)·(vv-c)
    a = vh - c
    b = vv - c
    f2 = -float(np.dot(a, b))
    if f2 <= 1e-6:
        meta["opozorilo"] = "Točki izginjanja nista pravokotni — brez metrike."
        return None, meta
    f = float(np.sqrt(f2))
    K = np.array([[f, 0, c[0]], [0, f, c[1]], [0, 0, 1.0]])
    K_inv = np.linalg.inv(K)
    r1 = K_inv @ np.array([vh[0], vh[1], 1.0])
    r2 = K_inv @ np.array([vv[0], vv[1], 1.0])
    r1 /= np.linalg.norm(r1)
    r2 /= np.linalg.norm(r2)
    r3 = np.cross(r1, r2)
    R = np.column_stack([r1, r2, r3])
    H = K @ R @ K_inv
    # premik/merilo: vse vogale slike prenesi in poravnaj v okvir
    vogali = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    preneseni = cv2.perspectiveTransform(vogali, H).reshape(-1, 2)
    minx, miny = preneseni.min(axis=0)
    T = np.array([[1, 0, -minx], [0, 1, -miny], [0, 0, 1.0]])
    meta["gorisce"] = f
    return T @ H, meta


def pas_ograje(slika_rect, pitch_px):
    """Določi območje OGRAJE (pas lamel) na rektificirani sliki.

    Princip: lamelni pas ima periodično izmenjavo temno/svetlo z
    `pitch_px` — energija |I(y+pitch/2) − I(y)| je tam visoka, drugje
    (okna, tla, nebo) nizka. Vrne (y0, y1, x0, x1) ali None.
    """
    if not pitch_px or pitch_px < 3:
        return None
    g = (cv2.cvtColor(slika_rect, cv2.COLOR_BGR2GRAY)
         if slika_rect.ndim == 3 else slika_rect).astype(float)
    h, w = g.shape
    pol = max(1, int(round(pitch_px / 2)))
    if h <= pol + 2:
        return None
    energija = np.abs(g[pol:, :] - g[:-pol, :])[:h - pol, :]
    energija = cv2.GaussianBlur(energija, (9, 9), 0)
    prag = 0.35 * float(energija.max())
    if prag <= 1e-6:
        return None
    maska = energija > prag
    # glajenje robov: energija oscilira znotraj pasu (deska/fuga) —
    # z glajenjem dobimo enoten pas, ne drobcev
    oken = max(3, 2 * pol + 1)
    vrstice = np.convolve(maska.mean(axis=1), np.ones(oken) / oken, mode="same")
    stolpci = np.convolve(maska.mean(axis=0), np.ones(oken) / oken, mode="same")

    def _najvecji_pas(sez, prag_delez=0.25):
        m = sez > (sez.max() * prag_delez if sez.max() > 0 else 1)
        najboljsi = None
        zac = None
        for i, t in enumerate(m):
            if t and zac is None:
                zac = i
            elif not t and zac is not None:
                if najboljsi is None or i - zac > najboljsi[1] - najboljsi[0]:
                    najboljsi = (zac, i)
                zac = None
        if zac is not None and (najboljsi is None or len(m) - zac > najboljsi[1] - najboljsi[0]):
            najboljsi = (zac, len(m))
        return najboljsi

    y_pas = _najvecji_pas(vrstice)
    x_pas = _najvecji_pas(stolpci, 0.4)
    if y_pas is None or x_pas is None:
        return None
    y0, y1 = y_pas[0], min(y_pas[1] + pol, h)     # energija zamaknjena za pol
    x0, x1 = x_pas
    if y1 - y0 < pitch_px or x1 - x0 < 4:
        return None
    return int(y0), int(y1), int(x0), int(x1)
