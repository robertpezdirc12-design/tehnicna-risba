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
    return int((dolzina_vir + kerf) // (dolzina_kosa + kerf))


def ostanek_po_rezih(dolzina_vir, n_kosov, dolzina_kosa, kerf):
    """Ostanek traku po rezu `n_kosov` kosov (ENKRATNO odštetje, B1)."""
    if n_kosov <= 0:
        return float(dolzina_vir)
    kerf = max(float(kerf or 0.0), 0.0)
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
    """Izbere trakove z najmanjšim odpadom — podprto VEČ tovarniških dolžin.

    Greedy: v vsakem koraku izbere trak, ki da najmanj odpada na kos.
    Zanka se vedno konča (vsak korak porabi vsaj 1 kos) — NI skrite
    omejitve števila poskusov. Vrne [(dolžina_trak, št. kosov), ...].
    Če kosa ni mogoče izrezati iz nobene dolžine ali količina ni
    izvedljiva, vrne krajši seznam — celovitost preverja razrez_podatki
    in pri pomanjkanju vrže jasno napako (A3).
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
                      if isinstance(d, (int, float)) and d > 0}, reverse=True)
    traki = []
    preost = n_kosov
    while preost > 0:
        naj = None
        for B in dolzine:
            kol = min(preost, kos_iz_vira(B, kos_dol, kerf))
            if kol <= 0:
                continue
            odpad = ostanek_po_rezih(B, kol, kos_dol, kerf)
            ucink = odpad / kol
            if naj is None or ucink < naj[0] - 1e-9 or \
                    (abs(ucink - naj[0]) <= 1e-9 and B < naj[1]):
                naj = (ucink, B, kol)
        if naj is None:
            break
        traki.append((naj[1], naj[2]))
        preost -= naj[2]
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
    assert len(kosovnica) == n_kosov, "kosovnica ne ustreza številu kosov"
    for (B, kol) in traki:
        ostanek = ostanek_po_rezih(B, kol, kos_dol, kerf)
        kerf_skupaj = B - kol * kos_dol - ostanek
        if abs(B - (kol * kos_dol + kerf_skupaj + ostanek)) > 1e-6:
            raise ValueError(f"Matematična kontrola razreza ni uspela za "
                             f"trak {fmt(B)} mm.")

    return {"traki": traki, "rez_rows": rez_rows, "viz_traki": viz_traki,
            "kosovnica": kosovnica, "iz_ost_kos": sum(k for _, k, _ in iz_ost),
            "ostanki_posodobitev": posodobitev,
            "preost_kosov": 0, "st_kosov": n_kosov}