# -*- coding: utf-8 -*-
"""Proizvodnja (production) — kanonični model količin in vrstice izpisov.

F2 (issue #5): izločeno iz monolita risba.py BREZ spremembe vedenja.
Vse količine štejejo iz ENEGA proizvodni_model (issue #6, §3).
"""
import vrata as vrat
import jedro

from jedro import (fmt, fmt_vejica, razpored, razpored_pokoncna,
                   razdeli_po_odprtinah,
                   pozicije_nosilcev, vrata_podatki,
                   pokoncna_pravila, st_vodoravnih_cevi,
                   odmik_vijak_max, opomba_kratkih_kosov)

def _dokazilo_vrstica(v):
    """Vrstica z merami in virom za rešeno katalogsko vrstico (brez ugibanja)."""
    mere = []
    for ime, vrednost in v["dimenzije"].items():
        if isinstance(vrednost, dict):
            if "nominal" in vrednost:
                besedilo = "%g" % vrednost["nominal"]
            elif "min" in vrednost and "max" in vrednost:
                besedilo = "%g..%g" % (vrednost["min"], vrednost["max"])
            elif "min" in vrednost:
                besedilo = "%g" % vrednost["min"]
            elif "max" in vrednost:
                besedilo = "%g" % vrednost["max"]
            else:
                continue
        elif isinstance(vrednost, (int, float)):
            besedilo = "%g" % vrednost
        else:
            continue
        mere.append(f"{ime} {besedilo} mm")
        if len(mere) == 3:
            break
    vrstica = (f"- {v['standard']} {v['designation']} ({v['profil']}): "
               + "; ".join(mere))
    if v["provenenca"]:
        vir = v["provenenca"][0]
        vrstica += (f" — vir: {vir.get('name', '?')} "
                    f"(dostopano {vir.get('accessed', '?')})")
        if len(v["provenenca"]) > 1:
            vrstica += f" [in še {len(v['provenenca']) - 1} virov]"
    return vrstica


def _kataloska_vrstica(ref):
    """Reši katalogsko referenco pritrdila in vrni dokazilno vrstico."""
    from mechanical.resolver import razresi

    try:
        v = razresi(ref["designation"], ref["standard"],
                    ref.get("profil", "iso"))
    except (KeyError, TypeError) as napaka:
        raise ValueError(
            "kataloška referenca pritrdila je nepopolna: %r" % (ref,)) from napaka
    return _dokazilo_vrstica(v)


def _kataloska_blok(c):
    """Vrstice »PRITRDILA — katalog« za naročilo, če so v cfg podane reference."""
    refi = [r for r in (c.get("vijak_lamela_ref"),
                        c.get("vijak_nosilec_ref")) if r]
    if not refi:
        return []
    return (["", "PRITRDILA — katalog (dokazila):"]
            + [_kataloska_vrstica(r) for r in refi])


def vrata_dokazila_vrstice(vp):
    """Dokazila kataloških pritrdil vseh vratnih kosovnic (za naročilo)."""
    viri = {}
    for enota in vp["vrata"] + vp["prehodi"]:
        viri.update(vrat.kataloski_viri(enota["kosovnica"]))
    if not viri:
        return []
    return (["", "PRITRDILA VRAT — katalog (dokazila):"]
            + [_dokazilo_vrstica(v) for _ozn, v in sorted(viri.items())])


def vrata_vrstice_kolicin(vp):
    """Postavke vrat/prehodov za količine (5-tuple, kot ostale postavke)."""
    vrstice = []
    for enota in vp["vrata"] + vp["prehodi"]:
        ozn = enota["oznaka"]
        for naziv, kol, enota_m, kljuc in vrat.kupljene_vrstice(enota["kosovnica"]):
            vrstice.append((f"VRATA {ozn} — {naziv}", f"{fmt(kol)}", enota_m,
                            kljuc, float(kol)))
        for ozn_k, dol, sir_k, kol, opis, _kljuc in enota["kosovnica"]["izdelani"]:
            vrstice.append((f"VRATA {ozn} — {opis} ({ozn_k})",
                            f"{kol} × {fmt(dol)} mm", "kos", None,
                            float(kol)))
    return vrstice


def vrata_vrstice_potrebscine(vp):
    """Vrstice »VRATA/PREHODI« za tabelo potrebščin na montažnem listu."""
    vrstice = []
    for enota in vp["vrata"] + vp["prehodi"]:
        ozn = enota["oznaka"]
        g = enota["g"]
        sir = g["odprtina"]["sirina"]
        vis_o = g["odprtina"]["visina"]
        vrstice.append([f"{ozn} ({g['tip']})", f"{fmt(sir)} × {fmt(vis_o)} mm",
                        "1 kompletno", f"x = {fmt(g['x'])} mm"])
        for ozn_k, dol, sir_k, kol, opis, _kljuc in enota["kosovnica"]["izdelani"]:
            vrstice.append([f"  {opis} ({ozn_k})", f"{fmt(dol)} mm",
                            f"{kol} kos", f"profil {fmt(sir_k)} mm"])
        for ozn_k, kol, enota_m, _kljuc, opis in enota["kosovnica"]["kupljeni"]:
            vrstice.append([f"  {opis} ({ozn_k})", "—", f"{fmt(kol)} {enota_m}",
                            "kupljeno"])
    return vrstice


