# Odločitev: 3D sloj in OCR (brez copylefta v izdelku)

*Datum odločitve: 2026-11-23. Podlaga: javni licenčni viri (spodaj) +
izmerjeno vedenje knjižnic v tem okolju. Odločitev ni estetska — vsaka
trditev ima vir ali meritev.*

## 1. Vprašanje

Projekt je MIT in se dostavlja kot samostojna Windows `.exe` datoteka
(PyInstaller). Za 3D in OCR sta bili predvideni dve poti:

| Pot | Koda | Dejanska odvisnost |
|---|---|---|
| 3D (CAD) | cadquery (Apache-2.0) | `cadquery-ocp` (OpenCASCADE, LGPL-2.1-only + izjema), `casadi` (LGPL-3.0), `nlopt` (LGPL-2.1+ / MIT), `numba`, `scipy` |
| OCR | PaddleOCR (Apache-2.0) ali TrOCR | uteži modelov (10–500 MB) z lastno licenco |

## 2. Ugotovljena dejstva

**OpenCASCADE (OCCT).** Od 6.7.0 je pod LGPL-2.1-only z dodatno izjemo
(`OCCT-exception-1.0`). Uradni FAQ pravi, da lahko izdelek distribuiraš
tudi lastniško, a moraš izpolniti pogoje LGPL, §6
(<https://web.archive.org/web/20210629131755/https:/dev.opencascade.org/resources/faq>,
obiskano 2026-11-23). SPDX potrjuje, da izjema velja za različice 6.7.0
in novejše (<https://spdx.org/licenses/OCCT-exception-1.0.html>).

**cadquery.** Koda je Apache-2.0, a `setup.py` zahteva `cadquery-ocp`,
`casadi`, `nlopt` in `numba`
(<https://github.com/CadQuery/cadquery/blob/master/setup.py>, PyPI
`cadquery 2.8.0`). Apache-2.0 koda torej ne pomeni Apache-2.0 izdelka.

**PyInstaller in LGPL.** PyInstaller sam ne spreminja licenc, a
„executable … can be shipped with whatever license you want, **as long
as it complies with the licenses of your dependencies**“
(<https://pyinstaller.org/en/latest/license.html>). LGPL zahteva
možnost zamenjave knjižnice; če uporabnik dobi izvorno kodo in navodila
za ponovno gradnjo, je to izvedljivo, a je trajna obveznost
(<https://velovix.github.io/post/lgpl-gpl-license-compliance-with-pyinstaller/>).
Dodatno: PyInstaller rad **odreže licenčna besedila** vgrajenih knjižnic
(<https://github.com/pyinstaller/pyinstaller/issues/5666>) — zato ima
projekt `THIRD_PARTY_NOTICES.md`.

**PaddleOCR.** Koda je Apache-2.0; neodvisna analiza je na Hugging Face
preverila 16 modelnih kartic in vse vrnile `apache-2.0`, a iste karte
niso bile preverjene na ModelScope/Baidu in avtorji opozarjajo, da je
treba licenco vsake uteži pogledati posebej
(<https://paddleocr.dev/license>, obiskano 2026-11-23).

**TrOCR.** Modelna kartica `microsoft/trocr-base-printed` **nima
navedene licence**; vzdrževalci navajajo, da je model del projekta
`microsoft/unilm` (MIT), a to na kartici ni zapisano
(<https://huggingface.co/microsoft/trocr-base-printed/discussions/15>,
obiskano 2026-11-23). Za distribucijo uteži je to pravno negotovo.

**OpenCV.** Od 4.5.0 je Apache-2.0 (prej BSD-3)
(<https://opencv.org/license/>); modul ArUco je mešanica BSD-3/Apache
(<https://packages.fedoraproject.org/pkgs/opencv/opencv-aruco/>). OpenCV
je v projektu že prisoten za foto sloj, zato QR branje ne doda nobene
nove odvisnosti.

## 3. Odločitev za 3D

**Ne vgrajujemo cadqueryja/OCP.** Namesto tega:

1. **Lasten mrežni sloj** (`tridim/`): prizme, kontrola zaprtosti,
   prostornina z izrekom o divergenci. Brez ene same nove odvisnosti.
2. **Izvoz STL / OBJ / GLB** z lastnimi pisalniki (`tridim/izvoz.py`).
   Format GLB je preverjen v testih (magija, različica, dolžine blokov,
   dostopi).
3. **Izvoz pokriva obe predlogi** (`model_ograde`): pokončno in prečno,
   slednja z lamelami, nosilci, okviri odprtin in stranskim krakom;
   geometrija se ujema s shematskim predogledom (`tridimenzionalno.py`) —
   to preverjata testska para.
4. **STEP ostane neobvezen most** (`tridim/step.py`): če cadquery ni
   nameščen, funkcija pove, kaj manjka in zakaj ni vgrajen. Ne izdelamo
   lažnega STEP iz mreže — triangulirana ploskev ni CAD model.

Test `tests/test_tridim.py::test_paket_ne_uvaža_copyleft_knjižnic`
preveri z AST, da se copyleft moduli uvažajo **samo** v `step.py`, in
`test_uvoz_paketa_ne_nalozi_cadqueryja` da v novem procesu potrdi, da
uvoz paketa ne naloži `cadquery`/`OCP`.

**Kdaj bi bilo drugače:** če bi se projekt relicenciral na
GPL-združljivo licenco **ali** če bi izdelek priložil LGPL knjižnice kot
ločene DLL-je z izvorno kodo in navodili za ponovno gradnjo. Oboje je
poslovna odločitev, ne tehnična; do takrat velja: copyleft ne gre v EXE.

## 4. Odločitev za OCR

**OCR fotografije ne vgrajujemo.** Namesto tega **QR oznake**
(`oznake.py`):

- kodo natisnemo sami, zato vsebina ni ugibanje; preverjanje je strogo
  (`TR1|projekt|šifra|višina|širina`), neveljavna koda se zavrne z
  razlogom, tuja QR koda se ne sprejme tiho;
- branje uporablja OpenCV (že vgrajen, Apache-2.0), brez modelov in brez
  prenosa uteži;
- izmerjeno: koda se prebere pri 25° obratu, šumu σ = 20, zameglitvi 5×5,
  pomanjšavi na 200 px in perspektivi (testi v `tests/test_oznake.py`);
- v GUI se vrednosti **ne** uveljavijo same: uporabnik potrdi
  (`_oznaka_preberi`).

**Kdaj bi OCR dodali:** ko bi bile izpolnjene vse tri zahteve hkrati —
(a) licenca uteži jasna in zapisana na kartici, (b) velikost in
delovanje brez GPU sprejemljiva za EXE, (c) merjena natančnost na
resničnih ročnih napisih boljša od QR poti. OCR bi bil **dodatek** za
primere brez oznake, ne nadomestilo zanjo; vmesnik bi moral vrniti isto
strukturo (`Oznaka`), da se potrditveni tok ne bi podvajal.

## 5. Posledice

- EXE ostane brez copylefta; nobena nova odvisnost ni bila dodana v
  `requirements.txt`.
- `THIRD_PARTY_NOTICES.md` našteje vgrajene knjižnice in njihove
  licence (OpenCV je Apache-2.0 in zahteva obvestilo).
- Če kdo želi 3D modele za CAD, jih dobi prek lastne namestitve
  cadqueryja (`pip install cadquery`), kar ni naša distribucija.
