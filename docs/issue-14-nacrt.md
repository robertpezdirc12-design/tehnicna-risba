# Issue #14 — Napredni razrez: zaloga, omejitve, spodnja meja, primerjava

*Nadgradnja `razrez.py` po zahtevi iz issue #14 (A–G). Osnovno načelo:
obstoječi algoritem in definicije ostanejo nedotaknjene (brez regresij),
nova zmogljivost je dokazljiva in testirana.*

## Fizični model reza (dokaz, točka C iz issue)

Obstoječi model („vsak kos nosi svoj rez“: `V = Σd + n·kerf + ostanek`)
je natanko primer **ločenega ostanka** (n rezov: n−1 med kosi + 1, ki
loči ostanek). Novi motor modelira OBAA primera po kosih:

- **flush** (zadnji kos do roba, brez ostanka): rezi = n−1,
- **ostanek ločen**: rezi = n (n−1 med kosi + 1 za ločitev),
- če je ostanek < `min_ostanek`: se NE shrani — gre v neuporabni odpad
  in zadnji rez ni potreben (rep ostane pri kosu/odpadu).

**Bilanca traku (invarianta, testirana):**
`B = zacetni_odrez + koncni_odrez + Σkosi + rezi·kerf + ostanek + odpad`

Definiciji ostajati dve, izrecno poimenovani:
- `odpad_skupaj` = poraba − Σkosi (ISTA definicija kot `metrika_reza` —
  vključuje kerf, odrez in ostanke; NI nova definicija),
- razčlenitev: kerf | odrez | uporabni ostanek | neuporabni odpad.

## A. Dejanska zaloga (bounded stock)
`ZalogovnaPostavka(dolzina, kolicina=None, material, profil, barva,
serija, vir, oznaka)` — `kolicina=None` = neomejeno (nazaj združljivo);
vsak trak v načrtu nosi svojo zalogovno postavko (sledljivost izvora);
mešanje nezdružljivih lastnosti (material/profil/barva/serija — prazno
= karkoli) je prepovedano; če zaloga ne zadošča → `ValueError` z
izpisom manjkajočih kosov (NIKOLI tihe dodatne palice).

## B. Proizvodne omejitve
`OmejitveReza(kerf, zacetni_odrez, koncni_odrez, min_ostanek,
min_dolzina_kosa, max_dolzina_kosa, toleranca, politika, cene_palice,
cas_reza_mm, cas_menjave)` — politika: „odpad“ | „palice“ | „cena“ |
„cas“ | „ostanki“; parametri so v klicu (profil materiala/stroja),
ne globalne konstante.

## C. Spodnja meja in optimalnost
Za vsak načrt: zahtevano, poraba, kerf/odrez/odpad/ostanki, izkoristek,
spodnja meja, absolutna in relativna vrzel, status:
- „dokazano optimalno“ — izčrpan eksaktni reševalnik (B&B za majhne
  primere, `max_stanj` varovalo),
- „optimalnost ni dokazana“ — samo hevristike + veljavna relaksacija,
- „omejen izračun“ — B&B se je ustavil na meji stanj,
- „neizvedljivo“ — zaloga ne zadošča.

Veljavna spodnja meja (relaksacija, isti model):
`LB = max(f(k*), Σ k* najmanjših primernih palic)` kjer
`f(k) = Σkosi + (N−k)·kerf + k·(zacetni+koncni)` in k* = najmanjše št.
palic s kapaciteto ≥ f(k) — obe komponenti sta matematično veljavni
za vsak izvedljiv načrt (dokaz v testih: noben načrt ne pade pod mejo).

## D. Primerjava načrtov
`primerjaj_nacrte()` generira: „rocno“ (vrstni red — bazna linija),
„ffd“, „bfd“, „najmanj-palic“, „najnizja-cena“ + „ekstaktno“ (če majhno).
Razvrstitev po izbrani politiki; tabela vsebuje KONKRETNO razporeditev
kosov po trakovih (ne le agregatov). Uporabnik izbere načrt — sistem ga
NE zamenja tiho (shranjen v cfg `optimizacija.nacrt`).

## E. Skladišče ostankov
Ostanki = zalogovne postavke `vir="ostanek"` (kolicina 1 — enkratna
poraba, preprečena dvojna uporaba); novonastali ostanki načrta so
označeni „ni vpisan v skladišče — potrdi“ (ločeno od potrjenih).

## F. Testi
`tests/test_razrez_napredno.py`: nezadostno zalogo, omejene količine,
mešane/enake dolžine, kerf+odrezi+flush/ostanek, prag ostanka, združljivost
lastnosti, dvojna poraba ostanka, determinizem, spodnja meja (noben načrt
pod mejo), vrzel, neizvedljivo, **bilanca vsakega traku**.

## G. Vmesnik in dokumentacija
Montažni list: blok „NAČRT RAZREZA“ — izbrani načrt + kriterij, traki s
grafičnim prikazom kosov, ločeno kerf/odrez/ostanki/odpad. GUI: meni
Orodja → „Primerjaj načrte razreza…“ (tabela, izbira, shranitev v cfg).