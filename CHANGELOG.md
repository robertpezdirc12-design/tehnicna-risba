# Zgodovina sprememb

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
