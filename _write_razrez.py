# -*- coding: utf-8 -*-
content = r'''# -*- coding: utf-8 -*-
"""razrez.py — optimizacija razreza čez več tovarniških dolžin, skladišče
ostankov, kosovnica in nabavni načrt (uporablja ga risba.py)."""

from __future__ import annotations

import copy
import math
import os
import tempfile

import yaml

MIN_OSTANKA = 100.0  # mm


def fmt(v):
    if v is None:
        return ""
    try:
        fv = float(v)
        if abs(fv - round(fv)) < 1e-9:
            return str(int(round(fv)))
        return f"{fv:.1f}".rstrip("0").rstrip(".")
    except Exception:
        return str(v)


def pot_ostanki(pot=None):
    if pot:
        return os.path.abspath(pot)
    return os.path.join(os.getcwd(), "ostanki.yaml")


def _normaliziraj_ostanek(o):
    if not isinstance(o, dict):
        return None
    try:
        dol = float(o.get("dolzina", 0) or 0)
    except (TypeError, ValueError):
        return None
    if dol <= 0:
        return None
    return {
        "dolzina": dol,
        "barva": str(o.get("barva", "") or ""),
        "profil": str(o.get("profil", "") or ""),
    }


def nalozi_ostanke(pot=None):
    p = pot_ostanki(pot)
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            podatki = yaml.safe_load(f)
    except Exception:
        return []
    if not podatki or not isinstance(podatki, list):
        return []
    out = []
    for o in podatki:
        no = _normaliziraj_ostanek(o)
        if no:
            out.append(no)
    return out


def shrani_ostanke(ostanki, pot=None):
    """Backup obstoječe datoteke + atomičen zapis. Vrne (pot, backup_pot_ali_None)."""
    p = pot_ostanki(pot)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    backup = None
    if os.path.exists(p):
        backup = p + ".bak"
        try:
            with open(p, "rb") as fi, open(backup, "wb") as fo:
                fo.write(fi.read())
        except Exception:
            backup = None
    clean = []
    for o in (ostanki or []):
        no = _normaliziraj_ostanek(o)
        if no and no["dolzina"] >= MIN_OSTANKA:
            no["dolzina"] = round(no["dolzina"], 3)
            if abs(no["dolzina"] - round(no["dolzina"])) < 1e-9:
                no["dolzina"] = int(round(no["dolzina"]))
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


def _kosi_na_vir(dolzina_vir, dolzina_kosa, kerf):
    if dolzina_kosa <= 0 or dolzina_vir < dolzina_kosa:
        return 0
    step = dolzina_kosa + max(kerf, 0.0)
    if step <= 0:
        return 0
    n = int((dolzina_vir + max(kerf, 0.0)) // step)
    while n > 0 and n * dolzina_kosa + (n - 1) * max(kerf, 0.0) > dolzina_vir + 1e-9:
        n -= 1
    while (n + 1) * dolzina_kosa + n * max(kerf, 0.0) <= dolzina_vir + 1e-9:
        n += 1
    return max(0, n)


def _remainder_po_rezih(dolzina_vir, n_kosov, dolzina_kosa, kerf):
    if n_kosov <= 0:
        return float(dolzina_vir)
    porabljeno = n_kosov * dolzina_kosa + (n_kosov - 1) * max(kerf, 0.0)
    return max(0.0, float(dolzina_vir) - porabljeno)


def _zdruzljive_dolzine(dolzine_deske):
    if dolzine_deske is None:
        return []
    if isinstance(dolzine_deske, (int, float, str)):
        dolzine_deske = [dolzine_deske]
    out = []
    for d in dolzine_deske:
        try:
            dv = float(d)
        except (TypeError, ValueError):
            continue
        if dv > 0:
            out.append(dv)
    return sorted(set(out), reverse=True)


def _resitev_za_nabavo(kolicina, dolzina_kosa, kerf, dolzina_nabave):
    cap = _kosi_na_vir(dolzina_nabave, dolzina_kosa, kerf)
    if cap <= 0:
        return None
    n_barov = math.ceil(kolicina / cap) if kolicina > 0 else 0
    plan = []
    preost = kolicina
    for _ in range(n_barov):
        vzemi = min(cap, preost)
        rem = _remainder_po_rezih(dolzina_nabave, vzemi, dolzina_kosa, kerf)
        plan.append({
            "source_type": "nabava",
            "length": float(dolzina_nabave),
            "cuts_count": vzemi,
            "kerf_total": (vzemi - 1) * max(kerf, 0.0) if vzemi > 0 else 0.0,
            "remainder": rem,
        })
        preost -= vzemi
    return plan


def _eval_plan(plan_nabava, st_razlicnih_dolzin):
    skupna_dolzina = sum(s["length"] for s in plan_nabava)
    odpad = sum(s["remainder"] for s in plan_nabava)
    st_virov = len(plan_nabava)
    return (round(odpad, 6), st_virov, st_razlicnih_dolzin, round(skupna_dolzina, 6))


def _greedy_mixed(kolicina, dolzina_kosa, kerf, lengths):
    preost = kolicina
    plan = []
    for _ in range(2000):
        if preost <= 0:
            break
        best_choice = None
        best_ckey = None
        for L in lengths:
            cap = _kosi_na_vir(L, dolzina_kosa, kerf)
            if cap <= 0:
                continue
            vzemi = min(cap, preost)
            rem = _remainder_po_rezih(L, vzemi, dolzina_kosa, kerf)
            pokrije_vse = vzemi >= preost
            ckey = (0 if pokrije_vse else 1, round(rem, 6), -vzemi, L)
            if best_ckey is None or ckey < best_ckey:
                best_ckey = ckey
                best_choice = (L, vzemi, rem)
        if best_choice is None:
            return None
        L, vzemi, rem = best_choice
        plan.append({
            "source_type": "nabava",
            "length": float(L),
            "cuts_count": vzemi,
            "kerf_total": (vzemi - 1) * max(kerf, 0.0) if vzemi > 0 else 0.0,
            "remainder": rem,
        })
        preost -= vzemi
    return plan if preost <= 0 else None


def _poisci_optimalno_nabavo(kolicina, dolzina_kosa, kerf, dolzine_deske):
    lengths = _zdruzljive_dolzine(dolzine_deske)
    if not lengths:
        return [], "Ni veljavnih nabavnih dolžin."
    usable = [L for L in lengths if _kosi_na_vir(L, dolzina_kosa, kerf) > 0]
    if not usable:
        return [], "Nobena nabavna dolžina ni dovolj velika za kos."
    if kolicina <= 0:
        return [], None

    best = None
    best_key = None

    for L in sorted(usable):
        plan = _resitev_za_nabavo(kolicina, dolzina_kosa, kerf, L)
        if plan is None:
            continue
        key = _eval_plan(plan, 1)
        tiebreak = (key, -L)
        if best is None or tiebreak < best_key:
            best = plan
            best_key = tiebreak

    usable_sorted = sorted(usable)
    if len(usable_sorted) >= 2:
        max_cap = max(_kosi_na_vir(L, dolzina_kosa, kerf) for L in usable_sorted)
        max_bars = min(math.ceil(kolicina / max_cap) + 2, 60)
        for i, L1 in enumerate(usable_sorted):
            c1 = _kosi_na_vir(L1, dolzina_kosa, kerf)
            for L2 in usable_sorted[i + 1:]:
                c2 = _kosi_na_vir(L2, dolzina_kosa, kerf)
                for n1 in range(0, max_bars + 1):
                    covered1 = n1 * c1
                    n2 = 0 if covered1 >= kolicina else math.ceil((kolicina - covered1) / c2)
                    if n1 + n2 > max_bars + 3:
                        continue
                    if n1 == 0 and n2 == 0:
                        continue
                    plan = []
                    preost = kolicina
                    bars = [(L1, c1)] * n1 + [(L2, c2)] * n2
                    bars.sort(reverse=True)
                    for Lb, cb in bars:
                        if preost <= 0:
                            break
                        vzemi = min(cb, preost)
                        rem = _remainder_po_rezih(Lb, vzemi, dolzina_kosa, kerf)
                        plan.append({
                            "source_type": "nabava",
                            "length": float(Lb),
                            "cuts_count": vzemi,
                            "kerf_total": (vzemi - 1) * max(kerf, 0.0) if vzemi > 0 else 0.0,
                            "remainder": rem,
                        })
                        preost -= vzemi
                    if preost > 0:
                        continue
                    st_razl = len(set(s["length"] for s in plan))
                    key = _eval_plan(plan, st_razl)
                    tiebreak = (key, tuple(sorted(s["length"] for s in plan, reverse=True)))
                    if best is None or tiebreak < best_key:
                        best = plan
                        best_key = tiebreak

    if len(usable_sorted) >= 3 and kolicina > 0:
        plan = _greedy_mixed(kolicina, dolzina_kosa, kerf, usable_sorted)
        if plan is not None:
            st_razl = len(set(s["length"] for s in plan))
            key = _eval_plan(plan, st_razl)
            tiebreak = (key, tuple(sorted(s["length"] for s in plan, reverse=True)))
            if best is None or tiebreak < best_key:
                best = plan
                best_key = tiebreak

    return best or [], None


def plan_razreza(dolzina_kosa, kolicina, dolzine_deske, kerf=3.0,
                 ostanki=None, barva="", profil="", uporabi_ostanke=True,
                 min_ostanek=MIN_OSTANKA):
    kerf = max(float(kerf or 0.0), 0.0)
    try:
        dolzina_kosa = float(dolzina_kosa)
    except (TypeError, ValueError):
        dolzina_kosa = 0.0
    try:
        kolicina = int(kolicina)
    except (TypeError, ValueError):
        kolicina = 0
    barva = str(barva or "")
    profil = str(profil or "")

    vhodni_ostanki = [copy.deepcopy(o) for o in (ostanki or [])]
    if kolicina <= 0 or dolzina_kosa <= 0:
        return {
            "ok": True, "napaka": None, "sources": [], "purchase": {},
            "consumed_offcuts": [], "new_offcuts": vhodni_ostanki,
            "totals": {"required_pieces": max(0, kolicina),
                       "required_piece_length": dolzina_kosa,
                       "stock_total": 0.0, "pieces_total": 0.0,
                       "kerf_total": 0.0, "remainder_total": 0.0,
                       "waste_total": 0.0, "from_offcuts": 0, "from_new": 0},
            "verify": {"ok": True, "diff": 0.0},
        }

    preost = kolicina
    sources = []
    consumed = set()

    if uporabi_ostanke and vhodni_ostanki:
        kandidati = []
        for idx, o in enumerate(vhodni_ostanki):
            if barva and str(o.get("barva", "")) != barva:
                continue
            if profil and str(o.get("profil", "")) != profil:
                continue
            cap = _kosi_na_vir(float(o.get("dolzina", 0)), dolzina_kosa, kerf)
            if cap > 0:
                kandidati.append((idx, o, cap))

        def kand_key(item):
            idx, o, cap = item
            L = float(o.get("dolzina", 0))
            rem = _remainder_po_rezih(L, cap, dolzina_kosa, kerf)
            return (round(rem, 6), -cap, -L, idx)

        kandidati.sort(key=kand_key)
        for idx, o, cap in kandidati:
            if preost <= 0:
                break
            vzemi = min(cap, preost)
            L = float(o.get("dolzina", 0))
            rem = _remainder_po_rezih(L, vzemi, dolzina_kosa, kerf)
            sources.append({
                "source_type": "ostanek",
                "length": L,
                "cuts_count": vzemi,
                "piece_length": dolzina_kosa,
                "kerf_loss": (vzemi - 1) * kerf if vzemi > 0 else 0.0,
                "remainder": rem,
                "offcut_index": idx,
                "barva": barva or str(o.get("barva", "")),
                "profil": profil or str(o.get("profil", "")),
            })
            consumed.add(idx)
            preost -= vzemi

    if preost > 0:
        nabava_plan, napaka = _poisci_optimalno_nabavo(preost, dolzina_kosa, kerf, dolzine_deske)
        if napaka or len(nabava_plan) == 0:
            lengths = _zdruzljive_dolzine(dolzine_deske)
            if not lengths:
                napaka = napaka or "Ni podanih nabavnih dolžin."
            elif all(_kosi_na_vir(L, dolzina_kosa, kerf) <= 0 for L in lengths):
                napaka = (napaka or
                          f"Kos {fmt(dolzina_kosa)} mm ne gre iz nobene nabavne dolžine "
                          f"({', '.join(fmt(L) for L in lengths)} mm) pri kerfu {fmt(kerf)} mm.")
            else:
                napaka = napaka or "Ni mogoče sestaviti načrta razreza."
            return {
                "ok": False, "napaka": napaka, "sources": sources, "purchase": {},
                "consumed_offcuts": sorted(consumed),
                "new_offcuts": copy.deepcopy(vhodni_ostanki),
                "totals": None, "verify": {"ok": False, "diff": None},
            }
        for s in nabava_plan:
            sources.append({
                "source_type": "nabava",
                "length": s["length"],
                "cuts_count": s["cuts_count"],
                "piece_length": dolzina_kosa,
                "kerf_loss": s.get("kerf_total", 0.0),
                "remainder": s["remainder"],
                "offcut_index": None,
                "barva": barva,
                "profil": profil,
            })

    new_offcuts = []
    for idx, o in enumerate(vhodni_ostanki):
        if idx not in consumed:
            new_offcuts.append(copy.deepcopy(o))
    for s in sources:
        rem = float(s.get("remainder", 0.0) or 0.0)
        if rem >= min_ostanek - 1e-9:
            new_offcuts.append({
                "dolzina": round(rem, 3),
                "barva": str(s.get("barva") or barva),
                "profil": str(s.get("profil") or profil),
            })

    purchase = {}
    for s in sources:
        if s["source_type"] == "nabava":
            L = s["length"]
            purchase[L] = purchase.get(L, 0) + 1

    stock_total = sum(float(s["length"]) for s in sources)
    pieces_total = sum(s["cuts_count"] * dolzina_kosa for s in sources)
    kerf_total = sum(float(s.get("kerf_loss", 0.0) or 0.0) for s in sources)
    remainder_total = sum(float(s.get("remainder", 0.0) or 0.0) for s in sources)
    diff = stock_total - (pieces_total + kerf_total + remainder_total)

    totals = {
        "required_pieces": kolicina,
        "required_piece_length": dolzina_kosa,
        "stock_total": round(stock_total, 6),
        "pieces_total": round(pieces_total, 6),
        "kerf_total": round(kerf_total, 6),
        "remainder_total": round(remainder_total, 6),
        "waste_total": round(remainder_total, 6),
        "from_offcuts": sum(s["cuts_count"] for s in sources if s["source_type"] == "ostanek"),
        "from_new": sum(s["cuts_count"] for s in sources if s["source_type"] == "nabava"),
    }
    ok = abs(diff) < 1e-6
    return {
        "ok": ok,
        "napaka": None if ok else f"Matematična neujemanje razreza: {diff}",
        "sources": sources,
        "purchase": purchase,
        "consumed_offcuts": sorted(consumed),
        "new_offcuts": new_offcuts,
        "totals": totals,
        "verify": {"ok": ok, "diff": diff},
    }


def optimiziraj_zalogo(dolzina_kosa, kolicina, dolzina_deske=5800, kerf=3.0):
    plan = plan_razreza(dolzina_kosa, kolicina, dolzina_deske, kerf,
                        ostanki=None, uporabi_ostanke=False)
    traki = [(s["length"], s["cuts_count"]) for s in plan.get("sources", [])]
    ostanki = [s["remainder"] for s in plan.get("sources", [])]
    odpad = sum(ostanki)
    poraba = sum(s["cuts_count"] * dolzina_kosa for s in plan.get("sources", []))
    return traki, ostanki, odpad, poraba


def porazdeli_z_ostanki(dol_kosa, kolicina, ostanki, kerf=3.0,
                        barva="", profil="", min_ostanek=MIN_OSTANKA):
    plan = plan_razreza(dol_kosa, kolicina, dolzine_deske=None, kerf=kerf,
                        ostanki=ostanki, barva=barva, profil=profil,
                        uporabi_ostanke=True, min_ostanek=min_ostanek)
    iz_ost = [(s["length"], s["cuts_count"]) for s in plan.get("sources", []) if s["source_type"] == "ostanek"]
    preost = int(kolicina) - sum(s["cuts_count"] for s in plan.get("sources", []) if s["source_type"] == "ostanek")
    return iz_ost, max(0, preost), plan.get("new_offcuts", copy.deepcopy(ostanki or []))
'''

with open(r'C:\Users\admin\Downloads\tehnicna-risba\razrez.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print('razrez.py written', len(content))
