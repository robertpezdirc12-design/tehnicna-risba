# Načrt 8 — DETAJL 1: sidranje (dimenzioniran, povezan s tabelo)

*Izboljšava 2 s prednostne lestvice, POPRAVLJENA po natančnem pregledu kode.*

## ⚠️ Popravek napake v primerjava-risbe.md

Primerjava je zapisala „samo čelni pogled“ in „detajli vez: MANJKA“ — to
**NI DRŽALO**. `narisi_ogrado` in `narisi_pokoncna` že rišeta:
čelni + bočni pogled, tloris (z zidom in nosilci), PREREZ A-A (pokončna
celo v merilu 1:5 s ploščo, osnovo in ankerji), DETAJL PRITRJEVANJA
(krog „NERAZMERJENO“: podlaga, osnova, ankerja, steber) in DETAJL
LAMELE/DESKE. Popravek je zapisan v dokumentu z datumom.

## Dejanska vrzel (po natančnem branju)
Profesionalni ograjni CAD (rdirail) dimenzionira sidranje: tip/Ø sidra,
**globino**, debelino plošče in **oddaljenost roba sidra od roba podlage**.
Pri nas:
- detajl je označen „NERAZMERJENO“, brez dimenzij globine/roba;
- podatki o sidranju živijo v TABELI (`montazni_sidranje`: beton → anker
  M10 / 60 mm, zid → fasadni Ø8 / 70 mm, les/jeklo → vijak Ø8 / 40 mm —
  „priporočeno, potrdi strokovnjak“) in so od detajla ločeni.

## Rešitev
1. **`jedro.priporoceno_sidranje(podlaga)`** — EDO vir resnice za tabelo in
   detajl: `(vrsta_podlage, sidro, globina_mm)` ali `(None, None, None)`
   za nepoznano podlago (iskreno: brez izmišljanja!).
2. **`risba`** (obe predlogi):
   - „DETAJL PRITRJEVANJA“ → **„DETAJL 1 — SIDRANJE“** (številke = detajli,
     črke = prerezi — dosledno, brez trka A/A);
   - „DETAJL LAMELE/DESKE“ → „DETAJL 2 — …“;
   - na detajlu nova dimenzija: **globina sidra** iz `priporoceno_sidranje`
     (označena „≈ priporočeno — potrdi strokovnjak“) ali „?? — določi
     projektant“, če podlage ni;
   - dimenzija **oddaljenosti roba** z iskrenim markerjem „?? določi
     projektant po podlagi“ (vrednosti NE IZMIŠLJAMO);
   - v prerezu A-A (pokončna, 1:5) se napisu ankerjev doda ista globina.
3. **`montazni_sidranje`** tabela: podatki iz `priporoceno_sidranje`,
   glava „SIDRANJE (priporočeno) — DETAJL 1“ (povezava med tabelo in risbo).
4. **docs/primerjava-risbe.md**: popravek z datumom (vrstici „bočni
   pogled/prerezi“ in „detajli vez“ → DELNO/IMAMO z opisom).

## Poštenost (pravila projekta)
- globine 60/70/40 mm so že označene „priporočeno — potrdi strokovnjak“;
  ostanejo ≈ / ocenjeno, NIKOLI „izmerjeno“;
- debelina plošče in oddaljenost roba = NEZNANO (??), ker nimamo podatka;
  NIČ se ne izmišlja;
- „NI statični izračun“ opomba ostaja.

## Preverjanje
- testi: `priporoceno_sidranje` (beton/zid/les-jeklo/nepoznano), PDF detajl
  vsebina za obe predlogi (globina za beton, „??“ brez podlage, naslova),
  tabela = enaka viru;
- realni GUI: generiranje + screenshot lista (detajl viden), pypdf besedilo.