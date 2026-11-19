# -*- coding: utf-8 -*-
"""Patch 3: optimiziraj_zalogo (vec tovarniskih dolzin) v obeh predlogah,
kosovnice, popavek dvojnega montazni_osnova klica pri pokončni."""
pot = "risba.py"
k = open(pot, encoding="utf-8").read()

# ---- ograda: fresh-deske zanka -> optimiziraj_zalogo + kosovnica ----
staro = '''    for i in range(deske):
        zac = min(na_desko, preost_kosov - i * na_desko)
        p1, p2 = pc, pc + zac - 1
        pc += zac
        ost = dl_deske - zac * sir - zac * kerf
        rez_rows.append([f"DESKA {i + 1} (nabava)", str(zac), f"{p1}–{p2}",
                         fmt(max(0, ost))])
        viz_traki.append((dl_deske,
                          [(f"L{p1 + j}", sir) for j in range(zac)]))
    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lego nosilcev (razmak največ {fmt(raz)} mm); "'''
novo = '''    traki = optimiziraj_zalogo(sir, preost_kosov,
                               c.get("dolzine_deske") or [dl_deske], kerf)
    for ti, (B, zac_k) in enumerate(traki):
        zac = min(zac_k, preost_kosov)
        p1, p2 = pc, pc + zac - 1
        pc += zac
        ost = max(0, B - zac * sir - zac * kerf)
        rez_rows.append([f"DESKA {ti + 1} (nabava, {fmt(B)} mm)", str(zac),
                         f"{p1}–{p2}", fmt(max(0, ost))])
        viz_traki.append((B, [(f"L{p1 + j}", sir) for j in range(zac)]))
    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lego nosilcev (razmak največ {fmt(raz)} mm); "'''
assert staro in k, "ograda fresh zanka"
k = k.replace(staro, novo)

# ---- ograda: kosovnica za ostanke in deske + postavke po dolžinah ----
staro = '''    por_m = deske * dl_deske / 1000
    odp_m = por_m - n * sir / 1000
    ax.text(20, y_iz - 5, f"PORABA: deske {deske} kos = {por_m:.2f} m • "
            f"odpad {odp_m:.2f} m ({odp_m / por_m * 100:.0f} %) • alu "
            f"palice {palice} kos = {palice * dl_palice / 1000:.1f} m",
            fontsize=6.5, color="#555555", ha="left", va="center")
    kolicine = {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{deske} kos = {fmt(por_m)}",
         "m", "wpc_deska_m", por_m),'''
novo = '''    por_m = sum(B for B, _ in traki) / 1000
    odp_m = por_m - n * sir / 1000
    ax.text(20, y_iz - 5, f"PORABA: deske {sum(t for _, t in traki)} kos = "
            f"{por_m:.2f} m • odpad {odp_m:.2f} m "
            f"({odp_m / por_m * 100:.0f} %) • alu palice {palice} kos = "
            f"{palice * dl_palice / 1000:.1f} m", fontsize=6.5,
            color="#555555", ha="left", va="center")
    kosovnica = []
    pc_k = 1
    for (oi, kol) in iz_ost:
        o = ostanki[oi]
        for j in range(kol):
            kosovnica.append((f"{pc_k}", sir,
                              f"ostanek #{oi + 1}", barva))
            pc_k += 1
    for (B, kol) in traki:
        for j in range(kol):
            kosovnica.append((f"{pc_k}", sir, f"deska #{B // 1000} m",
                              barva))
            pc_k += 1
    kolicine = {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{sum(t for _, t in traki)} kos "
         f"= {fmt(por_m)} m", "m", "wpc_deska_m", por_m),'''
assert staro in k, "ograda PORABA/kolicine"
k = k.replace(staro, novo)

