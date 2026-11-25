# Zgodovina sprememb

## v1.5.23 — 2026-11-25 (fotografije montaže naročnika: perspektivne vrzeli niso stebri)

**Naročnikove lastne fotografije montaže (delavniški plošči z znano
resnico: 11 desk + 2 stebra) so odkrili dve napaki, ki ju sintetika ni
mogla pokazati.**

- **`poisci_stebre` ne zamenja več perspektivnih vrzeli za stebre.**
  Primerjava širin z globalno mediano je na sliki u03 (vrzeli se
  perspektivno zožijo 64 → 2 px) prve tri vrzeli razglasila za „stebre“
  (rezultat: 3 stebri `izracunano` namesto `neznano`). Zdaj se vsak tek
  primerja z lokalno osnovo sosednjih širin.
- **Zanesljivost ritma je vidna.** S grobi koti je bila avtokorelacija u03
  razpršena (0,19, napačno obdobje 42 px) — sporočilo „ritem DESK“ zdaj
  vključuje zanesljivost in štetje označi kot grobo oceno (»približno«;
  izmerjen odmik +1 na obeh ploščah in r09).
- Poskus korekcije podobdobja je bil preizkušen in **odstranjen** — ni se
  sprožil niti na realnih niti na sintetičnih primerih.
- 2 nova regresijska testa (perspektivne vrzeli, pošteno sporočilo).
- Dokumentirano: `docs/izboljsave-zaznave-ograje.md` (4.5) z resnico,
  tremi neodvisnimi prehodi štetja in merjenim odmikom.
- Preverjeno: PFP **94 testov**; ruff čist; mypy brez novih.

## v1.5.22 — 2026-11-25 (resnične fotografije izdelka: dve samozavestni napaki manj)

**Fotografije iz galerije Roksal (WPC ograje) so pokazale, da je nova
meja 35 % prava, a da je iskanje stebrov po širini še preveč pogumno.**

- **`perioda.poisci_stebre()` strožje:** vsaj **3** široki temni teki
  (z dvema je CV razmika vedno 0, zato je bil vsak par razglašen za
  "stebre"), vsaj dva razmika in CV razmikov ≤ 0,20, širine stebrov pa
  podobne (CV ≤ 0,50).
- **Napaka, najdena na resnični fotografiji:** pokončna balustrada
  (`r06.jpg`) je vrnila **2 stebra, status `izracunano`** — iz dveh
  naključnih desk, ker je bil CV enega samega razmika 0. Zdaj: `neznano`
  + opozorilo *ritem DESK (53 elementov, 24 px)*.
- **Druga resnična fotografija** (`r09.jpg`, 13 desk med dvema stebroma):
  število desk **14** (resnica 13, **+7,7 %**), stebri `neznano` — z
  dvema stebroma jih program ne potrjuje (raje neznano kot ugibanje).
- **Sklep:** za horizontalne lamele (glavni izdelek) program ne izmišlja
  več stebrov; štetje stebrov na resničnih fotografijah ostaja odprto
  (potrebna sta ročna potrditev ali marker + znana geometrija).

Testi: **92** (`python -m pytest photo_fence_proposal/testi_pfp.py -q`).
## v1.5.21 — 2026-11-24 (deske niso stebri)

**Letvasta ograja je doslej vrnila 75 »stebrov« in razmak 108 mm —
samozavestno napačno. Zdaj program loči ritem desk od stebrov in raje
pove »neznano«, kot da bi štel deske.**

- **`perioda.MIN_RAZMERJE_STEBROV` (0,35):** perioda, ki je manjša od
  dobre tretjine višine ograje, je ritem **desk** (deske so ~0,1 višine
  narazen, stebri ~1 višino). Razmerje je brez merila, zato deluje tudi
  brez markerja.
- **`perioda.poisci_stebre()`:** kadar so na sliki hkrati ozke deske in
  široki stebri, jih loči po **širini temnega teka** (steber ≥ 1,8 ×
  mediana širine) in preveri enakomernost razmikov (CV ≤ 0,20). Brez
  izrazitih stebrov vrne `None` — ne izmišlja števila.
- **`zazeni._prestej_elemente()`:** če je zaznani ritem prefin, a stebrov
  ni mogoče ločiti, `stevilo_stebrov` dobi status `neznano` z razlago,
  `stevilo_polj` in `razmak_stebrov` pa se **ne izmišljata**; dokument
  dobi opozorilo z številom desk in razmakom v pikslih.
