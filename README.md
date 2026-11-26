# Generator tehničnih risb — balkonska ograja (WPC lamelle)

[SL] Profesionalni generator tehničnih risb (PDF A3, ISO 5457/7200) in montažnih
listov za balkonske in dvoriščne ograje iz WPC lamel (npr. WoodCore deske ROMB 67,
POLNA DESKA …). Namenjen montažerjem ograj: vpišeš mere s terena, dodaš fotografijo
in dobiš risbo za tisk + montažni list z rezalnim načrtom.

[EN] A lightweight Python tool that generates professional A3 technical drawings
(ISO 5457 frame, ISO 7200 title block) plus a 2-page production document
(installation sheet with cut plan, kerf-aware offcuts, checklist) for WPC
lamella railings — from user-entered dimensions, with an optional photo
measurement assistant.

![primer risbe](slike/BO-001-risba.png)

### Faze razvoja (issue #5) — izvedeno

| Faza | Vsebina | Stanje |
|---|---|---|
| F1 | P0 popravki pravilnosti (cene/predračun, DXF dolžina, reže, vrata ↔ kosovnica, montažne letve) | ✅ |
| F2 | Arhitektura: `jedro.py` + `proizvodnja.py` + `risba.py`, snapshoti, CI | ✅ |
| F3 | Varnost/UX: XSS, rate limit, UA, prag zanesljivosti merjenja | ✅ |
| F4 | Pilot novih vrst: `nova_vrsta.py` (deklarativna polja, predogled) | ✅ |
| F5 | CNC izvoz: `cnc.py` (CSV + informativni G-code) | ✅ |

Odpri še iz načrta (P4): dodatni tipi vrat. Statični izračun — odločitev
sprejeta: poenostavljen pregled (načrt 6) + statična priloga (načrt 16);
celovita statična potrditev ostaja pri pooblaščenem inženirju.

## Funkcije

- **Tehnična risba A3** — sprednji/stranski pogled, tloris z rezom A–A, prerez,
  detajl pritrjevanja, detajl lamele, izometrični pogled ali fotografija objekta
- **ISO list** — conatna mreža (ISO 5457), glava (ISO 7200), tabela revizij,
  simbol projekcije (prvi kot)
- **Montažni list (stran 2 PDF-a)** — potrebščine, rezalni načrt z ostanki
  (kerf-pozavesten), vizualni rez z izkoristkom, izračun višine, montažni
  koraki s sklici na detajle, kontrola terena, podpis stranke
- **Terenski list (modul `terenski_list`)** — popolnoma prazen A4/A3 list za
  prostoročno skico in ročno sestavljanje elementov (črte, puščice, oblike,
  besedilo, ročne mere z oznako »(ročno)«, izometrične kocke/kvadri),
  shranjevanje v YAML, PDF/predogled in tisk — `python terenski_list.py --gui`
  oziroma `python vmesnik.py --terenski`; brez povezave s proizvodnimi
  izračuni (ročne mere so anotacije, ne potrjene mere)
- **Predračun (priloga PDF-a, neobvezno)** — če v konfiguracijo vpišeš `cene:`
  (EUR/m, EUR/kos, delo), se samodejno ustvari orientacijski predračun;
  če so vse cene 0.00 (PRIMER), je jasno označen kot informativen in
  brez zavajajočih zneskov
- **Kosovnica + nalepke (priloga PDF-a)** — CSV `<nalog>-kosovnica.csv`
  (vsak kos: dolžina, vir — ostanek ali nabava) in nalepke za kose
  (izreži, označi, prilepi); sta prilogi in ne štejeta kot risalna lista
- **Naročilnik** — datoteka `<nalog>-narocilo.txt` s pripravljenim naročilom
  materiala (deske po modelu/barvi/dolžini, profili, pritrdila) za
  copy-paste v e-pošto dobavitelju
- **Razrez čez več tovarniških dolžin** — vpišeš npr. `5800; 4000; 2200` in
  optimizator izbere trakove z najmanj odpada (kerf-pozavestno); nabavne
  deske so štete po dolžinah v potrebščinah, naročilu in predračunu
- **Konfigurabilna pritrdila** — vijak lamela↔profil in vijak
  nosilec/osnova↔podlaga sta prosto besedilo; sledijo jim potrebščine,
  naročilo, detajli, montažni koraki in material (Inox/Pocinkano) iz naziva;
  dobavitelj v naročilu je nastavljiv (privzeto WoodCore)
- **Skladišče ostankov** — naslednji nalog lahko (izrecno vklopljeno)
  najprej porabi ostanke (po barvi in profilu, najdaljši prvi); privzeto je
  uporaba IZKLOPLJENA. Generiranje nikoli samodejno ne spreminja skladišča —
  odpis potrdiš sam (CLI: `--potrosi-ostanke`, GUI: gumb „ODPIŠI OSTANKE”),
  z varnostno kopijo in atomičnim zapisom. Datoteka `ostanki.yaml` je v
  uporabniški podatkovni mapi (`%APPDATA%\TehnicnaRisba`, Linux
  `~/.local/share/TehnicnaRisba`), ki jo lahko prekrižeš z okoljsko
  spremenljivko `TEHNICNA_RISBA_DATA`
