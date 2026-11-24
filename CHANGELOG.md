# Zgodovina sprememb

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