# --------------------------------------------- kanonični proizvodni model (issue #6)
def proizvodni_model(c):
    """KANONIČNI izračun količin — EN vir resnice za vse izpise.

    Tabela sestavnih delov (PDF stran 1), potrebščine montažnega lista,
    količine, kosovnica in naročilo smejo šteti SAMO iz tega modela —
    noben izpis ne izvaja lastnih vzporednih formul (issue #6, §3).

    Konstrukcijska pravila pritrjevanja (dokumentirana; F1/issue #5, O3):
    - pokončna (B2): deska v polju se prek MONTAŽNIH LETVI (za deskami)
      pritrdi na nosilno konstrukcijo — 2 vijaka na rob deske => 4 na
      desko. Deska, ki jo odprtina razreže, ohrani oba robova (stika) =>
      prav tako 4; deska znotraj odprtine odpade => 0. Štejejo se ROBOVI
      kosov (vijaki na risbi so na robovih desk — kot štetje).
    - prečna: vsaka lamele se pritrdi na vsak nosilec, ki ga prečka,
      z 2 vijakoma => 2 × Σ (prisotnost materiala na legi nosilca).
    - ankerji/pritrdila nosilca: 2 na nosilec/steber.
    Odprtine (vrata/prehodi) vplivajo na število kosov in pritrdila.
    """
    m = c.get("mere") or {}
    vp = vrata_podatki(c)
    odprtine = vp["odprtine"]
    predloga = c.get("predloga") or "ograja"
    # issue #6 (past pod-agenta): neznana/pomotoma zapisana predloga (npr.
    # ASCII "pokoncna") ne sme TIHO pasti v prečno vejo — jasna napaka.
    if predloga not in ("ograja", "pokončna"):
        raise ValueError(
            f"Neznana predloga {predloga!r} (dovoljeno: ograja, pokončna)")
    if predloga == "pokončna":
        p = razpored_pokoncna(m)
        ds = float(m.get("deska_sirina", 0) or 0)
        n_kosov = 0
        n_stikov = 0
        for xr in p["deske_x"]:
            intervali = razdeli_po_odprtinah(xr, xr + ds, odprtine)
            n_kosov += len(intervali)
            # stik = rob kosa, ki sovpada z robom deske (pritrditev na steber)
            if any(abs(a - xr) < 1e-6 for a, _b in intervali):
                n_stikov += 1
            if any(abs(b - (xr + ds)) < 1e-6 for _a, b in intervali):
                n_stikov += 1
        n_s = p["n_stebrov"]
        return {"tip": "pokoncna", "n_kosov": n_kosov,
                "n_brez_odprtin": p["n_desk"], "n_nosilcev": n_s,
                "n_stikov": n_stikov,
                "vijaki_element": n_stikov * 2,
                "pritrdila_nosilec": n_s * 2,
                # F1 (O3): montažne letve za deskami (vodoravne cevi) — prej
                # sploh niso bile v modelu/BOM, čeprav so fizični nosilec.
                # Število na polje iz navodil proizvajalca (MONTAZE_PROFILAV):
                # vse nepodprte razdalje (tudi robovi desk) ≤ razmak med
                # vodoravnima cevema; brez pravila ostane najmanj 2 na polje.
                "montazne_letve": st_vodoravnih_cevi(
                    p["deske_h"], c.get("profil")) * len(p["polja"]),
                "dolzina_elementa": p["deske_h"], "opis_elementa": "deska"}
    zg, sp, lamele, vrzel, n = razpored(m)
    xs_nos, razmak_dejanski = pozicije_nosilcev(
        m.get("sirina", 0) or 0, m.get("razmak_nosilcev", 1000) or 1000)
    n_kosov = 0
    stikov = 0
    for _z0, _z1 in lamele:
        intervali = razdeli_po_odprtinah(0, m.get("sirina", 0) or 0, odprtine)
        n_kosov += len(intervali)
        for xn in xs_nos:
            if any(a - 1e-6 <= xn <= b + 1e-6 for a, b in intervali):
                stikov += 1
    n_nos = len(xs_nos)
    return {"tip": "ograja", "n_kosov": n_kosov,
            "n_brez_odprtin": n, "n_nosilcev": n_nos,
            "n_stikov": stikov, "vijaki_element": stikov * 2,
            "pritrdila_nosilec": n_nos * 2,
            "dolzina_elementa": m.get("sirina", 0) or 0,
            "opis_elementa": "lamela", "razmak_dejanski": razmak_dejanski}
# =================== UI/UX Plan A: čisti izračun (brez risanja) ===================
def _opomba_kataloske_dolzine(c, spec):
    """Opozorilo, če nabavne dolžine niso kataloške za profil DESKA.

    Za deske so dolžine izrecno naštete (DESKA-150: 4000/2200 mm,
    DESKA-128: 2200 mm); za romb so dovoljene tudi druge tovarniške
    dolžine (razrez čez več dolžin — glej README), zato se ne opozarja.
    """
    if not spec or spec.get("tip") != "deska":
        return None
    dl = c.get("dolzine_deske") or [c.get("dolzina_deske", 5800)]
    kataloske = {float(d) for d in spec.get("nakupne_dolzine_mm") or ()}
    tuje = [d for d in dl if float(d) not in kataloske]
    if not tuje:
        return None
    return ("- POZOR: nastavljene nabavne dolžine ("
            + ", ".join(f"{fmt(float(d))}" for d in tuje) + " mm) niso "
            f"kataloške za {spec['ime']} ("
            + ", ".join(f"{fmt(d)}" for d in spec["nakupne_dolzine_mm"])
            + " mm) — preveri pri dobavitelju.")


