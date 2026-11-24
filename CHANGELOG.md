# Zgodovina sprememb

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