- **Izmerjeno (sintetično, `narisi_prizor`, 4 stebri + 75 desk):** prej
  `75` stebrov / razmak `108 mm` / status `izracunano`; zdaj `neznano` +
  opozorilo. Kjer so stebri izrazito širši: `4` stebri, `3` polja,
  razmak `2000 mm`. Scena samo s stebri (marker): `4` stebri, razmak
  `1975 mm` (resnica 2000, **−1,3 %** — napaka rektifikacije).
- Novi testi: `test_stetje_ne_zamenja_desk_za_stebre`,
  `test_stetje_najde_stebre_ob_deskah`,
  `test_perioda_poisci_stebre_po_sirini`,
  `test_perioda_poisci_stebre_brez_stebrov_vrne_none`.

Testi: **91** (`python -m pytest photo_fence_proposal/testi_pfp.py -q`).
## v1.5.20 — 2026-11-24 (F2 izmerjen in zavrnjen)

**Grounded SAM 2 na resničnih fotografijah ne šteje elementov in je
prepočasen — AI pot je zaprta z meritvijo, ne z mnenjem.**

- **`docs/meritev-f2-maske.md` (novo):** 5 fotografij z Wikimedia Commons
  (CC BY-SA), GroundingDINO Swin-B + SAM 2.1 hiera-small na CPU. Napaka
  štetja **−20 % … −98 %** (povprečje −54 %), čas **41–45 s/sliko** proti
  vratom ±10 % in ≤ 30 s. Poskusi s pragom 0,15 in 2×2 ploščicami
  natančnosti niso izboljšali (149 s/sliko).
- **Popravek štetja mask (`maske_ai._zdruzi`):** intervali se združujejo
  le ob **močnem prekrivanju** (polovica ožje maske), ne po razmiku — pri
  gosti ograji so deske tesno druga ob drugi, zato je staro pravilo vse
  zlepilo v en element. Test fragmentov posodobljen.
- **pytest:** `norecursedirs` dobi `.test` — klonirano tuje skladišče
  (Grounded-SAM-2) ima svoje `test_*.py`, ki bi jih pytest sicer pobral
  in javil kot napake zbirke (šum, ne napaka izdelka).
- **Sklep:** torch/GroundingDINO/SAM 2 ne pridejo v `requirements.txt`
  ali EXE; ostane `maske_ai.py` + `--maske` kot dokaz/opozorilo, EXE
  ostane 52,7 MB in brez AI.
- F2 v `docs/nacrt-draftwright-pro.md` je zdaj *izmerjeno in padlo*,
  v `docs/izboljsave-zaznave-ograje.md` pa zaprto z negativnim izidom.

Testi: **87** (`python -m pytest photo_fence_proposal/testi_pfp.py -q`).
## v1.5.19 — 2026-11-24 (AI kot dokaz, ne kot mera)

**Maske iz zunanjega AI orodja lahko potrdijo štetje — ne morejo ga nadomestiti.**

- **`maske_ai.py` (novo):** strogo branje/validacija JSON z maskami
  (neznana oznaka, točka zunaj slike, pokvarjen JSON → slovenska napaka)
  in **deterministično** štetje: stebri = združeni intervali po X, lamele
  = intervali po Y. Fragmenti istega stebra se združijo (prag 0,3 ×
  mediana širine), zato AI, ki en steber razdeli na dve maski, ne podvoji
  števila.
- **`zazeni.pozeni(..., maske_pot=...)` in `--maske maske.json`:** če se
  AI štetje ujema z našim periodičnim, opis dobi *»— potrjeno z AI
  maskami (N)«* in status **ostane** enak; ob nesoglasju je število
  `ocenjeno`, opis navede obe vrednosti, dokument dobi opozorilo *»metodi
  se ne ujemata … preveri ročno«*. AI nikoli ne dvigne statusa in nikoli
  ni prevzet tiho. Če našega štetja ni, je vrednost iz mask `ocenjeno`
  z jasno oznako vira.
- **`scripts/grounded_sam2_maske.py` (novo):** zunanji, neobvezni most
  Grounded SAM 2 → JSON (`--preveri` pove, kaj manjka; brez paketov se
  ustavi z navodilom, izdelek pa deluje naprej). **Kakovost AI mask v tem
  okolju NI izmerjena** — uteži (~1 GB) niso nameščene, zato vrata F2 iz
  `docs/nacrt-draftwright-pro.md` ostajajo odprta; skript je označen kot
  nepreverjen.
- **Testi:** 9 novih (krog shrani/preberi, tri zavrnitve, združevanje
  fragmentov, lamele, primerjava, potrditev in nesoglasje skozi `pozeni`).

Testi: **87** (`python -m pytest photo_fence_proposal/testi_pfp.py -q`).
## v1.5.18 — 2026-11-24 (merjenje)