def _nar_posebnosti(spec, pritrditev, temp_c=None, dolzina_deske_mm=None,
                    barva=None):
    """Vrstice naročila: elementi, odmiki vijaka, posebnosti vrtanja."""
    v = []
    if spec and spec.get("dimenzija_mm"):
        dim = "×".join(fmt_vejica(x) for x in spec["dimenzija_mm"])
        dol = spec.get("nakupne_dolzine_mm") or ()
        v.append(
            "- Dimenzija profila: " + dim
            + (("×" + " / ".join(fmt_vejica(x) for x in dol)) if dol else "")
            + " mm"
            + (" (naleganje na "
               + " ali ".join(fmt(x) for x in spec["montazne_sirine_mm"])
               + ")" if spec.get("montazne_sirine_mm") else "")
            + (" (samo za pokončno ograjo)"
               if spec.get("uporaba") == ("pokončna",) else "") + ".")
    r1, r2 = jedro.ROCAJI["standardni"], jedro.ROCAJI["polni"]
    d1, d2 = r1["dimenzija_mm"], r2["dimenzija_mm"]
    dn = r2["notranja_dimenzija_mm"]
    v.append(
        f"- Ročaj: {fmt(d1[0])}×{fmt(d1[1])}×{fmt(d1[2])} mm "
        f"({r1['opomba']}) ali {fmt(d2[0])}×{fmt(d2[1])}×{fmt(d2[2])} mm "
        f"(notranja dimenzija {fmt(dn[0])}×{fmt(dn[1])} mm). Samostojna "
        "prodaja ročajev ni možna. Vijači se v razmaku 50 cm "
        f"({fmt(jedro.ROCAJI['vijak_razmak_mm'])} mm) skozi ročaj v "
        "konstrukcijo (od zgoraj navzdol, vijak viden); predvrtje "
        f"{fmt_vejica(jedro.ROCAJI['vrtina_odmik_mm'])} mm večje od "
        "vijaka.")
    min_o = fmt(jedro.Pritrditev_DESK["odmik_vijak_min_mm"])
    max_o = odmik_vijak_max(pritrditev)
    if max_o is not None:
        v.append(
            f"- Odmik vijaka od roba reza: najmanj {min_o} mm, največ "
            f"{fmt(max_o)} mm (konstrukcija "
            + ("bočno na ploščo"
               if max_o == jedro.Pritrditev_DESK["odmik_vijak_max_bocno_mm"]
               else "na ploščo") + ").")
    else:
        v.append(
            f"- Odmik vijaka od roba reza: najmanj {min_o} mm; največ "
            f"{fmt(jedro.Pritrditev_DESK['odmik_vijak_max_na_plosco_mm'])} "
            "mm (konstrukcija na ploščo) oziroma "
            f"{fmt(jedro.Pritrditev_DESK['odmik_vijak_max_bocno_mm'])} mm "
            "(bočno na ploščo).")
    if barva and spec:
        v.append(f"- Barvni odtenek: "
                 f"{jedro.ujemanje_barve(barva, spec) or barva}.")
    if spec and spec.get("barve"):
        v.append("- Barvna paleta ("
                 + f"{len(spec['barve'])} barv"
                 + (f", {spec['st_povrsin']} površine"
                    if spec.get("st_povrsin") else "")
                 + "): " + ", ".join(spec["barve"]) + ".")
        v.append("- " + jedro.WOODCORE["barve_opomba_dobave"]
                 + " Posvetlitev prvo leto: "
                 + jedro.WOODCORE["posvetlitev_prvo_leto"] + ".")
    elif spec and spec.get("st_barv"):
        v.append(f"- Barvna paleta: na voljo {spec['st_barv']} barvnih "
                 "različic"
                 + (f" in {spec['st_povrsin']} površine"
                    if spec.get("st_povrsin") else "")
                 + " za ta profil — preveri izbrani odtenek.")
    v.append("- Skladiščenje: " + jedro.SKLADISCENJE_OPOMBA)
    if spec and spec.get("vrtina_kompozit_manjsa"):
        v.append(
            "- Vrtanje (posebnost profila): v kompozitni material luknja "
            "MANJŠA od vijaka, v konstrukcijo VEČJA — omogoči se "
            "raztezanje materiala."
            + (f" Vijak: {spec['vijak_dolzina_opis']}."
               if spec.get("vijak_dolzina_opis") else ""))
    # WoodCore splošna navodila (en vir resnice v jedro.py)
    w = jedro.WOODCORE
    v.append("- OPOZORILO: " + w["nosilnost_opozorilo"])
    v.append(f"- Garancija {w['garancija_let']} let: ne cepijo, ne razpadajo, "
             "ne gnijejo; izjeme: " + w["garancija_izjeme"] + ".")
    if spec and spec.get("drenazne_luknje"):
        d = w["drenazne_luknje"]
        v.append(f"- Drenažne luknje: fi {fmt_vejica(d['fi_mm'])} mm s "
                 f"spodnje strani, cca {fmt(d['odmik_od_roba_mm'])} mm od "
                 f"roba, v vsak prekat — {d['namen']}.")
    v.append("- Vijaki: " + w["vijaki"])
    if temp_c is not None and dolzina_deske_mm:
        gap = jedro.razmak_desk_mm(float(temp_c), dolzina_deske_mm / 1000)
        v.append(f"- Razmak med deskami: {fmt_vejica(gap)} mm (dolžina deske "
                 f"{fmt(dolzina_deske_mm)} mm, montaža pri "
                 f"{fmt_vejica(float(temp_c))} °C — tabela WoodCore); min. "
                 f"{fmt(w['odmik_od_sten_mm'])} mm odmik deske od vseh "
                 "sten.")
        if float(temp_c) < w["montazna_temp_min_c"]:
            v[-1] += (f" POZOR: montaža pod "
                      f"{fmt_vejica(w['montazna_temp_min_c'])} °C po "
                      "navodilih proizvajalca ni primerna.")
    v.append("- Orodja: " + w["orodja"])
    if barva and ("rustic" in str(barva).lower()
                  or "rustik" in str(barva).lower()):
        v.append("- " + w["barve_opomba_rustic"])
    return v


