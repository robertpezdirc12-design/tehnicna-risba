# -*- coding: utf-8 -*-
"""Neodvisni regresijski testi modela reza (issue #6, §5).

Testni program rešuje ENAKE majhne primere z NEODVISNO metodo (izčrpna
kombinatorična enumeracija polnitev trakov za enake kose) in rezultate
primerja s produkcijo (razrez.py). Mešane dolžine se preverjajo z ročno
izračunanimi pričakovanimi vrednostmi (T5) in invariantami, ker je
izčrpno iskanje za mešane kose eksponentno.

Pričakovane vrednosti so ročno izračunane v komentarjih — če test pade,
je treba UGOTOVITI, katera stran se moti (ne „popravljati“ testa na
dejavni rezultat). Dokazni primer iz issue #6: 3 kosi 500 mm, kerf 2 mm,
surovca [1002, 1552] → optimalno [(1552, 3)]: 1 surovec, 46 mm odpada
(stari greedy: 2 surovca, 500 mm odpada).
"""
import pytest

from razrez import (kos_iz_vira, ostanek_po_rezih, stevilo_palic,
                    optimiziraj_zalogo, porazdeli_z_ostanki,
                    razrez_podatki, razrez_kosov)


# --------------------------------------------------- referenčni reševalnik
def ref_optimum(kos_dol, n, dolzine, kerf):
    """Izčrpen NEODVISNI reševalnik za enake kose (enumeracija kombinacij).

    Vrne (Σ nabavljene dolžine, št. trakov, skupni odpad) optimalne
    razporeditve — drugačen algoritem kot produkcijski DP.
    """
    opts = []
    for B in sorted(set(dolzine)):
        kap = kos_iz_vira(B, kos_dol, kerf)
        for kol in range(1, kap + 1):
            opts.append((B, kol, ostanek_po_rezih(B, kol, kos_dol, kerf)))
    best = [None]

    def rek(preost, cost):
        if preost == 0:
            if best[0] is None or cost < best[0]:
                best[0] = cost
            return
        if cost[0] > best[0][0] if best[0] else False:
            return
        for (B, kol, odp) in opts:
            if kol <= preost:
                rek(preost - kol, (cost[0] + B, cost[1] + 1, cost[2] + odp))

    rek(n, (0, 0, 0.0))
    return best[0]


def prod_cost(traki, kos_dol, kerf):
    return (sum(B for B, _ in traki), len(traki),
            round(sum(ostanek_po_rezih(B, kol, kos_dol, kerf)
                      for B, kol in traki), 6))


# ------------------------------------------------------------- T1: model
def test_t1_model_reza_meje():
    """(V + kerf) // (k + kerf) = največje n z n·k + (n−1)·kerf ≤ V."""
    assert kos_iz_vira(1002, 500, 2) == 2    # 2·500 + 1·2 = 1002 ≤ 1002 (flush)
    assert kos_iz_vira(1001, 500, 2) == 1    # 2. kos bi rabil 1002 > 1001
    assert kos_iz_vira(1552, 500, 2) == 3    # 3·500 + 2·2 = 1504 ≤ 1552
    assert kos_iz_vira(1503, 500, 2) == 2    # 3 kosi rabijo 1504 > 1503
    assert kos_iz_vira(1504, 500, 2) == 3    # natanko 1504
    assert kos_iz_vira(1000, 1000, 3) == 1   # kos = trak, 0 rezov
    assert kos_iz_vira(999, 1000, 3) == 0    # kos daljši od traku
    assert kos_iz_vira(1000, 250, 0) == 4    # kerf 0
    assert kos_iz_vira(1002, 500, -5) == 2   # negativen kerf → 0
    assert kos_iz_vira(1002, 500, None) == 2


def test_t1_ostanki():
    assert ostanek_po_rezih(1552, 3, 500, 2) == 46      # 1552 − 3·502
    assert ostanek_po_rezih(1002, 2, 500, 2) == 0       # flush, šprica −2 → 0
    assert ostanek_po_rezih(1552, 0, 500, 2) == 1552
    assert ostanek_po_rezih(3000, 2, 1000, 3) == 994


def test_t1_ostanek_prekoracenje_vrne_napako():
    """3 kosov 500 mm iz 1002 mm ni mogoče — napaka, ne tiho 0."""
    with pytest.raises(ValueError):
        ostanek_po_rezih(1002, 3, 500, 2)


