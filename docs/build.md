# Windows build in izdaja (issue #6, §9)

## 1. Namen in obseg

Enostopenjski (onefile) samostojni `TehnicnaRisba.exe` za Windows iz
`vmesnik.py` (GUI) + `risba.py`, `razrez.py`, `vrata.py`, `dxf_izvoz.py`,
`merjenje.py`. Dokument opisuje **ponovljiv postopek gradnje**, smoke
preizkus, kontrolne vsote in pravila izdaje.

## 2. Predpostavke

- Windows 10/11, Python 3.11 (preverjeno: 3.11.9)
- PyInstaller 6.22.3 (+ pyinstaller-hooks-contrib 2026.10)
- odvisnosti iz `requirements.txt` (vključno **Pillow** — `merjenje.py`
  ga uvozi nepogojno) + `pypdf` za preverjanje artefaktov
- popoln freeze okolja gradnje: `requirements-build.txt`
- UPX **ni** potreben in ni nameščen (`TehnicnaRisba.spec` ima
  `upx=False` — konsistenten izid brez odvisnosti od zunanjega orodja)

## 3. Postopek gradnje

```bash
python -m pip install -r requirements.txt pypdf pyinstaller
python build_windows.py --smoke
```

`build_windows.py` po vrsti: preveri različice → zabeleži git stanje
(commit, veja, dirty) → `PyInstaller --clean --noconfirm TehnicnaRisba.spec`
→ SHA-256 in velikost EXE → funkcionalni smoke → zapiše
`build-zapisnik.json`. **Vsak korak je v zapisniku** — če karkoli pade,
se to vidi (brez tihih uspehov).

## 4. Ponovljivost in njene meje

PyInstaller **ne** zagotavlja bit-identičnega izida (časovni žigi v PE,
mtime vhodnih datotek). Definicija ponovljivosti tega projekta:

> **Isti commit + iste različice orodja → delujoč EXE z enako
> funkcionalnostjo**, dokazano s smoke preizkusom in strukturnimi
> kontrolami artefaktov; SHA-256 se vodi za sledljivost, ne za
> pričakovano enakost med gradnjami.

Hash PDF-ja se med gradnjami prav tako razlikuje (vgrajeni časovni
žigi/producer) — zato smoke preverja **strukturne lastnosti** (število
strani, prisotnost/odsotnost posameznih strani), ne hashov dokumentov.

## 5. Neinteraktivni smoke test

Program podpira preklop brez GUI (dodano v `vmesnik.py`):

```bash
TehnicnaRisba.exe --brez-zaslona <config.json|config.yaml>
TEHNICNA_RISBA_HEADLESS=1 TehnicnaRisba.exe <config.yaml>
```

Izvede generiranje PDF in konča z izhodno kodo (0 = uspeh, 1 = napaka —
napaka se izpiše v stderr; obdelana je z `try/except`, da windowed EXE
ne odpre modalnega dialoga). Smoke v `build_windows.py` preizkusi **oba**
načina in preveri: izhodno kodo, prisotnost PDF, **3 strani** (risba +
montažni list + nalepke; brez `cene` ni predračuna) s pypdf. Podatki
(ostanki ipd.) se v smoke pišejo v začasno mapo (`TEHNICNA_RISBA_DATA`),
ne v uporabniško.

## 6. `build-zapisnik.json` (kontrolne vsote)

Shema (verzija 1): `zapisnik_verzija`, `zacetek` (UTC), `trajanje_s`,
`razlicice` (python, pyinstaller, platform, upx), `git` (commit, veja,
dirty), `spec_sha256`, `ukaz`, `build` (exe, `velikost_b`, `sha256`),
`smoke` (pdf, strani, velikost_b, nacini).

Preverjanje EXE po prenosu:

```bash
# Windows
certutil -hashfile TehnicnaRisba.exe SHA256
# Linux/mac
sha256sum TehnicnaRisba.exe
```

Hash primerjaj z `build-zapisnik.json` (ali `.sha256` ob assetu).
Ujemanje = nespremenjen prenos.

## 7. Sledljivost in pravila izdaje

Veriga: **git commit → build-zapisnik.json (commit + hash) → GitHub tag/release**.

- obstoječe izdaje (`v1.0`, `v1.1`) nimajo zapisanega commit SHA in so
  nastale pred tem postopkom — nove izdaje to popravljajo;
- nova izdaja = **nov tag** (npr. `v1.2`), objavljena **kot DRAFT** in
  šele po potrditvi rešitve (§9);
- **nikoli** ne prepisuj assetov obstoječega taga (GitHub release nima
  immutable zaščite) — napako popravi z novim patch release;
- priporočeno: CI (GitHub Actions) za build zunaj lokalnega računalnika.

## 8. Podatkovne datoteke ob zagonu

- `zadnje_nastavitve.yaml` se piše **poleg EXE** — v zaščiteni mapi
  (npr. `Program Files`) to lahko pade z `PermissionError`;
- `ostanki.yaml`: legacy datoteka iz delovne mape se samodejno
  preseli v `%APPDATA%\TehnicnaRisba\`; `TEHNICNA_RISBA_DATA` preglasi
  podatkovno mapo (uporabno za testiranje);
- zunanjih podatkovnih datotek EXE **ne potrebuje** (privzete vrednosti
  so vgrajene); `cene.yaml` uporablja le spletni `api/` (Vercel), ne EXE;
- **znana omejitev:** `migracija.py` (shema v2) ni vključena v EXE —
  večsegmentne projekte pripravimo v repo (`python migracija.py`), EXE
  bere že migrirano konfiguracijo.

## 9. Znane pasti

- nepodpisan EXE → SmartScreen/AV opozorila so pričakovana (podpis
  kode = ločena odločitev);
- prvi zagon onefile EXE je počasnejši (razpakiranje v začasno mapo);
- `console=False` → izpisi `print()` v windowed EXE niso vidni; smoke se
  zanaša na izhodno kodo + artefakte, ne na stdout.

## 10. Kontrolni seznam za izdajo

1. [ ] vsi testi zeleni (`python -m pytest tests/`)
2. [ ] `python build_windows.py --smoke` uspe (zapisnik zapisan)
3. [ ] `git.commit` v zapisniku ustreza commitu, ki se objavlja (dirty: false)
4. [ ] SHA-256 EXE = hash v zapisniku; `.sha256` datoteka ob assetu
5. [ ] ročni GUI preizkus: nova ograja, vrata, PDF, CSV, DXF (Glej
       kontrolni seznam v `docs/issue-6-revizija.md`)
6. [ ] release objavljen **kot draft**, šele po uporabnikovi potrditvi