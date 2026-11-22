# Načrt 13 — Glavno okno = opravilna vrstica + delovni prostor

*Uporabnikova zahteva (slika zaslona): „vse, kar vidim na sliki, mora biti
skrito v opravilni vrstici zgoraj … da bo spodaj delovni prostor.“*

## Pred in po
- PREJ: glavno okno = cela obrazec (PROJEKT, MERE, PRITRDITEV, CENE,
  VRATA, napisi, ŽIVI POVZETEK, PREDGLED) — delovni prostor je bil skrit
  pod obrazcem.
- ZDAJ: glavno okno = **menijska vrstica (Datoteka • Urejanje • Pogled •
  Orodja • Pomoč) + delovni prostor (predogled risbe, čez celo okno)** +
  tanka vrstica stanja (skljkljiva: Pogled → Vrstica stanja).

## Obrazec → pogovorno okno
- cel obrazec (naslov, podnaslov, Predloga, PROJEKT, MERE, PRITRDITEV,
  FOTOGRAFIJA IN IZHOD, CENE, VRATA, ŽIVI POVZETEK) se zgradi v
  **pogovornem oknu „Podatki projekta“**, ki je ob zagonu **skrito**;
- pot: **Urejanje → Podatki projekta… (Ctrl+D)**;
- zapiranje okna (X) ga samo SKRIJE — podatki ostanejo (gradniki
  obstajajo ves čas → vsi obstoječi testi in živi povzetek delujejo);
- okno se odpre prilagojeno vsebini (nikoli odrezano) in centrirano nad
  glavnim oknom.

## Delovni prostor
- `PredogledCanvas` čez celotno glavno okno: risba se prikaže po
  Datoteka → NARIŠI RISBO; kolešček/vleci/dvoklik kot doslej;
- začetno sporočilo usmerja: risba = Datoteka → NARIŠI RISBO, podatki =
  Urejanje → Podatki projekta…;
- vrstica stanja (obvestila „Risba shranjena …“) je ena tanka vrstica na
  dnu in jo je mogoče skriti (Pogled → Vrstica stanja).

## Združljivost
- atributi ostajajo (`app.predogled`, `app.status`, `app.zivi_*`,
  `app.cb_*`, `app._vsebina`) → testi, ki dostopajo po atributih, ostanejo
  zeleni; `test_meni_popolnost` dobi novi vnos v `PRICAKOVANO`;
- nov regresijski test `tests/test_delovni_prostor.py`: glavno okno vsebuje
  samo prostor + vrstico stanja, obrazec je skrit in se odpre/zapre brez
  izgube podatkov.