# ------------------------------------------------------------- T2: palice
def test_t2_stevilo_palic():
    assert stevilo_palic(500, 3, 1552, 2) == 1     # kapaciteta 3
    assert stevilo_palic(500, 3, 1002, 2) == 2     # kapaciteta 2 → ceil(3/2)
    # kapaciteta (6000): 4·1200 + 3·3 = 4809 ≤ 6000 → 4 → ceil(9/4) = 3
    assert stevilo_palic(1200, 9, 6000, 3) == 3
    with pytest.raises(ValueError):
        stevilo_palic(5900, 1, 5800, 3)


# ------------------------------------------ T3: dokazni primer + referenca
def test_t3_dokazni_primer_iz_issue():
    """3 × 500 mm, kerf 2, zaloga [1002, 1552] → [(1552, 3)] (1 surovec)."""
    traki = optimiziraj_zalogo(500, 3, [1002, 1552], 2)
    assert sorted(traki) == [(1552.0, 3)]
    # bilanca: 1552 = 3·500 + 3·2 (rez) + 46 (ostanek)
    assert prod_cost(traki, 500, 2) == (1552.0, 1, 46.0)


def test_t3_dokazni_primer_5_kosov():
    """5 × 500 → [(1552, 3), (1002, 2)]: 2 surovca, 46 mm odpada."""
    traki = optimiziraj_zalogo(500, 5, [1002, 1552], 2)
    assert sorted(traki) == [(1002.0, 2), (1552.0, 3)]
    assert prod_cost(traki, 500, 2) == (2554.0, 2, 46.0)


def test_t3_kriterij_skupna_dolzina():
    """6 × 500 → 3×1002 (Σ 3006) pred 2×1552 (Σ 3104) — kriterij (ΣB, traki, odpad)."""
    traki = optimiziraj_zalogo(500, 6, [1002, 1552], 2)
    assert sorted(traki) == [(1002.0, 2), (1002.0, 2), (1002.0, 2)]
    assert prod_cost(traki, 500, 2) == (3006.0, 3, 0.0)


def test_t3_dokazni_primer_sirasa_zaloga():
    """5 × 1000, kerf 3, zaloga [5800, 4200, 3000] → [(5800, 5)]: 1 surovec."""
    traki = optimiziraj_zalogo(1000, 5, [5800, 4200, 3000], 3)
    assert sorted(traki) == [(5800.0, 5)]


def test_t3_primerjava_z_neodvisno_referenco():
    """Produkcijski DP mora doseči enako (ΣB, traki, odpad) kot izčrpna
    enumeracija — fiksen nabor majhnih primerov (regresijska mreža)."""
    primeri = [
        (500, 3, [1002, 1552], 2), (500, 5, [1002, 1552], 2),
        (500, 6, [1002, 1552], 2), (500, 2, [1002, 1552], 2),
        (1000, 5, [5800, 4200, 3000], 3), (1000, 2, [5800, 4200, 3000], 3),
        (2400, 4, [6000, 3000], 3), (250, 7, [1000, 2000], 0),
        (1200, 5, [3000], 3), (300, 9, [2000, 1000], 2),
    ]
    for kos_dol, n, dolzine, kerf in primeri:
        traki = optimiziraj_zalogo(kos_dol, n, dolzine, kerf)
        assert sum(k for _, k in traki) == n, (kos_dol, n, dolzine, kerf)
        ref = ref_optimum(kos_dol, n, dolzine, kerf)
        assert prod_cost(traki, kos_dol, kerf)[:2] == ref[:2], \
            (kos_dol, n, dolzine, kerf, traki, ref)


def test_t3_robni_primeri():
    assert optimiziraj_zalogo(500, 3, [], 2) == []
    assert optimiziraj_zalogo(500, -1, [1002], 2) == []
    assert optimiziraj_zalogo(0, 3, [1002], 2) == []
    assert optimiziraj_zalogo(5900, 3, [5800], 3) == []   # brez fiktivnih trakov


def test_t3_dolga_serija():
    """600 kosov po 100 mm iz 5800 mm — brez skrite omejitve; Σ kosov = 600."""
    traki = optimiziraj_zalogo(100, 600, [5800], 3)
    assert sum(k for _, k in traki) == 600
    for B, kol in traki:
        assert kol <= kos_iz_vira(B, 100, 3)


