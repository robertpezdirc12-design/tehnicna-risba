# Plan C — Barvni statusi mer v obrazcu (zaupanje pri vsaki meritvi)

## Vir (raziskava UI/UX)
- Metrologist: „vsak rezultat ima oceno zaupanja — takoj veš, ali številki
  verjeti ali posneti znovo“ (barvna označitev pri vsaki meritvi)

## Problem
V `merjenje.py` so meritve v seznamu brez statusa (le „M1: 1234 mm“),
rezultati zaznave pa v statusni vrstici — uporabnik ne loči na prvi pogled
zanesljive meritve od negotove.

## Cilj
1. Vsaka meritev v seznamu dobi **obarvan status** († izmerjeno — zeleno,
   ?? brez merila — rdeče) z legendo v oknu.
2. Rezultat samodejne zaznave dobi **zaupanje 0–1 z barvo**:
   zeleno ZANESLJIVO (≥ 0,75), oranžno PREVERI (≥ prag), rdeče NEGOTOVO.

## Spremembe
- `merjenje.py`: `BARVE_STATUSOV`, `status_meritve()`, `barva_zaupanja()`,
  `_vstavi_meritev()` (obarvan vnos v seznam), statusne vrstice zaznave z
  barvo + zaupanjem, legenda v oknu.

## Testi / verifikacija
1. `status_meritve()` / `barva_zaupanja()` — ročno preverjene meje.
2. GUI: `_vstavi_meritev()` obarva vnos (itemconfig fg) in doda znak.
3. Celotna glavna suita zelena.

## Zunaj obsega (iskreno)
- Prenos meritev nazaj v glavni obrazec (vmesnik) — ločena funkcionalnost.
- Samodejna kalibracija zaupanja iz fizične napake (model napake) —
  zaupanje ostaja hevristika nepravilnosti periodike (F3).