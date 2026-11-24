"""DXF izvoz za CAD/CNC (issue #3) — na osnovi ezdxf 1.4.5.

Specifikacija (docs/dxf-specifikacija.md):
- format R2010 (AC1024), enote mm ($INSUNITS=4, $MEASUREMENT=1), 1:1 realne mm
- plasti (fiksna shema, ISO 13567 struktura): M-ELEM-CONT, M-STEB-CONT,
  M-ODPR-CONT, M-OKOV-PRIT, M-POLN-SRAF, M-ANNO-DIMS, M-ANNO-CLIN,
  M-ANNO-TEXT, M-ANNO-FRAM — rez/vrtanje SAMO iz M-ELEM-CONT, M-STEB-CONT,
  M-ODPR-CONT (stara imena OUTLINE/POSTS/HOLES — glej LEGACY_SLOJI)
- konture: zaprte LWPOLYLINE brez ponovljene prve točke; luknje CIRCLE
- kote: statične (LINE + SOLID puščice + MTEXT) na plasti M-ANNO-DIMS
- OMEJITEV: DXF ne vsebuje G-code/toolpath/kompenzacije orodja ali kerfa —
  konture so nominalne mere.

Geometrija prihaja iz čistih funkcij (risba.razpored, risba.razpored_pokoncna,
vrata.geometrija_vrat) — isti vir resnice kot risba in količine.
"""
from __future__ import annotations

import os
from typing import Any, cast

import ezdxf
from ezdxf import units as ez_units

import jedro
import risba
import vrata

# Fiksna shema plasti po ISO 13567 strukturi (discipline-major-minor):
# (barva ACI, linetype, lw mm, ali vsebuje rez/vrtanje)
PLASTI = {
    "M-ELEM-CONT": (7, "CONTINUOUS", 0.50, True),    # konture kosov
    "M-STEB-CONT": (5, "CONTINUOUS", 0.35, True),    # stebri/nosilci, profili
    "M-ODPR-CONT": (1, "CONTINUOUS", 0.25, True),    # odprtine/vrtanje
    "M-OKOV-PRIT": (2, "CONTINUOUS", 0.25, False),   # okovje/pritrdila
    "M-POLN-SRAF": (8, "CONTINUOUS", 0.25, False),   # šrafure/polnila
    "M-ANNO-DIMS": (3, "CONTINUOUS", 0.18, False),   # kote
    "M-ANNO-CLIN": (6, "CENTER", 0.13, False),       # simetrične osi
    "M-ANNO-TEXT": (7, "CONTINUOUS", 0.25, False),   # besedila
    "M-ANNO-FRAM": (8, "CONTINUOUS", 0.25, False),   # okvir lista
}

# Prehodna tabela (Plan 2): stara interna imena -> ISO 13567 imena.
# Notranja koda (vrata.py, risba.py) uporablja stara imena; prevedejo se
# šele ob zapisu v DXF (globok modul — en vir resnice o geometriji).
LEGACY_SLOJI = {
    "OUTLINE": "M-ELEM-CONT",
    "POSTS": "M-STEB-CONT",
    "HOLES": "M-ODPR-CONT",
    "HARDWARE": "M-OKOV-PRIT",
    "FILL": "M-POLN-SRAF",
    "DIMENSIONS": "M-ANNO-DIMS",
    "CENTERLINES": "M-ANNO-CLIN",
    "TEXT": "M-ANNO-TEXT",
    "FRAME": "M-ANNO-FRAM",
}


def _sloj(ime):
    """Notranje (legacy) ali že ISO ime -> canonicalno ISO ime sloja."""
    return LEGACY_SLOJI.get(ime, ime)

MED_RAZMAK = 1000.0  # razmak med segmenti v model prostoru (mm)

OPOMBE_DXF = [
    "Mere v mm, tolerance ISO 2768-m.",
    "Konture so nominalne — BREZ kompenzacije orodja/kerfa.",
    "DXF NE vsebuje G-code ali toolpath poti.",
    "Rez/vrtanje SAMO iz plasti M-ELEM-CONT, M-STEB-CONT, M-ODPR-CONT "
    "(legacy imena: OUTLINE, POSTS, HOLES).",
    "Preveri mere na objektu pred izvedbo.",
    "Risba NI statični izračun — nosilnost/sidranje preveri usposobljen strokovnjak.",
]


# ---------------------------------------------------------------------------
# Osnovne entitete
# ---------------------------------------------------------------------------

