# -*- coding: utf-8 -*-
"""Proizvodnja (production) — kanonični model količin in vrstice izpisov.

F2 (issue #5): izločeno iz monolita risba.py BREZ spremembe vedenja.
Vse količine štejejo iz ENEGA proizvodni_model (issue #6, §3).
"""
import vrata as vrat
import jedro

from jedro import (fmt, razpored, razpored_pokoncna, razdeli_po_odprtinah,
                   pozicije_nosilcev, vrata_podatki)

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
                # F1 (O3): montažne letve za deskami (2 na polje) — prej
                # sploh niso bile v modelu/BOM, čeprav so fizični nosilec.
                "montazne_letve": 2 * len(p["polja"]),
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
    from jedro import traki_nabava
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
    kosovnica = rp["kosovnica"]
    for enota in vp["vrata"] + vp["prehodi"]:
        for ozn_k, dol, _s, kol, _op, _kl in enota["kosovnica"]["izdelani"]:
            for _ in range(int(kol)):
                kosovnica.append((f"{enota['oznaka']}-{ozn_k}", dol, "vrata",
                                  barva))
    wpc_postavke = [f"{B / 1000:.1f} m ({t} kos)"
                    for B, t in traki_nabava(traki)]
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
            for vr in vrata_vrstice_potrebscine(vp))
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