**Soglasje več posnetkov: napaka ene fotografije se ne skrije več v povprečju.**

- **`vec_posnetkov.py` (novo):** izmeri vsak posnetek posebej (marker +
  koti) in vrne mediano. Če se posnetki ne ujemajo znotraj **2 %**, mera
  NI izračunana (`Soglasje.dolzina_mm is None`), uporabnik pa dobi razpon
  (npr. *dolžina 5925–6600 mm, razpršenost 10,4 %*). Prag 2 % je izbran
  zavestno: napaka enega posnetka je 0,03–3 %, strožji prag bi zavračal
  pravilne meritve, ohlapnejši ne bi ujel napačne stranice markerja (5–13 %).
- **`zazeni.pozeni(..., dodatni=[(pot, koti), ...])`** in ukaz
  `--dodatna "pot.jpg|x,y;x,y;x,y;x,y"` (lahko večkrat, zahteva
  `--vogali`). Ob soglasju ima mera opis `soglasje 2 posnetkov
  (razpršenost 0,9 %)` in status `izracunano`; ročni vnos uporabnika ima
  prednost.
- **Okno »Predlog mer iz fotografije«:** novo neobvezno polje
  *2. posnetek (pot|x,y;…)* + gumb *Izberi …*; druga fotografija gre
  skozi `avtomatska_skica.izracunaj_mere_pot(dodatni=…)`, tako da sta
  soglasje in opozorilo vidna tudi brez ukazne vrstice.
- **Izmerjeno (sintetični sceni 6000×1000 mm, marker 300 mm):** 5925 in
  5980 mm → razpršenost 0,9 %, mediana 5952 mm (−0,8 %); preoster kot
  (marker neberljiv) vrne `None`, ne izmišljene mere.
- **`docs/nacrt-draftwright-pro.md` (novo):** raziskava zunanjih 3D/AI
  projektov (COLMAP, Grounded SAM 2, Open3D, CadQuery, FreeCAD, Meshroom,
  JSCAD, step2pdf) s preverjenimi zvezdicami/licencami in fazami z vrati;
  noben paket ni bil nameščen ali vgrajen.

Testi: **78** (`python -m pytest photo_fence_proposal/testi_pfp.py -q`).
## v1.5.17 — 2026-11-24 (vmesnik)

**Marker in koti tudi v oknu; izpeljana mera ni več lažno »izračunana«.**

- **GUI (`vmesnik.py`), okno »Predlog mer iz fotografije«:** novi polji
  *Koti ograje* (`x,y;x,y;x,y;x,y`) in *Marker (mm)* ter gumb *Natisni
  marker …* (shrani A4 list s tlorisom markerja in 100-mm kontrolno črto).
  Brez vnosa se obnaša kot prej, s koti se slika poravna, z markerjem se
  izmerita obe dimenziji.
- **`avtomatska_skica.izracunaj_mere_pot()`/`generiraj()`** sprejmeta
  `marker_mm`. Kadar je marker viden, sta dolžina in višina `izračunano`
  iz geometrije ravnine — neodvisno od zaznave lamel (prej so ob
  neprepoznanem ritmu ostale `neznano`).
- **Poštenost:** če je znana le ena dimenzija (npr. višina) in markerja ni,
  je izpeljana dimenzija zdaj `ocenjeno` z opozorilom, da razmerje stranic
  iz samih kotov ni določeno. Prej je bila označena `izračunano`, kar je
  bila lažna gotovost (perspektiva popači razmerje).
- **`vnos.py` (novo):** skupno razčlenjevanje kotov za CLI in GUI;
  `zazeni.razcleni_vogale` ga uporablja (ena implementacija, enaka
  sporočila).

Testi: **68** (`python -m pytest photo_fence_proposal/testi_pfp.py -q`).
## v1.5.16 — 2026-11-24 (merjenje)

**Merjenje z natisnjenim markerjem in periodično štetje elementov.**
Raziskava (`docs/izboljsave-zaznave-ograje.md`) je pokazala dvoje: mere se
lomijo zaradi perspektive in napačnega štetja, štirje koti ograje pa za
širino **geometrijsko ne zadostujejo** — pravokotnik 6:1 od daleč in 3:1 pod
drugim kotom dasta isto sliko. Zato:

- **`marker.py` (novo):** A4 list z ArUco markerjem (300 dpi, 100-mm kontrolna
  črta za preverjanje tiska) in meritev prek homografije markerja. Čelno
  izmerjeno **6000 × 1000 → 5998 × 998 mm (0,03 %)**, poševno z markerjem
  300 mm (68 px v sliki) **−1,3 % / −0,7 %**. Pod 60 px se marker zavrne,
  pod 120 px opozori (napaka naraste na 5–13 %).