# ------------------------------------------------ T4: porazdeli z ostanki
def test_t4_porazdelitev_brez_dvojnega_odstevanja():
    ostanki = [{"dolzina": 1200.0, "barva": "a", "profil": "p"},
               {"dolzina": 800.0, "barva": "a", "profil": "p"},
               {"dolzina": 1000.0, "barva": "b", "profil": "p"},
               {"dolzina": 600.0, "barva": "a", "profil": "p"},
               {"dolzina": 1002.0, "barva": "a", "profil": "p"}]
    kopija = [dict(o) for o in ostanki]
    iz_ost, preost, posodobljeno = porazdeli_z_ostanki(
        500, 7, ostanki, 2, "a", "p")
    # 1200 → 2 kosa (196), 1002 → 2 kosa (0), 800 → 1 kos (298), 600 → 1 (98)
    assert sum(k for _, k, _ in iz_ost) == 6
    assert preost == 1
    assert ostanki == kopija                     # vhod se NE mutira
    indeksi = [i for i, _, _ in iz_ost]
    assert len(indeksi) == len(set(indeksi))     # vsak ostanek največ 1×
    # 0 in 98 < MIN_OSTANKA → izbrisana; tuji (barva=b) ostane
    assert [o["dolzina"] for o in posodobljeno] == [196.0, 298.0, 1000.0]


def test_t4_filter_barve_profila():
    ostanki = [{"dolzina": 1200.0, "barva": "x", "profil": "y"}]
    iz_ost, preost, _ = porazdeli_z_ostanki(500, 1, ostanki, 2, "a", "p")
    assert iz_ost == [] and preost == 1


# ------------------------------------------- T5: mešane dolžine (razrez_kosov)
def test_t5_flush_kos_gre_v_trak():
    """Kos 3000 iz traku 3000 (0 rezov, flush) — prej zavrnjen (model A)."""
    r = razrez_kosov([("A", 3000)], [3000], 3)
    assert r["traki"] == [(3000.0, [("A", 3000.0)])]
    r = razrez_kosov([("A", 2998)], [3000], 3)   # šprica 2 mm < kerf
    assert r["traki"] == [(3000.0, [("A", 2998.0)])]


def test_t5_best_fit_surovec():
    """Kos 500 iz [5800, 3000] → najkrajša zadostna zaloga 3000."""
    r = razrez_kosov([("A", 500)], [5800, 3000], 3)
    assert r["traki"] == [(3000.0, [("A", 500.0)])]


def test_t5_ffd_dva_trakova():
    r = razrez_kosov([("A", 1200), ("B", 1200), ("C", 1200)], [3000], 3)
    assert len(r["traki"]) == 2
    assert sorted(len(k) for _, k in r["traki"]) == [1, 2]


def test_t5_konsolidacija_v_en_trak():
    """2 kosa 1000 iz [1000, 2000] → 1 trak 2000 (ne 2 × 1000)."""
    r = razrez_kosov([("A", 1000), ("B", 1000)], [1000, 2000], 0)
    assert r["traki"] == [(2000.0, [("A", 1000.0), ("B", 1000.0)])]


def test_t5_zavrne_predolgega():
    with pytest.raises(ValueError):
        razrez_kosov([("A", 5900)], [5800], 3)
    with pytest.raises(ValueError):
        razrez_kosov([("A", 0)], [3000], 3)


def test_t5_invariante_na_mrezi():
    """Vsak kos mora biti postavljen, kapaciteta trakov spoštovana,
    ostanek = max(0, B − Σd − n·kerf)."""
    prim = [([("A", 2500), ("B", 1500), ("C", 900)], [6000, 3000], 3),
            ([("A", 700), ("B", 700), ("C", 700), ("D", 700)], [2000], 2),
            ([("A", 2990), ("B", 2990)], [6000], 4)]
    for kosi, zaloge, kerf in prim:
        r = razrez_kosov(kosi, zaloge, kerf)
        assert r["st_kosov"] == len(kosi)
        assert sum(len(k) for _, k in r["traki"]) == len(kosi)
        for B, kt in r["traki"]:
            vsota = sum(d for _, d in kt)
            assert vsota + max(0, len(kt) - 1) * kerf <= B + 1e-6


# ------------------------------------- T5.7/5.9: razrez_podatki z dokaznim primerom
def test_t5_razrez_podatki_dokazni_primer():
    c = {"kerf": 2, "dolzine_deske": [1002, 1552], "uporabi_ostanke": False}
    rp = razrez_podatki(500, 3, c)
    # po popravku optimizatorja: 1 trak 1552 s 3 kosi (prej 2 trakova)
    assert sum(kol for _, kol in rp["traki"]) == 3
    assert len(rp["traki"]) == 1 and rp["traki"][0][0] == 1552.0
    assert len(rp["kosovnica"]) == 3
    # dejanske A5 invariante morajo prestati
    for B, kol in rp["traki"]:
        assert kol <= kos_iz_vira(B, 500, 2)