# Plan F — Bližnjice (Ctrl+…) + namigi (tooltips)

## Vir (raziskava UI/UX)
- QtoTakeoff/Plankore/TakeOn: standardne bližnjice (Ctrl+Z/Y/S/P…)
- magicplan: kontekstualna pomoč pri elementih

## Cilj
1. **Bližnjice**: Ctrl+N = NARIŠI RISBO, Ctrl+P = ODPRI PDF,
   Ctrl+S = SHRANI PROJEKT, Ctrl+E = IZVOZI DXF, F1 = pomoč z
   seznamom bližnjic (Ctrl+Z/Y sta že od Plan D).
2. **Namigi** ob prehodu miške na ključna polja (širina, kerf, razmak …)
   — kratka razlaga kaj pomeni in kako se izračuna.

## Spremembe
- `vmesnik.py`: razred `Namig` (hover tooltip), slovar `NAMIGI`,
  priklop v `_polje`, bližnjice + `_pomoc()` (F1).

## Testi / verifikacija
1. `Namig`: `_prikazi` ustvari okno z besedilom, `_konec` ga zapre.
2. Bližnjice so vezane (`bind_all` vrne ukaz) in `_pomoc` deluje.
3. `NAMIGI` pokriva ključna polja; namigi so pripeti na vnosna polja.

## Zunaj obsega (iskreno)
- Kontekstualni namigi ob vnosni napaki (imamo že inline validacijo vrat).
- Prilagodljive bližnjice (nastavitve).