def _plasti(doc):
    """Ustvari vse plasti po shemi (tudi prazne — CAM pričakuje fiksno shemo)."""
    for ime, (barva, ltype, _lw, _rez) in PLASTI.items():
        if ime not in doc.layers:
            doc.layers.add(ime, color=barva, linetype=ltype)


def kvadrat(msp, x, y, w, h, layer):
    """Zaprta kontura pravokotnika (CCW, brez ponovljene prve točke)."""
    layer = _sloj(layer)
    if w <= 0 or h <= 0:
        return None
    tocke = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return msp.add_lwpolyline(tocke, format="xy", close=True, dxfattribs={"layer": layer})


def crta(msp, x1, y1, x2, y2, layer):
    layer = _sloj(layer)
    return msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})


def krog(msp, x, y, premer, layer):
    layer = _sloj(layer)
    return msp.add_circle((x, y), premer / 2.0, dxfattribs={"layer": layer})


def tekst(msp, x, y, niz, visina=2.5, layer="TEXT", rot=0.0):
    layer = _sloj(layer)
    return msp.add_mtext(niz, dxfattribs={"layer": layer, "char_height": visina,
                                          "rotation": rot}).set_location((x, y))


def _puscica(msp, x, y, smer_x, dolzina=2.5, layer="DIMENSIONS"):
    """SOLID trikotna puščica kote (klin v smeri smer_x)."""
    layer = _sloj(layer)
    p1 = (x, y)
    p2 = (x + smer_x * dolzina, y + dolzina / 6.0)
    p3 = (x + smer_x * dolzina, y - dolzina / 6.0)
    msp.add_solid([p1, p2, p3, p3], dxfattribs={"layer": layer})


def kota_h(msp, x1, x2, y, y_text, vrednost, layer="DIMENSIONS"):
    """Vodoravna kota (statična: podaljški + dim črta + 2 puščici + tekst)."""
    crta(msp, x1, y_text + 1.2, x1, y + 0.8, layer)
    crta(msp, x2, y_text + 1.2, x2, y + 0.8, layer)
    crta(msp, x1, y, x2, y, layer)
    _puscica(msp, x1, y, +1)
    _puscica(msp, x2, y, -1)
    tekst(msp, (x1 + x2) / 2.0, y + 1.0, f"{vrata.fmt_mm(vrednost)} mm",
          layer=layer)


def kota_v(msp, y1, y2, x, x_text, vrednost, layer="DIMENSIONS"):
    """Navpična kota."""
    layer = _sloj(layer)
    crta(msp, x_text - 1.2, y1, x + 0.8, y1, layer)
    crta(msp, x_text - 1.2, y2, x + 0.8, y2, layer)
    crta(msp, x, y1, x, y2, layer)
    _puscica(msp, x, y1, 0)
    msp.add_solid([(x, y1), (x + 0.4, y1 + 2.5), (x - 0.4, y1 + 2.5),
                   (x - 0.4, y1 + 2.5)], dxfattribs={"layer": layer})
    msp.add_solid([(x, y2), (x + 0.4, y2 - 2.5), (x - 0.4, y2 - 2.5),
                   (x - 0.4, y2 - 2.5)], dxfattribs={"layer": layer})
    tekst(msp, x + 1.0, (y1 + y2) / 2.0, f"{vrata.fmt_mm(vrednost)} mm",
          layer=layer, rot=90.0)


# ---------------------------------------------------------------------------
# Geometrija segmentov (isti vir resnice kot risba)
# ---------------------------------------------------------------------------

