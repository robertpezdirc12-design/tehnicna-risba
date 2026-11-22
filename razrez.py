# -*- coding: utf-8 -*-
"""razrez.py — optimizacija razreza čez več tovarniških dolžin, skladišče
ostankov, kosovnica in naročilo (uporablja ga risba.py in vmesnik.py).

MODEL REZA (enoten povsod — A2/B1):
    kosov ni mogoče izrezati brez reza; vsak kos "nosi" svoj rez (kerf),
    zato n kosov dolžine k iz traku dolžine V zasede n * (k + kerf).
    - zmogljivost traku:  kos_iz_vira(V, k, kerf) = (V + kerf) // (k + kerf)
      (+ kerf v števcu: zadnji kos se lahko konča ob robu traku)
    - ostanek po rezu:   V - n * (k + kerf), zarezan na 0 (če je trak
      porabljen do konca, rezov ni več za odštet)
    - kontrola:          V = n * k + kerf_skupaj + ostanek  (drži točno)
    Isti model se uporablja v validaciji (preveri_cfg), optimizatorju,
    prikazu ostankov, kosovnici in naročilu.
"""

import copy
import math
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import yaml

MIN_OSTANKA = 100.0  # mm — krajših kosov ne hranimo v skladišču


def fmt(v):
    """Število brez odvečnih decimalk (2500.0 -> 2500, 47.5 -> 47.5)."""
    try:
        fv = float(v)
        if abs(fv - round(fv)) < 1e-9:
            return str(int(round(fv)))
        return f"{fv:.2f}".rstrip("0").rstrip(".")
    except Exception:
        return str(v)


