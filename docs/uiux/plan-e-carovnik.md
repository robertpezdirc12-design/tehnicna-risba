# Plan E — Čarovnik po korakih (voden vnos)

## Vir (raziskava UI/UX)
- Metrologist: 3 jasni koraki (slika → označi → preberi)
- PhotoMeter: navodila korak za korakom

## Problem
Glavni obrazec ima 20+ polj naenkrat; nov uporabnik ne ve, kje začeti.
„Preprosti način“ zmanjša nered, a ne vodi.

## Cilj
Gumb **ČAROVNIK** odpre voden vnos po 5 korakih:
1. Vrsta in ime (predloga, ime projekta)
2. Mere ograje (širina, višina, globina, odcep)
3. Lamele/deske (št., višina/širina, debelina, vrzel)
4. Vrata/prehodi (neobvezno — isti dialogi kot v obrazcu)
5. Pregled in zaključek

Koraki imajo napredek (Korak n/5 + progressbar), gumba Nazaj/Naprej,
validacijo pred naprej (neveljavno polje ostane na koraku z jasnim
sporočilom).

## Arhitekturna odločitev
Čarovnik NE KOPIRA stanja — ureja ISTE `StringVar`-je kot glavni obrazec.
Zato delujejo živi povzetek (Plan A) in undo/redo (Plan D) samodejno.

## Spremembe
- `vmesnik.py`: razred `Carovnik(tk.Toplevel)` + gumb ČAROVNIK v vrstici.

## Testi / verifikacija
1. Koraki: naprej/nazaj, mejniki (1. in zadnji korak).
2. Sprememba v čarovniku piše v `app.v` (isti vir).
3. Validacija: neveljavna širina blokira naprej z obvestilom.
4. Zaključek zapre okno; stanje ostane v obrazcu.

## Zunaj obsega (iskreno)
- Voden vnos za cene/vijake (napredne postavke) — ostanejo v obrazcu.
- Animacije/prehodi med koraki.