- **`perioda.py` (novo):** perioda in število elementov iz svetilnostnega
  profila (CLAHE, odstranjen trend), avtokorelacija z izborom najmanjšega
  lokalnega maksimuma ≥ 0,6 × maksimuma; štetje z lokalno normalizacijo in
  kontrolo popolnosti. Sintetično točno (10/16/8/26 elementov, perioda ±1 px);
  na tuji fotografiji `k1-izrez` 23 od ročno preštetih 26 — ker je pričakovanih
  28, program rezultat označi `ocenjeno` in opozori, namesto da bi se lagal.
- **`zazeni.py`:** `--vogali "x,y;x,y;x,y;x,y"` (poravnava v čelni pogled +
  periodično štetje) in `--marker-mm` (merilo). Brez markerja program širine
  **ne izračuna** in to pove; ročni `--dolzina`/`--visina` ostaneta veljavna.
- **Dokumentacija:** `docs/izboljsave-zaznave-ograje.md` popravljena — koraki
  1–3 so označeni kot narejeni, z izmerjenimi številkami in dokazom o
  nedoločenosti širine; `photo_fence_proposal/README.md` dobi navodilo za
  marker.

Testi: **66** (`python -m pytest photo_fence_proposal/testi_pfp.py -q`).
## v1.5.15 — 2026-11-24 (preverjanje)

**Ročno potrjena dolžina zdaj povozi zaznavo.** Preizkus: `--dolzina 4000
--visina 1000` je obdržal 19 zaznanih »stebrov« iz fotografije (18 polj,
180 vijakov) — nesmisel za 4 m ograjo. Zdaj se polja in stebri izračunajo iz
potrjene dolžine in razmaka (zaznanega, če je verjeten, sicer privzetih
2000 mm), z opozorilom, da je zaznava nasprotovala meritvi.

Rezultat za 4 × 1 m: **2 polji, 3 stebri, 5 lamel, 20 vijakov** (prej 19
stebrov, 180 vijakov). Testi: **55**.

## v1.5.14 — 2026-11-24 (preverjanje)

**Preizkus na poljubnih fotografijah z interneta** (Wikimedia Commons:
baročni balkon, hiša s tremi balkoni, stekleni balkon nebotičnika). Rezultat:
na tujih fotografijah mere **niso uporabne** (baročni balkon: 24 000 mm
namesto ~11 m; hiša s tremi balkoni: 1582 mm; izrez enega balkona: 2198 mm).
Program tega ne more ugotoviti sam — zato je zdaj vsaj **glasno**:

- **Opozorila zaznave so se izgubljala:** zavržena mera (»višina 12 250 mm ni
  fizično verodostojna«) je ostala le v internem objektu in ni prišla v
  povzetek, PDF niti JSON. Zdaj se prenesejo v dokument.
- **Kosovnica je bila v nasprotju z zaznavo:** 19 zaznanih stebrov in 18 polj
  sta dala »Steber 2 kos« (izpeljava iz dolžine, ker razmak ni bil znan).
  Zdaj velja število polj + 1.
- **Nov preizkus razmaka stebrov:** razmak < 300 mm ali > 5000 mm pomeni, da
  zaznani vertikalci niso stebri (na steklenem balkonu 193 mm) — opozorilo.
- **Predračun ob neuporabni zaznavi:** označen je kot groba ocena
  (»ni podlaga za ponudbo«), tudi ko so cene iz cenika.

Preverjeno: `testi_pfp.py` **54 testov** (3 novi), sintetični prizori
ostajajo znotraj ±3,9 %, ruff čist.

## v1.5.13 — 2026-11-24 (orodja)

**Fotografija → mere → risba → predračun** v enem toku (`photo_fence_proposal`).
Dodatek ostaja samostojen in brez AI modelov — vse lokalno (OpenCV).

- **`izracun.py`** — nov modul: kosovnico ovrednoti s cenikom `cene.yaml`
  (WPC po metrih porabe, stebri po metrih profila, vijaki po kosih, delo po
  urah). Cene se **ne izmišljajo**: manjkajoč ključ pomeni »cena po
  dogovoru«, skupni znesek ostane neizračunan, dokler cena manjka.
  Postavke, ki jih kosovnica ne vsebuje (sidra, osnove, nosilci, zaključni
  profili), se ne prištejejo tiho — izpišejo se kot opozorilo za monterja.
- **`07-predracun.pdf` in `08-predracun.csv`** — A4 predračun z glavo
  (podjetje/stranka/objekt), postavkami, seštevki, statusi mer in blokom
  opozoril. Dokler ključne mere niso potrjene, je dokument označen
  **INFORMATIVNO** in ni ponudba.
