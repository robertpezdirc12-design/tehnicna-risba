# Plan B — Lupa pri klikih vogalov (natančnost klikov)

## Vir (raziskava UI/UX)
- Metrologist: „pinch-zoom + vgrajena lupa pustita natančen klik na točko“
- Otja: „če samodejna zaznava ne uspe, tapni vogale sam — s povečavo“

## Problem
`avtomatska_skica.izberi_vogale` (P1) uporablja navaden `plt.ginput` —
klik na 1920×1080 sliki brez povečave ima lahko napako 10–30 px, kar je
pri dolžini ograje ~200 px višine napaka 5–15 %.

## Cilj
Interaktivni klik 4 vogalov z:
1. **Lupo** (inset) ob kurzorju — povečan izrez okoli kazalca s križcem,
2. prikazom koordinat v živo,
3. **razveljavitvijo** zadnjega klika (tipka `u` / desni klik),
4. oštevilčenimi označevalci TL, TR, BR, BL in povezovalnimi črtami,
5. zaključkom s tipko `Enter` (ko so 4 točke).

## Spremembe
- `photo_fence_proposal/avtomatska_skica.py`:
  - `_povecava(rgb, x, y, polmer, faktor)` — čisti izrez/povečava (testno),
  - `izberi_vogale(slika_pot, vnosi=None)` — nova interaktivna zanka
    (vnosi omogoča programsko pot/avtomatizacijo testov).

## Testi / verifikacija
1. `_povecava`: pike na (x, y) je v središču izreza in povečana (ročno
   preverjena svetlost/površina).
2. `izberi_vogale(vnosi=...)`: 4 točke → vrne jih v redu; 3 točke → jasna
   napaka (ne vrne nepopolnega).
3. Interaktivni tok simuliran z matplotlib dogodki (Agg): 4 kliki + Enter
   vrnejo 4 točke; `u` razveljavi zadnji klik.
4. Celotni pfp testi zeleni.

## Zunaj obsega (iskreno)
- Pinch-zoom na dotik (mobilne naprave) — namizna aplikacija uporablja
  kolešček/povečavo nad sliko, ne dotika.
- Samodejna zaznava vogalov ostaja v `zaznavanje.py`; ročni klik je
  nadomestilo, ko je zaznava negotova.