def _elementi_segmenta(mere, tip, vrata_sez=None, prehodi_sez=None):
    """2D elementi sprednjega pogleda segmenta (realni mm, od (0, 0))."""
    el: list = []
    odcep = mere.get("odcep", 0.0)
    visina = mere["visina"]
    sirina = mere["sirina"]

    if tip == "ograja":
        zg, sp, lamele, _vrzel, _n = risba.razpored(mere)
        el.append(("kvadrat", (0.0, sp[0], sirina, sp[1] - sp[0]), "POSTS"))
        el.append(("kvadrat", (0.0, zg[0], sirina, zg[1] - zg[0]), "POSTS"))
        for z0, z1 in lamele:
            el.append(("kvadrat", (0.0, z0, sirina, z1 - z0), "OUTLINE"))
        poz, _raz = risba.pozicije_nosilcev(sirina, mere.get("razmak_nosilcev", 2500.0))
        for x in poz:
            el.append(("kvadrat", (x - 40.0, odcep, 80.0, visina - odcep), "POSTS"))
    elif tip == "pokončna":
        r = risba.razpored_pokoncna(mere)
        for x in r["centri"]:
            el.append(("kvadrat", (x - mere["steber_sirina"] / 2.0, odcep,
                                   mere["steber_sirina"], visina - odcep), "POSTS"))
        for x in r["deske_x"]:
            el.append(("kvadrat", (x, r["deske_z"][0], mere["deska_sirina"],
                                   r["deske_h"]), "OUTLINE"))
        # ročaj
        if r.get("rocaj") is not None:
            z0, z1 = r["rocaj"]
            el.append(("kvadrat", (0.0, z0, sirina, z1 - z0), "POSTS"))
    else:
        raise ValueError(f"Neznan tip segmenta {tip!r} — dovoljeno: "
                         "ograja, pokončna.")

    # Vrata in prehodi v segmentu (odprtine v polnilu).
    for i, v in enumerate(vrata_sez or [], start=1):
        H_o_v = float(v.get("visina") or 0)
        if H_o_v + odcep > visina + 1e-9:
            raise ValueError(
                f"Vrata {i}: višina {H_o_v:g} z odcepom {odcep:g} presega "
                f"višino ograje {visina:g}.")
        g = vrata.geometrija_vrat(v, v.get("sirina", 900.0), H_o_v)
        for vrsta, podatki, plast in vrata.elementi_vrat(g):
            if vrsta == "kvadrat":
                px, py, pw, ph = podatki
                el.append(("kvadrat", (px + v.get("x", 0.0), py + odcep, pw, ph),
                           plast))
            elif vrsta == "crta":
                x1, y1, x2, y2 = podatki
                el.append(("crta", (x1 + v.get("x", 0.0), y1 + odcep,
                                    x2 + v.get("x", 0.0), y2 + odcep), plast))
            elif vrsta == "krog":
                cx, cy, d = podatki
                el.append(("krog", (cx + v.get("x", 0.0), cy + odcep, d), plast))
    for p in prehodi_sez or []:
        H_o_p = float(p.get("visina") or 0)
        if H_o_p + odcep > visina + 1e-9:
            raise ValueError(
                f"Prehod: višina {H_o_p:g} z odcepom {odcep:g} presega "
                f"višino ograje {visina:g}.")
        g = vrata.geometrija_prehoda(p, p.get("sirina", 1000.0), H_o_p)
        for vrsta, podatki, plast in vrata.elementi_prehoda(g):
            if vrsta == "kvadrat":
                px, py, pw, ph = podatki
                el.append(("kvadrat", (px + p.get("x", 0.0), py + odcep, pw, ph),
                           plast))
    return el


def _narisi_elemente(msp, el, dx=0.0, rot=0.0):
    """Nariše elemente z zamikom dx (rotacija v1 ni vključena — glej omejitve)."""
    for vrsta, podatki, plast in el:
        if vrsta == "kvadrat":
            x, y, w, h = podatki
            kvadrat(msp, x + dx, y, w, h, plast)
        elif vrsta == "crta":
            x1, y1, x2, y2 = podatki
            crta(msp, x1 + dx, y1, x2 + dx, y2, plast)
        elif vrsta == "krog":
            cx, cy, d = podatki
            krog(msp, cx + dx, cy, d, plast)


# ---------------------------------------------------------------------------
# Glavni izvoz
# ---------------------------------------------------------------------------

def segmenti_iz_cfg(cfg):
    """Razpakira segmente iz cfg (shema v2) ali sestavi enega (shema v1)."""
    if cfg.get("segmenti"):
        segmenti: list = []
        for s in cfg["segmenti"]:
            if not isinstance(s, dict):
                raise ValueError(f"Segment {len(segmenti) + 1} mora biti "
                                 "objekt (dict).")
            mere_s = s.get("mere")
            if mere_s is not None and not isinstance(mere_s, dict):
                raise ValueError(f"Segment {s.get('ime') or len(segmenti) + 1}: "
                                 "'mere' mora biti objekt.")
            tip = jedro.normaliziraj_predlogo(
                s.get("tip") or cfg.get("predloga"))
            if tip not in ("ograja", "pokončna"):
                raise ValueError(f"Segment {s.get('ime') or len(segmenti) + 1}: "
                                 f"neznan tip {s.get('tip')!r} — dovoljeno: "
                                 "ograja, pokončna.")
            mere = dict(cfg.get("mere") or {})
            mere.update(mere_s or {})
            mere = risba.zdruzi({"mere": mere})["mere"]
            segmenti.append({
                "ime": s.get("ime") or f"S{len(segmenti) + 1}",
                "tip": tip,
                "mere": mere,
                "kot": float(s.get("kot") or 0.0),
                "vrata": s.get("vrata") or [],
                "prehodi": s.get("prehodi") or [],
            })
        return segmenti
    mere = risba.zdruzi(cfg)["mere"]
    return [{
        "ime": "Glavni",
        "tip": jedro.normaliziraj_predlogo(cfg.get("predloga")),
        "mere": mere,
        "kot": 0.0,
        "vrata": cfg.get("vrata") or [],
        "prehodi": cfg.get("prehodi") or [],
    }]


