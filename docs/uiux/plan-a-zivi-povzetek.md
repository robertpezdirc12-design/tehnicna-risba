# Plan A — Živi predogled + živa kosovnica/cena

## Vir (raziskava UI/UX)
- Paper2Quote: „live cost preview v inspector pane“
- Visual Fence Pro: „gledaš, kako cena narašča — skupaj se posodablja v živo“

## Cilj
Med vnosom v glavnem vmesniku uporabnik TAKOJ vidi:
1. **shematski živi predogled** ograje (deske, stebri, odprtine, ključne mere),
2. **živo kosovnico** (WPC m, alu m, nosilci, vijaki, vrata),
3. **živo ceno** (SKUPAJ brez DDV + opozorila o manjkajočih cenah).

## Arhitekturna odločitev (issue #6 — en vir resnice)
Živi povzetek NE SME imeti lastnih vzporednih formul. Zato:

1. `proizvodnja.izracunaj_kolicine(c)` — ČISTI izračun količin
   (postavke, narocilo, kosovnica, ostanki_posodobitev) BREZ risanja.
   Formule so izločene iz `risba.py` (obe veji: `ograja` + `pokončna`)
   BREZ spremembe; `risba.narisi_montazni_list` / `narisi_montazni_pokoncna`
   zdaj za povratne podatke kličeta to funkcijo.
2. `proizvodnja.predracun_znesek(cene, postavke)` — čisti seštevek cene
   (isti algoritem kot `risba.narisi_predracun`; ta ga zdaj uporablja).
3. `vmesnik.py` — panel »ŽIVI POVZETEK« (shematsko platno + vrstice),
   osveževanje z debounce (600 ms) ob vsaki spremembi polja,
   preklopno (živo/ročno) + gumb »Osveži«.

## Spremembe po datotekah
- `proizvodnja.py`: +`izracunaj_kolicine`, +`predracun_znesek`
- `risba.py`: klica novi funkciji (povratni količini), brez spremembe izpisov
- `vmesnik.py`: +`ZiviPovzetek` (platno + vrstice), debounce, sledenje spremembam
- `tests/test_zivi_povzetek.py`: nova

## Testi / verifikacija
1. `izracunaj_kolicine(cfg)` == `kolicine` iz `risba.generiraj(cfg)`
   (obe predlogi) — dokaz, da izločitev ni spremenila številk.
2. `predracun_znesek` — ročno preverjen seštevek + manjkajoče cene.
3. GUI: po spremembi polja se povzetek osveži (napisi se spremenijo);
   neveljavni vnos ne povzroči sesutja, ampak status napake.
4. Celotni testi: snapshot + vsi ostali zeleni.

## Zunaj obsega (iskreno)
- Prikaz ni CAD-predogled risbe (ta ostane gumb NARIŠI RISBO);
  živi prikaz je shematski in informativen.
- Cena je orientacijska (kot veljavni predračun), brez DDV.