# ---------------------------------------------------------------- model reza
def kos_iz_vira(dolzina_vir, dolzina_kosa, kerf):
    """Koliko kosov dolžine `dolzina_kosa` da trak `dolzina_vir` (s kerf rezom)."""
    try:
        dolzina_vir = float(dolzina_vir)
        dolzina_kosa = float(dolzina_kosa)
    except (TypeError, ValueError):
        return 0
    kerf = max(float(kerf or 0.0), 0.0)
    if dolzina_kosa <= 0 or dolzina_vir < dolzina_kosa:
        return 0
    # odmik 1e-9: `//` na floatih bi sicer pri necelih dolžinah lahko floor-oval navzdol
    return int((dolzina_vir + kerf + 1e-9) // (dolzina_kosa + kerf))


def ostanek_po_rezih(dolzina_vir, n_kosov, dolzina_kosa, kerf):
    """Ostanek traku po rezu `n_kosov` kosov (ENKRATNO odštetje, B1).

    Model reza (fizični, issue #6): `n` kosov potrebuje `n−1` rezov, če se
    zadnji kos konča ob robu traku (flush), sicer `n` rezov (zadnji loči
    ostanek). Ostanek = max(0, B − n·(k + kerf)): šprica < kerf se vknjiži
    v porabo žage in ni uporaben kos. Če zahtevanih kosov fizično ni
    mogoče izrezati, funkcija vrže jasno napako (ne tiho 0).
    """
    if n_kosov <= 0:
        return float(dolzina_vir)
    kerf = max(float(kerf or 0.0), 0.0)
    if n_kosov > kos_iz_vira(dolzina_vir, dolzina_kosa, kerf):
        raise ValueError(
            f"{n_kosov} kosov po {fmt(dolzina_kosa)} mm ni mogoče izrezati "
            f"iz traku {fmt(dolzina_vir)} mm (kerf {fmt(kerf)} mm).")
    return max(0.0, float(dolzina_vir) - n_kosov * (float(dolzina_kosa) + kerf))


def stevilo_palic(dolzina_kosa, n_kosov, dolzina_palice, kerf):
    """Koliko tovarniških palic je potrebnih za `n_kosov` kosov dolžine
    `dolzina_kosa` (isti model reza kot povsod — regresija agregatne formule).

    Vrne število palic. Če kos ne gre iz nobene palice, vrže ValueError.
    """
    try:
        dolzina_kosa = float(dolzina_kosa)
        dolzina_palice = float(dolzina_palice)
        n_kosov = int(n_kosov)
    except (TypeError, ValueError):
        raise ValueError("Neveljavni podatki za izračun palic.")
    if n_kosov <= 0:
        return 0
    na_palico = kos_iz_vira(dolzina_palice, dolzina_kosa, kerf)
    if na_palico <= 0:
        raise ValueError(
            f"Kos {fmt(dolzina_kosa)} mm je daljši od tovarniške dolžine "
            f"palice {fmt(dolzina_palice)} mm (kerf {fmt(kerf)} mm) — "
            "potreben spoj ali druga dolžina palice.")
    return int(math.ceil(n_kosov / na_palico))


# ---------------------------------------------------------------- podatkovna mapa (B5)
def uporabniska_mapa():
    """Stalna uporabniška podatkovna mapa (deluje tudi iz Windows EXE).

    Vrstni red: okoljska spremenljivka TEHNICNA_RISBA_DATA, sicer
    %APPDATA%\\TehnicnaRisba (Windows) oziroma ~/.local/share/TehnicnaRisba.
    """
    nadomestilo = os.environ.get("TEHNICNA_RISBA_DATA")
    if nadomestilo:
        return os.path.abspath(nadomestilo)
    if sys.platform == "win32":
        baza = (os.environ.get("APPDATA")
                or os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
    else:
        baza = (os.environ.get("XDG_DATA_HOME")
                or os.path.join(os.path.expanduser("~"), ".local", "share"))
    return os.path.join(baza, "TehnicnaRisba")


def pot_ostanki(pot=None):
    """Pot do skladišča ostankov. Brez argumenta = uporabniška podatkovna mapa.

    Če tam datoteke še ni, se obstoječa »stara« datoteka iz delovne mape
    (legacy lokacija) varno prekopira (vir ostane nedotaknjen).
    """
    if pot:
        return os.path.abspath(pot)
    nova = os.path.join(uporabniska_mapa(), "ostanki.yaml")
    if not os.path.exists(nova):
        stara = os.path.join(os.getcwd(), "ostanki.yaml")
        if os.path.exists(stara) and os.path.abspath(stara) != nova:
            try:
                os.makedirs(os.path.dirname(nova), exist_ok=True)
                shutil.copy2(stara, nova)
                shutil.copy2(stara, nova + ".migracija.bak")
            except Exception:
                return stara
    return nova


# ---------------------------------------------------------------- skladišče ostankov
def _normaliziraj_ostanek(o):
    """Normalizira ostanek, ohrani pa VSE obstoječe metapodatke (B1)."""
    if not isinstance(o, dict):
        return None
    try:
        dol = float(o.get("dolzina", 0) or 0)
    except (TypeError, ValueError):
        return None
    if dol <= 0:
        return None
    nov = dict(o)
    nov["dolzina"] = round(dol, 3)
    nov["barva"] = str(o.get("barva", "") or "")
    nov["profil"] = str(o.get("profil", "") or "")
    return nov


def nalozi_ostanke(pot=None):
    p = pot_ostanki(pot)
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            podatki = yaml.safe_load(f) or []
    except Exception:
        return []
    if not isinstance(podatki, list):
        return []
    out = []
    for o in podatki:
        no = _normaliziraj_ostanek(o)
        if no:
            out.append(no)
    return out


def shrani_ostanke(seznam, pot=None):
    """Varno shranjevanje skladišča (B1): varnostna kopija + začasna
    datoteka + atomičen `os.replace` (prekinitev ne poškoduje datoteke).

    Vrne (pot, backup_pot_ali_None)."""
    p = pot_ostanki(pot)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    backup = None
    if os.path.exists(p):
        backup = p + ".bak"
        try:
            shutil.copy2(p, backup)
        except Exception:
            backup = None
    clean = []
    for o in (seznam or []):
        no = _normaliziraj_ostanek(o)
        if no and no["dolzina"] >= MIN_OSTANKA:
            clean.append(no)
    fd, tmp = tempfile.mkstemp(prefix=".ostanki_", suffix=".tmp", dir=d or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(clean, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
    return p, backup


# ---------------------------------------------------------------- optimizacija
def optimiziraj_zalogo(kos_dol, n_kosov, dolzine_zaloge, kerf):
    """Optimalna razporeditev ENAKIH kosov po nabavnih dolžinah zaloge.

    Algoritem: dinamično programiranje po številu preostalih kosov
    (issue #6 — prejšnji greedy je bil v ~38 % majhnih primerov slabši,
    npr. 3 kosi 500 mm / kerf 2 / zaloga [1002, 1552]: greedy je porabil
    2 surovca z 500 mm odpada namesto 1 surovca z 46 mm odpada).

    Kriterij (leksikografsko, dokumentirano):
      (1) najmanjša SKUPNA nabavljena dolžina (material = strošek),
      (2) najmanjše število trakov (enostavnost razreza),
      (3) najmanjši skupni odpad.
    Za enake kose je rešitev po tem kriteriju globalno optimalna.
    Rezultat preverja še NEODVISNI referenčni reševalnik v
    tests/test_rez_model.py. Vrne [(dolžina_trak, št. kosov), ...];
    prazno, če kosa ni mogoče izrezati iz nobene dolžine (A3).

    Omejitev modela: konstantna širina kerfe in kvadratni konci zaloge;
    ne obravnava hkratnih rezov več kosov z istim nožem.
    """
    kerf = max(float(kerf or 0.0), 0.0)
    try:
        kos_dol = float(kos_dol)
        n_kosov = int(n_kosov)
    except (TypeError, ValueError):
        return []
    if n_kosov <= 0 or kos_dol <= 0:
        return []
    dolzine = sorted({float(d) for d in (dolzine_zaloge or [])
                      if isinstance(d, (int, float)) and d > 0})
    if not dolzine:
        return []
    # vse možne polnitve posameznega traku: [(B, [(kol, ostanek), ...])]
    moznosti = []
    for B in dolzine:
        kap = kos_iz_vira(B, kos_dol, kerf)
        if kap >= 1:
            moznosti.append((B, [(kol, ostanek_po_rezih(B, kol, kos_dol, kerf))
                                 for kol in range(1, kap + 1)]))
    if not moznosti:
        return []
    # DP: f[q] = (Σ nabavljene dolžine, št. trakov, odpad, prejšnji q, B, kol)
    INF = (float("inf"), float("inf"), float("inf"), -1, None, 0)
    f = [INF] * (n_kosov + 1)
    f[0] = (0.0, 0, 0.0, -1, None, 0)
    for q in range(1, n_kosov + 1):
        for B, kombinacije in moznosti:
            for kol, ostanek in kombinacije:
                if kol > q:
                    continue
                prej = f[q - kol]
                if prej[0] == float("inf"):
                    continue
                kand = (prej[0] + B, prej[1] + 1, prej[2] + ostanek,
                        q - kol, B, kol)
                if (kand[0], kand[1], kand[2]) < (f[q][0], f[q][1], f[q][2]):
                    f[q] = kand
    if f[n_kosov][0] == float("inf"):
        return []
    traki = []
    q = n_kosov
    while q > 0:
        _zb, _st, _odp, prej, B, kol = f[q]
        traki.append((B, kol))
        q = prej
    traki.reverse()
    return traki


def porazdeli_z_ostanki(dol_kosa, n_kosov, ostanki, kerf, barva, profil):
    """Kosi najprej z ostanki iste barve/profila (najdaljši ostanek prvi).

    NE mutira vhodnih ostankov (vsak ostanek je porabljen največ enkrat).
    Vrne (iz_ost, preostalo št. kosov, posodobljeno skladišče):
      iz_ost: [(indeks, št. kosov, ostanek_po_rezu)]
      posodobljeno skladišče: ostanki z novimi dolžinami; tisti < 100 mm
      se izbrišejo (MIN_OSTANKA).
    """
    pari = [(i, o) for i, o in enumerate(ostanki)
            if str(o.get("barva", "")).lower() == str(barva).lower()
            and str(o.get("profil", "")).lower() == str(profil).lower()
            and kos_iz_vira(o.get("dolzina", 0), dol_kosa, kerf) >= 1]
    pari.sort(key=lambda p: -p[1].get("dolzina", 0))
    iz_ost = []
    preost = int(n_kosov)
    zamenjano = {}
    for (i, o) in pari:
        if preost <= 0:
            break
        kol = min(kos_iz_vira(o["dolzina"], dol_kosa, kerf), preost)
        nov_dol = ostanek_po_rezih(o["dolzina"], kol, dol_kosa, kerf)
        zamenjano[i] = nov_dol
        iz_ost.append((i, kol, nov_dol))
        preost -= kol
    posodobljeno = []
    for i, o in enumerate(ostanki):
        if i in zamenjano:
            if zamenjano[i] >= MIN_OSTANKA:
                nov = copy.deepcopy(o)
                nov["dolzina"] = round(zamenjano[i], 3)
                posodobljeno.append(nov)
        else:
            posodobljeno.append(copy.deepcopy(o))
    return iz_ost, preost, posodobljeno


# ---------------------------------------------------------------- celoten načrt
def razrez_podatki(kos_dol, n_kosov, c, oznaka="KOS", glava="KOSI ŠT."):
    """Celoten razrez za montažni list: ostanki + optimizacija + vrste.

    EN sam vir resnice za rezalni načrt (A5): risba, montažni list,
    kosovnica in naročilo uporabljajo ta izračun.

    Vrne dict: traki, rez_rows (glava + vrste), viz_traki, kosovnica,
    iz_ost_kos, ostanki_posodobitev (B1: celotno posodobljeno skladišče —
    tudi ko starih ostankov ne uporabljamo, se novi iz nabave evidentirajo),
    preost_kosov, st_kosov.

    Če razrez ni popoln (manjkajo kosi), vrže ValueError z manjkajočim
    številom kosov — nepopolnega načrta NE vrne kot uspešnega (A3).
    """
    kerf = float(c.get("kerf", 3.0) or 0.0)
    barva = str(c.get("barva") or "Antracit")
    profil = (c.get("profil") or "").strip()
    dl_zaloge = c.get("dolzine_deske") or [c.get("dolzina_deske", 5800)]
    if not isinstance(dl_zaloge, (list, tuple)):
        dl_zaloge = [dl_zaloge]
    uporabi = bool(c.get("uporabi_ostanke", False))
    kos_dol = float(kos_dol)
    n_kosov = int(n_kosov)

    # trenutno skladišče vedno preberemo (za varno posodobitev),
    # za rez pa ga uporabimo le, če je uporabnik to izrecno vklopil.
    trenutni = nalozi_ostanke()
    iz_ost, preost, ostanki_po_porabi = porazdeli_z_ostanki(
        kos_dol, n_kosov, (trenutni if uporabi else []), kerf, barva, profil)

    traki = optimiziraj_zalogo(kos_dol, preost, dl_zaloge, kerf)

    izdelani = sum(k for _, k, _ in iz_ost) + sum(k for _, k in traki)
    if izdelani != n_kosov:
        raise ValueError(
            f"Razrez ni popoln: izdelanih {izdelani} od {n_kosov} kosov "
            f"({fmt(kos_dol)} mm) — manjka {n_kosov - izdelani}. "
            "Preveri dolžine desk v nabavi in kerf.")

    # novi ostanki iz NABAVNIH desk (B1) + enotno posodobljeno skladišče
    novi_iz_nabave = []
    for B, kol in traki:
        rem = ostanek_po_rezih(B, kol, kos_dol, kerf)
        if rem >= MIN_OSTANKA:
            novi_iz_nabave.append({"dolzina": round(rem, 3),
                                   "barva": barva, "profil": profil})
    if uporabi:
        osnova = [o for o in ostanki_po_porabi
                  if o.get("dolzina", 0) >= MIN_OSTANKA]
        spremenjeno = bool(iz_ost) or bool(novi_iz_nabave)
    else:
        osnova = copy.deepcopy(trenutni)
        spremenjeno = bool(novi_iz_nabave)
    posodobitev = osnova + novi_iz_nabave if spremenjeno else None

    rez_rows = [["VIR", "KOSOV", glava, "OSTANEK PO REZU (mm)"]]
    viz_traki = []
    kosovnica = []
    pc = 1
    for st, (oi, kol, ostanek) in enumerate(iz_ost, 1):
        dol = trenutni[oi]["dolzina"] if uporabi else 0.0
        p1, p2 = pc, pc + kol - 1
        pc += kol
        rez_rows.append([f"OSTANEK #{st} ({fmt(dol)} mm)",
                         str(kol), f"{p1}–{p2}", fmt(ostanek)])
        viz_traki.append((dol,
                          [(f"{oznaka}{p1 + j}", kos_dol) for j in range(kol)]))
        for j in range(kol):
            kosovnica.append((f"{p1 + j}", kos_dol, f"ostanek #{st}", barva))
    for ti, (B, kol) in enumerate(traki, 1):
        p1, p2 = pc, pc + kol - 1
        pc += kol
        ost = ostanek_po_rezih(B, kol, kos_dol, kerf)
        rez_rows.append([f"DESKA {ti} (nabava, {fmt(B)} mm)", str(kol),
                         f"{p1}–{p2}", fmt(ost)])
        viz_traki.append((B, [(f"{oznaka}{p1 + j}", kos_dol)
                              for j in range(kol)]))
        for j in range(kol):
            kosovnica.append((f"{p1 + j}", kos_dol, f"deska #{ti}", barva))

    # A5 — invariante: število kosov in matematična kontrola razreza
    if len(kosovnica) != n_kosov:
        raise ValueError("kosovnica ne ustreza številu kosov")
    for (B, kol) in traki:
        ostanek = ostanek_po_rezih(B, kol, kos_dol, kerf)
        kerf_skupaj = B - kol * kos_dol - ostanek
        # dejavne kontrole (issue #6): št. kosov ne presega kapacitete traku,
        # poraba kerfa pa ustreza številu fizičnih rezov (n−1 ali n).
        if kol > kos_iz_vira(B, kos_dol, kerf):
            raise ValueError("A5: število kosov presega kapaciteto traku")
        if not ((kol - 1) * kerf - 1e-6 <= kerf_skupaj <= kol * kerf + 1e-6):
            raise ValueError("A5: poraba kerfa ni skladna s številom rezov")

    return {"traki": traki, "rez_rows": rez_rows, "viz_traki": viz_traki,
            "kosovnica": kosovnica, "iz_ost_kos": sum(k for _, k, _ in iz_ost),
            "ostanki_posodobitev": posodobitev,
            "preost_kosov": 0, "st_kosov": n_kosov}

# ---------------------------------------------------------------- razrez več kosov
def razrez_kosov(kosi, dolzine_zaloge, kerf, barva="", profil=""):
    """Razrez kosov RAZLIČNIH dolžin (npr. vratni kosi) — first-fit-descending.

    ``kosi``: [(oznaka, dolzina_mm), ...]; ``dolzine_zaloge``: dovoljene
    nabavne dolžine (mm). Vsak kos mora iti v natanko en trak — če kos ne
    gre iz nobene dolžine zaloge, vrže ValueError (nepopolnega načrta ne
    vračamo kot uspešnega, enako kot A3 pri razrez_podatki).

    Vrne dict: traki [(B, [(oznaka, dolzina), ...]), ...], rez_rows,
    kosovnica [(oznaka, dolzina, vir, barva)], st_kosov.
    """
    kerf = max(float(kerf or 0.0), 0.0)
    dolzine = sorted({float(d) for d in (dolzine_zaloge or [])
                      if isinstance(d, (int, float)) and d > 0}, reverse=True)
    if not dolzine:
        raise ValueError("Ni dovoljenih dolžin zaloge za razrez.")
    vnosi = []
    for oznaka, dol in kosi:
        dol = float(dol)
        if dol <= 0:
            raise ValueError(f"Kos {oznaka} ima neveljavno dolžino {dol}.")
        if kos_iz_vira(max(dolzine), dol, kerf) < 1:
            raise ValueError(
                f"Kos {oznaka} ({fmt(dol)} mm) je daljši od najdaljše "
                f"nabavne dolžine {fmt(max(dolzine))} mm (kerf {fmt(kerf)}).")
        vnosi.append((oznaka, dol))
    # FFD: najdaljši kosi najprej, v prvi trak, ki ga sprejme.
    vnosi.sort(key=lambda t: -t[1])
    traki = []  # [(B, [kosi], preostanek_prostora)]
    for oznaka, dol in vnosi:
        postavljen = False
        # t[2] = preostanek prostora = B − Σd − m·kerf (m = št. kosov v traku).
        # Model B (kot kos_iz_vira): m kosov potrebuje m−1 rezov; pogoj
        # `dol <= t[2]` dopušča tudi flush (kos do roba brez zadnjega reza).
        # Best-fit: obstoječi trak z NAJMANJ prostora, ki kos še sprejme.
        kandidati = [t for t in traki if dol <= t[2] + 1e-9]
        if kandidati:
            t = min(kandidati, key=lambda t: t[2])
            t[1].append((oznaka, dol))
            t[2] -= dol + kerf
            postavljen = True
        if not postavljen:
            # best-fit surovec: najkrajša zaloga, ki še sprejme kos (model B)
            B = min((d for d in dolzine if kos_iz_vira(d, dol, kerf) >= 1),
                    default=None)
            if B is None:
                raise ValueError(f"Kos {oznaka} ({fmt(dol)} mm) ne gre v noben trak.")
            traki.append([B, [(oznaka, dol)], B - dol - kerf])

    # Konsolidacija: če se vsi kosi dveh trakov prilegajo v eno samo zalogo
    # (model B: Σd + (n−1)·kerf ≤ B) in to ne poveča skupne nabavljene
    # dolžine, ju zamenjaj z enim trakom — popravi znane slabosti BFD
    # (npr. 2 kosa 1000 mm iz [1000, 2000] → en trak 2000 namesto dveh 1000).
    spremenjeno = True
    while spremenjeno:
        spremenjeno = False
        for i in range(len(traki)):
            for j in range(len(traki) - 1, i, -1):
                Bi, ki, _ = traki[i]
                Bj, kj, _ = traki[j]
                vsi = ki + kj
                potrebno = (sum(d for _, d in vsi)
                            + max(0, len(vsi) - 1) * kerf)
                B_nov = min((d for d in dolzine if d + 1e-9 >= potrebno),
                            default=None)
                if B_nov is not None and B_nov <= Bi + Bj + 1e-9:
                    traki[i] = [B_nov, vsi,
                                B_nov - sum(d for _, d in vsi) - len(vsi) * kerf]
                    del traki[j]
                    spremenjeno = True
                    break
            if spremenjeno:
                break

    rez_rows = []
    kosovnica = []
    for ti, (B, kosi_t, ostanek) in enumerate(traki, 1):
        ozn = ", ".join(f"{o} ({fmt(d)})" for o, d in kosi_t)
        rez_rows.append([f"TRAK {ti} ({fmt(B)} mm)", str(len(kosi_t)), ozn,
                         fmt(max(0.0, ostanek))])
        for o, d in kosi_t:
            kosovnica.append((o, d, f"trak #{ti}", barva))
    assert len(kosovnica) == len(vnosi), "razrez ni popoln"
    return {"traki": [(B, kosi_t) for B, kosi_t, _ in traki],
            "rez_rows": rez_rows, "kosovnica": kosovnica,
            "st_kosov": len(vnosi)}


def naivni_rez(kosi, dolzine_zaloge, kerf):
    """Ročni rez BREZ optimizacije — bazna linija (NestingCalc vzor).

    Kosi gredo v trak PO VRSTNEM REDU seznama (kakor jih delavec prebere s
    seznama): trenutni trak se polni, dokler naslednji kos ne gre vanj;
    BREZ sortiranja, BREZ pogleda naprej, BREZ konsolidacije trakov.
    Nova vrstica = najkrajša zaloga, ki kos še sprejme (model B).

    Vrne dict: traki [(B, [(oznaka, dolzina), ...]), ...], st_kosov.
    """
    kerf = max(float(kerf or 0.0), 0.0)
    dolzine = sorted({float(d) for d in (dolzine_zaloge or [])
                      if isinstance(d, (int, float)) and d > 0}, reverse=True)
    if not dolzine:
        raise ValueError("Ni dovoljenih dolžin zaloge za razrez.")
    traki = []  # [B, [kosi], preostanek_prostora]
    for oznaka, dol in kosi:
        dol = float(dol)
        if dol <= 0:
            raise ValueError(f"Kos {oznaka} ima neveljavno dolžino {dol}.")
        if kos_iz_vira(max(dolzine), dol, kerf) < 1:
            raise ValueError(
                f"Kos {oznaka} ({fmt(dol)} mm) je daljši od najdaljše "
                f"nabavne dolžine {fmt(max(dolzine))} mm (kerf {fmt(kerf)}).")
        if traki and dol <= traki[-1][2] + 1e-9:
            t = traki[-1]                 # polnjenje TRENUTNEGA traku
            t[1].append((oznaka, dol))
            t[2] -= dol + kerf
        else:
            B = min((d for d in dolzine if kos_iz_vira(d, dol, kerf) >= 1),
                    default=None)
            if B is None:
                raise ValueError(f"Kos {oznaka} ({fmt(dol)} mm) ne gre v noben trak.")
            traki.append([B, [(oznaka, dol)], B - dol - kerf])
    return {"traki": [(B, kosi_t) for B, kosi_t, _ in traki],
            "st_kosov": sum(len(kosi_t) for _B, kosi_t, _ in traki)}


def metrika_reza(kosi, dolzine_zaloge, kerf):
    """Primerjava optimiziranega in ročnega reza (Plan 3 — NestingCalc vzor).

    Odpad = nabavljena dolžina − Σ dolžin kosov (vključuje reze/kerf in
    ostanke — ISTA definicija za obe poti, zato sta številki primerljivi).

    Vrne dict: uporabno_mm, opt_*, rocno_* (poraba/odpad/delez/traki),
    prihranek_mm (koliko MANJ materiala porabi optimizator) in
    prihranek_delez (delek ročne porabe).
    """
    kosi = [(o, float(d)) for o, d in kosi]
    if not kosi:
        raise ValueError("Metrika reza potrebuje vsaj en kos.")
    opt = razrez_kosov(kosi, dolzine_zaloge, kerf)
    roc = naivni_rez(kosi, dolzine_zaloge, kerf)
    uporabno = sum(d for _o, d in kosi)
    por_o = sum(B for B, _t in opt["traki"])
    por_r = sum(B for B, _t in roc["traki"])
    return {
        "uporabno_mm": uporabno,
        "opt_poraba_mm": por_o,
        "opt_odpad_mm": por_o - uporabno,
        "opt_odpad_delez": (por_o - uporabno) / por_o if por_o else 0.0,
        "opt_traki": len(opt["traki"]),
        "rocno_poraba_mm": por_r,
        "rocno_odpad_mm": por_r - uporabno,
        "rocno_odpad_delez": (por_r - uporabno) / por_r if por_r else 0.0,
        "rocno_traki": len(roc["traki"]),
        "prihranek_mm": por_r - por_o,
        "prihranek_delez": (por_r - por_o) / por_r if por_r else 0.0,
    }


def razrez_kosov_podatki(kosi, c, oznaka="KOS", glava="KOSI ŠT."):
    """Kot razrez_podatki, a za kose RAZLIČNIH dolžin (vrata, razrezane lamele).

    Vrne isti nabor ključev kot razrez_podatki (traki, rez_rows, viz_traki,
    kosovnica, iz_ost_kos, ostanki_posodobitev, preost_kosov, st_kosov), da
    lahko montažni list porabi isti izpis. Novi ostanek traku >= MIN_OSTANKA
    se evidentira v skladišču (B1) enako kot pri razrez_podatki.
    """
    kerf = float(c.get("kerf", 3.0) or 0.0)
    barva = str(c.get("barva") or "Antracit")
    dl_zaloge = c.get("dolzine_deske") or [c.get("dolzina_deske", 5800)]
    if not isinstance(dl_zaloge, (list, tuple)):
        dl_zaloge = [dl_zaloge]
    r = razrez_kosov(kosi, dl_zaloge, kerf, barva)
    trenutni = nalozi_ostanke()
    novi_ostanki = []
    rez_rows = [[glava, "ŠT.", "DOLŽINE", "OSTANE"]]
    viz_traki = []
    for ti, (B, kosi_t) in enumerate(r["traki"], 1):
        ostanek = B - sum(d for _o, d in kosi_t) - kerf * len(kosi_t)
        ostanek = max(0.0, ostanek)
        ozn = ", ".join(f"{o} ({fmt(d)})" for o, d in kosi_t)
        rez_rows.append([f"TRAK {ti} ({fmt(B)} mm)", str(len(kosi_t)), ozn,
                         fmt(ostanek)])
        viz_traki.append((B, [(o, d) for o, d in kosi_t]))
        if ostanek >= MIN_OSTANKA:
            novi_ostanki.append({"dolzina": round(ostanek, 3), "barva": barva,
                                 "profil": str(c.get("profil") or "")})
    posodobitev = [copy.deepcopy(o) for o in trenutni] + novi_ostanki
    return {"traki": r["traki"], "rez_rows": rez_rows, "viz_traki": viz_traki,
            "kosovnica": r["kosovnica"], "iz_ost_kos": 0,
            "ostanki_posodobitev": posodobitev,
            "preost_kosov": 0, "st_kosov": r["st_kosov"]}

# ============================================================ issue #14 === #
# Napredni razrez: model dejanske zaloge (A), proizvodne omejitve (B),
# spodnja meja in status optimalnosti (C), primerjava načrtov (D),
# skladišče ostankov (E).
#
# FIZIČNI MODEL (dokaz — glej docs/issue-14-nacrt.md):
#   trak B: kosi p1..pn, rezi = n−1 (flush) ALI n (ločen ostanek/odpad).
#   Bilanca: B = zacetni_odrez + koncni_odrez + Σkosi + rezi·kerf
#              + ostanek + odpad   (vsota vedno natanko B).
#   Obstojeci model („vsak kos nosi svoj rez“) je natanko primer z
#   ločenim ostankom (n rezov) — NOVA definicija odpada NI uvedena:
#   „odpad_skupaj“ = poraba − Σkosi (kot metrika_reza), razčlenitev na
#   kerf/odrez/ostanek/odpad pa je ločeno poročana.
# ======================================================================== #


@dataclass(frozen=True)
class ZalogovnaPostavka:
    """Postavka dejanske zaloge (issue #14 A) — količinsko omejena."""

    dolzina: float
    kolicina: Optional[int] = None      # None = neomejeno (nazaj združljivo)
    material: str = ""
    profil: str = ""
    barva: str = ""
    serija: str = ""
    vir: str = "zaloga"                 # "zaloga" | "ostanek"
    oznaka: str = ""


@dataclass(frozen=True)
class Kos:
    """Kos za razrez — lastnosti določajo združljive surovce."""

    oznaka: str
    dolzina: float
    material: str = ""
    profil: str = ""
    barva: str = ""
    serija: str = ""


@dataclass(frozen=True)
class OmejitveReza:
    """Proizvodne omejitve (issue #14 B) — vezane na stroj/material."""

    kerf: float = 3.0
    zacetni_odrez: float = 0.0
    koncni_odrez: float = 0.0
    min_ostanek: float = MIN_OSTANKA
    min_dolzina_kosa: float = 0.0
    max_dolzina_kosa: Optional[float] = None
    toleranca: float = 0.0
    politika: str = "odpad"     # "odpad"|"palice"|"cena"|"cas"|"ostanki"
    cene_palice: Optional[Dict[float, float]] = None
    cas_reza_mm: float = 0.0
    cas_menjave: float = 0.0


@dataclass
class Trak:
    """En surovec v načrtu — sledljivost do zalogovne postavke."""

    zaloga: ZalogovnaPostavka
    kosi: List[Tuple[str, float]] = field(default_factory=list)
    zacetni_odrez: float = 0.0
    koncni_odrez: float = 0.0
    rezi: int = 0
    kerf_skupaj: float = 0.0
    ostanek_mm: float = 0.0
    odpad_mm: float = 0.0

    @property
    def dolzina(self) -> float:
        return self.zaloga.dolzina

    def bilanca_napaka(self) -> float:
        """B − (odrezi + kosi + kerf + ostanek + odpad); mora biti 0."""
        return (self.dolzina - self.zacetni_odrez - self.koncni_odrez
                - sum(d for _o, d in self.kosi) - self.kerf_skupaj
                - self.ostanek_mm - self.odpad_mm)


def zdruzljivo(a, b) -> bool:
    """Združljivost lastnosti (material/profil/barva/serija); '' = karkoli."""
    for kljuc in ("material", "profil", "barva", "serija"):
        av = getattr(a, kljuc, "") or ""
        bv = getattr(b, kljuc, "") or ""
        if av and bv and av != bv:
            return False
    return True


def preveri_omejitve(o: OmejitveReza) -> None:
    """Validacija omejitev (Varni privzeti — napake javimo, ne tiho popravimo)."""
    if o.kerf < 0 or o.zacetni_odrez < 0 or o.koncni_odrez < 0:
        raise ValueError("Kerf in odrezi ne smejo biti negativni.")
    if o.min_ostanek < 0:
        raise ValueError("min_ostanek ne sme biti negativen.")
    if o.toleranca < 0:
        raise ValueError("toleranca ne sme biti negativna.")
    if o.max_dolzina_kosa is not None and o.max_dolzina_kosa <= 0:
        raise ValueError("max_dolzina_kosa mora biti pozitivna.")
    if o.politika not in ("odpad", "palice", "cena", "cas", "ostanki"):
        raise ValueError(f"Neznana politika optimizacije: {o.politika!r}.")
    if o.politika == "cena" and not o.cene_palice:
        raise ValueError("Politika 'cena' zahteva cene_palice "
                         "{dolzina: cena}.")


def _zapri_trak(trak: Trak, o: OmejitveReza) -> Trak:
    """Zapre trak po fizičnem modelu: rezi n−1 (flush) ali n (ločen rep)."""
    n = len(trak.kosi)
    if n == 0:
        trak.rezi = 0
        trak.kerf_skupaj = 0.0
        trak.ostanek_mm = 0.0
        trak.odpad_mm = (trak.dolzina - trak.zacetni_odrez - trak.koncni_odrez)
        return trak
    preostanek = (trak.dolzina - trak.zacetni_odrez - trak.koncni_odrez
                  - sum(d for _oz, d in trak.kosi) - (n - 1) * o.kerf)
    if abs(preostanek) <= 1e-9:
        trak.rezi = n - 1                    # flush — zadnji kos do roba
        trak.kerf_skupaj = (n - 1) * o.kerf
        trak.ostanek_mm = 0.0
        trak.odpad_mm = 0.0
    else:
        trak.rezi = n                        # zadnji rez loči rep
        trak.kerf_skupaj = n * o.kerf
        rep = preostanek - o.kerf
        if rep < -1e-9:
            raise ValueError(
                "Trak ne zapre bilance: za zadnji rez manjka "
                f"{fmt(-rep)} mm (kerf {fmt(o.kerf)}).")
        if rep >= o.min_ostanek:
            trak.ostanek_mm = rep
            trak.odpad_mm = 0.0
        else:
            trak.ostanek_mm = 0.0
            trak.odpad_mm = max(0.0, rep)
    return trak


def _preostanek_traku(trak: Trak, o: OmejitveReza) -> float:
    """Prostor po kosih in medreznih kerfih (brez zadnjega reza)."""
    n = len(trak.kosi)
    if n == 0:
        return trak.dolzina - trak.zacetni_odrez - trak.koncni_odrez
    return (trak.dolzina - trak.zacetni_odrez - trak.koncni_odrez
            - sum(d for _oz, d in trak.kosi) - (n - 1) * o.kerf)


def _lahko_zaprem(trak: Trak, o: OmejitveReza) -> bool:
    """Trak je zapirljiv: flush ali dovolj prostora za zadnji rez."""
    p = _preostanek_traku(trak, o)
    return abs(p) <= 1e-9 or p + 1e-9 >= o.kerf


def _strosek(trak: Trak, o: OmejitveReza) -> float:
    """Cena traku za politiko 'cena' (neznana dolžina = napaka)."""
    if not o.cene_palice:
        return 0.0
    cena = o.cene_palice.get(float(trak.dolzina))
    if cena is None:
        raise ValueError(f"Za dolžino {fmt(trak.dolzina)} mm ni cene palice.")
    return float(cena)


def _strosek_nacrta(traki: List[Trak], o: OmejitveReza):
    """Leksikografski cilj glede na politiko (determinističen, primerljiv)."""
    poraba = sum(t.dolzina for t in traki)
    st = len(traki)
    ostanek = sum(t.ostanek_mm for t in traki)
    if o.politika == "palice":
        return (st, poraba)
    if o.politika == "cena":
        return (sum(_strosek(t, o) for t in traki), poraba)
    if o.politika == "cas":
        rezov = sum(t.rezi for t in traki)
        return (rezov * o.cas_reza_mm + st * o.cas_menjave, poraba)
    if o.politika == "ostanki":
        return (poraba, -ostanek)
    return (poraba, st)                       # "odpad" (≡ poraba − Σkosi)


@dataclass
class Nacrt:
    """Rezalni načrt z razporeditvijo kosov po trakovih (issue #14 C/D)."""

    ime: str
    strategija: str
    politika: str
    traki: List[Trak]
    status: str = "optimalnost ni dokazana"   # | dokazano optimalno |
                                              # | omejen izračun | neizvedljivo
    spodnja_meja_mm: Optional[float] = None
    opomba: str = ""

    def metrike(self) -> dict:
        """Ključne številke načrta z IZRECNO definicijo vsakega odtoka."""
        zahtevano = sum(d for t in self.traki for _o, d in t.kosi)
        poraba = sum(t.dolzina for t in self.traki)
        kerf = sum(t.kerf_skupaj for t in self.traki)
        odrez = sum(t.zacetni_odrez + t.koncni_odrez for t in self.traki)
        ostanek = sum(t.ostanek_mm for t in self.traki)
        odpad = sum(t.odpad_mm for t in self.traki)
        return {
            "ime": self.ime,
            "strategija": self.strategija,
            "politika": self.politika,
            "status": self.status,
            "st_kosov": sum(len(t.kosi) for t in self.traki),
            "zahtevano_mm": zahtevano,
            "poraba_mm": poraba,
            "st_trakov": len(self.traki),
            "kerf_mm": kerf,
            "odrez_mm": odrez,
            "ostanek_mm": ostanek,
            "odpad_mm": odpad,
            # stara definicija (kot metrika_reza) — NI nova:
            "odpad_skupaj_mm": poraba - zahtevano,
            "izkoristek": (zahtevano / poraba) if poraba else 0.0,
            "delez_odpada": ((poraba - zahtevano) / poraba) if poraba else 0.0,
            "novi_ostanki": self._novi_ostanki(),
            "spodnja_meja_mm": self.spodnja_meja_mm,
        }

    def _novi_ostanki(self) -> List[Tuple[str, float]]:
        """Ostanki tega načrta — označeni kot NEVPISANI v skladišče."""
        izhod = []
        i = 0
        for t in self.traki:
            if t.ostanek_mm > 0:
                i += 1
                izhod.append((f"O-{i}", t.ostanek_mm))
        return izhod

    def preveri_bilanco(self) -> None:
        """Invariata: B = odrezi + kosi + kerf + ostanek + odpad (vsak trak)."""
        for t in self.traki:
            napaka = t.bilanca_napaka()
            if abs(napaka) > 1e-6:
                raise AssertionError(
                    f"Trak {fmt(t.dolzina)} mm: bilanca zaprta za "
                    f"{fmt(napaka)} mm.")


# ------------------------------------------------------------------- A/B --- #

def _normaliziraj_zalogo(zaloga) -> List[ZalogovnaPostavka]:
    """Seznam/dict/tuple → postavke; preveri količine in dolžine."""
    if isinstance(zaloga, ZalogovnaPostavka):
        postavke = [zaloga]
    elif isinstance(zaloga, dict):
        postavke = []
        for dolzina, kolicina in zaloga.items():
            postavke.append(ZalogovnaPostavka(dolzina=float(dolzina),
                                              kolicina=kolicina))
    else:
        postavke = []
        for p in (zaloga or []):
            if isinstance(p, ZalogovnaPostavka):
                postavke.append(p)
            elif isinstance(p, dict):
                postavke.append(ZalogovnaPostavka(**p))
            else:
                dolzina = float(p)
                postavke.append(ZalogovnaPostavka(dolzina=dolzina))
    if not postavke:
        raise ValueError("Zaloga je prazna — ni dovoljenih dolžin zaloge.")
    for p in postavke:
        if p.dolzina <= 0:
            raise ValueError(f"Zalogovna postavka {fmt(p.dolzina)} mm "
                             "ni pozitivna.")
        if p.kolicina is not None and p.kolicina < 0:
            raise ValueError("Količina zaloge ne sme biti negativna.")
    return postavke


def _normaliziraj_kose(kosi) -> List[Kos]:
    izhod = []
    for k in (kosi or []):
        if isinstance(k, Kos):
            kos = k
        elif isinstance(k, dict):
            kos = Kos(**k)
        else:
            oznaka, dolzina = k[0], k[1]
            kos = Kos(oznaka=str(oznaka), dolzina=float(dolzina))
        if kos.dolzina <= 0:
            raise ValueError(f"Kos {kos.oznaka} ima neveljavno dolžino "
                             f"{fmt(kos.dolzina)}.")
        izhod.append(kos)
    return izhod


def _preveri_kose(kosi: List[Kos], o: OmejitveReza) -> None:
    for k in kosi:
        if k.dolzina < o.min_dolzina_kosa - 1e-9:
            raise ValueError(
                f"Kos {k.oznaka} ({fmt(k.dolzina)} mm) je krajši od "
                f"najmanjše dovoljene dolžine {fmt(o.min_dolzina_kosa)} mm.")
        if o.max_dolzina_kosa is not None and \
                k.dolzina > o.max_dolzina_kosa + o.toleranca + 1e-9:
            raise ValueError(
                f"Kos {k.oznaka} ({fmt(k.dolzina)} mm) presega največjo "
                f"dovoljeno dolžino {fmt(o.max_dolzina_kosa)} mm.")


def _preveri_zalogo(kosi: List[Kos], postavke: List[ZalogovnaPostavka],
                    o: OmejitveReza) -> None:
    """Vsak kos mora iti v natanko en trak; zaloga mora zadoščati.

    Če zaloga ne zadošča, javimo ValueError z izpisom MANJKAJOČIH kosov —
    nikoli tiho ne odpremo dodatne palice (issue #14 A).
    """
    for k in kosi:
        primerni = [p for p in postavke
                    if zdruzljivo(p, k)
                    and p.dolzina + 1e-9 >= k.dolzina + o.zacetni_odrez
                    + o.koncni_odrez
                    and (p.dolzina - o.zacetni_odrez - o.koncni_odrez
                         - k.dolzina) + 1e-9 >= 0]
        if not primerni:
            raise ValueError(
                f"Kos {k.oznaka} ({fmt(k.dolzina)} mm) ne gre v noben "
                "dovoljen surovec (dolžina/lastnosti).")
    # groba količinska preveritev: kosi + najmanjši kerfi proti prostornini
    potrebno = sum(k.dolzina for k in kosi) + max(0, len(kosi) - 1) * o.kerf
    na_voljo = 0.0
    for p in postavke:
        if p.kolicina is None:
            na_voljo = math.inf
            break
        na_voljo += p.kolicina * (p.dolzina - o.zacetni_odrez - o.koncni_odrez)
    if na_voljo + 1e-6 < potrebno:
        raise ValueError(
            "Zaloga ne zadošča: potrebno vsaj "
            f"{fmt(potrebno)} mm, na voljo {fmt(na_voljo)} mm. "
            "Dodatnih palic NE odpiramo samodejno.")


class _ZalogaStanje:
    """Količinsko stanje zaloge z umikom/vrnitvijo (za iskanje)."""

    def __init__(self, postavke: List[ZalogovnaPostavka]):
        self.postavke = postavke
        self.kolicine: List[Optional[int]] = [p.kolicina for p in postavke]

    def na_voljo(self, i: int) -> bool:
        return self.kolicine[i] is None or (self.kolicine[i] or 0) > 0

    def umakni(self, i: int) -> bool:
        if not self.na_voljo(i):
            return False
        if self.kolicine[i] is not None:
            self.kolicine[i] = (self.kolicine[i] or 0) - 1
        return True

    def vrni(self, i: int) -> None:
        if self.kolicine[i] is not None:
            self.kolicine[i] = (self.kolicine[i] or 0) + 1

    def kopija(self) -> "_ZalogaStanje":
        novo = _ZalogaStanje(self.postavke)
        novo.kolicine = list(self.kolicine)
        return novo


def _pripravi_trak(postavka: ZalogovnaPostavka, o: OmejitveReza) -> Trak:
    return Trak(zaloga=postavka, zacetni_odrez=o.zacetni_odrez,
                koncni_odrez=o.koncni_odrez)


def _greedy_nacrt(kosi: List[Kos], stanje: _ZalogaStanje,
                  o: OmejitveReza, strategija: str) -> Optional[Nacrt]:
    """Hevristični načrt: ffd | bfd | najmanj-palic | najnizja-cena | rocno."""
    traki: List[Trak] = []
    if strategija == "rocno":
        vrstni_red = list(kosi)
    else:
        vrstni_red = sorted(kosi, key=lambda k: (-k.dolzina, k.oznaka))

    for kos in vrstni_red:
        postavljen = False
        # 1) obstoječi traki — izbira po strategiji
        kandidati = []
        for ti, t in enumerate(traki):
            if not zdruzljivo(t.zaloga, kos):
                continue
            p = _preostanek_traku(t, o)
            # dodan kos: + kos.dolzina + kerf (novi medrezni rez)
            nov_p = p - kos.dolzina - o.kerf
            if nov_p < -1e-9:
                continue
            # po dodajanju mora biti trak zapirljiv (flush ali ≥ kerf)
            if not (abs(nov_p) <= 1e-9 or nov_p + 1e-9 >= o.kerf):
                continue
            kandidati.append((ti, nov_p))
        if kandidati:
            if strategija == "bfd":
                ti = min(kandidati, key=lambda x: (x[1], x[0]))[0]
            elif strategija == "najmanj-palic":
                ti = max(kandidati, key=lambda x: (x[1], -x[0]))[0]
            else:                             # ffd / rocno / najnizja-cena
                ti = kandidati[0][0]
            traki[ti].kosi.append((kos.oznaka, kos.dolzina))
            postavljen = True
        if postavljen:
            continue
        # 2) nov trak — izbira surovca po strategiji
        moznosti = []
        for i, postavka in enumerate(stanje.postavke):
            if not stanje.na_voljo(i) or not zdruzljivo(postavka, kos):
                continue
            prostor = postavka.dolzina - o.zacetni_odrez - o.koncni_odrez
            if prostor + 1e-9 < kos.dolzina:
                continue
            if not (abs(prostor - kos.dolzina) <= 1e-9
                    or prostor - kos.dolzina + 1e-9 >= o.kerf):
                continue
            moznosti.append((i, postavka, prostor))
        if not moznosti:
            raise ValueError(
                f"Kos {kos.oznaka} ({fmt(kos.dolzina)} mm) ne gre v noben "
                "preostali surovec — zaloga ne zadošča.")
        if strategija == "najmanj-palic":
            i, postavka, _ = max(moznosti, key=lambda x: (x[1].dolzina, -x[0]))
        elif strategija == "najnizja-cena":
            if o.cene_palice:
                i, postavka, _ = min(
                    moznosti,
                    key=lambda x: (o.cene_palice.get(  # type: ignore[union-attr]
                        float(x[1].dolzina), math.inf), x[1].dolzina, x[0]))
            else:
                i, postavka, _ = min(moznosti,
                                     key=lambda x: (x[1].dolzina, x[0]))
        else:                                  # ffd / bfd / rocno
            i, postavka, _ = min(moznosti, key=lambda x: (x[1].dolzina, x[0]))
        if not stanje.umakni(i):
            raise AssertionError("Zaloga se je izpraznila brez opozorila.")
        t = _pripravi_trak(postavka, o)
        t.kosi.append((kos.oznaka, kos.dolzina))
        traki.append(t)

    for t in traki:
        _zapri_trak(t, o)
    nacrt = Nacrt(ime=strategija, strategija=strategija,
                  politika=o.politika, traki=traki)
    nacrt.preveri_bilanco()
    return nacrt


# --------------------------------------------------------------------- C --- #

def spodnja_meja(kosi, zaloga, omejitve=OmejitveReza()) -> dict:
    """Veljavna spodnja meja porabe za ISTI model in omejitve.

    LB = min_k max(f(k), lb2(k)) čez IZVEDLJIVE k:
      f(k) = Σkosi + (N−k)·kerf + k·(zacetni+koncni)  — material, ki ga
      vsak izvedljiv načrt s k palicami NUJNO porabi (rezov ≥ N−k);
      lb2(k) = vsota k najmanjših primernih palic iz zaloge (upoštevaje
      količine) — vsak načrt s k palicami porabi vsaj toliko;
      izvedljiv k mora še zadostovati kapaciteti: Σ k najdaljših palic ≥ f(k).
    Min prek vseh izvedljivih k velja za vsak načrt (njegov lastni k
    vključi obe komponenti) — testi preverijo, da noben načrt ne pade
    pod mejo. (Opomba: uporaba f(k*) pri najmanjšem k bi bila NEVELJAVNA,
    kadar se f zmanjšuje s k — dokazano s protiprimerom v testih.)
    """
    o = omejitve
    preveri_omejitve(o)
    kos_sez = _normaliziraj_kose(kosi)
    postavke = _normaliziraj_zalogo(zaloga)
    _preveri_kose(kos_sez, o)
    if not kos_sez:
        return {"spodnja_meja_mm": 0.0, "k_palice": 0,
                "opis": "ni kosov"}
    n = len(kos_sez)
    skupaj = sum(k.dolzina for k in kos_sez)
    trim = o.zacetni_odrez + o.koncni_odrez

    def f(k: int) -> float:
        return skupaj + (n - k) * o.kerf + k * trim

    # količinsko: koliko palic je sploh na voljo (neomejeno = ∞)
    neomejeno = any(p.kolicina is None for p in postavke)
    dolge = sorted((p.dolzina for p in postavke), reverse=True)

    def kapaciteta(k: int) -> float:
        if neomejeno:
            return k * (dolge[0] if dolge else 0.0)
        # največja možna kapaciteta k palic iz omejene zaloge
        zal = sorted(((p.dolzina, p.kolicina or 0) for p in postavke),
                     key=lambda x: -x[0])
        preostalo = k
        vsota = 0.0
        for dolzina, kol in zal:
            vzemi = min(preostalo, kol)
            vsota += vzemi * dolzina
            preostalo -= vzemi
            if preostalo <= 0:
                break
        return vsota

    k_zvezdica = None
    for k in range(1, n + 1):
        if kapaciteta(k) + 1e-6 >= f(k):
            k_zvezdica = k
            break
    if k_zvezdica is None:
        return {"spodnja_meja_mm": math.inf, "k_palice": None,
                "opis": "zaloga ne zadošča (ni izvedljivega načrta)"}

    # lb2(k) = vsota k najmanjših primernih palic (upoštevaje količine)
    min_kos = min(k.dolzina for k in kos_sez)
    primerne = sorted(p.dolzina for p in postavke
                      if p.dolzina - trim + 1e-9 >= min_kos)

    def lb2(k: int) -> float:
        if neomejeno:
            return k * (primerne[0] if primerne else 0.0)
        if len(primerne) < k:
            return math.inf
        return sum(primerne[:k])

    # veljavna meja: min prek izvedljivih k od max(f(k), lb2(k)) —
    # vsak načrt s k palicami ima porabo ≥ max(f(k), lb2(k))
    najboljsa = math.inf
    for k in range(1, n + 1):
        if kapaciteta(k) + 1e-6 < f(k):
            continue                       # k palic kapacitetno ne zadošča
        kandidat = max(f(k), lb2(k))
        if kandidat < najboljsa:
            najboljsa = kandidat
    if najboljsa is math.inf:
        return {"spodnja_meja_mm": math.inf, "k_palice": None,
                "opis": "premalo primernih palic v zalogi"}
    return {"spodnja_meja_mm": najboljsa, "k_palice": k_zvezdica,
            "opis": "veljavna relaksacija (material + kapaciteta)"}


def ekstaktni_nacrt(kosi, zaloga, omejitve=OmejitveReza(),
                    max_stanj: int = 200000) -> Optional[Nacrt]:
    """Eksaktni iskalnik (branch & bound) za majhne primere.

    Vrne optimalni načrt (status „dokazano optimalno“) ali None, če je
    bil izračun omejen z max_stanj (takrat hevristike NI dokazano
    optimalne). Cilj je leksikografski glede na politiko.
    """
    o = omejitve
    preveri_omejitve(o)
    kos_sez = _normaliziraj_kose(kosi)
    postavke = _normaliziraj_zalogo(zaloga)
    _preveri_kose(kos_sez, o)
    if len(kos_sez) > 14 or len(postavke) > 8:
        return None                       # preveliko — pošteno: ni poskusa
    _preveri_zalogo(kos_sez, postavke, o)
    stanje = _ZalogaStanje(postavke)
    vrstni_red = sorted(kos_sez, key=lambda k: (-k.dolzina, k.oznaka))
    najboljsa: List[Trak] = []
    naj_strosek = [None]                 # celica — gnezdena funkcija jo deli
    stanja = [0]
    omejeno = [False]

    def racunaj(traki: List[Trak]):
        return _strosek_nacrta(traki, o)

    def isci(i: int, traki: List[Trak]):
        if stanja[0] >= max_stanj:
            omejeno[0] = True
            return
        stanja[0] += 1
        if naj_strosek[0] is not None and racunaj(traki) > naj_strosek[0]:
            return                            # odrez: slabši od najboljšega
        if i == len(vrstni_red):
            st = racunaj(traki)
            if naj_strosek[0] is None or st < naj_strosek[0]:
                naj_strosek[0] = st
                najboljsa[:] = [
                    Trak(zaloga=t.zaloga, kosi=list(t.kosi),
                         zacetni_odrez=t.zacetni_odrez,
                         koncni_odrez=t.koncni_odrez) for t in traki]
            return
        kos = vrstni_red[i]
        # (a) obstoječi traki
        for t in traki:
            if not zdruzljivo(t.zaloga, kos):
                continue
            p = _preostanek_traku(t, o)
            nov_p = p - kos.dolzina - o.kerf
            if nov_p < -1e-9:
                continue
            if not (abs(nov_p) <= 1e-9 or nov_p + 1e-9 >= o.kerf):
                continue
            t.kosi.append((kos.oznaka, kos.dolzina))
            isci(i + 1, traki)
            t.kosi.pop()
            if omejeno[0]:
                return
        # (b) novi trakovi — brez podvajanja enakih surovcev
        videne = set()
        for ix, postavka in enumerate(stanje.postavke):
            if not stanje.na_voljo(ix) or not zdruzljivo(postavka, kos):
                continue
            kljuc = (postavka.dolzina, postavka.material, postavka.profil,
                     postavka.barva, postavka.serija)
            if kljuc in videne:
                continue
            videne.add(kljuc)
            prostor = (postavka.dolzina - o.zacetni_odrez - o.koncni_odrez)
            if prostor + 1e-9 < kos.dolzina:
                continue
            if not (abs(prostor - kos.dolzina) <= 1e-9
                    or prostor - kos.dolzina + 1e-9 >= o.kerf):
                continue
            if not stanje.umakni(ix):
                continue
            t = _pripravi_trak(postavka, o)
            t.kosi.append((kos.oznaka, kos.dolzina))
            traki.append(t)
            isci(i + 1, traki)
            traki.pop()
            stanje.vrni(ix)
            if omejeno[0]:
                return

    isci(0, [])
    if naj_strosek[0] is None:
        raise ValueError("Ni izvedljivega načrta (zaloga ne zadošča).")
    traki = najboljsa
    for t in traki:
        _zapri_trak(t, o)
    nacrt = Nacrt(ime="ekstaktno", strategija="ekstaktno",
                  politika=o.politika, traki=traki,
                  status=("omejen izračun" if omejeno[0]
                          else "dokazano optimalno"))
    nacrt.preveri_bilanco()
    return nacrt


STRATEGIJE = ("rocno", "ffd", "bfd", "najmanj-palic", "najnizja-cena")


def razrez_nacrt(kosi, zaloga, omejitve=OmejitveReza(),
                 strategija: str = "ffd") -> Nacrt:
    """En rezalni načrt z razporeditvijo kosov po trakovih.

    ``kosi``: [(oznaka, dolzina), Kos ali dict]; ``zaloga``: seznam
    ZalogovnaPostavka, dict {dolzina: količina} ali seznam dolžin
    (neomejeno — nazaj združljivo).
    """
    if strategija not in STRATEGIJE:
        raise ValueError(f"Neznana strategija: {strategija!r} "
                         f"(dovoljene: {', '.join(STRATEGIJE)}).")
    o = omejitve
    preveri_omejitve(o)
    kos_sez = _normaliziraj_kose(kosi)
    postavke = _normaliziraj_zalogo(zaloga)
    _preveri_kose(kos_sez, o)
    _preveri_zalogo(kos_sez, postavke, o)
    return _greedy_nacrt(kos_sez, _ZalogaStanje(postavke), o, strategija)  # type: ignore[return-value]


def primerjaj_nacrte(kosi, zaloga, omejitve=OmejitveReza(),
                     vkljuci_ekstaktno: bool = True) -> dict:
    """Generira in primerja več načrtov (issue #14 D).

    Vrne dict: nacrti (razvrščeni po politiki), spodnja_meja, tabela
    (vrstice za prikaz), statusi. Uporabnik izbere načrt — klicatelj ga
    shrani; sistem ga NE zamenja tiho.
    """
    o = omejitve
    preveri_omejitve(o)
    kos_sez = _normaliziraj_kose(kosi)
    postavke = _normaliziraj_zalogo(zaloga)
    _preveri_kose(kos_sez, o)
    _preveri_zalogo(kos_sez, postavke, o)
    meja = spodnja_meja(kos_sez, postavke, o)
    nacrti: List[Nacrt] = []
    for strategija in STRATEGIJE:
        n = _greedy_nacrt(kos_sez, _ZalogaStanje(postavke), o, strategija)
        if n is not None:
            nacrti.append(n)
    if vkljuci_ekstaktno and len(kos_sez) <= 12:
        e = ekstaktni_nacrt(kos_sez, postavke, o)
        if e is not None:
            nacrti.append(e)
    lb = meja.get("spodnja_meja_mm")
    for n in nacrti:
        m = n.metrike()
        if n.status == "dokazano optimalno":
            n.spodnja_meja_mm = m["poraba_mm"]   # optimum = meja
        else:
            n.spodnja_meja_mm = lb
    nacrti.sort(key=lambda n: (_strosek_nacrta(n.traki, o), n.ime))
    for n in nacrti:
        if n.status == "dokazano optimalno":
            continue
        if any(x.status == "dokazano optimalno" for x in nacrti):
            n.status = "optimalnost ni dokazana"
    tabela = []
    for n in nacrti:
        m = n.metrike()
        lb_n = n.spodnja_meja_mm
        vrzel = (m["poraba_mm"] - lb_n) if lb_n not in (None, math.inf) else None
        tabela.append({
            "ime": n.ime,
            "strategija": n.strategija,
            "status": n.status,
            "st_trakov": m["st_trakov"],
            "poraba_mm": m["poraba_mm"],
            "kerf_mm": m["kerf_mm"],
            "odrez_mm": m["odrez_mm"],
            "ostanek_mm": m["ostanek_mm"],
            "odpad_mm": m["odpad_mm"],
            "odpad_skupaj_mm": m["odpad_skupaj_mm"],
            "izkoristek": m["izkoristek"],
            "spodnja_meja_mm": lb_n,
            "vrzel_mm": vrzel,
            "vrzel_delez": (vrzel / lb_n) if (vrzel is not None and lb_n) else None,
        })
    return {"nacrti": nacrti, "spodnja_meja": meja, "tabela": tabela,
            "kriterij": o.politika}