- **Kontrola pravilnosti** — pred izvozom program preveri mere in geometrijo;
  pri napaki NE nastane nepopoln PDF
- **Konstrukcijska varnost** — risba izrecno NI statični izračun; nosilnost,
  sidranje in veterno breme preveri usposobljen strokovnjak (na listu)
- **Statična priloga (PDF, `statika.py`)** — revizijsko sledljiv izračunski
  list za pooblaščenega inženirja: vhodni podatki, povpraševanje (demand)
  po kategorijah obtežb z viri, formule, kontrolni seznam odprtega
  (zmogljivost, γ, sidranje veter EN 1991-1-4, SI NA) in podpisni blok;
  `python statika.py --priloga projekt.yaml` ali meni Orodja; informativno —
  NI statični izračun
- **Samodejni izračuni** — lega in količina nosilcev (razmak), št. vijakov,
  št. tovarniških desk/palic iz mer
- **Grafični vmesnik (Tkinter)** — preprosti/napredni način, samodejno
  shranjevanje nastavitev, celozaslonski predogled z povečavo
- **Merjenje s fotografije** (pomožno) — kalibracija na znano dimenzijo
  (npr. 67 mm = širina deske), klik-merjenje, zaznavanje pasov in pik (OpenCV);
  ritem lamel merita DVA neodvisna estimatorja (profil + robovi `scikit-image`)
  — ob nesoglasju so mere eksplicitno OCENJENO in zahtevajo potrditev.
  V glavnem GUI je tudi **Predlog mer iz fotografije** (Vstavi/Orodja): mere
  se ponudijo za vnos v polja s potrditvijo — sistem ničesar ne zapolni sam,
  z izbirno referenčno višino so mere IZMERJENO/IZRAČUNANO namesto OCENJENO.
