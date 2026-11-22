# Načrt 11 — Statusni tok: V DELU → ZA POTRDITEV → IZVEDENO

*Izboljšava 5 s prednostne lestvice: „status že imamo → promocija v proces“.
Javni speci (cityofmadison): shop risbo odgovorna oseba POTRDI PRED
izdelavo/montažo; as-built stanje se loči od kvalitetnih opazk (BcStep:
„quality observation ≠ drawing change“).*

## Stanje (po natančnem pregledu)
- `jedro.DOVOLJENI_STATUSI = ("V DELU", "ZA POTRDITEV", "IZVEDENO")` +
  validacija v `preveri_cfg` že obstajata; naslovni blok kaže STATUS
  (stran 1, obe predlogi).
- **Manjka:** vmesnik statusa SPLOH NIMA (ni polja, `status_dokumenta`
  ni v `_zberi_cfg`); ni varovala za IZVEDENO (komentar v jedro pravi
  „IZVEDENO se sme uporabiti šele po terenski potrditvi“); ni statusnega
  žiga na listu; montažni list statusa ne kaže.

## Rešitev
1. **Polje STATUS** (combobox: V DELU / ZA POTRDITEV / IZVEDENO) v
   PROJEKT vrstici 3 — vrednosti iz `jedro.DOVOLJENI_STATUSI` (en vir);
   tok v `_zberi_cfg` / `_nalozi_cfg_v_polja`.
2. **Varovalo za IZVEDENO** — ob izbiri se zahteva izrecna potrditev:
   „Status IZVEDENO pomeni, da je delo izvedeno in terensko preverjeno.
   To je izjava odgovorne osebe — program tega ne more preveriti.“
   Brez potrditve se status povrne. (Nazaj prehodi so svobodni —
   popravki/revizije se vračajo v V DELU.)
3. **Statusni žig čez list** (profesionalni „FOR APPROVAL / NOT FOR
   CONSTRUCTION“ žigi):
   - V DELU → „V DELU — OSNUTEK“ (siv, prosojen),
   - ZA POTRDITEV → „ZA POTRDITEV — NI ZA IZDELAVO“ (rdeč, prosojen),
   - IZVEDENO → brez žiga (čista končna risba; STATUS je v naslovnem bloku).
   Žig je prosojen (alpha 0.12) in ne moti branja risbe; izriše se na
   straneh z naslovnim blokom + na montažnem listu (`status_vodni_zig`).
4. **Montažni list**: vrstica „STATUS: … • REV. …“ v glavi — status je
   viden tudi v delavnici/na terenu (isti vir kot naslovni blok).

## Poštenost
- program NE MORE preveriti dejanske izvedbe — zato je IZVEDENO izrecna
  IZJAVA uporabnika (potrditveni dialog), nikoli samodejno;
- „Risba NI statični izračun“ ostaja; status ni izračun, ampak procesno
  stanje dokumenta.

## Preverjanje
- testi: combobox + tok v cfg, varovalo IZVEDENO (da/ne), žigi v PDF
  (osnutek/potrditev prisotna, izvedba brez žiga), STATUS na montažnem
  listu, povrnitev statusa ob nalaganju projekta;
- realni GUI: izbira statusa + dialog + posnetek žiga na listu.