def izracunaj_kolicine(c, rp=None):
    """Količine/naročilo/kosovnica BREZ risanja (UI/UX Plan A).

    EN vir resnice (issue #6): `risba.narisi_montazni_*` za povratne
    vrednosti kličeta TO funkcijo, `vmesnik` pa za živi povzetek.
    Formule so izločene iz risba.py brez spremembe.

    rp: že izračunani razrez (če ga klicatelj ima) — sicer se izračuna.
    Vrne {"postavke", "narocilo", "ostanki_posodobitev", "kosovnica",
    "skupine_reza" (kosi po profilih za CNC), "kerf"}.
    """
    import datetime
    from jedro import (traki_nabava, romb_montaza, romb_zaklucek,
                       deska_montaza, montaza_profila)
    from razrez import (razrez_podatki, razrez_kosov_podatki, stevilo_palic)

    predloga = c.get("predloga") or "ograja"
    if predloga not in ("ograja", "pokončna"):
        raise ValueError(
            f"Neznana predloga {predloga!r} (dovoljeno: ograja, pokončna)")

    m = c["mere"]
    profil = c.get("profil") or ("POLNA DESKA 100" if predloga == "pokončna"
                                 else "ROMB 67")
    barva = c.get("barva") or "Antracit"
    dl_palice = c.get("dolzina_palice", 6000)
    kerf = c.get("kerf", 3.0)
    vp = vrata_podatki(c)

    if predloga == "pokončna":
        sir, vis = m["sirina"], m["visina"]
        p = razpored_pokoncna(m)
        n_d, n_s = p["n_desk"], p["n_stebrov"]
        deska_h = p["deske_h"]
        vijak_lamela_naziv = (c.get("vijak_lamela")
                              or "Vijak M8×70 (deska↔steber)")
        vijak_nosilec_naziv = c.get("vijak_nosilec") or "Anker M10"
        if vp["odprtine"]:
            kosi_d = []
            for xr in p["deske_x"]:
                kosi_d += razdeli_po_odprtinah(
                    xr, xr + (m.get("deska_sirina", 100) or 100),
                    vp["odprtine"])
            n_eff = len(kosi_d)
        else:
            n_eff = n_d
            kosi_d = [(f"D{i + 1}", float(deska_h)) for i in range(n_eff)]
        model = proizvodni_model(c)
        if rp is None:
            rp = razrez_podatki(deska_h, n_eff, c, oznaka="D",
                                glava="DESKE ŠT.")
        traki = rp["traki"]
        kos_iz_ost = rp["iz_ost_kos"]
        kos_v: list = []
        if vp["vrata"] or vp["prehodi"]:
            for enota in vp["vrata"] + vp["prehodi"]:
                for ozn_k, dol, _s, kol, _op, _kl in \
                        enota["kosovnica"]["izdelani"]:
                    for _ in range(int(kol)):
                        kos_v.append((f"{enota['oznaka']}-{ozn_k}",
                                      float(dol)))
            if kos_v:
                rv = razrez_kosov_podatki(kos_v, c, oznaka="V",
                                          glava="VRATA ŠT.")
                rp["rez_rows"] += rv["rez_rows"][1:]
                rp["viz_traki"] += rv["viz_traki"]
        steber_dim = f"{fmt(m['steber_sirina'])}×{fmt(m['steber_debelina'])}"
        palice_s = stevilo_palic(vis, n_s, dl_palice, kerf)
        vijaki = model["vijaki_element"]
        datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
        nar = [
            f"NAROČILO — WPC material "
            f"({c.get('dobavitelj') or 'WoodCore'})",
            f"Naloga: {c['risba_st']} • Datum: {datum}",
            f"Stranka: {c.get('stranka') or '—'} • Objekt: "
            f"{c.get('objekt') or '—'}",
            "",
            "DESKE:",
            f"- {profil}, barva {barva}"
            + "".join(f" — {t} kos × {fmt(B)} mm"
                      for B, t in traki_nabava(traki))
            + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
            "",
            "PROFILI (aluminij):",
            f"- {steber_dim} — {palice_s} kos × {fmt(dl_palice)} mm "
            f"(razrez: {n_s} × {fmt(vis)} mm — stebri)",
            "",
            "OSTALA PRITRDITVA:",
            f"- Ročaj — 1 kos × {fmt(sir)} mm",
            f"- Osnove za steber — {n_s} kos",
            f"- {vijak_lamela_naziv} — {vijaki} kos",
            f"- {vijak_nosilec_naziv} — {n_s * 2} kos",
        ]
        # navodila za pokončno ograjo (MONTAZE_PROFILAV / jedro.py)
        spec_p = montaza_profila(profil)
        pr_p = pokoncna_pravila(profil)
        if pr_p:
            n_cevi = st_vodoravnih_cevi(deska_h, profil)
            nar += [
                "",
                f"MONTAŽA POKONČNO ({spec_p['ime']}):",
                f"- Vodoravne cevi (montažne letve): {n_cevi} na polje = "
                f"{model['montazne_letve']} kos — razmak med vodoravnima "
                f"cevema največ {fmt(pr_p['razmak_max_vodoravne_cevi_mm'])} "
                "mm.",
            ]
            if pr_p.get("kotnik_na_vodoravne_cevi"):
                nar += [f"- L-kotniki na vodoravnih ceveh — "
                        f"{n_d * n_cevi} kos (skozi kotnik se pritrjuje romb "
                        "— skrito vijačenje)."]
            if spec_p.get("opomba_alu_vidna_pokoncno"):
                nar += ["- " + spec_p["opomba_alu_vidna_pokoncno"]]
            if pr_p.get("skrito_vijacenje"):
                nar += ["- Skrito vijačenje — vijaki niso vidni na licu."]
            if spec_p.get("montazne_sirine_mm"):
                nar += ["- Montaža na širino "
                        + " ali ".join(f"{fmt(d)} mm"
                                       for d in spec_p["montazne_sirine_mm"])
                        + "."]
            if spec_p.get("pritrditev_od_spredaj"):
                nar += [f"- Pritrditev od spredaj skozi desko — vijaki VIDNI "
                        f"na licu; predvrtje — luknja "
                        f"{fmt_vejica(spec_p['vrtina_odmik_mm'])} mm večja od "
                        f"vijaka; vijak {spec_p['lega_vijaka']}."]
        nar += _nar_posebnosti(montaza_profila(profil),
                              c.get("pritrditev"), c.get("montazna_temp_c"),
                              max((B for B, _ in traki), default=0), barva)
        opomba_dl = _opomba_kataloske_dolzine(c, montaza_profila(profil))
        if opomba_dl:
            nar += [opomba_dl]
        nar += _kataloska_blok(c)
        por_s = sum(B for B, _ in traki) / 1000
        por_st = palice_s * dl_palice / 1000
        kosovnica = rp["kosovnica"]
        wpc_postavke = [f"{B / 1000:.1f} m ({t} kos)"
                        for B, t in traki_nabava(traki)]
        v_vrst = vrata_vrstice_kolicin(vp)
        for enota in vp["vrata"] + vp["prehodi"]:
            for ozn_k, dol, _s, kol, _op, _kl in \
                    enota["kosovnica"]["izdelani"]:
                for _ in range(int(kol)):
                    kosovnica.append((f"{enota['oznaka']}-{ozn_k}", dol,
                                      "vrata", barva))
        nar += opomba_kratkih_kosov(kosovnica)
        skupine_reza = [{"oznaka": "DESKE", "kosi": list(kosi_d)},
                        {"oznaka": "VRATA", "kosi": list(kos_v)}]
        return {"postavke": [
            (f"WPC deske {profil} (nabava: "
             + " + ".join(wpc_postavke) + ")",
             f"{fmt(por_s)} m", "m", "wpc_deska_m", por_s),
            ("Alu stebri (nabava)", f"{palice_s} kos = {fmt(por_st)} m", "m",
             "alu_m", por_st),
            ("Ročaj", "1", "kos", "rocaj_kos", 1),
            ("Osnove za steber", f"{n_s}", "kos", "osnova_kos", n_s),
            (vijak_lamela_naziv, f"{vijaki}", "kos", "vijak_kos", vijaki),
            (vijak_nosilec_naziv, f"{n_s * 2}", "kos", "anker_kos", n_s * 2),
        ] + v_vrst,
            "narocilo": "\n".join(nar) + (("\n\nVRATA/PREHODI:\n" + "\n".join(
                f"- {vr[0]}: {vr[1]} {vr[2]}"
                for vr in vrata_vrstice_potrebscine(vp)))
                + "\n".join(vrata_dokazila_vrstice(vp))
                if vp["vrata"] or vp["prehodi"] else ""),
            "ostanki_posodobitev": rp["ostanki_posodobitev"],
            "kosovnica": kosovnica,
            "skupine_reza": skupine_reza,
            "kerf": kerf}

    # ---- prečna (ograja) ----
    sir = m["sirina"]
    zg, sp, lamele, vrzel, n = razpored(m)
    raz = m.get("razmak_nosilcev", 1000)
    xs_nos, _razmak = pozicije_nosilcev(sir, raz)
    n_nos = len(xs_nos)
    model = proizvodni_model(c)
    vijaki = model["vijaki_element"]
    vijak_lamela_naziv = (c.get("vijak_lamela")
                          or "RF vijak M8×70 (lamela↔profil)")
    vijak_nosilec_naziv = (c.get("vijak_nosilec")
                           or f"Pritrdilni vijaki za "
                             f"{c.get('podlaga') or 'podlago'}")
    if vp["vrata"] or vp["prehodi"]:
        kosi_l: list = []
        for _z0, _z1 in lamele:
            for xa, xb in razdeli_po_odprtinah(0, sir, vp["odprtine"]):
                kosi_l.append((f"L{len(kosi_l) + 1}", xb - xa))
        if rp is None:
            rp = razrez_kosov_podatki(kosi_l, c, oznaka="L",
                                      glava="LAMELE ŠT.")
    elif rp is None:
        rp = razrez_podatki(sir, n, c, oznaka="L", glava="LAMELE ŠT.")
    if not vp["vrata"] and not vp["prehodi"]:
        kosi_l = [(f"L{i + 1}", float(sir)) for i in range(n)]
    traki = rp["traki"]
    kos_iz_ost = rp["iz_ost_kos"]
    kos_v = []                       # tip je naveden že zgoraj (ista funkcija)
    if vp["vrata"] or vp["prehodi"]:
        for enota in vp["vrata"] + vp["prehodi"]:
            for ozn_k, dol, _s, kol, _op, _kl in \
                    enota["kosovnica"]["izdelani"]:
                for _ in range(int(kol)):
                    kos_v.append((f"{enota['oznaka']}-{ozn_k}", float(dol)))
        if kos_v:
            rv = razrez_kosov_podatki(kos_v, c, oznaka="V",
                                      glava="VRATA ŠT.")
            rp["rez_rows"] += rv["rez_rows"][1:]
            rp["viz_traki"] += rv["viz_traki"]
    palice_zg = stevilo_palic(sir, 1, dl_palice, kerf)
    palice_sp = stevilo_palic(sir, 1, dl_palice, kerf)
    palice = palice_zg + palice_sp
    dim_zg = c.get("profil_zg_dim") or "80×40×3"
    dim_sp = c.get("profil_sp_dim") or "60×40×3"
    dim_nos = c.get("nosilec_dim") or "50×50×5"
    por_m = sum(B for B, _ in traki) / 1000
    por_alu = palice * dl_palice / 1000
    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    nar = [
        f"NAROČILO — WPC material "
        f"({c.get('dobavitelj') or 'WoodCore'})",
        f"Naloga: {c['risba_st']} • Datum: {datum}",
        f"Stranka: {c.get('stranka') or '—'} • Objekt: "
        f"{c.get('objekt') or '—'}",
        "",
        "DESKE:",
        f"- {profil}, barva {barva}"
        + "".join(f" — {t} kos × {fmt(B)} mm" for B, t in traki_nabava(traki))
        + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
        "",
        "PROFILI (aluminij) — vsaka sekcija svoja zaloga:",
        f"- {dim_zg} (zgornji) — {palice_zg} kos × {fmt(dl_palice)} mm "
        f"(razrez: 1 × {fmt(sir)} mm)",
        f"- {dim_sp} (spodnji) — {palice_sp} kos × {fmt(dl_palice)} mm "
        f"(razrez: 1 × {fmt(sir)} mm)",
        "",
        "PRITRDILNI MATERIAL:",
        f"- {vijak_lamela_naziv} — {vijaki} kos",
        f"- {vijak_nosilec_naziv} — {n_nos * 2} kos",
        f"- Nosilni nosilec {dim_nos} — {n_nos} kos",
    ]
    romb = romb_montaza(profil)
    if romb:
        # MONTAZA_ROMB (en vir resnice v jedro.py): L-kotnik LEVO in DESNO
        # na vsakem stebričku; romb brez alu cevi NI mogoče montirati.
        nar += [
            f"- L-kotnik za pritrditev romba — {2 * n_nos} kos "
            f"({romb['kotniki_na_stebriku']} na stebriček: levo in desno)",
        ]
        if (c.get("vmesna_povezava")
                and _razmak > romb["razmak_max_stebriki_mm"]):
            nar += [f"- Vmesna povezava (iz zgornje cevi) — "
                    f"{max(1, n_nos - 1)} kos "
                    f"(razmak {fmt(round(_razmak))} mm > "
                    f"{fmt(romb['razmak_max_stebriki_mm'])} mm — NI "
                    "privijačena v tla)"]
        zak = romb_zaklucek(c.get("zaklucek"))
        if zak == "letvica":
            nar += [f"- Zaključna letvica (WPC) — 2 kos × "
                    f"{fmt(m['visina'])} mm",
                    f"- Vijaki za zaključno letvico — {2 * n} kos "
                    "(1 na lamelo, vsaka stran)",
                    "- (Letvica je opcija za zaključevanje prečne romb "
                    "ograje.)"]
        elif zak == "cepi":
            nar += [f"- Čepi za romb profile (levi + desni) — {2 * n} parov "
                    f"(1 par na vsak konec lamele)",
                    f"- Čepi za stebričke — {n_nos} kos",
                    "- " + romb["zaklucek_cepi_opomba"]]
        nar += ["", "OPOZORILO: montaža romba BREZ alu cevi v sredini NI "
                "mogoča — deske brez alu cevi se NE kupujejo! Romb profil "
                "se kupi SAMO skupaj z alu cevjo — ta je vključena v ceno "
                "romb deske."]
    deska = deska_montaza(profil)
    if deska:
        # MONTAZE_PROFILAV (en vir resnice v jedro.py)
        if deska.get("pritrditev_od_spredaj"):
            nar += [f"- Montaža ({deska['ime']}): pritrditev od spredaj skozi "
                    "desko v konstrukcijo — vijaki VIDNI na licu; predvrtje — "
                    f"luknja {fmt_vejica(deska['vrtina_odmik_mm'])} mm večja od "
                    f"vijaka; vijak {deska['lega_vijaka']}."]
        elif deska.get("skrito_vijacenje"):
            nar += [f"- Montaža ({deska['ime']}): skrito vijačenje — vijaki "
                    "niso vidni na licu"
                    + ("; montaža na širino "
                       + " ali ".join(f"{fmt(d)} mm"
                                      for d in deska["montazne_sirine_mm"])
                       if deska.get("montazne_sirine_mm") else "") + "."]
    nar += _nar_posebnosti(montaza_profila(profil),
                          c.get("pritrditev"), c.get("montazna_temp_c"),
                          max((B for B, _ in traki), default=0), barva)
    nar += ["- Spoji desk na dolžino: obvezno na stebričku! Pritrdilni "
            "vijak na vsaki deski 3 cm od roba reza deske."]
    opomba_dl = _opomba_kataloske_dolzine(c, montaza_profila(profil))
    if opomba_dl:
        nar += [opomba_dl]
    nar += _kataloska_blok(c)
    kosovnica = rp["kosovnica"]
    for enota in vp["vrata"] + vp["prehodi"]:
        for ozn_k, dol, _s, kol, _op, _kl in enota["kosovnica"]["izdelani"]:
            for _ in range(int(kol)):
                kosovnica.append((f"{enota['oznaka']}-{ozn_k}", dol, "vrata",
                                  barva))
    wpc_postavke = [f"{B / 1000:.1f} m ({t} kos)"
                    for B, t in traki_nabava(traki)]
    nar += opomba_kratkih_kosov(kosovnica)
    skupine_reza = [{"oznaka": "LAMELE", "kosi": list(kosi_l)},
                    {"oznaka": "VRATA", "kosi": list(kos_v)}]
    kolicine = {"postavke": [
        (f"WPC deske {profil} (nabava: " + " + ".join(wpc_postavke) + ")",
         f"{fmt(por_m)} m", "m", "wpc_deska_m", por_m),
        ("Alu profili (nabava)", f"{palice} kos = {fmt(por_alu)} m", "m",
         "alu_m", por_alu),
        (f"Nosilni nosilci {dim_nos}", f"{n_nos}", "kos", "nosilec_kos", n_nos),
        (vijak_lamela_naziv, f"{vijaki}", "kos", "vijak_kos", vijaki),
        (vijak_nosilec_naziv, f"{n_nos * 2}", "kos", "fasadni_kos",
         n_nos * 2),
    ],
        "narocilo": "\n".join(nar),
        "ostanki_posodobitev": rp["ostanki_posodobitev"],
        "kosovnica": kosovnica,
        "skupine_reza": skupine_reza,
        "kerf": kerf,
    }
    if vp["vrata"] or vp["prehodi"]:
        kolicine["postavke"] += vrata_vrstice_kolicin(vp)
        kolicine["narocilo"] += "\n\nVRATA/PREHODI:\n" + "\n".join(
            f"- {vr[0]}: {vr[1]} {vr[2]}"
            for vr in vrata_vrstice_potrebscine(vp)) \
            + "\n".join(vrata_dokazila_vrstice(vp))
    if romb:
        kotniki = 2 * n_nos
        kolicine["postavke"].append(
            ("L-kotnik za pritrditev romba", f"{kotniki}", "kos",
             "kotnik_kos", kotniki))
        if (c.get("vmesna_povezava")
                and _razmak > romb["razmak_max_stebriki_mm"]):
            vmesne = max(1, n_nos - 1)
            # vmesna povezava je izdelana po meri — brez cenovnega ključa
            # (Plan G: cene si ne izmišljamo)
            kolicine["postavke"].append(
                ("Vmesna povezava (iz zgornje cevi)", f"{vmesne}", "kos",
                 None, vmesne))
        if zak == "letvica":
            # letvica je izdelana po meri — brez cenovnega ključa (Plan G)
            kolicine["postavke"].append(
                ("Zaključna letvica (WPC)",
                 f"2 kos × {fmt(m['visina'])} mm", "m", None,
                 2 * m["visina"] / 1000))
            kolicine["postavke"].append(
                ("Vijaki za zaključno letvico", f"{2 * n}", "kos",
                 "vijak_kos", 2 * n))
        elif zak == "cepi":
            kolicine["postavke"].append(
                ("Čepi za romb profile (levi in desni)",
                 f"{4 * n}", "kos", None, 4 * n))
            kolicine["postavke"].append(
                ("Čepi za stebričke", f"{n_nos}", "kos", None, n_nos))
    return {"postavke": kolicine["postavke"], "narocilo": kolicine["narocilo"],
            "ostanki_posodobitev": kolicine["ostanki_posodobitev"],
            "kosovnica": kolicine["kosovnica"],
            "skupine_reza": kolicine["skupine_reza"],
            "kerf": kolicine["kerf"]}


