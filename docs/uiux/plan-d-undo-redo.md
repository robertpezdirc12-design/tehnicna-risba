# Plan D — Undo/Redo (Ctrl+Z/Y) za polja in vrata

## Vir (raziskava UI/UX)
- QtoTakeoff/TakeOn/Plankore: Ctrl+Z/Y, „undo se obnaša kot pravi urejevalnik“
- Paper2Quote: ledger undo — povrnitev projekta na katero koli točko

## Problem
V `vmesnik.py` ni razveljavitve: pomotoma spremenjeno polje ali izbrisana
vrata so trajno izgubljena.

## Cilj
- Zgodovina stanj (polja, vrata, kljukici) z mejo 50 korakov,
- Ctrl+Z = razveljavi, Ctrl+Y / Ctrl+Shift+Z = ponovi,
- gumba „Razveljavi/Ponovi“ v orodni vrstici (omogočena glede na položaj),
- zgodovina se zapisuje ZAMAKNJENO (700 ms) — en vnos na vnosni cikel,
  ne na vsako tipko.

## Spremembe
- `vmesnik.py`: `_zgodovina_stanje/_zgodovina_zabelezi/_zgodovina_obnovi`,
  `_razveljavi/_ponovi`, zastavica `_obnavljam` (obnova ne sproža nove
  zgodovine), gumba + bližnjici.

## Testi / verifikacija
1. Sprememba polja → undo vrne staro vrednost → redo spet novo.
2. Vrata: dodaj → undo odstrani → redo povrne (vključno s podatki).
3. Obnova ne ustvarja novih vnosov zgodovine.
4. Konec začetka zgodovine: undo na prvem vnosu ne naredi nič (brez napake).

## Zunaj obsega (iskreno)
- Undo posameznih znakov znotraj polja (to ureja že Tk vnosno polje).
- Trajna zgodovina prek sej (ledger) — tu je zgodovina v pomnilniku.