- CLI: `--cene`, `--brez-predracuna`, `--podjetje`, `--stranka`, `--objekt`;
  brez cenika se predračun ne izdela (jasno opozorilo, ne tiho ničla).
- **Konzola (Windows cp1250):** izpis je prek cevi v UTF-8, znaki `≈`, `×`,
  `—` se za konzolo zamenjajo — `UnicodeEncodeError` pri povzetku je
  odpravljen (enak razred napake kot v v1.5.8).
- Preverjeno: `testi_pfp.py` **51 testov** (7 novih za predračun), ruff čist,
  mypy brez novih napak; na realni fotografiji dokument ostane
  INFORMATIVNI PREDLOG (zaznava 15 »stebrov« namesto dejanskih — meritve
  se ne izmišljajo).

## v1.5.12 — 2026-11-24 (orodja)

Dodano je **ločeno orodje za ilustracije** — ne del izdelka, ne v EXE-ju,
aplikacija ga nikoli ne kliče. Tehnične risbe ostajajo deterministične;
slike so namenjene izključno ročni pripravi marketinških ilustracij.

- **`scripts/slike_cloudflare.py`** — generiranje prek Cloudflare Workers AI
  (`@cf/black-forest-labs/flux-1-schnell`) z brezplačno kvoto **10 000
  nevronov/dan** na račun (obnova 00:00 UTC; pozimi 01:00 po lokalnem času).
  Pri 1024×1024 in 4 korakih je to ~58 nevronov oz. **do ~173 slik/dan**.
  Ključ se bere **samo iz okoljskih spremenljivk** (`CLOUDFLARE_API_TOKEN`,
  `CLOUDFLARE_ACCOUNT_ID`) — nikoli iz datoteke ali ukazne vrstice; ob
  manjkajoči spremenljivki skript pove, katera manjka, in ne kliče API-ja.
- Napake so izrecne: prazno povpraševanje, koraki izven 1–8, neveljaven
  base64, vsebina, ki ni JPEG/PNG, in porabljena kvota (s sklicem na
  00:00 UTC) — nič ne odpove tiho.
- `tests/test_slike_cloudflare.py` — **15 testov brez omrežja** (klic je
  nadomeščen): manjkajoče okolje, prazno povpraševanje, meje korakov, zapis
  v novo mapo, napačna končnica, napaka API-ja, razlaga kvote, pokvarjen
  base64, vsebina, ki ni slika, ocena nevronov in obe poti CLI-ja.
- `ilustracije/` je v `.gitignore` — generirane slike ne gredo v repozitorij
  (spletna stran `slike/` še naprej prikazuje resnične izdelke programa).
- Preverjeno: polna suite; ruff čist; mypy brez novih napak.

## v1.5.11 — 2026-11-24 (testi)

Zadnja dokumentirana testna vrzel iz revizije („`preveri_cfg` B1–B7“) je
zaprta. Vedenja ne spreminjamo — preverjeno je, da je vsaka veja res
dosegljiva in da napaka ostane v seznamu, nikoli izjema.

- **`preveri_cfg` ima zdaj pokrite vse veje** (24 novih testov v
  `tests/test_preveri_cfg_veje.py`): izklop optimizacije (A6) v obeh
  oblikah, nedovoljen status dokumenta, slaba oblika revizij, prevelik
  ročaj/odcep, deska širša od razpona, razmak stebrov ≤ širina stebra,
  cona profilov, prevelike lamele, negativen kerf, starejši zapis
  `dolzina_deske`, napačen seznam dolžin, premajhna nabavna dolžina,
  prekratka alu palica (profil in steber), neobstoječa fotografija,
  `segmenti` v napačni obliki ter defenzivni veji (geometrija in
  `vrata_podatki` vržeta izjemo → napaka v seznamu, ne sesutje).
- Pokritost jedra pri branju `preveri_cfg`: **v telesu funkcije ni več
  neizvedene vrstice ali veje** (prej ~20 vej); skupna pokritost
  `jedro.py` 71 % → 80 % (le s testi, ki se dotaknejo validacije).
- `docs/issue-6-revizija.md`: najdba P2/P3 je označena kot odpravljena
  (v1.5.9–v1.5.11).

## v1.5.10 — 2026-11-24 (testi)

Sprememba vedenja ni nobena — zapira se dokumentirana testna vrzel iz
revizije (najdba P2/P3: „krajšanje rezalnega načrta brez testov“).