def kolicina_z_enoto(kol_str, enota):
    """Združi količino in enoto BREZ podvajanja (npr. '17.4 m m').

    Skupna logika za predračun in ponudbo (en izvor resnice).
    """
    k, e = str(kol_str), str(enota or "")
    return k if (not e or k.endswith(e)) else f"{k} {e}"


def predracun_znesek(cene, postavke):
    """Čisti seštevek predračuna (Plan A) — EN algoritem za vse izpise.

    Vrne {"skupaj", "vrstice", "manjkajoce_cene", "vse_nic", "delno"}.
    """
    def _kol(kol_str, enota):
        return kolicina_z_enoto(kol_str, enota)

    cene = cene or {}
    uporabljene = [float(cene.get(kljuc) or 0)
                   for (_n, _k, _e, kljuc, num) in postavke if num and kljuc]
    if cene.get("dela_ure") and cene.get("dela_ur_cena"):
        uporabljene.append(float(cene.get("dela_ur_cena") or 0))
    vse_nic = all(abs(v) < 1e-9 for v in uporabljene) if uporabljene else True
    delno = any(abs(v) < 1e-9 for v in uporabljene) and not vse_nic
    skup = 0.0
    vrstice = []
    manjkajoce_cene = []
    for (naziv, kol_str, enota, kljuc, num) in postavke:
        if kljuc is None:
            # Izdelani kosi (npr. vratni profili) nimajo cenovnega ključa —
            # NE izmišljamo cene (politika Plan G): "cena po dogovoru".
            if num:
                vrstice.append([naziv, _kol(kol_str, enota),
                                "cena po dogovoru (ni cenovnega ključa)",
                                "po dogovoru"])
            continue
        cena = cene.get(kljuc)
        if cena is None:
            if num:
                manjkajoce_cene.append(str(kljuc))
                vrstice.append([naziv, _kol(kol_str, enota),
                                "CENA MANJKA (ni upoštevano)", "—"])
            continue
        if not num:
            continue
        sk = num * cena
        if abs(cena) < 1e-9:
            vrstice.append([naziv, _kol(kol_str, enota),
                            "PRIMER (ni obračunano)", "ni obračunano"])
        else:
            vrstice.append([naziv, _kol(kol_str, enota),
                            f"{cena:.2f} EUR/{enota}", f"{sk:.2f} EUR"])
            skup += sk
    ur, ur_c = cene.get("dela_ure"), cene.get("dela_ur_cena")
    if ur and ur_c is not None:
        if abs(float(ur_c or 0)) < 1e-9:
            vrstice.append(["Delo (izdelava + montaža)", f"{fmt(ur)} h",
                            "PRIMER (ni obračunano)", "ni obračunano"])
        else:
            vrstice.append(["Delo (izdelava + montaža)", f"{fmt(ur)} h",
                            f"{ur_c:.2f} EUR/h", f"{ur * ur_c:.2f} EUR"])
            skup += ur * ur_c
    return {"skupaj": skup, "vrstice": vrstice,
            "manjkajoce_cene": manjkajoce_cene,
            "vse_nic": vse_nic, "delno": delno}
