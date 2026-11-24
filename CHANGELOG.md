# Zgodovina sprememb

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