- **Krajšanje montažnega lista je zdaj zaklenjeno s testi.** Nad 10 vrstami
  se v REZALNEM NAČRTU pokaže 10 vrst in vrstica „… ostalih N vrst“ s
  sklicem na CSV/nalepke; vizualni rez pokaže največ 5 trakov in zapiše
  „prikazanih 5 od N trakov“. Prej teh mej ni preverjal noben test.
  Štirje testi: okrnitev nad 10 vrstami, neokrnjenih 10 vrst, 7 trakov
  (5 + zapis), 5 trakov (brez zapisa).
- Čiščenje vej: vse feature veje so bile že zlite v `main` (0 lastnih
  commitov), zato so odstranjene lokalno in na `origin` — ostane samo
  `main`.
- Preverjeno: polna suite; ruff čist; mypy brez novih.

## v1.5.9 — 2026-11-24 (popravek)

- **Podan kot med segmenti ni več tiho izgubljen v DXF.** `kot` je del
  podatkovnega modela, vendar v1 riše segmente v skupni ravnini; uporabnik
  s `kot: 90` je dobil raven tloris brez vsakega namiga. Zdaj DXF ob
  podanem kotu doda opombo „Kot med segmenti (vogali) NI narisan — segmenti
  so v skupni ravnini; tloris z vogali je načrtovana razširitev.“
  Brez podanega kota opombe ni (brez šuma).
- Štirje novi testi za dokumentirane vrzeli: opomba ob kotu in odsotnost
  opombe brez njega (DXF) ter padec predračuna in padec nalepk (PDF ostane
  veljaven, opozorilo pove, kaj manjka, PNG pa se ne ustvari).
- `docs/dxf-specifikacija.md`: omejitev vogalov je zdaj opisana kot
  nikoli tiha.
- Preverjeno: polna suite (spodaj); ruff čist; mypy brez novih.

## v1.5.8 — 2026-11-24 (popravek)

- **CLI za 3D ne sesuje več na Windows konzoli (cp1250).** `tridim/__main__.py`
  je tiskal `m³` (`\u00b3`), kar `cp1250` ne pozna — `test_cli_izvozi_glb`
  in `test_cli_precna_predloga` sta padla z `UnicodeEncodeError`. Zdaj
  izpisuje `m3`.
- Preverjeno: hitra suite **699 passed, 3 skipped**; ruff čist; mypy brez novih.

## v1.5.7 — 2026-11-24 (popravek)

- **Neveljavno merilo ne sesuje risanja.** `merilo: "abc"`, `merilo: "1:0"`
  ali `merilo: null` je obšlo validacijo in padlo šele v `int()` oziroma
  deljenju z nič med risanjem. `preveri_cfg` zdaj zahteva `auto` ali
  `1:N` s pozitivnim celim N; `generiraj` slabo vrednost zavrne pred
  risanjem, z jasnim sporočilom namesto sledi sklada.
- 16 novih testov: veljavne oblike (`auto`, `1:20`, `20`), neveljavne
  (`abc`, `1:0`, `null`, ...) in zavrnitev v `generiraj`.
- Preverjeno: polna suite **770 passed, 2 skipped**; ruff čist; mypy 0.

## v1.5.6 — 2026-11-24 (popravek)

- **Neznan ali napačno zapisan tip segmenta v DXF ni več tiho
  pokončna ograja.** `_elementi_segmenta` je imel `else` vejo, ki je
  vsak tip razen `"ograja"`/`"ograda"` izrisala kot pokončno. Segment
  s `tip: "OGRAJA"` ali celo tipkarsko napako (`"ograaj"`) je tako
  ustvaril napačno geometrijo za CNC. Zdaj se tip normalizira, neznan
  tip pa se zavrne z jasno napako.
- `preveri_cfg` preveri tudi segmente: seznam, vsak vnos kot dict,
  `tip` (ograja/pokončna) in `mere` kot objekt. Prej so se slabi
  segmenti ujeli šele v DXF izvozu ali pa so se tiho izrisali.
- Trije novi testi: velika začetnica tipa, neznan tip in slaba oblika
  segmentov.
- Preverjeno: polna suite **754 passed, 2 skipped** (preskok Tk se
  spreminja z okoljem); ruff čist; mypy 0.

## v1.5.5 — 2026-11-24 (popravek)

- **Predloga se normalizira pred validacijo.** `preveri_cfg` je
  `predloga: "POKONČNA"` ali `"Ograda"` primerjal strogo in zato
  pokončno predlogo validiral kot prečno: `razmak_stebrov: 0` je tako
  šel skozi, čeprav je `generiraj` isto predlogo izrisal kot pokončno.
  `zdruzi` in `preveri_cfg` zdaj uporabljata isto obliko (male črke,
  „ograda“ = „ograja“); neznana predloga ostane neznana in se zavrne.
