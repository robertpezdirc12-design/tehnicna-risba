# -*- coding: utf-8 -*-
import sys

new_funcs = r'''

def _kosovnica_iz_plana(plan, label_prefix, barva):
    """Vrne (kosovnica_entries, rez_rows, viz_traki)."""
    kos = []
    rez_rows = []
    viz_traki = []
    pc = 1
    kos_idx = 1
    ostanek_n = 1
    nabava_n = 1
    for s in plan.get("sources", []):
        n = int(s.get("cuts_count", 0))
        L = float(s.get("length", 0))
        piece = float(s.get("piece_length", 0))
        if n <= 0:
            continue
        p1 = pc
        p2 = pc + n - 1
        if s.get("source_type") == "ostanek":
            vir_ime = f"OSTANEK #{ostanek_n}"
            rez_rows.append([f"{vir_ime} ({fmt(L)} mm)", str(n), f"{p1}–{p2}", fmt(s.get("remainder", 0))])
            for j in range(n):
                kos.append((str(kos_idx), piece, vir_ime, barva))
                kos_idx += 1
            viz_traki.append((L, [(f"{label_prefix}{p1 + j}", piece) for j in range(n)]))
            ostanek_n += 1
        else:
            vir_ime = f"NABAVA {nabava_n}"
            rez_rows.append([f"{vir_ime} ({fmt(L)} mm)", str(n), f"{p1}–{p2}", fmt(s.get("remainder", 0))])
            for j in range(n):
                kos.append((str(kos_idx), piece, f"{vir_ime} ({fmt(L)} mm)", barva))
                kos_idx += 1
            viz_traki.append((L, [(f"{label_prefix}{p1 + j}", piece) for j in range(n)]))
            nabava_n += 1
        pc += n
    return kos, rez_rows, viz_traki


def _narocilo_wpc_opis(plan, profil, barva):
    purchase = plan.get("purchase", {})
    if not purchase:
        return f"- {profil}, barva {barva} — ni nove nabave (kosi iz ostankov)"
    deli = [f"{int(k)} kos × {fmt(L)} mm" for L, k in sorted(purchase.items(), reverse=True)]
    return f"- {profil}, barva {barva} — nabava: " + " + ".join(deli)


def narisi_montazni_list(ax, c):
    """Stran 2 za predlogo "ograja" (prečna)."""
    m = c["mere"]
    sir = m["sirina"]
    zg, sp, lamele, vrzel, n = razpored(m)
    raz = m.get("razmak_nosilcev", 1000)
    n_nos = max(2, math.ceil(sir / raz) + 1)
    h_ograje = max(zg) - min(sp)
    dno, vrh = min(sp), max(zg)
    profil = c.get("profil", PRIVZETO["profil"])
    barva = c.get("barva", PRIVZETO["barva"])
    vijak_lamela_naziv = c.get("vijak_lamela") or "Vijak (do dobavitelja)"
    vijak_nosilec_naziv = c.get("vijak_nosilec") or f"Pritrdilni vijaki za {c.get('podlaga') or 'podlago'}"
    pritrdilo_ime = pritrdilo_material(vijak_nosilec_naziv)
    kerf = float(c.get("kerf", PRIVZETO.get("kerf", 3.0)) or 0.0)
    dolzine_deske = c.get("dolzine_deske") or [5800]
    uporabi_ostanke = bool(c.get("uporabi_ostanke", True))
    ostanki_skladisce = nalozi_ostanke() if uporabi_ostanke else []
    dl_palice = float(c.get("dolzina_palice", 6000) or 6000)
    n_vij = n * n_nos

    pot = [
        ["Lesena letev / nosilec 20×40", "20 × 40 mm", f"{n_nos * 2} kos × {fmt(raz)} mm", "montaža na nosilce"],
        ["Lamele WPC", f"{fmt(sir)} × {fmt(m['lamela_v'])} mm", f"{n} kos × {fmt(sir)} mm", profil],
        ["Nosilna alu cev 50×30", "50 × 30 mm", f"{n_nos} kos × {fmt(h_ograje)} mm", "navpično, v polnosti lamele"],
        ["C-objemka za cev 50×30", "za 50 × 30 mm", f"{n_nos * 2} kos", f"pritrditev na {c.get('podlaga') or 'podlago'}"],
        ["Zaključni alu U-profil", "50 × 30 mm", "2 kos × dolžina ograje", "zgoraj in spodaj"],
        [vijak_lamela_naziv, vijak_dim(vijak_lamela_naziv), f"{n_vij} kos", "2 × na lamelo na nosilec (skozi notranjo cev)"],
        [vijak_nosilec_naziv, vijak_dim(vijak_nosilec_naziv, pritrdilo_ime), f"{n_nos * 2} kos", f"v {c.get('podlaga') or 'podlago'}, 2 × na nosilec"],
        ["Pokrivne kapice / čepi", "za C-objemko", f"{n_nos * 2} kos", "skrijejo vijake"],
    ]

    sestava = [
        ("Zaključni alu profil", "50 × 30 mm (U)"),
        ("WPC lamela", f"{fmt(m['lamela_v'])} mm  (×{n})"),
        ("Vmesna letev", "20 × 40 mm"),
        ("Nosilna alu cev", "50 × 30 mm"),
        ("C-objemka", "→ podlaga"),
    ]

    plan_l = plan_razreza(sir, n, dolzine_deske, kerf,
                          ostanki=ostanki_skladisce, barva=barva, profil=profil,
                          uporabi_ostanke=uporabi_ostanke)
    if not plan_l.get("ok"):
        raise ValueError("Razrez lamel ni mogoč: " + (plan_l.get("napaka") or "neznana napaka"))
    kos_l, rez_rows, viz_traki = _kosovnica_iz_plana(plan_l, "L", barva)

    les_dol = max(6000.0, float(dl_palice))
    plan_les = plan_razreza(raz, n_nos * 2, [les_dol], 0.0,
                            ostanki=None, barva="", profil="Lesena letev 20×40",
                            uporabi_ostanke=False)
    palice_letev = len([s for s in plan_les.get("sources", []) if s.get("cuts_count", 0) > 0])
    por_letev = n_nos * 2 * raz / 1000.0
    nab_letev = palice_letev * les_dol / 1000.0
    odp_letev = max(0.0, nab_letev - por_letev)

    cev_kosov = n_nos
    u_kosov = 2
    plan_cev = plan_razreza(h_ograje, cev_kosov, [dl_palice], kerf,
                            ostanki=None, barva="", profil="Nosilna alu cev 50×30",
                            uporabi_ostanke=False)
    plan_u = plan_razreza(sir, u_kosov, [dl_palice], kerf,
                          ostanki=None, barva="", profil="Zaključni alu U-profil 50×30",
                          uporabi_ostanke=False)
    palice_cev = len([s for s in plan_cev.get("sources", []) if s.get("cuts_count", 0) > 0])
    palice_u = len([s for s in plan_u.get("sources", []) if s.get("cuts_count", 0) > 0])
    palice_alu = palice_cev + palice_u
    nab_alu = palice_alu * dl_palice / 1000.0
    por_alu = (cev_kosov * h_ograje + u_kosov * sir) / 1000.0
    odp_alu = max(0.0, nab_alu - por_alu)

    alu_rez_rows = []
    alu_viz = []
    for i, s in enumerate([x for x in plan_cev.get("sources", []) if x.get("cuts_count", 0) > 0], 1):
        alu_rez_rows.append([f"CEV {i} (nabava, {fmt(s['length'])} mm)", str(s['cuts_count']),
                             f"cevi × {fmt(h_ograje)} mm", fmt(s.get("remainder", 0))])
        alu_viz.append((s["length"], [(f"C{i}.{j+1}", h_ograje) for j in range(int(s["cuts_count"]))]))
    for i, s in enumerate([x for x in plan_u.get("sources", []) if x.get("cuts_count", 0) > 0], 1):
        alu_rez_rows.append([f"U-PROFIL {i} (nabava, {fmt(s['length'])} mm)", str(s['cuts_count']),
                             f"U-profili × {fmt(sir)} mm", fmt(s.get("remainder", 0))])
        alu_viz.append((s["length"], [(f"U{i}.{j+1}", sir) for j in range(int(s["cuts_count"]))]))

    koraki = [
        f"Odmeri in označi pozicije {n_nos} nosilcev (razmak {fmt(raz)} mm) na {c.get('podlaga') or 'podlago'}.",
        "Pritrdi C-objemke z vijaki; preveri navpičnost.",
        f"Vstavi nosilne alu cevi 50×30 (višina {fmt(h_ograje)} mm) v objemke in privij.",
        "Namesti lesene letve 20×40 vodoravno na vrh in dno cevi (nosilec za lamele).",
        f"Vgradi lamele ({vijak_lamela_naziv} skozi notranjo alu cev; brez predrtja ne vrtaj!).",
        "Namesti zaključna alu U-profila zgoraj in spodaj.",
        "Kontrola ravni in višine, slika izvedbo, pridobi podpis stranke.",
    ]

    rez_rows_prikaz = [["VIR (WPC)", "KOSOV", "OZNAKE", "OSTANEK (mm)"]] + rez_rows
    if alu_rez_rows:
        rez_rows_prikaz.append(["— ALUMINIJ (ločeno) —", "", "", ""])
        rez_rows_prikaz.extend(alu_rez_rows)
    if plan_les.get("sources"):
        rez_rows_prikaz.append(["— LESENE LETVE (ločeno) —", "", "", ""])
        for i, s in enumerate(plan_les.get("sources", []), 1):
            rez_rows_prikaz.append([f"LETEV {i} (nabava, {fmt(s['length'])} mm)", str(s["cuts_count"]),
                                    f"letve × {fmt(raz)} mm", fmt(s.get("remainder", 0))])

    viz_prikaz = viz_traki + alu_viz
    for i, s in enumerate(plan_les.get("sources", []), 1):
        viz_prikaz.append((s["length"], [(f"T{i}.{j+1}", raz) for j in range(int(s["cuts_count"]))]))

    montazni_osnova(ax, c, pot, rez_rows_prikaz, viz_prikaz, koraki, sestava=sestava)

    cona_z = zg[0] - sp[1]
    n_vrst_r = len(rez_rows_prikaz) - 1
    y_iz = 197 - (8.5 + 7 + min(n_vrst_r, 11) * 7) - 5.5
    ax.text(20, y_iz, f"IZRAČUN VIŠINE: {fmt(dno)} + {fmt(cona_z)} + {fmt(m['visina'] - vrh)} = {fmt(m['visina'])} mm  "
            f"(dno + polje {n} lamel + vrh)", fontsize=7.0, ha="left", va="top", fontweight="bold")
    y_iz -= 4.2
    nab_wpc = sum(L * k for L, k in plan_l.get("purchase", {}).items()) / 1000.0
    por_wpc = plan_l.get("totals", {}).get("pieces_total", 0) / 1000.0
    kerf_wpc = plan_l.get("totals", {}).get("kerf_total", 0) / 1000.0
    ost_nab_wpc = sum(s.get("remainder", 0) for s in plan_l.get("sources", []) if s.get("source_type") == "nabava") / 1000.0
    ax.text(20, y_iz,
            f"PORABA MATERIALA (WPC): kupljeno {nab_wpc:.2f} m, iz ostankov {plan_l.get('totals', {}).get('from_offcuts', 0)} kos, "
            f"v kosih {por_wpc:.2f} m, kerf {kerf_wpc:.3f} m, ostanki iz nabave {ost_nab_wpc:.2f} m • "
            f"Letve kupljeno {nab_letev:.2f} m / v kosih {por_letev:.2f} m / ostanek {odp_letev:.2f} m • "
            f"Alu kupljeno {nab_alu:.2f} m / v kosih {por_alu:.2f} m / ostanek {odp_alu:.2f} m",
            fontsize=6.4, ha="left", va="top", color="#555555")
    y_iz -= 4.2
    ax.text(20, y_iz,
            f"MATEMATIČNA KONTROLA RAZREZA (WPC): {fmt(plan_l.get('totals', {}).get('stock_total', 0))} mm = "
            f"{fmt(plan_l.get('totals', {}).get('pieces_total', 0))} mm (kosi) + "
            f"{fmt(plan_l.get('totals', {}).get('kerf_total', 0))} mm (kerf) + "
            f"{fmt(plan_l.get('totals', {}).get('remainder_total', 0))} mm (ostanki)",
            fontsize=6.0, ha="left", va="top", color="#555555")
    y_iz -= 4.8
    ax.text(20, y_iz,
            "SIDRANJE: priporočene globine sidranja po podlagi so v tabeli desno — pred izvedbo potrdi s projektantom in navodili dobavitelja.",
            fontsize=6.0, ha="left", va="top", color="#555555", style="italic")
    y_iz -= 3.8
    ax.text(20, y_iz,
            "OPOZORILO: risba je informativna in ni statični izračun. Nosilnost, sidranje in veterno breme preveri usposobljen strokovnjak.",
            fontsize=6.0, ha="left", va="top", color="#555555", fontweight="bold")

    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    nar = [
        f"NAROČILO — WPC material ({c.get('dobavitelj') or 'WoodCore'})",
        f"Naloga: {c['risba_st']} • Datum: {datum} • Predloga: {c.get('predloga', 'ograja')}",
        "",
        "DESKE (WPC):",
        _narocilo_wpc_opis(plan_l, profil, barva),
        f"  Rez: {n} kos × {fmt(sir)} mm  |  kerf {fmt(kerf)} mm",
        "",
        "PROFILI / NOSILCI:",
        f"- Nosilna alu cev 50×30 — {palice_cev} kos × {fmt(dl_palice)} mm (reza: {cev_kosov} × {fmt(h_ograje)} mm)",
        f"- Zaključni alu U-profil 50×30 — {palice_u} kos × {fmt(dl_palice)} mm (reza: {u_kosov} × {fmt(sir)} mm)",
        f"- Lesena letev 20×40 — {palice_letev} kos × {fmt(les_dol)} mm (reza: {n_nos * 2} × {fmt(raz)} mm)",
        "",
        "PRITRDILNI MATERIAL:",
        f"- {vijak_lamela_naziv} — {n_vij} kos",
        f"- {vijak_nosilec_naziv} — {n_nos * 2} kos",
        f"- C-objemke za cev 50×30 — {n_nos * 2} kos",
        f"- Pokrivne kapice / čepi — {n_nos * 2} kos",
    ]

    postavke = [
        (f"WPC deske {profil}", por_wpc, "m", "wpc_m", por_wpc),
        ("Nosilna alu cev 50×30", cev_kosov * h_ograje / 1000.0, "m", "alu_cev_m", cev_kosov * h_ograje / 1000.0),
        ("Zaključni alu U-profil 50×30", u_kosov * sir / 1000.0, "m", "alu_u_m", u_kosov * sir / 1000.0),
        ("Lesena letev 20×40", por_letev, "m", "letev_m", por_letev),
        (vijak_lamela_naziv, n_vij, "kos", "vijak_lamela_kos", n_vij),
        (vijak_nosilec_naziv, n_nos * 2, "kos", "vijak_nosilec_kos", n_nos * 2),
        ("C-objemka za cev 50×30", n_nos * 2, "kos", "objemka_kos", n_nos * 2),
        ("Pokrivne kapice / čepi", n_nos * 2, "kos", "kapica_kos", n_nos * 2),
    ]

    return {
        "postavke": postavke,
        "narocilo": "\n".join(nar),
        "ostanki_posodobitev": plan_l.get("new_offcuts"),
        "kosovnica": kos_l,
        "plan_wpc": plan_l,
    }


def narisi_montazni_pokoncna(ax, c):
    """Stran 2 za predlogo "pokončna" (stebri + navpične deske)."""
    m = c["mere"]
    sir, vis = m["sirina"], m["visina"]
    odcep = m["odcep"]
    p = razpored_pokoncna(m)
    n_d, n_s = p["n_desk"], p["n_stebrov"]
    n_polj = n_d - 1
    ds, vr = m["deska_sirina"], m["vrzel"]
    rob = p["rob"]
    deska_h = vis - odcep
    profil = c.get("profil", PRIVZETO["profil"])
    barva = c.get("barva", PRIVZETO["barva"])
    dl_palice = float(c.get("dolzina_palice", 6000) or 6000)
    kerf = float(c.get("kerf", PRIVZETO.get("kerf", 3.0)) or 0.0)
    dolzine_deske = c.get("dolzine_deske") or [5800]
    uporabi_ostanke = bool(c.get("uporabi_ostanke", True))
    ostanki_skladisce = nalozi_ostanke() if uporabi_ostanke else []
    vijak_lamela_naziv = c.get("vijak_lamela") or "Vijak za WPC/les"
    vijak_nosilec_naziv = c.get("vijak_nosilec") or "Anker/vijak za podlago"

    pritrditev = c.get("pritrditev") or "vrh"
    pritrd_opis = ("Vpetje v tla (sidranje stebra v podlago)" if pritrditev == "tla"
                   else "Bočna pritrditev na steno" if pritrditev == "bok"
                   else "Pritrditev na vrh nosilca")

    vijaki = n_d * n_s * 2
    pot = [
        [f"WPC deska {profil}", f"{fmt(ds)} × {fmt(m['deska_debelina'])} mm", f"{n_d} kos × {fmt(deska_h)} mm", "navpično (med stebre)"],
        ["Alu steber 60×40", "60 × 40 mm", f"{n_s} kos × {fmt(vis)} mm", "nosilec ograje"],
        ["Ročaj / zaključni profil", f"širina {fmt(sir)} mm", "1 kos", "na vrhu stebrov"],
        ["Osnove za steber", "90 × 90 × 6 mm", f"{n_s} kos", pritrd_opis],
        [vijak_lamela_naziv, vijak_dim(vijak_lamela_naziv), f"{vijaki} kos", "2 × na desko na steber (levo + desno)"],
        [vijak_nosilec_naziv, vijak_dim(vijak_nosilec_naziv, "jeklo"), f"{n_s * 2} kos", "pritrditev osnov na podlago"],
    ]
    sestava = [
        ("Ročaj / profil", f"širina {fmt(sir)} mm"),
        (f"WPC deska {profil}", f"{fmt(m['deska_sirina'])}×{fmt(m['deska_debelina'])} mm (×{n_d})"),
        ("Vmesna vrzel", f"{fmt(vr)} mm" if vr else "0 mm"),
        ("Alu steber 60×40", f"v = {fmt(vis)} mm (×{n_s})"),
        ("Osnova 90×90×6", "pritrditev"),
    ]

    koraki = [
        "Odmeri in označi pozicije stebrov na podlagi.",
        "Pritrdi osnove z vijaki za podlago (glej DETALJ PRITRJEVANJA).",
        "Postavi stebre v osnove; kontroliraj navpičnost.",
        f"Vgradi deske med stebre (2 × {vijak_lamela_naziv} na desko na steber; spodaj pusti odcep).",
        f"Namesti ročaj/profil na vrh (skupna dolžina {fmt(sir)} mm).",
        "Končna kontrola: višine, razmaki, stabilnost; slika izvedbo in podpis.",
    ]

    plan_d = plan_razreza(deska_h, n_d, dolzine_deske, kerf,
                          ostanki=ostanki_skladisce, barva=barva, profil=profil,
                          uporabi_ostanke=uporabi_ostanke)
    if not plan_d.get("ok"):
        raise ValueError("Razrez desk ni mogoč: " + (plan_d.get("napaka") or "neznana napaka"))
    kos_d, rez_rows, viz_traki = _kosovnica_iz_plana(plan_d, "D", barva)

    plan_s = plan_razreza(vis, n_s, [dl_palice], kerf,
                          ostanki=None, barva="", profil="Alu steber 60×40",
                          uporabi_ostanke=False)
    if not plan_s.get("ok"):
        raise ValueError("Razrez stebrov ni mogoč: " + (plan_s.get("napaka") or "neznana napaka"))
    palice_s = len([s for s in plan_s.get("sources", []) if s.get("cuts_count", 0) > 0])

    rez_rows_prikaz = [["VIR (WPC deske)", "KOSOV", "OZNAKE", "OSTANEK (mm)"]] + rez_rows
    rez_rows_prikaz.append(["— ALUMINIJ stebri (ločeno) —", "", "", ""])
    viz_prikaz = list(viz_traki)
    for i, s in enumerate([x for x in plan_s.get("sources", []) if x.get("cuts_count", 0) > 0], 1):
        rez_rows_prikaz.append([f"STEBER-PALICA {i} (nabava, {fmt(s['length'])} mm)", str(s["cuts_count"]),
                                f"stebri × {fmt(vis)} mm", fmt(s.get("remainder", 0))])
        viz_prikaz.append((s["length"], [(f"S{i}.{j+1}", vis) for j in range(int(s["cuts_count"]))]))

    nab_wpc = sum(L * k for L, k in plan_d.get("purchase", {}).items()) / 1000.0
    por_wpc = plan_d.get("totals", {}).get("pieces_total", 0) / 1000.0
    kerf_wpc = plan_d.get("totals", {}).get("kerf_total", 0) / 1000.0
    ost_nab_wpc = sum(s.get("remainder", 0) for s in plan_d.get("sources", []) if s.get("source_type") == "nabava") / 1000.0
    nab_alu = palice_s * dl_palice / 1000.0
    por_alu = n_s * vis / 1000.0
    odp_alu = max(0.0, nab_alu - por_alu)

    montazni_osnova(ax, c, pot, rez_rows_prikaz, viz_prikaz, koraki, sestava=sestava)

    n_vrst_r = len(rez_rows_prikaz) - 1
    y_iz = 197 - (8.5 + 7 + min(n_vrst_r, 11) * 7) - 5.5
    ax.text(20, y_iz, f"IZRAČUN VIŠINE: {fmt(vis)} = {fmt(m['rocaj_v'])} (ročaj) + {fmt(deska_h)} (deske) + {fmt(odcep)} (odcep) • "
            f"polje: {fmt(sir)} = 2×{fmt(rob)} (rob) + {n_polj}×{fmt(vr)} (vrzel) + {n_d}×{fmt(ds)} (deske)",
            fontsize=6.8, ha="left", va="top", fontweight="bold")
    y_iz -= 4.2
    ax.text(20, y_iz,
            f"PORABA MATERIALA (WPC): kupljeno {nab_wpc:.2f} m, iz ostankov {plan_d.get('totals', {}).get('from_offcuts', 0)} kos, "
            f"v kosih {por_wpc:.2f} m, kerf {kerf_wpc:.3f} m, ostanki iz nabave {ost_nab_wpc:.2f} m • "
            f"Alu stebri kupljeno {nab_alu:.2f} m / v kosih {por_alu:.2f} m / ostanek {odp_alu:.2f} m",
            fontsize=6.4, ha="left", va="top", color="#555555")
    y_iz -= 4.2
    ax.text(20, y_iz,
            f"MATEMATIČNA KONTROLA RAZREZA (WPC): {fmt(plan_d.get('totals', {}).get('stock_total', 0))} mm = "
            f"{fmt(plan_d.get('totals', {}).get('pieces_total', 0))} mm (kosi) + "
            f"{fmt(plan_d.get('totals', {}).get('kerf_total', 0))} mm (kerf) + "
            f"{fmt(plan_d.get('totals', {}).get('remainder_total', 0))} mm (ostanki)",
            fontsize=6.0, ha="left", va="top", color="#555555")
    y_iz -= 4.8
    ax.text(20, y_iz,
            "SIDRANJE: priporočene globine sidranja po podlagi so v tabeli desno — pred izvedbo potrdi s projektantom in navodili dobavitelja.",
            fontsize=6.0, ha="left", va="top", color="#555555", style="italic")
    y_iz -= 3.8
    ax.text(20, y_iz,
            "OPOZORILO: risba je informativna in ni statični izračun. Nosilnost, sidranje in veterno breme preveri usposobljen strokovnjak.",
            fontsize=6.0, ha="left", va="top", color="#555555", fontweight="bold")

    datum = c.get("datum") or datetime.date.today().strftime("%d.%m.%Y")
    nar = [
        f"NAROČILO — WPC material ({c.get('dobavitelj') or 'WoodCore'})",
        f"Naloga: {c['risba_st']} • Datum: {datum} • Predloga: {c.get('predloga', 'pokončna')}",
        "",
        "DESKE (WPC):",
        _narocilo_wpc_opis(plan_d, profil, barva),
        f"  Rez: {n_d} kos × {fmt(deska_h)} mm  |  kerf {fmt(kerf)} mm",
        "",
        "PROFILI (aluminij):",
        f"- Alu steber 60×40 — {palice_s} kos × {fmt(dl_palice)} mm (razrez: {n_s} × {fmt(vis)} mm)",
        "",
        "OSTALA PRITRDITVA:",
        f"- Ročaj — 1 kos × {fmt(sir)} mm",
        f"- Osnove za steber — {n_s} kos",
        f"- {vijak_lamela_naziv} — {vijaki} kos",
        f"- {vijak_nosilec_naziv} — {n_s * 2} kos",
    ]

    postavke = [
        (f"WPC deske {profil}", por_wpc, "m", "wpc_m", por_wpc),
        ("Alu steber 60×40", por_alu, "m", "alu_stebri_m", por_alu),
        ("Ročaj / zaključni profil", sir / 1000.0, "m", "rocaj_m", sir / 1000.0),
        ("Osnove za steber", n_s, "kos", "osnova_kos", n_s),
        (vijak_lamela_naziv, vijaki, "kos", "vijak_lamela_kos", vijaki),
        (vijak_nosilec_naziv, n_s * 2, "kos", "vijak_nosilec_kos", n_s * 2),
    ]

    return {
        "postavke": postavke,
        "narocilo": "\n".join(nar),
        "ostanki_posodobitev": plan_d.get("new_offcuts"),
        "kosovnica": kos_d,
        "plan_wpc": plan_d,
    }

'''

with open('risba.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_imp = 'from razrez import (nalozi_ostanke, shrani_ostanke,\n                     porazdeli_z_ostanki, optimiziraj_zalogo)'
new_imp = 'from razrez import (nalozi_ostanke, shrani_ostanke,\n                     porazdeli_z_ostanki, optimiziraj_zalogo,\n                     plan_razreza, _kosi_na_vir)'
if old_imp in content:
    content = content.replace(old_imp, new_imp)
elif 'from razrez import' in content and 'plan_razreza' not in content.split('from razrez import', 1)[1].split('from matplotlib', 1)[0]:
    content = content.replace('optimiziraj_zalogo)', 'optimiziraj_zalogo, plan_razreza, _kosi_na_vir)')

marker_start = '\ndef narisi_montazni_list(ax, c):\n'
marker_end = '\n\ndef narisi_nalepke(ax, c, kosovnica):\n'
i = content.find(marker_start)
j = content.find(marker_end)
if i == -1 or j == -1 or j <= i:
    print('MARKERS NOT FOUND', i, j)
    sys.exit(1)

content = content[:i] + '\n' + new_funcs.rstrip() + '\n' + content[j+1:]

with open('risba.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print('replaced', i, j)
