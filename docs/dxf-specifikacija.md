# DXF izvoz (CAD/CNC) — specifikacija

Modul: `dxf_izvoz.py` (ezdxf 1.4.5, MIT). Izvoz: `python risba.py projekt.yaml --dxf`,
gumb `IZVOZI DXF` v vmesniku ali `dxf_izvoz.izvozi_dxf(cfg, pot)`.

## Format in enote

- DXF **R2010 (AC1024)** — bere AutoCAD ≥ 2010, LibreCAD, Fusion 360, FreeCAD, CAM uvozniki.
- Enote: **milimetri**, `$INSUNITS = 4`, `$MEASUREMENT = 1`; vse koordinate so
  **realne mm 1:1** (3000 mm ograja = 3000 enot), NE papirne mm iz PDF-ja.
- Slovenski znaki (č/š/ž) so zapisani v UTF-8 (R2010).

## Shema plasti (fiksna — vse vedno ustvarjene; ISO 13567 struktura)

Od Plan 2 (2026) so sloji po strukturi ISO 13567 `discipline-major-minor`.
Notranja koda še uporablja stara imena (prevedejo se ob zapisu —
`dxf_izvoz.LEGACY_SLOJI`).

| Plast (ISO) | Barva | Vsebina | Rez/vrtanje |
|---|---|---|---|
| `M-ELEM-CONT` | 7 | zaprte konture kosov (lamele, deske, krila vrat) | **DA** |
| `M-STEB-CONT` | 5 | stebri/nosilci, profili, okvir vrat | **DA** |
| `M-ODPR-CONT` | 1 | luknje (`CIRCLE`, realni premer) | **DA** (vrtanje) |
| `M-OKOV-PRIT` | 2 | okovje (tečaji, ročaji, ključavnice) | NE |
| `M-POLN-SRAF` | 8 | šrafure, prečke, diagonale | NE |
| `M-ANNO-DIMS` | 3 | kote (statične črte + puščice + tekst) | NE |
| `M-ANNO-CLIN` | 6 | osi | NE |
| `M-ANNO-TEXT` | 7 | oznake, opome | NE |
| `M-ANNO-FRAM` | 8 | okvir lista + naslovni blok (papirni layout A3) | NE |

**Rez/vrtanje SAMO iz plasti `M-ELEM-CONT`, `M-STEB-CONT`, `M-ODPR-CONT`.**

### Prehodna tabela (stara -> nova imena)

Za CAM skripte, ki še berejo stara imena:

| staro | novo |
|---|---|
| `OUTLINE` | `M-ELEM-CONT` |
| `POSTS` | `M-STEB-CONT` |
| `HOLES` | `M-ODPR-CONT` |
| `HARDWARE` | `M-OKOV-PRIT` |
| `FILL` | `M-POLN-SRAF` |
| `DIMENSIONS` | `M-ANNO-DIMS` |
| `CENTERLINES` | `M-ANNO-CLIN` |
| `TEXT` | `M-ANNO-TEXT` |
| `FRAME` | `M-ANNO-FRAM` |

Python: `dxf_izvoz.LEGACY_SLOJI` (slovar) in `dxf_izvoz._sloj(ime)`
(prevod; sprejme obe obliki, ISO vrne nespremenjenega).

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