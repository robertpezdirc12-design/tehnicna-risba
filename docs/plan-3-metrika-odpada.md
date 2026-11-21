# Plan 3 — Metrika odpada % + optimizator proti ročnemu rezanju

## Vir (raziskava)
- NestingCalc benchmark: meri % odpada proti **ročnemu rezanju brez
  optimizacije** (kosi po vrstnem red seznama, brez sortiranja/pogleda
  naprej) — dokaz vrednosti optimizatorja.
- Praksa: 10 % odpada je privzeta vrednost pri 92 % postavkah (MassBid),
  pri optimiziranem razrezu 2–7 % (IRONBID).

## Spremembe
- `razrez.naivni_rez(kosi, dolzine_zaloge, kerf)` — bazna linija ročnega
  reza: kosi PO VRSTNEM REDU, polnjenje trenutnega traku, brez
  sortiranja/pogleda naprej/konsolidacije (točno po NestingCalc opisu).
- `razrez.metrika_reza(kosi, dolzine_zaloge, kerf)` — primerjava obeh
  poti: poraba/odpad/delek/traki + prihranek.
  **Definicija odpada:** nabavljena dolžina − Σ dolžin kosov (vključuje
  kerf in ostanke) — ISTA za obe poti, zato primerljivo.
- Montažni list: pri mešanih dolžinah (lamele okoli vrat/prehodov)
  primerjalna vrstica „primerjava brez ostankov: ročno X m (odpad Y %)
  → prihranek Z m“.

## Odločitve (iskreno)
- Primerjava teče **BREZ skladišča ostankov** — jasno označeno v izpisu,
  ker bi bila številka z ostanki primerljiva z „ročno“ le, če bi tudi
  delavec imel skladišče; scenarija sta sicer različna.
- Prihranek se izpiše SAMO, če je > 0 (pri enakih kosih je 0 — nič
  zavajajočega „prihranka“).
- Odpadni faktor v ponudbi (npr. +10 %) NI dodan — to je poslovna
  politika, ne meritev; predlog ostaja ločena odločitev.

## Verifikacija
- `test_razrez.py`: 4 novi testi (ročni rez brez pogleda naprej,
  primerjava z ročnim 4000 vs 3000 mm, kerf enakovredno, napake)
- `test_pdf_ciklus.py`: integracijski test — vrstica v montažnem listu
- ročni izračun primera [1500, 900] / [2000, 3000]: ročno 4000,
  optimizator 3000, prihranek 1000 mm (test preverja natanko to)