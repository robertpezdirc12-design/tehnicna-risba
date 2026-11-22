# Primerjava risb: naš delavniški paket proti profesionalni praksi

*Drugi krog raziskave, 2026-11-21. Tokrat ne produkti, ampak SAME RISBE in
njihovo življenje: kaj profesionalci narišejo na list, kaj z risbami počnejo
v procesu, in kako se naš 4-stranski paket primerja točko za točko.*
*Viri spodaj (opsteel.co.uk, procutsteel.com, renderdraw.com, APEGBC smernice,
ISO 2553/128/129-1, cityofmadison.com spec, rdirail.com CAD detajli,
Operon/CUBE/Trueleveler/BcStep — sistemi za upravljanje risb).*

## 1. Anatomija profesionalne delavniške risbe

### Vrste risb v kompletu (opsteel.co.uk, renderdraw.com)
| Vrsta | Namen | Uporabniki |
|---|---|---|
| **General arrangement (GA)** | postavitev, mreže, osi, nivoji, oznake elementov | vodja projekta, inženir, teren |
| **Assembly (piece) drawing** | en kos za pošiljanje: glavni del, plošče, varovi, luknje | sestavljalec, varilec, kontrola |
| **Single-part drawing** | en kos za rezanje/vrtanje | rezanje, CNC |
| **Erection / marking** | kje se kaj montira | monterji na terenu |

### Kaj mora vsebovati telo risbe (procutsteel.com, APEGBC)
1. oznaka profila/materiala + kakovostni razred;
2. **delovne točke in referenčne črte** (mere se merijo iz konsistentnih točk, ne z robov, ki se lahko razlikujejo);
3. luknje: lokacije + mere iz referenčnega konca/flane;
4. **montažni kosi z oznakami (part marks)**, postavljeni na element;
5. usmerjenost — *„da se kos ne more namestiti narobe obrnjen“* (opomba ali simbol);
6. prerezi in detajli pri vezeh, kadar tloris ni dovolj;
7. **kote tako, da delavnici ni treba seštevati verige** (nobenega računanja na mestu);
8. varilni simboli (ISO 2553:2019 — dva sistema označevanja, A/B);
9. tolerance: **splošna toleranca v naslovnem bloku** (npr. „FRACTION ±1/16, XX ±0.01, ANGLE ±1.0°, 125 RMS“ — rdirail CAD list) — kota brez ± je podvržena splošni toleranci;
10. specifikacija zaščite/barve (npr. „galvanized + 3-slojni cink-epoksi, RAL 9005“ — cityofmadison).

### Standardi črt in simbolov
- **ISO 128-2**: široke črte (0,5/0,7) za vidne robove in okvir, ozke (0,25/0,35) za kote, podaljške, šrafure; črtkane za skrite robove (indumor.com).
- **ISO 129-1**: Ø, R, □, SØ, SR, dolžina loka — simboli pred številko.
- **ISO 2553:2019**: varilni simboli (referenčna črta enojna/dvojna).
- **ISO 5457/7200**: format lista + naslovni blok (to že imamo).
- Kaveljček iz prakse (Kings Form Metal): *„ne mešaj ISO in AWS konvencij na isti izdani risbi“*.

## 2. Kaj počnejo z risbami (življenjski cikel)

| Faza | Profesionalna praksa | Vir |
|---|---|---|
| 1. **Potrditev** | shop drawing gre inženirju **pred izdelavo**; javni projekti to izrecno zahtevajo („prior to installation“) | cityofmadison spec |
| 2. **Izdaja (issue)** | transmittal: kdo je dobil katero revizijo; register z statusom/revizijo zgodovine | CUBE, APEGBC |
| 3. **Revizije** | vsaka sprememba = nova revizija; **diff med izdajama** (dodano/odstranjeno/spremenjeno, označeno na obeh listih) — „revision clouds ujamejo nekatere spremembe, spregledajo druge“ | Operon |
| 4. **Delavnica** | assembly + single-part risbe; kosi z oznakami; CNC/NC iz modela; kosovnica za nabavo/nesting | citotech, OD3 |
| 5. **Kontrola (QC)** | kontrolni seznam vezan na risbo; oznake kosov se preverijo proti listu | renderdraw |
| 6. **Teren** | erection risba; terenske korekcije (redline) se vežejo na trenutno revizijo | Trueleveler, Bluebeam |
| 7. **As-built** | končno stanje; **ločeno** se beleži kaj je bila napaka/kontrola in kaj sprememba risbe („quality observation ≠ drawing change“) | BcStep |
| 8. **Arhiv** | vsaka revizija ostane dostopna; markup ostane pri svoji reviziji | Trueleveler |
| 9. **Prodaja** | risba kot prodajni material („customer-ready in a minute“, foto-mockupi) | Ornamental Designer Pro |