# ------------------------------------------------------ issue #14 (G/E) --- #
# Rezni načrt iz dejanske zaloge: skupine kosov → primerjava strategij →
# izbrani načrt (potrjen ali samodejen). En vir za GUI in montažni list.

def rezne_skupine(c):
    """Skupine kosov za rezni načrt — en vir za vmesnik in risbo.

    Vrne [(ime_skupine, [(oznaka, dolzina)], barva, profil), ...].
    Lamele: n kosov dolžine širine (ob odprtinah razrezane na segmente);
    vrata: kosi okvirjev/kril (ločen profil). Opomba: informativni izračun
    za primerjavo — montažni list uporablja svoje natanko izračunane kose.
    """
    m = c.get("mere") or {}
    sir = float(m.get("sirina") or 0)
    n = int(c.get("stevilo_lamel") or 0) or jedro.privzeto_stevilo_lamel(m)
    vp = jedro.vrata_podatki(c)
    barva = str(c.get("barva") or "")
    profil = str(c.get("profil") or "")
    if vp["odprtine"]:
        kosi_l: list = []
        for _ in range(max(1, n)):
            for xa, xb in jedro.razdeli_po_odprtinah(0, sir, vp["odprtine"]):
                kosi_l.append((f"L{len(kosi_l) + 1}", float(xb - xa)))
    else:
        kosi_l = [(f"L{i + 1}", float(sir)) for i in range(max(1, n))]
    kosi_v: list = []
    for enota in vp["vrata"] + vp["prehodi"]:
        for ozn_k, dol, _sir_k, kol, _op, _kl in enota["kosovnica"]["izdelani"]:
            for _ in range(int(kol)):
                kosi_v.append((f"{enota['oznaka']}-{ozn_k}", float(dol)))
    return [("LAMELE", kosi_l, barva, profil),
            ("VRATA", kosi_v, barva, "vrata")]


