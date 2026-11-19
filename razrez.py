# -*- coding: utf-8 -*-
"""razrez.py — optimizacija razreza čez več tovarniških dolžin, skladišče
ostankov, kosovnica in nalepke (uporablja ga risba.py)."""

import os

import yaml


def fmt(v):
    return f"{v:g}"


def pot_ostanki():
    return os.path.join(os.getcwd(), "ostanki.yaml")


def nalozi_ostanke():
    try:
        with open(pot_ostanki(), encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    except Exception:
        return []


def shrani_ostanke(seznam):
    with open(pot_ostanki(), "w", encoding="utf-8") as f:
        yaml.safe_dump(seznam, f, allow_unicode=True, sort_keys=False)


def optimiziraj_zalogo(kos_dol, n_kosov, dolzine_zaloge, kerf):
    """Izbere trakove z najmanjšim odpadom — podprto VEČ tovarniških dolžin.

    Greedy: v vsakem koraku izbere trak, ki da najmanj odpada na kos.
    Vrne [(dolžina_trak, št. kosov na traku), ...] po vrstnem redu reza.
    """
    traki = []
    preost = n_kosov
    poskusi = 0
    while preost > 0 and poskusi < 500:
        poskusi += 1
        naj = None
        for B in sorted(set(int(d) for d in dolzine_zaloge)):
            if B < kos_dol:
                continue
            kol = min(preost, max(1, int((B + kerf) // (kos_dol + kerf))))
            odpad = B - kol * kos_dol - kol * kerf
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

    Vrne (iz_ost [(indeks, št. kosov)], preostalo št. kosov, novi_ostanki).
    Ostanki < 100 mm po rezanju se iz skladišča izbrišejo.
    """
    pari = [(i, o) for i, o in enumerate(ostanki)
            if str(o.get("barva", "")).lower() == str(barva).lower()
            and str(o.get("profil", "")).lower() == str(profil).lower()
            and o.get("dolzina", 0) >= dol_kosa + kerf]
    pari.sort(key=lambda p: -p[1].get("dolzina", 0))
    iz_ost = []
    preost = n_kosov
    for (i, o) in pari:
        if preost == 0:
            break
        kol = min(int((o["dolzina"] + kerf) // (dol_kosa + kerf)), preost)
        o["dolzina"] = o["dolzina"] - kol * (dol_kosa + kerf)
        iz_ost.append((i, kol))
        preost -= kol
    novi = [o for o in ostanki if o.get("dolzina", 0) >= 100]
    return iz_ost, preost, novi


def razrez_podatki(kos_dol, n_kosov, c):
    """Celoten razrez za montažni list: ostanki + optimizacija + vrste.

    Vrne dict: traki [(dolžina, št. kosov)], rez_rows (glava + vrste),
    viz_traki [(dolžina, [(oznaka, dol)])], kosovnica
    [(oznaka, dolžina, vir, material)], iz_ost_kos, ostanki_posodobitev,
    preost_kosov.
    """
    kerf = c.get("kerf", 3.0)
    barva = c.get("barva") or "Antracit"
    profil = (c.get("profil") or "").strip()
    dl_zaloge = c.get("dolzine_deske") or [c.get("dolzina_deske", 5800)]
    if not isinstance(dl_zaloge, (list, tuple)):
        dl_zaloge = [dl_zaloge]

    ostanki = nalozi_ostanke() if c.get("uporabi_ostanke", True) else []
    iz_ost, preost, ostanki_novi = porazdeli_z_ostanki(
        kos_dol, n_kosov, ostanki, kerf, barva, profil)
    iz_ost_kos = sum(k for _, k in iz_ost)

    traki = optimiziraj_zalogo(kos_dol, preost, dl_zaloge, kerf)

    rez_rows = [["VIR", "KOSOV", "KOSI ŠT.", "OSTANEK PO REZU (mm)"]]
    viz_traki = []
    kosovnica = []
    pc = 1
    for (oi, kol) in iz_ost:
        o = ostanki[oi]
        p1, p2 = pc, pc + kol - 1
        pc += kol
        ost_nov = max(0, o["dolzina"] - kol * (kos_dol + kerf))
        rez_rows.append([f"OSTANEK #{oi + 1} ({fmt(o['dolzina'])} mm)",
                         str(kol), f"{p1}–{p2}", fmt(ost_nov)])
        viz_traki.append((o["dolzina"],
                          [(f"{p1 + j}", kos_dol) for j in range(kol)]))
        for j in range(kol):
            kosovnica.append((f"{p1 + j}", kos_dol,
                              f"ostanek #{oi + 1}", barva))
    for ti, (B, kol) in enumerate(traki):
        p1, p2 = pc, pc + kol - 1
        pc += kol
        ost = max(0, B - kol * kos_dol - kol * kerf)
        rez_rows.append([f"DESKA {ti + 1} (nabava, {fmt(B)} mm)", str(kol),
                         f"{p1}–{p2}", fmt(ost)])
        viz_traki.append((B, [(f"{p1 + j}", kos_dol) for j in range(kol)]))
        for j in range(kol):
            kosovnica.append((f"{p1 + j}", kos_dol,
                              f"deska #{ti + 1}", barva))
    return {"traki": traki, "rez_rows": rez_rows, "viz_traki": viz_traki,
            "kosovnica": kosovnica, "iz_ost_kos": iz_ost_kos,
            "ostanki_posodobitev": (ostanki_novi if iz_ost else None),
            "preost_kosov": preost}