- Dva nova testa: velika začetnica ne obide geometrije pokončne in
  `zdruzi` vrne kanonično ime predloge.
- Preverjeno: polna suite **750 passed, 3 skipped** (en preskok: Tk
  okolje); ruff čist; mypy 0.

## v1.5.4 — 2026-11-24 (popravek)

- **Večsegmentni projekt ne izgleda več tiho kot en segment.** PDF še
  vedno nariše samo glavni pogled (vsi segmenti so v DXF izvozu), a zdaj
  to zapiše v opozorila dokumenta in na stderr, namesto da bi uporabnik
  dobil na videz popoln enosegmentni PDF.
- CLI zastavici `--dxf` in `--potrosi-ostanke` sta prvič pokriti z
  resničnim podprocesom: DXF se prebere z `ezdxf`, odpis ostankov pa
  preveri novo zalogo in varnostno kopijo (`tests/test_cli_zastavice.py`).
- Preverjeno: polna suite **748 passed, 3 skipped** (en preskok: Tk okolje); ruff čist; mypy 0.

## v1.5.3 — 2026-11-24 (popravek)

- **Fuzzing validacije je odkril tri sesutja.** `preveri_cfg` mora vedno
  vrniti seznam napak, tudi pri nesmiselnih vrednostih:
  `razmak_stebrov: 0` pri pokončni (deljenje z nič), `vrata`/`prehodi`
  kot niz ali seznam nizov (`.get` na nizu) in `inf` v merah pokončne
  (preliv pri pretvorbi v celo število). Zdaj so vsi trije primeri
  napaka v seznamu, ne izjema.
- `vrata`/`prehodi` morata biti seznam slovarjev; `dolzina_palice` mora
  biti pozitivno končno število (prej je niz ali `inf` tiho obšel
  preverbo). Vse numerične mere zavrnejo `NaN` in neskončnost.
- **Neveljavna konfiguracija ni več sled sklada.** `preveri_cfg`,
  `zdruzi`, `nalozi_konf` in `generiraj` za seznam/niz vrnejo jasno
  `ValueError`; CLI pri neobstoječi ali neveljavni YAML datoteki izpiše
  „Napaka pri branju konfiguracije“ namesto `Traceback`.
- 20 novih testov: 18 v `tests/test_validacija_tipov.py` in 2 CLI
  (`tests/test_cli_napake.py`); fuzz čez vse mere in najvišje ključe
  ne najde več nobene izjeme.
- Preverjeno: polna suite **746 passed, 2 skipped**; ruff čist; mypy 0.


## v1.5.2 — 2026-11-24 (popravek)

- **Validacija ne sesuje več na napačnih tipih.** `preveri_cfg` je npr.
  pri `deska_sirina: "100"` (YAML niz) vrgel `TypeError` namesto seznama
  napak — CLI, GUI in API pa pričakujejo slednjega. Zdaj so vse numerične
  mere preverjene tipsko, izračuni pa se izvedejo le z veljavnimi
  vrednostmi; `mere` kot seznam in `vrzel` sta prav tako pokrita.
- **`generiraj({})` ne piše več tiho `BO-001.pdf` v trenutno mapo.**
  Manjkajoč `izhod` je jasna `ValueError`; test preveri, da v CWD ne
  nastane nobena datoteka.
- `zdruzi` sprejme `mere: null` iz YAML kot manjkajoče mere (prej
  `TypeError`); nepravilna oblika `mere` gre do validacije, ki jo javi.
- 21 novih hitrih testov (`tests/test_validacija_tipov.py`) za napačne
  tipe, `mere: null`, manjkajoč `izhod` in ohranitev veljavnih konfiguracij.
- Preverjeno: polna suite **726 passed, 2 skipped**; ruff čist; mypy 0.

## v1.5.1 — 2026-11-23 (popravek)

- **Različica v programu je bila 1.2**, čeprav je bila izdaja v1.5: GUI
  je ob preverjanju posodobitev ponujal »novo« v1.3–v1.5, ki je bila že
  nameščena. Zdaj 1.5.1, usklajeno na treh mestih (`posodobitev.VERZIJA`,
  `pyproject.toml`, najnovejša izdaja v tem dnevniku) — preverja
  `tests/test_build.py`.