def _zaloga_iz_cfg(c, barva, profil):
    """Zaloga za skupino: tovarniške dolžine (neomejeno) + skladišče ostankov
    (omejeno, vir='ostanek' — enkratna poraba, sledljivost ohranjena)."""
    from razrez import ZalogovnaPostavka, nalozi_ostanke
    dolzine = c.get("dolzine_deske") or [c.get("dolzina_palice") or 5800]
    zaloga = []
    for d in dolzine:
        try:
            fd = float(d)
        except (TypeError, ValueError):
            continue
        if fd > 0:
            zaloga.append(ZalogovnaPostavka(
                fd, kolicina=None, barva=barva, profil=profil))
    for o in nalozi_ostanke():
        try:
            od = float(o.get("dolzina") or 0)
        except (TypeError, ValueError):
            continue
        if od <= 0:
            continue
        zaloga.append(ZalogovnaPostavka(
            od, kolicina=1,
            barva=str(o.get("barva") or ""), profil=str(o.get("profil") or ""),
            vir="ostanek", oznaka=str(o.get("oznaka") or o.get("ime") or "")))
    return zaloga


def rezni_nacrt(skupine, c):
    """Issue #14: napredni rezni načrt — primerjava + izbrani načrt.

    ``skupine``: [(ime, kosi, barva, profil), ...] (iz rezne_skupine ali
    natanko izračunanih kosov risbe). Vrne dict:
      - skupine: [{ime, tabela, izbran (metrike), viz_traki, bilanca}],
      - kriterij (politika), izbrani_nacrt, status_izbire
        ("potrjen" | "samodejno — NI potrjen"),
      - tabela_vse: vrstice za GUI (skupina + primerjava).
    Izbrani načrt pride iz cfg["optimizacija"]["nacrt"] — sistem ga NE
    zamenja tiho; brez izbire velja najboljši po kriteriju in je označen
    kot NEPOTRJEN.
    """
    from razrez import OmejitveReza, primerjaj_nacrte
    opt = c.get("optimizacija") or {}
    if not isinstance(opt, dict):
        opt = {}
    politika = str(opt.get("kriterij") or "odpad")
    izbrano = str(opt.get("nacrt") or "")
    o = OmejitveReza(kerf=float(c.get("kerf") or 3.0), politika=politika,
                     cene_palice=(opt.get("cene_palice")
                                  if politika == "cena" else None))
    izhod_skupine: list = []
    izhod_tabela: list = []
    for ime, kosi, barva, profil in skupine:
        if not kosi:
            continue
        zaloga = _zaloga_iz_cfg(c, barva, profil)
        pr = primerjaj_nacrte(kosi, zaloga, o)
        izbran = None
        for n in pr["nacrti"]:
            if izbrano and n.strategija == izbrano:
                izbran = n
                break
        if izbran is None and pr["nacrti"]:
            izbran = pr["nacrti"][0]        # najboljši po kriteriju
        viz: list = []
        bilanca = {"odrez_mm": 0.0, "kerf_mm": 0.0, "ostanek_mm": 0.0,
                   "odpad_mm": 0.0}
        if izbran is not None:
            viz = [(t.dolzina, list(t.kosi)) for t in izbran.traki]
            m = izbran.metrike()
            bilanca = {"odrez_mm": m["odrez_mm"], "kerf_mm": m["kerf_mm"],
                       "ostanek_mm": m["ostanek_mm"], "odpad_mm": m["odpad_mm"]}
        izhod_skupine.append({
            "ime": ime,
            "tabela": pr["tabela"],
            "izbran": (izbran.metrike() if izbran is not None else None),
            "viz_traki": viz,
            "bilanca": bilanca,
        })
        for vrstica in pr["tabela"]:
            izhod_tabela.append({"skupina": ime, **vrstica})
    return {"kriterij": politika, "skupine": izhod_skupine,
            "tabela_vse": izhod_tabela,
            "izbrani_nacrt": izbrano or "samodejno",
            "status_izbire": "potrjen" if izbrano
                             else "samodejno — NI potrjen"}