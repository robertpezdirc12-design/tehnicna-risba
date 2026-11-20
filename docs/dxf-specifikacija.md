# DXF izvoz (CAD/CNC) — specifikacija

Modul: `dxf_izvoz.py` (ezdxf 1.4.5, MIT). Izvoz: `python risba.py projekt.yaml --dxf`,
gumb `IZVOZI DXF` v vmesniku ali `dxf_izvoz.izvozi_dxf(cfg, pot)`.

## Format in enote

- DXF **R2010 (AC1024)** — bere AutoCAD ≥ 2010, LibreCAD, Fusion 360, FreeCAD, CAM uvozniki.
- Enote: **milimetri**, `$INSUNITS = 4`, `$MEASUREMENT = 1`; vse koordinate so
  **realne mm 1:1** (3000 mm ograja = 3000 enot), NE papirne mm iz PDF-ja.
- Slovenski znaki (č/š/ž) so zapisani v UTF-8 (R2010).

## Shema plasti (fiksna — vse vedno ustvarjene)

| Plast | Barva | Vsebina | Rez/vrtanje |
|---|---|---|---|
| `OUTLINE` | 7 | zaprte konture kosov (lamele, deske, krila vrat) | **DA** |
| `POSTS` | 5 | stebri/nosilci, profili, okvir vrat | **DA** |
| `HOLES` | 1 | luknje (`CIRCLE`, realni premer) | **DA** (vrtanje) |
| `HARDWARE` | 2 | okovje (tečaji, ročaji, ključavnice) | NE |
| `FILL` | 8 | šrafure, prečke, diagonale | NE |
| `DIMENSIONS` | 3 | kote (statične črte + puščice + tekst) | NE |
| `CENTERLINES` | 6 | osi | NE |
| `TEXT` | 7 | oznake, opome | NE |
| `FRAME` | 8 | okvir lista + naslovni blok (papirni layout A3) | NE |

**Rez/vrtanje SAMO iz plasti `OUTLINE`, `POSTS`, `HOLES`.**

## Pravila kontur (CNC)

- vsak kos = **ena zaprta `LWPOLYLINE`** (`closed=True`), brez ponovljene prve točke
  (dvojna točka = dvojni rez v nekaterih CAM-ih), ≥ 3 točke, brez ničelnih segmentov;
- luknje = `CIRCLE` na `HOLES` (realni premer) ali `HARDWARE` (informativno);
- kote so **statične** (LINE + SOLID puščice + MTEXT) — CAM-uvozniki DIMENSION
  entitet pogosto ignorirajo; kote so izpeljane iz konfiguracije, asociativnost
  nima vrednosti;
- brez podvojenih entitet (kontrola v `preveri_dxf`).

## Več segmentov

`cfg["segmenti"]` (shema v2): segmenti so postavljeni zaporedno z razmakom
`MED_RAZMAK = 1000 mm`, vsak s svojo oznako na `TEXT` in lastnimi kotami.
Kot (`kot`) je del podatkovnega modela; v1 izriše segmente v skupni ravnini
(vogali v tlorisu so načrtovana razširitev).

## Preverjanje kakovosti (`preveri_dxf`)

`izvozi_dxf` po zapisu vedno preveri: `doc.audit()` brez napak, round-trip z
`ezdxf.readfile`, `$INSUNITS == 4`, prisotnost vseh 9 plasti, zaprtost kontur,
odsotnost podvojenih entitet, neprazno rezalno geometrijo. Neveljaven DXF se
ne vrne kot uspešen.

## OMEJITVE (zapisane tudi v samem DXF, v opombah)

- DXF **NE vsebuje** G-code ali toolpath poti orodja;
- konture so **nominalne mere** — brez kompenzacije orodja/kerfa (kerf vpliva
  le na rezalni načrt v PDF);
- brez nestinga, vpenjanja in CAM priprave; tolerance: ISO 2768-m splošno;
- 2D orisi — debeline kosov so v kosovnici, ne v geometriji;
- **risba NI statični izračun** — nosilnost/sidranje preveri usposobljen
  strokovnjak (enako kot PDF);
- kote so posnetek konfiguracije — po spremembi je potreben nov izvoz.