## 3. Naš paket — kaj je na listih (dejansko stanje)

| Stran | Vsebina |
|---|---|
| **1. RISBA (A3)** | čelni pogled ograje + vrat, kote (višine, razmaki, odprline), tabela kosov (št/naziv/material/dimenzije/količina), 6 opomb (ISO 2768-m tolerance, WPC spec, RAL 7016, pritrditev, razmak nosilcev, „NI statični izračun“), ISO 7200 naslovni blok (št. risbe, STATUS, rev), mreža lista |
| **2. MONTAŽNI LIST** | potrebščine (tabela materiala), rezalni načrt (traki, kosi, ostanek), primerjava z ročnim rezom, montažni koraki, podpisna vrstica (IZDELAL/STRANKA/DATUM MONTAŽE) |
| **3. PREDRAČUN** | postavke s cenami („cena po dogovoru“ brez izmišljanja), SKUPAJ, opombe |
| **4. NALEPKE** | oznake kosov za izrez/prilepitev (delno = part marks!) |
| **Priloge** | DXF (ISO 13567 plasti), kosovnica CSV, nalepke PNG, G-code + cutlist CSV, ponudba PDF, naročilo TXT |

## 4. Točka za točko: kaj imamo / kaj manjka

> **⚠️ POPRAVEK (22. 11. 2026, načrt 8):** dve oceni v tej tabeli sta bili
> **NAPAČNI** — napisani po spominu, ne po natančnem branju kode.
> `narisi_ogrado`/`narisi_pokoncna` dejansko že rišeta bočni pogled,
> tloris, PREREZ A-A (pokončna v 1:5 s ploščo in ankerji) in DETAJL
> PRITRJEVANJA + DETAJL LAMELE/DESKE. Prvotni oceni sta popravljeni
> spodaj; dejanska vrzel (nerazmerjen detajl brez dimenzij sidranja)
> je bila odpravljena v načrtu 8 (DETAJL 1 — SIDRANJE z globino sidra
> ≈ priporočeno in iskrenim '??' za oddaljenost roba).

| Profesionalni element | Naše stanje | Resnost |
|---|---|---|
| Čelni pogled s kotami | ✅ imamo | — |
| **Bočni pogled / tloris / prerezi** | ✅ POPRAVLJENO: bočni + tloris + PREREZ A-A že obstajajo (prej napačno ocenjeno „samo čelni“) | — |
| **Detajli vez (sidranje, podnožje, var)** | ✅ POPRAVLJENO: DETAJL 1 — SIDRANJE (dimenzioniran, povezan s tabelo) + DETAJL 2; varjenih vezi ni (vijačena izvedba) | — |
| Kote brez seštevanja verige | ✅ kote so neposredne | — |
| Delovne točke / referenčne črte | △ dimenzioniramo z robov | srednja |
| Oznake kosov (part marks) | ✅ nalepke + oznake L/V/D | — |
| Usmerjenost kosov („ne obrni narobe“) | △ nalepke, brez simbola usmerjenosti | srednja |
| Varilni simboli ISO 2553 | ❌ (naše ograje so vijačene — a okviri vrat bi lahko bili varjeni) | nizka/srednja |
| Splošni blok toleranc | △ opomba „ISO 2768-m“, brez bloka (± kot/± mm) | srednja |
| Specifikacija zaščite/barve | ✅ RAL 7016, WPC spec, „preveri z vzorcem“ | — |
| ISO 128 debeline črt | △ risba matplotlib, enotne črte | nizka |
| **Revizijska tabela / oblaki sprememb** | ❌ le STATUS polje | **visoka** |
| Potrditev (approval) stranke/inženirja | △ podpisna vrstica na montažnem listu | srednja |
| Register/transmittal izdaj | ❌ | srednja |
| Kontrolni seznam (QC) | ❌ | srednja |
| As-built beleženje | ❌ | nizka (naš obseg) |
| Kosi „per shipping piece“ | △ nalepke, brez sestavnih risb kosov | srednja |
| Montažni koraki | ✅ imamo (redko pri konkurenci!) | — |
| Podpisna vrstica IZDELAL/STRANKA | ✅ imamo | — |
| Poštena opozorila (NI statični izračun) | ✅ — pri konkurenci nič takega | — |

**Povzetek (popravljen 22. 11. 2026):** naš paket je funkcionalno blizu
*malega obrtniškega kompleta* (pogledi + prerezi + detajli + montažni list
+ kosi + nalepke + pogodbeni podpisi), kar je več, kot je zapisala prva
(napačna) ocena. Preostale vrzeli so: **revizije (odpravljeno, načrt 7)**,
**blok toleranc, QC seznam, tok ZA POTRDITEV → IZVEDENO**.