def izvozi_dxf(cfg, pot=None):
    """Izvozi DXF iz konfiguracije (isti cfg kot risba.generiraj).

    Vrne (pot, porocilo) kjer je porocilo slovar iz ``preveri_dxf``.
    """
    cfg = risba.zdruzi(cfg)
    napake = risba.preveri_cfg(cfg)
    if napake:
        raise ValueError("Neveljavna konfiguracija: " + "; ".join(napake))
    if pot is None:
        pot = os.path.splitext(cfg["izhod"])[0] + ".dxf"

    doc = ezdxf.new("R2010", setup=True)
    doc.units = ez_units.MM
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    doc.header["$AUNITS"] = 0
    _plasti(doc)
    msp = doc.modelspace()

    segmenti = segmenti_iz_cfg(cfg)
    x0 = 0.0
    for s in segmenti:
        el = _elementi_segmenta(s["mere"], s["tip"], s["vrata"], s["prehodi"])
        _narisi_elemente(msp, el, dx=x0)
        sirina = s["mere"]["sirina"]
        visina = s["mere"]["visina"]
        # Kote segmenta (lokalno).
        kota_h(msp, x0, x0 + sirina, -120.0, -120.0, sirina)
        kota_v(msp, 0.0, visina, x0 - 120.0, x0 - 120.0, visina)
        tekst(msp, x0, visina + 40.0,
              f"{s['ime']} — {s['tip']} {vrata.fmt_mm(sirina)}x{vrata.fmt_mm(visina)}")
        x0 += sirina + MED_RAZMAK

    # F1 (issue #5, O1): skupna dolžina = vsota ŠIRIN segmentov — risalni
    # razmiki (MED_RAZMAK) so samo postavitev na listu in se NE štejejo.
    skupna_dolzina = sum(s["mere"]["sirina"] for s in segmenti)
    if len(segmenti) > 1:
        kota_h(msp, 0.0, skupna_dolzina, -300.0, -300.0, skupna_dolzina)

    # Opombe (na plasti TEXT, nad risbo). Kadar je v projektu podan kot med
    # segmenti, to izrecno povemo: ta izvoz riše segmente v skupni ravnini,
    # tiho ravnanje pa bi uporabniku dalo napačen tloris (vogali so
    # načrtovana razširitev — glej docs/dxf-specifikacija.md).
    opombe = list(OPOMBE_DXF)
    if any(s["kot"] for s in segmenti):
        opombe.append("Kot med segmenti (vogali) NI narisan — segmenti so v "
                      "skupni ravnini; tloris z vogali je načrtovana "
                      "razširitev.")
    y_op = max(s["mere"]["visina"] for s in segmenti) + 120.0
    for i, op in enumerate(opombe):
        tekst(msp, 0.0, y_op + i * 12.0, f"{i + 1}. {op}")

    _naslovni_blok(doc, cfg, skupna_dolzina)

    auditor = doc.audit()
    if auditor.errors:
        raise ValueError(f"DXF audit napake: {auditor.errors}")
    doc.saveas(pot)

    porocilo = preveri_dxf(pot)
    if not porocilo["veljaven"]:
        raise ValueError(f"DXF preverjanje ni uspelo: {porocilo['napake']}")
    return pot, porocilo