# ---- pokončna: fresh-deske zanka -> optimiziraj_zalogo + kosovnica ----
staro = '''    for i in range(deske):
        zac = min(na_desko, preost_desk - i * na_desko)
        p1, p2 = pc, pc + zac - 1
        pc += zac
        ost = dl_deske - zac * deska_h - zac * kerf
        rez_rows.append([f"DESKA {i + 1} (nabava)", str(zac), f"{p1}–{p2}",
                         fmt(max(0, ost))])
        viz_traki.append((dl_deske,
                          [(f"D{p1 + j}", deska_h) for j in range(zac)]))
    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lege stebrov (razmak največ {fmt(m['razmak_stebrov'])} mm); "'''
novo = '''    traki = optimiziraj_zalogo(deska_h, preost_desk,
                               c.get("dolzine_deske") or [dl_deske], kerf)
    for ti, (B, zac_k) in enumerate(traki):
        zac = min(zac_k, preost_desk)
        p1, p2 = pc, pc + zac - 1
        pc += zac
        ost = max(0, B - zac * deska_h - zac * kerf)
        rez_rows.append([f"DESKA {ti + 1} (nabava, {fmt(B)} mm)", str(zac),
                         f"{p1}–{p2}", fmt(max(0, ost))])
        viz_traki.append((B, [(f"D{p1 + j}", deska_h) for j in range(zac)]))
    koraki = [
        "Preveri dejanske mere objekta in primerjaj z risbo.",
        f"Označi lege stebrov (razmak največ {fmt(m['razmak_stebrov'])} mm); "'''
assert staro in k, "pokončna fresh zanka"
k = k.replace(staro, novo)

# ---- pokončna: kosovnica + postavke ----
staro = '''    por_s = deske * dl_deske / 1000
    odp_s = por_s - n_d * deska_h / 1000
    ax.text(20, y_iz - 5, f"PORABA: deske {deske} kos = {por_s:.2f} m • "
            f"odpad {odp_s:.2f} m ({odp_s / por_s * 100:.0f} %) • alu "
            f"palice {palice_s} kos = {palice_s * dl_palice / 1000:.1f} m",
            fontsize=6.5, color="#555555", ha="left", va="center")
    return {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{deske} kos = {fmt(por_s, 2)}",
         "m", "wpc_deska_m", por_s),
        ("Alu stebri (nabava)", f"{palice_s} kos = {fmt(por_st, 2)}", "m",
         "alu_m", por_st),
        ("Ročaj", "1", "kos", "rocaj_kos", 1),
        ("Osnove za steber", f"{n_s}", "kos", "osnova_kos", n_s),
        ("Vijaki M8×70", f"{vijaki}", "kos", "vijak_kos", vijaki),
        ("Anker M10", f"{n_s * 2}", "kos", "anker_kos", n_s * 2),
    ],'''
novo = '''    por_s = sum(B for B, _ in traki) / 1000
    odp_s = por_s - n_d * deska_h / 1000
    ax.text(20, y_iz - 5, f"PORABA: deske {sum(t for _, t in traki)} kos = "
            f"{por_s:.2f} m • odpad {odp_s:.2f} m "
            f"({odp_s / por_s * 100:.0f} %) • alu palice {palice_s} kos = "
            f"{palice_s * dl_palice / 1000:.1f} m", fontsize=6.5,
            color="#555555", ha="left", va="center")
    kosovnica = []
    pc_k = 1
    for (oi, kol) in iz_ost:
        o = ostanki[oi]
        for j in range(kol):
            kosovnica.append((f"{pc_k}", deska_h,
                              f"ostanek #{oi + 1}", barva))
            pc_k += 1
    for (B, kol) in traki:
        for j in range(kol):
            kosovnica.append((f"{pc_k}", deska_h, f"deska #{B // 1000} m",
                              barva))
            pc_k += 1
    return {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{sum(t for _, t in traki)} kos "
         f"= {fmt(por_s)} m", "m", "wpc_deska_m", por_s),
        ("Alu stebri (nabava)", f"{palice_s} kos = {fmt(por_st)}", "m",
         "alu_m", por_st),
        ("Ročaj", "1", "kos", "rocaj_kos", 1),
        ("Osnove za steber", f"{n_s}", "kos", "osnova_kos", n_s),
        ("Vijaki M8×70", f"{vijaki}", "kos", "vijak_kos", vijaki),
        ("Anker M10", f"{n_s * 2}", "kos", "anker_kos", n_s * 2),
    ],
    "kosovnica": kosovnica,'''
