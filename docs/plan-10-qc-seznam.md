# Načrt 10 — QC seznam (kontrola delavnica + teren, potrditvena polja)

*Izboljšava 4 s prednostne lestvice: „QC seznam (montažni koraki +
potrditvena polja)“ — profesionalna praksa: kontrolni seznam vezan na
risbo, kosi se preverjajo proti listu (renderdraw/AISC).*

## Stanje (po natančnem pregledu — NIČ ne bom podcenil)
Montažni list ŽE ima „KONTROLA NA TERENU“ (7 točk s kljukicami □) in
„MONTAŽNI KORAKI“. Manjka pa:
- **kontrola v delavnici** (mere/kosi/material po TEJ risbi — kriteriji
  vezani na strani/detajle risbe);
- **potrditvena polja pri montažnih korakih** (vsak korak se kljukira);
- **podpis kontrole** (QC) v podpisni vrstici (zdaj: IZDELAL/STRANKA/DATUM).

## Rešitev
1. **MONTAŽNI KORAKI + ☐**: vsak korak dobi potrditveno polje
   („MONTAŽNI KORAKI — potrdi ☐“) — monter kljukira opravljeno.
2. **KONTROLNI SEZNAM (QC)** namesto „KONTROLA NA TERENU“ — dve skupini:
   - DELAVNICA: mere/kote (str. 1, blok toleranc) • material/barva
     (vzorec proizvajalca) • kosi in oznake/nalepke (str. 2, rezalni
     načrt) • sidranje (DETAJL 1);
   - TEREN: mere objekta in lege pritrditve • višina/raven/delovanje
     vrat • statiko potrdil strokovnjak (opomba 6).
   Vsaka točka nosi KRITERIJ (sklic na risbo) — kontrola je vezana na list.
3. **Podpisna vrstica**: dodano polje KONTROLA (QC podpis) —
   IZDELAL | KONTROLA | STRANKA | DATUM MONTAŽE.

## Lega (brez prekrivanj — preverjeno)
Desni stolpec: QC blok (288, 256) z 7 točkami v 2 skupinah (višina ≈ 38 mm)
→ spodnji rob ≈ 218; SIDRANJE ostane na 214; SESTAVA na 180. Montažni
koraki se premikajo v desni stolpec le, ko je sestava None — nespremenjeno.

## Poštenost
Potrditvena polja so PRAZNA (obrazec za izpolnjevanje) — nič ni označeno
kot opravljeno; „Risba NI statični izračun“ ostaja tudi v QC točki.

## Preverjanje
- PDF (obe predlogi): „KONTROLNI SEZNAM“, skupini DELAVNICA/TEREN,
  „☐“ v korakih, „KONTROLA (QC podpis)“ v podpisni vrstici;
- izrez lista (brez prekrivanj);
- tests/test_qc_seznam.py.