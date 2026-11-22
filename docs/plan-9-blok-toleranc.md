# Načrt 9 — Blok splošnih toleranc (ISO 2768-m)

*Izboljšava 3 s prednostne lestvice: „kota brez ± ni določena“ (rdirail CAD
ima na listu blok „FRACTION ±1/16, XX ±0.01, ANGLE ±1.0° …“).*

## Stanje
Opomba 1 že omenja „tolerance ISO 2768-m“, a na listu NI bloka s
konkretnimi vrednostmi — kota brez oznake tolerance je zato nedoločena.

## Rešitev
- `risba.blok_toleranc(ax, x0, y_top, sirina)`: tabela
  **SPLOŠNE TOLERANCE (ISO 2768-m)** — lineare vrednosti razreda m
  (0.5–3 ±0.1 … 2000–4000 ±2) v dveh parih stolpcev, spodaj koti
  (≤10 ±1° … >400 ±5′) + „kote brez oznake veljajo po tem bloku
  (vir: ISO 2768-1)“.
- Postavitev: sredina lista (prostor med tlorisom in detajli) pri OBEH
  predlogah — x=120, y_top=172 (mm od spodaj), preverjeno s posnetki obeh
  listov.
- Opomba 1 se razširi: „… tolerance ISO 2768-m — glej blok SPLOŠNE
  TOLERANCE …“.

## Poštenost
Vrednosti so **javno objavljene vrednosti standarda ISO 2768-1** (razred m),
ne naše meritve — v bloku je naveden vir. Nič se ne izmišlja.

## Preverjanje
- PDF (obe predlogi): „SPLOŠNE TOLERANCE“, vrednosti ±0.1/±1.2/±2, koti,
  sklic v opombi 1;
- realni GUI: generiranje + izrez lista z blokom;
- regresijski testi v tests/test_blok_toleranc.py.