- Testi neinteraktivnega zagona (issue #6, P2): kode 0/1/2, branje
  JSON in YAML, resničen CLI klic z `TEHNICNA_RISBA_HEADLESS=1` in
  preverjen PDF. Vstopna točka je izluščena v
  `vmesnik.zazeni_brez_zaslona` (izjeme še vedno ujame ista funkcija).
- Test, da `.spec` izloči OCR verigo (`rapidocr_onnxruntime`,
  `onnxruntime`, `transformers`, `torch`, `pandas`) in da OCR ni v
  `requirements.txt` — 312 MB regresija se ne more vrniti tiho.
- `build-zapisnik.json` odstranjen iz indeksa: `.gitignore` ga je že
  pokrival, a je ostal sleden in je vsaka gradnja umazala delovno drevo.
  Zdaj je res lokalni artefakt (datoteka na disku ostane).

## v1.5 — 2026-11-23 (build)

- `TehnicnaRisba.spec`: izločena OCR veriga (`rapidocr` → `onnxruntime` →
  `onnxruntime.transformers` → `transformers` → `torch`) in `pandas`.
  Izmerjeno: EXE **312 MB → 55,3 MB**, gradnja **21:39 → 2:40**, smoke
  nespremenjen (3 strani + terenski PDF).
- `build-zapisnik.json` je artefakt gradnje (v `.gitignore`).

## v1.4 — 2026-11-23

- GUI: *Orodja → Izvozi 3D model (STL/OBJ/GLB)…* (preveri mrežo, pove
  prostornino in opombe).
- Neobvezna OCR pot (`rapidocr-onnxruntime`, ni v `requirements.txt`, ni v
  EXE): QR ima prednost, OCR je nadomestna pot s pragom zaupanja 0,60 in
  obvezno potrditvijo.

## v1.3 — 2026-11-23 (zaklep)

Nadaljevanje v1.2 (oznake v1.0–v1.2 so iz predhodnih izdaj). Ta izdaja
doda katalog, statiko, foto sloj, 3D izvoz, QR oznake in ocenjevalnik
modelov ter zaklene kakovostna vrata.

### Risba in proizvodnja
- Prečna in pokončna predloga, montažni list, kosovnica, naročilo,
  predračun, terenski list, revizije.
- Vrata/prehodi: `enokrilna`, `dvokrilna`, `pasja`, `prehodna`, `drsna`,
  `dvokrilna_drsna`; `preklop` je obvezen vnos brez privzete vrednosti
  (geometrija se ne ugiba).
- Razrez z enotnim pravilom reza (kerf), ostanki, optimizacija po dolžinah.

### Katalog in statika
- `mechanical/`: resolver standardov (`iso` / `legacy_din` ločena),
  katalog 9 vrst pritrdil z javno provenienco, BOM, kontrola.
- `statika.py`: informativni pregled + statična priloga (PDF) —
  izrecno **ni** statični izračun.

### Foto sloj (predlogi, ne avtoriteta)
- Merjenje s kalibracijo, zaznava lamel/vijakov z zaupanjem.
- Dva neodvisna ocenjevalnika ritma + `nesoglasje` → status `OCENJENO`.
- Predlog mer v GUI: vsako mero uporabnik potrdi posebej.

### 3D
- `tridim/`: lastne mreže (brez cadqueryja/OCP — LGPL), izvoz
  **STL / OBJ / GLB**, kontrola zaprtosti in prostornina z izrekom o
  divergenci.
- Obe predlogi; prečna z lamelami, nosilci, okviri odprtin in stranskim
  krakom; ujemanje s shematskim predogledom je testirano.
- STEP je neobvezen most (`pip install cadquery`), namenoma ni v EXE.

### QR oznake
- `oznake.py`: format `TR1|projekt|šifra|višina|širina`; branje prek
  OpenCV brez modelov; neveljavna/tuja koda se zavrne z razlogom.
- GUI: branje in zapis oznake; vrednosti se uveljavijo šele po potrditvi.

### Kakovost in pravila
- 622 testov v hitri zanki, ~680 v polni; pokritost ~80 % (prag 65).
- ruff brez napak, mypy baseline **0** (ratchet).
- `THIRD_PARTY_NOTICES.md` + `scripts/preveri_licence.py` (CI preverja):
  PyInstaller odreže licenčna besedila, zato jih hranimo v repozitoriju.
- `benchmark/`: ocenjevanje kodiranja **brez AI-žirije** (skriti testi,
  canary, pass@k, Wilson, McNemar, bootstrap).

### Znane omejitve (namenoma)
- OCR fotografije ni vgrajen (licence uteži + velikost); QR je nadomestilo.
- OpenCV ni v EXE (`.spec` izključi `cv2`) → foto/QR le v Python različici.
- 3D je masni model: vijaki, globinski odmiki in pritrdila niso modelirani.
- Ročne mere na terenskem listu so anotacije, ne proizvodne mere.
