# -*- coding: utf-8 -*-
"""Proizvodnja (production) — kanonični model količin in vrstice izpisov.

F2 (issue #5): izločeno iz monolita risba.py BREZ spremembe vedenja.
Vse količine štejejo iz ENEGA proizvodni_model (issue #6, §3).
"""
import vrata as vrat

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