- **CLI + konfiguracija YAML** — za ponavljajoče naloge
- **Vrata in prehodi (issue #3)** — enokrilna/dvokrilna/pasja/prehodna vrata
  ter prehodi v obeh predlogah ograje; odprtine vplivajo na polnilo, razrez,
  količine in kosovnico (ne le na risbo); tečaji/vijaki/prečke/diagonale po
  dokumentiranih konstrukcijskih pravilih (docs/issue-3-vrata-dxf.md)
- **Večsegmentni projekti (YAML shema v2)** — segmenti z lastnimi merami,
  vrati/prehodi in koti (vogali); migracija starih projektov v1→v2 brez
  izgube (`migracija.py`)
- **DXF izvoz za CAD/CNC** — `python risba.py projekt.yaml --dxf` ali gumb
  v GUI: DXF R2010, mm 1:1, 9 plasti (rez/vrtanje iz OUTLINE/POSTS/HOLES),
  zaprte konture brez dvojnih rezov, kote, naslovni blok; omejitve (brez
  G-code/kompenzacije orodja) v `docs/dxf-specifikacija.md`
- **Mehansko katalogsko jedro (F0/F1, `mechanical/`)** — katalog standardnih
  delov s provenanco (ISO 4032/4017, DIN 934/933; profila `iso`/`legacy_din`
  strogo ločena), resolver brez ugibanja, izpeljan BOM in kontrola dokumenta
  (popolnost/reference/standardi/enote + gating: incomplete → detajl blokiran);
  `python -m mechanical.kontrola mechanical/examples/vijacnik.yaml`
  Kupljeni deli vrat (vijak M8x40, matica M8, podložka M8) nosijo kataloške
  reference (ISO 4017/4032/7089) — `vrata.kataloski_viri()` vrne mere in vire;
  naročilo lahko doda dokazila prek `vijak_lamela_ref`/`vijak_nosilec_ref`
  (blok »PRITRDILA — katalog«); brez referenc so izpisi nespremenjeni.

![montažni list](slike/TEREN-01-montazni-list.png)

## Montaža WPC profilov (navodila proizvajalca)

Program pozna navodila za montažo treh profilov (`jedro.MONTAZE_PROFILAV`
— en vir resnice) in jih upošteva v validaciji, risbi, montažnem listu in
naročilu.

### ROMB DESKA-67 (širina 6,7 cm, dolžina 5,8 m)

Profil romb se reže na poljubne dolžine:

- **Alu cev v sredini romba je POGOJ montaže** — nevidno pritrjevanje gre
  skozi to cev. Romba brez alu cevi NI mogoče montirati, zato nakup
  desk brez alu cevi ni mogoč.
- **L-kotnik LEVO in DESNO na vsakem stebričku**; rf vijak gre skozi
  L-kotnik v alu cev sredine romba z **zadnje strani** — vijak ni viden
  s sprednje strani.
- **Vrtanje** (za vijak 3,9): izvrtina 3,2 skozi romb in aluminij, nato
  se luknja v rombu poveča na 4,2–4,5 — v kompozit je luknja vedno
  večja od vijaka zaradi raztezanja materiala.
- **Razmiki stebričkov**: največ **145 cm** (z L-kotnikoma levo in
  desno). Nad 145 cm je potrebna **vmesna povezava iz zgornje cevi** (NI
  privijačena v tla) — dovoljena do **180 cm** in se vklopi z
  `vmesna_povezava: true` v konfiguraciji. Pri razmaku **≥ 180 cm** je
  potreben dodatni stebriček.
- **Zaključek ograje** — dve izvedbi: s **čepi** (zaprtje odprtih koncev
  romb desk in stebričkov) ali z **zaključno letvico**, ki se privije
  **iz strani v romb profile** (1 vidni vijak na lamelo) in skrije
  odprte konce desk. Izbira v konfiguraciji: `zaklucek: cepi` ali
  `zaklucek: letvica`; brez izbire dokumenti ponudijo obe izvedbi.

### DESKA-150 (terasna deska, širina 15 cm, dolžini 4 m in 2,2 m)

- deska se odžaga na poljubno dolžino;
- **pritrditev od spredaj** — vijaki gredo skozi desko v konstrukcijo, na
  licu so **vidni** (del zasnove);
- **predvrtje**: luknja mora biti **1 mm večja** od dimenzije vijaka;
- vijak se privije **v sredino deske, kjer je rebro v profilu**;
- stebrički za vodoravno postavitev desk: največ **133–140 cm**.

### DESKA-128 (polna deska, širina 12,8 cm, dolžina 2,2 m)

- enako kot DESKA-150: odžaga po meri, pritrditev **od spredaj z vidnimi
  vijaki**, predvrtje — **luknja 1 mm večja** od vijaka, vijak **v sredino
  deske**;
- stebrički za vodoravno postavitev desk: največ **180 cm** pri ograjah do
  150 cm višine, pri višjih največ **150 cm** (enako za POLNA DESKA 100).

### POLNA DESKA 57/32 (pokončna in vodoravna)

- montaža na širino **57 ali 32 mm**; pritrditev z RF vijaki skozi cev
  **iz zadnje strani** — vijaki niso vidni (skrito vijačenje);
- vijak je dolg **približno 2/3 globine profila**;
- **obrnjeno vrtanje**: v kompozit se vrta luknja **manjša** od vijaka, v
  konstrukcijo **večja** (raztezanje materiala);
- stebrički: največ **150 cm ne glede na višino ograje**; nosilci
  (vodoravne cevi) največ **100 cm**.

### Pokončna ograja (4 profili)

Za pokončne ograje veljajo profili **POLNA DESKA 57/32**, **POLNA DESKA
100**, **POLNA DESKA 128** in **ROMB DESKA 67**; merilo je **razmak med
vodoravnima cevema** (montažnima letvama za deskami):

| profil | razmak ≤ | posebnosti |
|---|---|---|
| POLNA DESKA 57/32 | 100 cm | montaža na širino **57 ali 32 mm**, skrito vijačenje; vrtanje obratno (kompozit manjša luknja, konstrukcija večja) |
| POLNA DESKA 100 | 80 cm | — |
| POLNA DESKA 128 | 100 cm | — |
| ROMB DESKA 67 | 110 cm | na vodoravne cevi zmontiraj **kotnik**, skozi katerega se pritrjuje romb — skrito vijačenje |

Program izračuna število vodoravnih cevi na polje (`jedro.st_vodoravnih_cevi`)
tako, da so vse nepodprte razdalje (tudi robovi desk) ≤ ta razmak; doslejšnji
„2 na polje“ ostane minimum.

## Pritrditev desk (odmiki vijaka od roba reza)

- minimalen odmik vijaka od roba reza: **30 mm**;
- konstrukcija montirana **na ploščo** (balkon, dvoriščna ograja): največ
  **150 mm**;
- konstrukcija montirana **bočno na ploščo** (balkon): največ **100 mm**.

Program vključi pravilo v naročilo in opombe glede na nastavitev
`pritrditev` (`vrh` = na ploščo, `bočno` = bočno na ploščo). Kosi, krajši
od 60 mm, dobijo opozorilo (2 vijaka ne prideta v kos). Priporočen razmak
med deskami je 5–30 mm; možno je tudi prekrivanje desk (montaža iz obeh
strani); deske se obdelujejo kot les (zaokrožitev, poljubne oblike).

## Elementi (dimenzije izdelkov)

| element | dimenzija | uporaba / opomba |
|---|---|---|
| POLNA DESKA 57/32 | 57×32×5800 mm | naleganje na 57 ali 32; **samo za pokončno ograjo**; 4 barve |
| POLNA DESKA 100 | 100×12×5800 mm | **samo za pokončno ograjo**; 8 barv |
| POLNA DESKA 128 | 128×16,5×2200 mm | polna deska (brez prekatov); pokončno **ali prečno**; 6 barv |
| DESKA-150 | 150×25×4000 / 2200 mm | terasni profil (votel); vidni vijaki na rebro; 7 barv, 3 površine (Klasik, Rustik …); zaključni pokrovček |
| KUBO 80/42 | 80×42×5800 / 5000 mm | pokončne pregrade; skrito vijačenje; montaža na širino 80 ali 42 mm; alu cev 20×60×2 / 25×25×2 / 20×20×2 — za zunaj ELOKSIRANA; 4 barve |
| ROMB DESKA 67 | 67×26×5800 mm | z ALU CEVJO v sredini; pokončno ali prečno; 7 barv |
| Ročaj (standardni) | 95×45×5800 mm | na zalogi samo še v WHITE odtenku; ostali odtenki v polnem profilu |
| Ročaj (poln profil, WPC) | 92×45×5800 mm | notranja dimenzija 55×30 mm |

**Samostojna prodaja ročajev ni možna** — ročaj gre vedno skupaj z ograjo.
Program validira uporabo profila (POLNA DESKA 100/57/32 zavrne prečno
predlogo) in v naročilo vključi dimenzije elementov.

**Barvni odtenki** (imena z barvne lestvice WoodCore; `jedro.BARVE_ALIAS`
prepozna tudi domača imena, npr. „Antracit“ → „Amazon wood“;
preverjanje konfiguracije zavrne odtenek, ki ni na voljo za izbrani
profil):

| Profil | Odtenki |
|---|---|
| ROMB DESKA 67, DESKA-150 | Amazon wood, Ash wood, Golden teak, Burma teak, Oak wood + Rustik: Rustic oak, Rustic walnut (7) |
| POLNA DESKA 100 | kot zgoraj + White (8) |
| POLNA DESKA 128 | Amazon wood, Ash wood, Burma teak, Oak wood + Rustik (6) — brez Golden teak/White |
| POLNA DESKA 57/32, KUBO 80/42 | Amazon wood, Oak wood + Rustik (4) |

Rustic odtenka sta večbarvna — odtenek in razpored lis med deskami in
serijami opazneje variirata; pri vseh odtenkih barvni odtenek med
dobavami malenkost varira in se lahko razlikuje od vzorca. **Barva prvo
leto posvetli za 5–10 %**, nato ostane enaka.

**Čepi za romb**: čepi so **levi in desni** — za vsak konec lamele je
potreben par (levi + desni čep). Opcija za zaključevanje **prečne** romb
ograje je tudi zaključna letvica (pri pokončni predlogi veljajo čepi).

**Skladiščenje**: deske je pred montažo potrebno hraniti v suhem in
zračnem prostoru; podlaga naj bo ravna in čista, deske na odlagalni
podlagi po celotni dolžini in širini, podprte na največ 50 cm.
Začasno skladiščenje zunaj mora biti obvezno pokrito (tveganje
zastajanja vlage in plesni). V primeru neustreznega skladiščenja se
reklamacija ne upošteva.

### Splošna WoodCore navodila (PDF + O materialu + FAQ — `jedro.WOODCORE`)

- **Material**: 60 % bambusovih vlaken, 30 % polietilena (HDPE),
  10 % aditivov. Garancija 15 let: ne cepijo, ne razpadajo, ne gnijejo;
  izjeme: težke obremenitve in udarci niso kriti, posvetlitev 5–10 % in
  barvne variacije niso krite; neupoštevanje navodil montaže izniči
  garancijo.
- **Temperatura montaže**: montaža pri zunanji temperaturi pod **5 °C
  ni primerna** (program pri `montazna_temp_c` < 5 doda opozorilo).

- **Orodja**: baterijski vrtalnik (ročni izvijač ne pride v poštev —
  WPC je pretrd), rezila Widia (HM), brusni papir granulacija 40 za
  praske in poškodovane robove; glavo vijaka ugreznite z grezilom.
- **Vijaki**: priporočeni so nerjaveči; dovoljeni tudi standardni RF
  vijaki, odporni na rjo in korozijo.
- **Nosilnost**: WoodCore desk se ne sme uporabljati za nosilce, tramove,
  podporne stebre ali druge gradbene elemente — neupoštevanje lahko
  izniči garancijo.
- **Drenažne luknje** (voti profili — romb, DESKA-150): fi 4,2 mm s
  spodnje strani, cca 5 cm od roba, v vsak prekat — voda ne sme
  zastajati (zmrzne in desko poči). Polne deske (57/32, 100, 128) jih
  ne potrebujejo.
- **Odmik od sten**: najmanj 6 mm; raztezek deske 12 mm na 4 m
  (−30…+40 °C; PDF navaja „cca 10 mm“).
- **Razmak med deskami po temperaturi montaže** (`jedro.razmak_desk_mm`;
  izbirno polje `montazna_temp_c` ga izpiše v naročilu):

| temp. °C | 1 m | 2 m | 3 m | 4 m | 5 m |
|---|---|---|---|---|---|
| −25 | 2,75 | 5,5 | 8,25 | 11 | 11 |
| −20 / −15 | 2,5 | 5 | 7,5 | 10 | 10 |
| −10 | 2,25 | 4,5 | 6,75 | 9 | 9 |
| −5 | 2 | 4 | 6 | 8 | 8 |
| 0 / 5 | 1,75 | 3,5 | 5,25 | 7 | 7 |
| 10 | 1,5 | 3 | 4,5 | 6 | 6 |
| 15 / 20 | 1,25 | 2,5 | 3,75 | 5 | 5 |
| 25 | 1 | 2 | 3 | 4 | 4 |
| 30 | 1 | 1,5 | 2,25 | 3 | 3 |
| 35 | 1 | 1,5 | 1,8 | 2 | 2 |

  Vir: tabela „Zahteva za zahodno in Vzhodno Evropo“ (stran 6);
  pri −25 °C/1 m je v viru tiskano „2,27“ — očitna tipkarska napaka za
  2,75 (5,5 = 2×2,75). Vrstici 40/45 °C sta v viru prazni — zato
  `montazna_temp_c` velja za −25…35 °C.

### Montaža desk: usmerjenost je ODLOČILNA (rešitev spora 110 ↔ 180/150)

Obe vrednosti sta **uradni** — nanašata se na različni usmerjenosti
montaže desk (potrjeno na straneh prečnih/pokončnih ograj in pregrad;
jedro to loči prek `razmak_max_stebriki_precna_mm` /
`razmak_max_stebriki_pokoncna_mm`):

| profil | prečna montaža — stebrički | pokončna montaža — stebrički | vodoravne cevi (pokončno) |
|---|---|---|---|
| ROMB 67 | 145 cm (L-kotnika levo+desno; 145–180 cm z vmesno povezavo iz zgornje cevi) | 150 cm (vertikalni nosilci ≤ 100 cm, s kotnikom/ploščatim alu) | 110 cm |
| DESKA-128 | **110 cm** | **180 cm do 150 cm višine / 150 cm višje** | 100 cm |
| DESKA-150 | 133–140 cm (povzetek strani: 130 cm) | — | — |
| POLNA DESKA 100 | — | 180 cm do 150 cm višine / 150 cm višje | 80 cm |
| POLNA DESKA 57/32 | — | 150 cm (ne glede na višino) | 100 cm |

- Prečna: **spoji desk na dolžino obvezno na stebričku** (pritrdilni
  vijak 3 cm od roba reza deske).
- Pokončna romb: z razmaki med deskami je **vidna alu cev** v sredini
  profila — vsako desko zapri s čepi ali reši v detajlu konstrukcije.
- Priporočen razmak med deskami: 0,5–3 cm (FAQ pokončnih ograj navaja
  0,2–3 cm); možno prekrivanje desk iz obeh strani.
- Ročaj: vijači se v razmaku **50 cm** skozi ročaj v konstrukcijo (od
  zgoraj navzdol, vijak viden); predvrtje 1 mm večje od vijaka.
- Čepi za romb so dražji in **ne garantirajo**, da voda ne bo prišla v
  profil — priporočen je zaključek, ki zakrije odprtine.

Validacija (`preveri_cfg`) preverja **dejanski** razmak med nosilci (kot
je kotiran na risbi — `razmak_nosilcev` je le zgornja meja) in pri
preseganju zavrne izvoz z jasnim navodilom. L-kotniki (2 na stebriček)
so samodejno v potrebščinah, kosovnici in naročilu.

## Stanje projekta

| Issue | Vsebina | Stanje |
|---|---|---|
| #1 | AI pregled aplikacije in predlog izboljšav | ✅ zaprt |
| #2 | P0/P1 popravki izračunov, PDF, ostanki + regresijski testi (74) | ✅ zaprt (PR #4) |
| #3 | Vrata, prehodi, segmenti, DXF/CNC (61 novih testov) | ✅ zaprt (PR #7) |
| #5 | Strokovna analiza in razvojni načrt (primerjava z DrawAFence) | ✅ zaprt — poročilo A–H v issue #5 (ciljna arhitektura, fazni načrt F1–F5) |
| #6 | P0: revizija izračunov, kerfa, razreza + preverjena Windows izdaja | ✅ zaprt (PR #11; izdaja v1.2 **objavljena**) |
| #8 | ADD-ON: ograja iz fotografije (ločen modul, brez AI modelov) | ✅ zaprt (PR #13 — `photo_fence_proposal/`; testirano na 5 realnih fotografijah: uporabno kot vizualni predlog, mere zahtevajo potrditev) |

**Izdaja v1.2 je objavljena** (tag `v1.2`, EXE + SHA-256 + build-zapisnik; sledljivost commit `02f513c`).
| #9, #10 | Prazen terenski list — prostoročno risanje, elementi, tisk A4/A3 | ✅ zaprti (PR #12; #10 dvojnik #9) |

Testi: `python -m pytest tests/` — celotna zbirka; hitra razvojna zanka je
`pytest tests/ -q -n auto -m "not pocasi"` (počasni PDF testi nosijo marker
`pocasi`, timeout 600 s/test). CI (GitHub Actions,
`.github/workflows/testi.yml`) ob vsakem pushu požene ruff + mypy ratchet +
celotno zbirko vzporedno s coverage (ratchet prag 65 %).

## Namestitev

Potreben je Python 3.9+ (razvit in testiran na 3.11, Windows):

```bash
python -m pip install matplotlib pyyaml pillow opencv-python
```

## Uporaba

**Grafični vmesnik (priporočeno):**

```bash
python vmesnik.py
```

Vpišeš mere (Enter = privzete), po želji izbereš fotografijo, klikneš
**NARIŠI RISBO**. Nastavitve se samodejno shranijo (`zadnje_nastavitve.yaml`).

**Ukazna vrstica:**

```bash
python risba.py                    # vprašanja v terminalu
python risba.py projekt.yaml       # iz konfiguracije
python risba.py projekt.yaml -o BO-002.pdf
```

**Merjenje s fotografije:**

```bash
python merjenje.py fotografija.jpg
```

## Primer konfiguracije (`projekt.yaml`)

```yaml
ime: BALKONSKA OGRAJA
risba_st: BO-001
izdelal: R. Pezdirc
stranka: Ana Novak               # naročnik (gre v glavo risbe)
objekt: Radovljica, Tržaška 15
mere:
  sirina: 2450                   # dolžina ograje (mm)
  visina: 950                    # višina od tal do vrha (mm)
  globina: 1050                  # stranska dolžina (mm)
  odcep: 50                      # spodnji profil nad tlemi (mm)
  lamela_v: 60                   # višina lamel (mm)
  debelina: 20                   # debelina lamel (mm)
  lamele: 10                     # število lamel
  razmak_nosilcev: 900           # največji razmak nosilcev (mm)
barva: "Antracit"                # odtenek (validira se po katalogu barv)
profil: ROMB 67                  # model deske (WoodCore)
dolzina_deske: 5800              # tovarniška dolžina deske (mm)
kerf: 3                          # širina rezila (mm)
foto: poslikava_terena.jpg       # neobvezno — vstavi se na risbo
```

## Struktura projekta

```
risba.py            risalni motor (kote, šrafura, tabele, ISO glava) + obe predlogi
razrez.py           optimizacija razreza (več dolžin, ostanki, kosovnica)
vmesnik.py          grafični vmesnik (Tkinter)
merjenje.py         pomožno merjenje s fotografije (kalibracija + zaznavanje)
statika.py          poenostavljen statični pregled + statična priloga (PDF) — informativno
tridim/             3D mreža in izvoz STL/OBJ/GLB (brez copylefta) + neobvezni STEP most
oznake.py           QR oznake projektov (branje/zapis brez modelov)
api/index.py        spletni generator (Vercel, Flask)
mechanical/         katalogsko jedro F0/F1 (resolver, BOM, kontrola) — brez ograjne kode
cene.yaml           javni cenik za spletni predračun
TehnicnaRisba.spec  PyInstaller spec za Windows EXE
projekt_primer.yaml primer konfiguracije s komentarji
slike/              primeri izhodov
```

## Kako deluje izračun rezalnega načrta

Enoten model reza (kerf) velja povsod — v validaciji, optimizatorju,
risbah, kosovnici in naročilu: n kosov dolžine `k` iz traku `V` zasede
`n × (k + kerf)`; ostanek je `V − n × (k + kerf)`. Iz širine ograje,
števila lamel in tovarniških dolžin desk (npr. `5800; 4000; 2200`)
optimizator izbere trakove z najmanjšim odpadom na kos, najprej porabi
skladišče ostankov (če je vklopljeno), nato izpiše ostanek vsakega traku
in izkoristek. Če razrez ni popoln (manjkajo kosi), program tega ne
označi kot uspeh, ampak javi napako.

**Konstrukcijska geometrija (dokumentirana odločitev):**

- **pokončna predloga** — stebri so v enakomernih legah, deske potekajo
  po poljih med stebri in so pritrjene na oba sosednja stebra (2 vijaka
  na stik = **4 vijake na desko**); uporabnikova `vrzel` se uporabi
  natanko in se ne prilagaja tiho; če se deske ne prilegajo, je to
  jasna napaka,
- **prečna (ograja)** — vhod je število lamel, vrzel med lamelami se
  izračuna porazdeljeno; razmak nosilcev je največja dovoljena vrednost,
  na risbi in v listih pa se kotira **dejanski** razmak.

## Testi (regresijski)

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### Ocenjevanje modelov za kodiranje (skriptno, brez AI-žirije)

`benchmark/` meri kakovost kodiranja **izključno z izvajanjem skritih
testov** (SWE-bench vzorec: FAIL_TO_PASS + PASS_TO_PASS), z canary
žetoni proti uhajanju rešitve in s statistiko (pass@k, Wilson, parni
bootstrap, McNemar). Ocenjevalnik je validiran s ponarejenimi agenti —
brez klica kateregakoli modela:

```bash
python -m benchmark.tek --seznam
python -m benchmark.tek \
  --agent "python benchmark/ponarejeni_agent.py --nacin ok" \
  --ponovitve 3 --izhod rezultati.json
```

Metodologija, viri in omejitve: `docs/benchmark-modelov.md`.

Hitrejša razvojna zanka (vzporedno + brez počasnih PDF testov, marker
`pocasi`; vzporedna varnost testov je preverjena — izhodi so v `tmp_path`):

```bash
python -m pytest tests/ -q -n auto -m "not pocasi"
```

`pytest-timeout` (600 s/test) varuje pred zataknjenimi teki tudi v CI.

Testi (74) v mapi `tests/` pokrivajo vse popravke: življenjski cikel
`PdfPages` in štetje strani s `pypdf`, dolžino kosa za obe predlogi,
validacijo (kerf, dolžine, ročaj/palica), dvojno odštevanje ostankov,
varno skladišče, palice, vijake, pokončno geometrijo, informativni
predračun in krog shranjevanja nastavitev v GUI.

## Neobvezne knjižnice (strategija paketov)

Jedro (`requirements.txt`) ostaja vitko in se ne širi, dokler koda paketov ne uvozi.
O odločitvah za dodatne knjižnice (scipy/trimesh/meshio, `scikit-image`, `cadquery`,
OCR/ML sloj) in o **licenčnih prepovedih** za EXE (`gmsh`, `pymeshlab` = GPL;
`pythonocc-core` = samo conda + LGPL) glej
[docs/analiza-paketov.md](docs/analiza-paketov.md).

## Izdelava Windows EXE (samostojni program)

```bash
python -m pip install pyinstaller
python build_windows.py --smoke
# rezultat: dist/TehnicnaRisba.exe + build-zapisnik.json (hash, različice, smoke)
```

`build_windows.py` je dokumentiran, ponovljiv postopek (različice →
PyInstaller iz `TehnicnaRisba.spec` → SHA-256 → funkcionalni smoke prek
neinteraktivnega načina `--brez-zaslona` / `TEHNICNA_RISBA_HEADLESS=1`).
Spec vključi risba.py + razrez.py + vrata.py + dxf_izvoz.py + migracija.py +
vmesnik.py; nastavitve se shranijo poleg EXE (`zadnje_nastavitve.yaml`),
ostanki pa v uporabniško podatkovno mapo (`%APPDATA%\TehnicnaRisba`).

**Poštena izjava o preizkusih:** regresijski testi (163) so bili izvedeni v
razvojnem okolju Windows 10/11 / Python 3.11.9 / matplotlib 3.11.2;
EXE je bil zgrajen s `build_windows.py` in funkcionalno preizkušen z
neinteraktivnim smoke testom (PDF 2 strani, preverjen s pypdf) —
kontrolne vsote v `build-zapisnik.json`. Bit-identičnost izida ni
zagotovljena (časovni žigi PyInstaller). **Izdaja ni objavljena** —
objavi jo šele po potrditvi rešitve.

## Vrata, prehodi, segmenti in DXF (issue #3)

Razširitev podpira vgradnjo vrat in prehodov v **obe** predlogi ograje, z
pravilnimi merami, količinami in izvozom za CAD/CNC.

- **Vrata** (`vrata:` v YAML ali sekcija »VRATA IN PREHODI« v GUI): tipi
  `enokrilna`, `dvokrilna`, `pasja`, `prehodna`, `drsna`, `dvokrilna_drsna`;
  mere, smer odpiranja,
  tečaji, zaklep, ročaj, prečke, diagonala. Geometrija živi v `vrata.py`
  (edini vir resnice) — risba, količine, kosovnica in DXF porabljajo isti
  izračun. Odprtine vplivajo na polnilo (lamele/deske se razrežejo okoli
  njih), razrez, količine in kosovnico — ne le na risbo.
  Pri `drsna` je **`preklop` (mm) obvezen vhod brez privzete vrednosti**
  (kolikor se krilo prekriva z zapornim stebrom), smer je parkiranje
  (`levo`/`desno`); krilo = odprtina + preklop, umik (`teka`) = širina krila.
  Pri `dvokrilna_drsna` je `preklop` prekrivanje kril v sredini (pogoj
  zaprtja `2·krilo − preklop = S_o`); smer ni vhod (simetrično), umik je
  potreben na vsaki strani. Obe drsni vrsti brez okvirja v odprtini in brez
  tečajev; vodila/rolle in zaporni steber niso v kosovnici (ni kataloških
  podatkov) — vnašajo se ročno.
- **Prehodi** (`prehodi:`): odprtina brez kril (prehodna vrata), s svojimi
  količinami (zaključni stebri/profili, sidranje).
- **Več segmentov** (`segmenti:`, YAML shema v2): vsak segment ima lahko
  lastne mere, vrata/prehode in kot (vogal). Stare datoteke (shema v1) se
  samodejno migrirajo v pomnilniku (`migracija.py`), brez izgube podatkov.
- **DXF izvoz** (`--dxf`, gumb »IZVOZI DXF«): R2010, mm 1:1, 9 plasti
  (rez/vrtanje iz OUTLINE/POSTS/HOLES), zaprte konture, kote, naslovni blok.
  **Omejitve:** brez G-code/toolpath, brez kompenzacije orodja/kerfa —
  podrobnosti v `docs/dxf-specifikacija.md`.

Pravila količin (tečaji, vijaki, prečke, diagonala) in odločitve so
dokumentirani v `docs/issue-3-vrata-dxf.md`. **Risba NI statični izračun** —
nosilnost, sidranje in veterno breme preveri usposobljen strokovnjak.

## 3D model (STL / OBJ / GLB)

Iz istih mer kot risba se zgradi masni 3D model (stebri, deske, ročaj,
osnovne plošče). Globinski odmiki in vijaki namenoma niso modelirani —
2D risba jih ne poda, izmišljene lege bi bile laž; model to pove v
opombah.

```bash
python -m tridim --vhod projekt_pokoncna.yaml --izhod ograja.stl
python -m tridim --vhod projekt_pokoncna.yaml --izhod ograja.glb
```

Podprti sta obe predlogi: **pokončna** (stebri + deske + ročaj + osnovne
plošče) in **prečna/ograja** (vodoravne lamele med profiloma, nosilci,
okvirji odprtin za vrata/prehode, pri globini > 0 še stranski krak v
L-obliki). Tla iz 3D predogleda niso del modela — so le orientacija.
Neznano predlogo program zavrne z razlago, ne ugiba.

Prostornina in zaprtost mreže sta preverjeni v testih (izrek o
divergenci), ne le „izgleda v redu“. **Zakaj ne cadquery:** OpenCASCADE
je LGPL-2.1 (`casadi` LGPL-3.0), zato copyleft ne gre v EXE; STEP izvoz
je zato neobvezen most (`--step`, `pip install cadquery`), podrobno v
`docs/odlocitev-3d-in-ocr.md`.

## QR oznake projektov (brez OCR modelov)

Koda projekta se natisne kot QR in prebere s fotografije — deterministično,
brez modelov in brez prenosa uteži:

```bash
python oznake.py --zapisi projekt.yaml --izhod oznaka.png
python oznake.py --preberi fotografija.png
```

Če je nameščen `rapidocr-onnxruntime` (ni v `requirements.txt`), program
zna prebrati tudi **natisnjeno** oznako brez QR kode: `python oznake.py
--preberi slika.png` najprej poskusi QR, nato OCR. Rezultat OCR je vedno
označen kot „vir: OCR“ in zahteva potrditev — ročne pisave namenoma ne
obeta. Namestitev: `python -m pip install rapidocr-onnxruntime`.

V GUI: *Vstavi → Preberi oznako projekta (QR)…* in *Orodja → Zapiši
oznako projekta (QR)…*. Prebrane vrednosti se **ne** uveljavijo same —
program vpraša za potrditev. Format `TR1|projekt|šifra|višina|širina`;
neveljavna ali tuja koda se zavrne z razlogom.

## Revizija izračunov (issue #6, P0)

Kanonični `proizvodni_model` (en vir resnice za tabele, montažni list,
količine, kosovnico in naročilo), fizično pravilen model reza (DP
optimizator, kerf model B), usklajen model vrat (veriga vključuje profile
okvirja), neodvisni regresijski testi modela reza in ponovljiv Windows
build (`build_windows.py`). Podrobnosti in dokazila:
[docs/issue-6-revizija.md](docs/issue-6-revizija.md).

## Znane omejitve

- Samodejno zaznavanje lamel/vijakov na fotografijah je **pomožno** — na
  terenskih posnetkih pod kotom ni zanesljivo; zanesljiva pot je kalibracija +
  klik-merjenje. Odtenek WPC se potrdi z vzorcem proizvajalca (ni RAL).
- Predlogi **prečno** (vodoravne lamele) in **pokončno** (navpične deske na
  stebrih) sta polno podprti.
- Odpis ostankov po rezanju je ročen: gumb „ODPIŠI OSTANKE" v GUI ali
  CLI zastavica `--potrosi-ostanke` (namenoma — potrdiš, da so kose res
  rezali po načrtu).
- Če se kakšen dodaten list (montažni list, predračun, nalepke) ne more
  izrisati, program to jasno javi kot opozorilo (CLI vrne kodo 2, GUI
  pokaže status) — dokument NI tiho prikazan kot popoln.
- **matplotlib >= 3.10.7:** `savefig` po zaprtju `PdfPages` tiho prepise
  PDF v 0 B. Program zato vse strani zapiše v ENEM ciklu `PdfPages`
  (brez risanja po zaprtju) — priporočena različica je v `requirements.txt`.
- Spletni generator (`api/`) na Vercelu NI aktiven — objavljena je statična
  predstavitvena stran (`index.html`); lokalni program je Windows EXE/CLI.

## Avtorske pravice in licenca

Koda je objavljena pod licenco **MIT** (glej `LICENSE`). WPC in znamke
proizvajalcev pripadajo njihovim lastnikom (npr. WoodCore / roksal.com —
vir referenčnih specifikacij).

Samostojni EXE vsebuje tudi kodo tretjih oseb (matplotlib, numpy, ezdxf,
PyYAML, Pillow, ttkbootstrap, PyInstaller bootloader); njihove licence in
razlogi za vključitev so v `THIRD_PARTY_NOTICES.md`, ki ga strojno
preverja `scripts/preveri_licence.py --preveri` (tudi v CI).