assert staro in k, "pokončna PORABA/kosovnica"
k = k.replace(staro, novo)

# ---- ograda: kosovnica v kolicine (return) ----
staro = '''        ("Fasadni vijaki Ø8×80 + tipli", f"{n_nos * 2}", "kos",
         "fasadni_kos", n_nos * 2),
    ],
    "narocilo": "\\n".join(nar),
    "ostanki_posodobitev": (ostanki_novi if kos_iz_ost else None),
    }
    return {"postavke": kolicine["postavke"], "narocilo": kolicine["narocilo"],
            "ostanki_posodobitev": kolicine["ostanki_posodobitev"]}'''
novo = '''        ("Fasadni vijaki Ø8×80 + tipli", f"{n_nos * 2}", "kos",
         "fasadni_kos", n_nos * 2),
    ],
    "kosovnica": kosovnica,
    "narocilo": "\\n".join(nar),
    "ostanki_posodobitev": (ostanki_novi if kos_iz_ost else None),
    }
    return {"postavke": kolicine["postavke"], "narocilo": kolicine["narocilo"],
            "ostanki_posodobitev": kolicine["ostanki_posodobitev"],
            "kosovnica": kolicine["kosovnica"]}'''
assert staro in k, "ograda return kosovnica"
k = k.replace(staro, novo)

# ---- pokončna: odstrani DUPLIKAT montazni_osnova klica ----
staro = '''    montazni_osnova(ax, c, pot, rez_rows, viz_traki, koraki)

    nar = [
        "NAROČILO — WPC material (WoodCore)",
        f"Naloga: {c['risba_st']} • Datum: {datum}",
        f"Stranka: {c.get('stranka') or '—'} • Objekt: "
        f"{c.get('objekt') or '—'}",
        "",
        "DESKE:",
        f"- {profil}, barva {barva} — {deske} kos × {fmt(dl_deske)} mm "
        f"(razrez po {fmt(deska_h)} mm)"
        + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
        "",
        "PROFILI (aluminij):",
        f"- 60×40×5 — {palice_s} kos × {fmt(dl_palice)} mm "
        f"(razrez: {n_s} × {fmt(vis)} mm — stebri)",
        "",
        "OSTALA PRITRDITVA:",
        f"- Ročaj — 1 kos × {fmt(sir)} mm",
        f"- Osnove za steber — {n_s} kos",
        f"- Vijaki M8×70 Inox A2 — {vijaki} kos",
        f"- Anker M10 — {n_s * 2} kos",
    ]
    montazni_osnova(ax, c, pot, rez_rows, viz_traki, koraki)

    cona_z = p["deske_z"][1] - p["deske_z"][0]'''
novo = '''    nar = [
        "NAROČILO — WPC material (WoodCore)",
        f"Naloga: {c['risba_st']} • Datum: {datum}",
        f"Stranka: {c.get('stranka') or '—'} • Objekt: "
        f"{c.get('objekt') or '—'}",
        "",
        "DESKE:",
        f"- {profil}, barva {barva} — {deske} kos × {fmt(dl_deske)} mm "
        f"(razrez po {fmt(deska_h)} mm)"
        + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
        "",
        "PROFILI (aluminij):",
        f"- 60×40×5 — {palice_s} kos × {fmt(dl_palice)} mm "
        f"(razrez: {n_s} × {fmt(vis)} mm — stebri)",
        "",
        "OSTALA PRITRDITVA:",
        f"- Ročaj — 1 kos × {fmt(sir)} mm",
        f"- Osnove za steber — {n_s} kos",
        f"- Vijaki M8×70 Inox A2 — {vijaki} kos",
        f"- Anker M10 — {n_s * 2} kos",
    ]
    montazni_osnova(ax, c, pot, rez_rows, viz_traki, koraki)

    cona_z = p["deske_z"][1] - p["deske_z"][0]'''
assert staro in k, "duplikat montazni_osnova"
k = k.replace(staro, novo)

