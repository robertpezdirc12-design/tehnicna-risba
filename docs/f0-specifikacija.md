# F0 — Specifikacija sheme in konvencij (brez kode)

**Status:** formalno začeto (zaklenjeno ob B1/B13)  
**Načelo:** aditivno, brez posega v obstoječo ograjno kodo. Shema in konvencije so licenčno nevtralne.

## 1. Entitete in polja (opisno)

### DocumentSet
- `številka`, `revizija`
- `privzeti_format` (npr. A4 privzeto; per-list možno preglasiti)
- `standard` (ISO, primarni)
- `profil_kataloga` (`iso` | `legacy_din`)
- `projekcija` (prvi kot)

### PartDef
- `id`, `naziv`, `part_number`, `revizija`
- `source` (`custom` | `standard`)
- `material`, `masa` (opcijsko), `finish`, `notes`
- `status` (`complete` | `incomplete` | `placeholder`)
- `geometry` (za `custom`) ali `standard_ref` (za `standard`)
- `drawing_hints`

### GeometryDef (custom)
- `tip` (`parametric_profile` | `primitive_set` | `feature_list`)
- `parametri` (ime → vrednost + enota + toleranca)
- `značilke` (npr. valj, izvrtina, navoj, hex, posnet, radij)
- `datum` / `csys` (koordinatni sistem)

### StandardRef
- `standard`, `designation`
- `length` (če velja)
- `properties` (npr. `material_grade`, `coating`)
- `catalog_key`

### AssemblyDef
- `id`, `naziv`
- `items[]`: `instance_id`, `part_ref`, `quantity`, `transform`, `find_no`, `overrides`
- `joints` (kasneje)
- `exploded_state` (opcijsko)

### DrawingSheet
- `id`, `title`, `sheet_no`, `sheet_total`, `scale`, `format`, `projection`
- `views[]`
- `annotations` (balloons / dimensions / leaders / notes)
- `tables` (bom_ref / revisions / title_block)
- `export_targets`

### BOM (izpeljan)
- `source_assembly_ref`
- `rows[]`: `find_no`, `part_ref`, `qty`, `name`, `material`, `standard`, `note`, `mass`

## 2. Konvencije

- Enote: **mm**.
- Navoj: kot **oznaka-string** (npr. `M10`, `M10×35`).
- Tolerance: **ISO 286** ali ±.
- Merila: **ISO 5455**.
- Glava risbe: **ISO 7200** (180 mm).
- Okvir/formati: **ISO 5457**.
- Prikaz navoja: **ISO 6410-3**.
- Kotiranje: **ISO 129-1**.
- Vrste črt: **ISO 128**.
- Projekcija: **prvi kot** (privzeto).
- Standard: **ISO primarni**; opcijski `legacy_din` profil (ekspliciten, nikoli pomešan z `iso`).
- Format: **A4 privzeto**, možno per-list.

## 3. Gating (popolnost)

| Status | Pomen | Dovoljenja |
|---|---|---|
| `complete` | geometrija/definicija dovolj določena | detajl dovoljen |
| `incomplete` | manjkajo ključne mere/definicije | detajl **blokiran**; sestav le z eksplicitnim `placeholder` |
| `placeholder` | nadomestna/nezadostna definicija | vidno označen; ne nadomešča manjkajoče geometrije |

## 4. `vijacnik.yaml` — ciljna specifikacija (primer)

| Poz. | Del | Znano | Status |
|---|---|---|---|
| 1 | Ogrodje | naziv, SIVI LIT, 1 kos | `incomplete` |
| 2 | Vreteno | naziv, C45, 1 kos | `incomplete` |
| 3 | Ročica | Ø12, L100, R6, C45 | `complete` |
| 4 | Podložka | Ø18/Ø10,5×5, C45 | `complete` (custom, ne ISO 7089) |
| 5 | Matica | ISO 4032 M10 | `complete` ob razrešitvi (resolver) |
| 6 | Vijak | ISO 4017 M10×35 | `complete` ob razrešitvi (resolver) |

- **Sestav:** 6 instanc, `find_no` 1–6; transformacije 1–2 nedoločene.
- **List 1/2:** sestav, izometrija, M1:2, BOM (1–2 placeholder).
- **List 2/2:** detajli 3–6, M1:1 (1–2 ne).
- **Odprto:** konvencija dolžine ročice `L100` (potrebna potrditev/razjasnitev).
- **Manjkajoča polja (1, 2):** gabariti, izvrtine, navojni sedež, rebra, ključne dolžine/premeri, tolerance, datum/csys — detajl blokiran do dopolnitve.

Formalni primer: `mechanical/examples/vijacnik.yaml`.

## 5. Izhodni kriterij F0

- Shema definira vsa polja/tipe/enote.
- `vijacnik.yaml` specifikacija s poz. 3–6 `complete` in 1–2 `incomplete` + seznam manjkajočih polj.
- ISO konvencije zapisane.
- Profil kataloga ekspliciten (`iso` / `legacy_din`).
- Brez posega v ograjno kodo.