def _naslovni_blok(doc, cfg, skupna_dolzina):
    """Okvir ISO 5457 + naslovni blok v papirnem layoutu (A3)."""
    layout = doc.layouts.new("LIST 1 (A3)")
    msp_p = layout
    # Okvir lista (papirni mm).
    kvadrat(msp_p, 5.0, 5.0, 410.0, 287.0, "FRAME")
    for i in range(1, 9):
        crta(msp_p, 5.0 + i * 51.25, 5.0, 5.0 + i * 51.25, 292.0, "FRAME")
    for j in range(1, 6):
        crta(msp_p, 5.0, 5.0 + j * 47.83, 415.0, 5.0 + j * 47.83, "FRAME")
    # Naslovni blok.
    kvadrat(msp_p, 250.0, 10.0, 160.0, 38.0, "FRAME")
    p = {k: cfg.get(k) for k in ("ime", "stranka", "risba_st", "rev", "datum",
                                 "material", "izdelal", "pregledal", "odobril")}
    vrstice = [
        (f"{p['ime'] or 'PROJEKT'}", 3.0),
        (f"NAROČNIK: {p['stranka'] or '—'}   RISBA ŠT.: {p['risba_st'] or '—'}"
         f"   REV.: {p['rev'] or '—'}", 2.2),
        (f"MATERIAL: {p['material'] or '—'}   MERILO: 1:1 (model)", 2.2),
        (f"DATUM: {p['datum'] or '—'}   FORMAT: A3   LIST: 1/1", 2.2),
        (f"IZDELAL: {p['izdelal'] or '—'}   PREGLEDAL: {p['pregledal'] or '—'}"
         f"   ODOBRIL: {p['odobril'] or '—'}", 2.2),
        (f"Skupna dolžina postavitve: {vrata.fmt_mm(skupna_dolzina)} mm", 2.2),
    ]
    y = 44.0
    for niz, visina in vrstice:
        y -= visina + 3.0
        tekst(msp_p, 253.0, y, niz, visina=visina, layer="TEXT")


# ---------------------------------------------------------------------------
# Preverjanje kakovosti
# ---------------------------------------------------------------------------

def preveri_dxf(pot):
    """Preveri DXF datoteko: audit, round-trip, plasti, zaprtost, dvojniki.

    Vrne slovar: {"veljaven": bool, "napake": [...], "stevila": {plast: n},
                  "dxfversion": ..., "insunits": ...}.
    """
    napake = []
    if not os.path.exists(pot) or os.path.getsize(pot) == 0:
        return {"veljaven": False, "napake": ["datoteka ne obstaja ali je prazna"],
                "stevila": {}}

    doc = ezdxf.readfile(pot)
    auditor = doc.audit()
    if auditor.errors:
        napake.append(f"audit napake: {auditor.errors}")
    if doc.dxfversion != "AC1024":
        napake.append(f"pričakovana različica AC1024, dobljena {doc.dxfversion}")
    if doc.header.get("$INSUNITS", 0) != 4:
        napake.append(f"$INSUNITS mora biti 4 (mm), dobljeno {doc.header.get('$INSUNITS')}")

    plasti = {l.dxf.name for l in doc.layers}
    manjkajoce = set(PLASTI) - plasti
    if manjkajoce:
        napake.append(f"manjkajoče plasti: {sorted(manjkajoce)}")

    msp = doc.modelspace()
    stevila: dict = {}
    videne = set()
    for e in msp:
        layer = e.dxf.layer
        stevila[layer] = stevila.get(layer, 0) + 1
        if layer in PLASTI and PLASTI[layer][3] and e.dxftype() == "LWPOLYLINE":
            lw = cast(Any, e)   # ezdxf stubs ne ožijo DXFGraphic → LWPOLYLINE
            if not lw.closed:
                napake.append(f"odprta kontura na {layer}")
            tocke = list(lw.get_points("xy"))
            if len(tocke) < 3:
                napake.append(f"kontura z < 3 točkami na {layer}")
            if tocke and tocke[0] == tocke[-1] and lw.closed:
                napake.append(f"ponovljena prva točka na {layer}")
        kljuc = (e.dxftype(), layer, str(e.dxf.handle))
        if kljuc in videne:
            napake.append(f"podvojena entiteta {kljuc}")
        videne.add(kljuc)

    rezalne = [ime for ime, (_b, _l, _w, rez) in PLASTI.items() if rez]
    if not any(stevila.get(ime) for ime in rezalne):
        napake.append("na rezalnih plasteh (M-ELEM-CONT/M-STEB-CONT/"
                      "M-ODPR-CONT; legacy OUTLINE/POSTS/HOLES) "
                      "ni rezalne geometrije")

    return {
        "veljaven": not napake,
        "napake": napake,
        "stevila": stevila,
        "dxfversion": doc.dxfversion,
        "insunits": doc.header.get("$INSUNITS"),
    }