# ---- naročilo: več dolžin desk (ograda) ----
staro = '''        "DESKE:",
        f"- {profil}, barva {barva} — {deske} kos × {fmt(dl_deske)} mm "
        f"(razrez po {fmt(sir)} mm)"
        + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
        "",
        "PROFILI (aluminij):",
        f"- 80×40×3 — {palice} kos × {fmt(dl_palice)} mm "
        f"(razrez: 2 × {fmt(sir)} mm)",'''
novo = '''        "DESKE:",
        f"- {profil}, barva {barva}"
        + "".join(f" — {t} kos × {fmt(B)} mm" for B, t in traki)
        + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
        "",
        "PROFILI (aluminij):",
        f"- 80×40×3 — {palice} kos × {fmt(dl_palice)} mm "
        f"(razrez: 2 × {fmt(sir)} mm)",'''
assert staro in k, "nar deske vec dolzin"
k = k.replace(staro, novo)

# ---- naročilo: več dolžin desk (pokončna) ----
staro = '''        "DESKE:",
        f"- {profil}, barva {barva} — {deske} kos × {fmt(dl_deske)} mm "
        f"(razrez po {fmt(deska_h)} mm)"
        + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
        "",
        "PROFILI (aluminij):",
        f"- 60×40×5 — {palice_s} kos × {fmt(dl_palice)} mm "
        f"(razrez: {n_s} × {fmt(vis)} mm — stebri)",'''
novo = '''        "DESKE:",
        f"- {profil}, barva {barva}"
        + "".join(f" — {t} kos × {fmt(B)} mm" for B, t in traki)
        + (f" + {kos_iz_ost} kos iz ostankov" if kos_iz_ost else ""),
        "",
        "PROFILI (aluminij):",
        f"- 60×40×5 — {palice_s} kos × {fmt(dl_palice)} mm "
        f"(razrez: {n_s} × {fmt(vis)} mm — stebri)",'''
assert staro in k, "nar deske vec dolzin pokončna"
k = k.replace(staro, novo)

# ---- ograda: kolicine "postavke" WPC deske po dolzinah ----
staro = '''    kolicine = {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{sum(t for _, t in traki)} kos "
         f"= {fmt(por_m)} m", "m", "wpc_deska_m", por_m),'''
novo = '''    wpc_postavke = [f"{fmt(B / 1000, 1)} m ({t} kos)"
                    for B, t in traki]
    kolicine = {"postavke": [
        (f"WPC deske {profil} (nabava: " + " + ".join(wpc_postavke) + ")",
         f"{fmt(por_m)} m", "m", "wpc_deska_m", por_m),'''
assert staro in k, "ograda postavke vec dolzin"
k = k.replace(staro, novo)

# ---- pokončna: kolicine postavke vec dolzin ----
staro = '''    return {"postavke": [
        (f"WPC deske {profil} (nabava)", f"{sum(t for _, t in traki)} kos "
         f"= {fmt(por_s)} m", "m", "wpc_deska_m", por_s),'''
novo = '''    wpc_postavke = [f"{fmt(B / 1000, 1)} m ({t} kos)" for B, t in traki]
    return {"postavke": [
        (f"WPC deske {profil} (nabava: " + " + ".join(wpc_postavke) + ")",
         f"{fmt(por_s)} m", "m", "wpc_deska_m", por_s),'''
assert staro in k, "pokončna postavke vec dolzin"
k = k.replace(staro, novo)

# ---- ograda return: kosovnica ----
staro = '''    return {"postavke": kolicine["postavke"], "narocilo": kolicine["narocilo"],
            "ostanki_posodobitev": kolicine["ostanki_posodobitev"]}'''
novo = '''    return {"postavke": kolicine["postavke"], "narocilo": kolicine["narocilo"],
            "ostanki_posodobitev": kolicine["ostanki_posodobitev"],
            "kosovnica": kolicine["kosovnica"]}'''
assert staro in k, "ograda return kosovnica"
k = k.replace(staro, novo)

open(pot, "w", encoding="utf-8").write(k)
print("risba.py: multi-stock + kosovnica + duplikat OK")
