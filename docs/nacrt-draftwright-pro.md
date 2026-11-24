# Načrt »Draftwright PRO« — kaj od zunanjih 3D/AI projektov vzamemo in kaj ne

*Raziskava: 2026-11-24. Vsaka trditev ima vir ali meritev; nič ni bilo
nameščeno ali vgrajeno — dokument je odločitev, ne obljuba.*

## 1. Vprašanje

Predlog je bil: *fotografije → Grounded SAM 2 → kalibracija + COLMAP +
Open3D → CadQuery/FreeCAD → dokumentacija*. Ali to reši problem, ki ga
imamo, in po kakšni ceni?

Naš problem (izmerjeno v 1.5.16–1.5.18): ena fotografija z markerjem
**150–300 mm** da dolžino in višino z napako **0,03 % čelno** in **1–3 %
poševno**; brez markerja širine ni mogoče izračunati (homografija ima
8 prostostnih stopenj, 4 koti = 8 enačb → razmerje stranic ni določeno).
Ostane ena resnična napaka: **število stebrov** (26 ročno proti 23
zaznanim na `k1-izrez`, −1…−3 elementa).

## 2. Preverjena dejstva (GitHub API, 2026-11-24)

| Projekt | Zvezdice | Licenca | Zadnji push | Izvor |
|---|---|---|---|---|
| colmap/colmap | 13 285 | BSD-3 (API: NOASSERTION) | 2026-11-24 | 86 MB |
| IDEA-Research/Grounded-SAM-2 | 3 817 | Apache-2.0 | 2025-11-11 | 236 MB |
| isl-org/Open3D | 14 248 | MIT (API: NOASSERTION) | 2026-11-14 | 616 MB |
| CadQuery/cadquery | 6 166 | Apache-2.0 (jedro OCCT: LGPL-2.1 + izjema) | 2026-11-24 | 15 MB |
| FreeCAD/FreeCAD | 35 758 | LGPL-2.1 | 2026-11-24 | 3,0 GB |
| alicevision/Meshroom | 13 109 | MPL-2.0 | 2026-11-24 | 14 MB |
| jscad/OpenJSCAD.org | 3 283 | MIT | 2026-11-07 | 60 MB |
| maowiz/step2pdf | **3** | **brez licence** | 2026-07-15 | 2,6 MB |

Odtisi skladov so že izmerjeni v `docs/analiza-paketov.md`: open3d
~273 MB, cadquery + cadquery-ocp ~650–750 MB, torch ~580 MB, pyvista
~315 MB. Naš EXE je 52,7 MB.

## 3. Tri korekcije predpostavk

1. **»STEP je le poenostavljen približek.«** `tridim/step.py` piše pravi
   **BREP (AP214)** prek cadqueryja, ne triangulacije — poenostavljena je
   *geometrija* (kvadri, brez zaokrožitev), ne *format*. cadquery ni v
   EXE-ju namerno: `casadi` je **LGPL-3.0 brez izjeme**
   (`docs/odlocitev-3d-in-ocr.md`, varovano z AST-testom).
2. **»COLMAP izmeri prostor.«** SfM je **do merila nedoločen**; merilo
   prinese šele marker. COLMAP torej ne odpravi naše odvisnosti od
   markerja, doda tretjo dimenzijo in orto-foto.
3. **»AI najde merilo.«** Ne — zato brez markerja širine ne izračunamo
   in to v dokumentu tudi zapišemo.

## 4. Verdikt

| Projekt | Odločitev | Razlog |
|---|---|---|
| **Grounded SAM 2** | **spike (1–2 dni), zunaj EXE** | edini kandidat, ki rešuje napako štetja (baluster ≠ steber); Apache-2.0; cena: torch + uteži (~0,9–1 GB) — nikoli v izdelku, le neobvezna pot z maskami v JSON (vzorec: OCR/rapidocr) |
| **COLMAP** | **zunanje orodje, šele po F2** | za ravno ograjo ne doda mere; ponavljajoče se lamele so znana slepa pega ujemanja značk (tveganje, ne meritev) |
| **Open3D** | **ne** | 273 MB za ravnino; numpy zadošča; smiselno le v paru s COLMAP |
| **CadQuery** | **ostane neobvezni most** (že je) | 650–750 MB + LGPL-3.0 casadi; pravi CAD v izdelku je poslovna odločitev |
| **FreeCAD / TechDraw** | **ločen proces, ne nadomestilo** | LGPL-2.1 za ločen proces je sprejemljiv, a ~1 GB in zamenjava risalnega jedra (817 testov) je največji rizik |
| **Meshroom** | **ne** | GUI nad AliceVision; ne meri nič bolje kot COLMAP |
| **JSCAD** | **odloženo** | brskalniški 3D; spletni del 3D pregleda nima, EXE izvaža GLB |
| **step2pdf** | **ne prevzemaj** | **brez licence** = vse pravice pridržane; 3 zvezdice; cevni elementi |

## 5. Faze z vrati (vsaka faza je lahko zadnja)

| Faza | Delo | Vrata | Če pade |
|---|---|---|---|
| **F0 — narejeno** | marker + koti + soglasje več posnetkov | 0,03 % čelno; 1–3 % poševno; soglasje 2 posnetkov | — |
| **F1 — 2–3 dni** | več posnetkov brez AI: vsak posnetek poravnan, mere se morajo ujemati | razpršenost ≤ 2 % | ostane en posnetek + marker |
| **F2 — spike** | Grounded SAM 2 zunaj EXE: maske stebrov/lamel v JSON, štetje ostane naše | napaka štetja ±10 % na 5 tujih fotografijah, ≤ 30 s/sliko na CPU | AI pot se ne vgradi |
| **F3** | COLMAP + Open3D kot zunanje orodje za orto-foto | dolžina z markerjem ±2 % | orodje ostane eksperimentalno |
| **F4** | FreeCAD/CadQuery kot ločen CAD strežnik (FreeCADCmd) | ujemanje z našo risbo ±0,1 mm na 5 projektih | ostane `tridim/step.py` most |

## 6. Pravila, ki se v teh fazah ne smejo zlomiti

- EXE ostane brez copylefta in brez AI; nobena faza ne doda odvisnosti v
  `requirements.txt` ali `TehnicnaRisba.spec`.
- Vsaka mera nosi status (`izmerjeno` / `izracunano` / `ocenjeno` /
  `neznano`); AI ali 3D ne sme tiho povišati statusa.
- PFP ostane samostojen in determinističen: zunanja orodja komunicirajo
  **samo prek datotek** (maske, oblak, STEP).
- Brez omrežja v izdelku; uteži se ne prenašajo samodejno.

## 7. Česa v tem načrtu NI

- Ni vgrajevanja torch/onnxruntime/COLMAP v EXE — velikost 52,7 MB →
  >1 GB in kršitev lastnih licenčnih pravil.
- Ni zamenjave risalnega jedra (matplotlib + ezdxf) s FreeCADom.
- Ni obljube, da bo AI izboljšal mere: dokler F2 ne pokaže ±10 % pri
  štetju, AI ostane poskus.

## 8. Viri

- GitHub API: `https://api.github.com/repos/<owner>/<repo>` (24. 11. 2026);
- `docs/odlocitev-3d-in-ocr.md` (licence OCCT/cadquery, odločitev 3D);
- `docs/analiza-paketov.md` (izmerjeni odtisi skladov);
- `docs/izboljsave-zaznave-ograje.md` (meritve PFP, koraki 1–3c);
- <https://github.com/robertpezdirc12-design/tehnicna-risba> (stanje 1.5.17).
