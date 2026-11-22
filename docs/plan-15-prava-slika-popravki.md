# Načrt 15 — Popravki po preizkusu s PRAVO sliko

*Uporabnik (2026-11-22): „merjenje zelen ekran, 3d ni to to — testiraj s
pravo sliko in preverjaj popravljaj vse ker ne deluje.“*

Preizkušeno z uporabnikovo fotografijo balkona
(`Temp/pi_balkon_slike/balkon_blizu.png`, 1920×1080 — lokalno, NE v repo)
po natanko uporabnikovi poti: vmesnik → scena → „Meri s slike“ (merjenje
kot DRUGA Tk-korenina) → kalibracija → merjenje → 3D.

## Ugotovitvi (dve pravi napaki)

### 1. „Zelen ekran“ pri merjenju
- **Vzrok:** uporabnik je odprl **majhno sliko (320×240)** — program jo
  je napihnil čez celotno okno z glajenjem (BILINEAR) → zamegljen
  enobarven madež. Program pri tem NI opozoril na netočnost.
- Preizkus: 320×240 izrez prave slike reproducira pojav.
- **Popravki (`merjenje.py`):**
  - `mala_slika` (min stranica < 400 px ali < 300k pikslov) →
    **opozorilo** „MAJHNA slika, mere bodo zelo NETOČNE!“ v statusu in
    prek `messagebox.showwarning` (priporočilo ≥ 1600 px);
  - prikaz pri povečavi uporablja **NEAREST** — uporabnik vidi realne
    piksle namesto zamegljenega madeža (pri umanjšavi ostane BILINEAR);
  - meritve na majhni sliki so v seznamu označene
    **„(mala slika — netočno)“** — poštenostna oznaka potuje tudi v
    shranjen projekt.

### 2. „3D ni to to“
- **Vzrok:** model je risal **samo raven segment** ograje; `globina`
  (stranska dolžina balkona, npr. 1200 mm) je bila uporabljena le kot
  razmerje osi (`glob*3`), tla pa fiksna (±150 mm). Balkon je
  **L-oblika** (prednja 3000 + stranska 1200) — stranska ograja v 3D
  sploh ni obstajala.
- **Popravki (`tridimenzionalno.py`):**
  - **L-oblika**: prednji segment (vzdolž x pri y=0) + stranski (vzdolž
    y pri x=0) — vsak z lamelami, profili in nosilci (skupni `segment`);
  - tla = **balkonska plošča** sirina × stranska dolžina;
  - pravo razmerje osi (`box_aspect` = mere, ne `glob*3` hack);
  - barve lamel sledijo izbrani barvi (`jedro.barva_hex`, en vir
    resnice z risbo) — npr. „Teak“ = #a9764f;
  - naslov je iskren: „(L-oblika: prednja + stranska • shematsko iz
    vnesenih mer — NI model iz slike)“ (3D NI izlučen iz fotografije —
    to bi zahtevalo model iz slike, izven obsega in brez AI nedosegljivo
    zanesljivo).

## Preverjanje
- `tests/test_prava_slika_popravki.py` (6): L-oblika (stranski segment
  obstaja, tla segajo čez obe stranici, naslov iskren), ravna ograja
  brez stranice, barva lamel sledi cfg, opozorilo majhne slike,
  velika slika brez opozorila, oznaka „netočno“ na meritvi.
- Realni e2e s pravo sliko: kalibracija 0,51 px/mm → meritev
  1106,9 mm (označena), majhna slika → opozorilo + oster prikaz,
  3D L-oblika. Posnetki: `Temp/pi_e2e/*.png`.

## Izven obsega
- 3D iz slike (fotogrametrija / model iz fotografije) — zahteva model
  iz slike; naša pravila „brez AI“ to onemogočajo zanesljivo.
- Perspektivna korekcija merjenja (možna razširitev po ImageMeter).