## 5. Ograjno-specifične zahteve (konkretni vzorci)

Iz javnega speca (City of Madison, ograja) in proizvajalskih CAD listov
(rdirail, Avalon/Finyl):
1. **Shop drawings za potrditev inženirju PRED montažo** — izrecna zahteva;
2. **Detajli podnožja**: base plate debelina (5/16"), sidra (wedge anchors),
   oddaljenost roba sidra od roba betona;
3. **Blok toleranc** na listu (±1/16, ±0.01, ±1.0°, RMS);
4. **Zaščita**: cinkanje + 3-slojni sistem barve, barva po RAL;
5. Postavitvena pravila („na naklonu ostanejo stebri pokonci, letve sledijo terenu“);
6. Tabele dolžin stebrov (A/B/C dimenzije).

## 6. Kaj počnejo z risbami — naše stanje po točkah

1. **Potrditev pred izdelavo** → delno (podpisna vrstica + ponudba); ni ločenega lista „ZA POTRDITEV“ (imamo STATUS polje!). **Nadgradnja: STATUS = ZA POTRDITEV → po potrditvi IZVEDENO.**
2. **Izdaja/transmittal** → ni ga.
3. **Revizije + diff** → ni (največja vrzel; primerjaj „en model — ena revizija“).
4. **Delavnica** → ✅ rezalni načrt + kosovnica + CNC/CSV + nalepke.
5. **QC** → ni kontrolnega seznama (lahko: stran 2 „montažni koraki“ + checkbox stolpec).
6. **Teren** → ✅ terenski list (unikat!), a brez povezave z revizijami.
7. **As-built** → ni.
8. **Arhiv** → ✅ YAML projekta (odpri/shrani) — zgodovina revizij ni.
9. **Prodaja** → ✅ ponudba 3 variant + foto predogled + avtomatska skica.

## 7. Prednostne izboljšave (vrstni red — ponudba)

| # | Izboljšava | Zakaj (iz primerjave) | Velikost |
|---|---|---|---|
| 1 | **Revizijska tabela + št. revizije + diff povzetek** („kaj se je spremenilo“) | Operon: „revision clouds spregledajo spremembe“ | srednja |
| 2 | **Bočni pogled + prerez sidranja** (detajl A: podnožje/sidra) | pro shop drawings: „show base plates and connection on shop drawings“ | srednja |
| 3 | **Blok toleranc** (± mm / ±° / splošno) na list | rdirail listi; kota brez ± ni določena | majhna |
| 4 | **QC seznam** (montažni koraki + potrditvena polja) | praksa kontrole | majhna |
| 5 | **„ZA POTRDITEV / IZVEDENO“ tok** (status že imamo → promocija v proces) | city spec: potrditev pred montažo | majhna |
| 6 | Simbol usmerjenosti kosov + delovne točke | „kos se ne more namestiti narobe“ | srednja |
| 7 | Varilni simboli ISO 2553 (če bodo varjeni okviri) | ISO 2553:2019 | srednja |

**Izvedeno (22. 11. 2026):** #1 → načrt 7 (revizije + diff);
#2 → načrt 8 (DETAJL 1 — SIDRANJE; bočni pogled/prerezi so že obstajali,
vrzel je bil le nerazmerjen detajl brez dimenzij).

## 8. Viri (2026-11-21)

- opsteel.co.uk/guides/steel-fabrication-drawings — vrste risb (GA/assembly/single-part/erection)
- procutsteel.com/blog/what-to-include-in-steel-shop-drawing — telo risbe (delovne točke, usmerjenost, „brez seštevanja verige“)
- renderdraw.com/guides/steel/steel-shop-drawings — kdo kaj uporablja; QC
- APEGBC Guidelines on Shop Drawings — 11 obveznih elementov (revizije, identifikacija materialov, terenske mere)
- iso.org/standard/72740.html — ISO 2553:2019 varilni simboli (sistema A/B)
- indumor.com — ISO 128-2 črte (0,5/0,25 skupini), ISO 129-1 simboli (Ø R □ SØ)
- kingsformmetal.com KFR-011 — „ne mešaj ISO in AWS na isti izdani risbi“
- cityofmadison.com StdSpecs 5-5-3 — ograja: shop drawings za potrditev PRED montažo, zaščita, sidranje
- rdirail.com CAD (Avalon/Finyl) — base plate 5/16", wedge anchors, blok toleranc (±1/16, ±0.01, ±1.0°, 125 RMS), tabele dolžin
- operonsolutions.com — revizijski diff med izdajama (clouds so nezanesljivi)
- cube.ms / trueleveler.com / bcstep.com / bluebeam.com — register, transmittal, markup ob reviziji, as-built („quality observation ≠ drawing change“)
- ornamentaldesignerpro.com — risba kot prodajni material