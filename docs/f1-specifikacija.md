# F1 — Katalog resolver + BOM + validate (specifikacija logike)

**Status:** formalno začeto (zaklenjeno ob B1/B13, licenčni gate za podatke odprt)  
**Načelo:** aditivno, brez posega v obstoječo ograjno kodo. Logika je licenčno nevtralna; katalogski podatki se vgrajujejo le z javno provenanco.

## 1. Resolver — pogodba

- **Vhod:** `(designation, standard, profil)` — npr. `("M10", "ISO 4032", "iso")` ali `("M10x35", "ISO 4017", "iso")`.
- **Izhod:** dimenzije + provenanca (vir, datum dostopa/preverjanja, opombe).
- **Napake (brez ugibanja):**
  - neznan `profil` → napaka
  - neznan `standard` v danem profilu → napaka
  - manjkajoča velikost/varianta (`designation`/`length`) → napaka
- **Ločitev profilov:** `iso` in `legacy_din` sta strogo ločena; resolver ne sme vračati vrednosti iz napačnega profila.

## 2. Ciljne katalogske vrstice (vgradnja s provenanco)

Vrednosti preverjene iz javnih virov v predhodnem koraku; formalni zapis: `mechanical/catalog/*.yaml`.

| Profil | Standard | Velikost | Ključne dimenzije | Provenanca (javni vir) |
|---|---|---|---|---|
| `iso` | ISO 4032 | M10 | `s=16` (15,73–16,00); `m=8,40` (8,04–8,40); `e≥17,77`; `P=1,5` | wermac tabela ISO 4032 |
| `iso` | ISO 4017 | M10×35 | `s=16`; `k=6,4` (A 6,22–6,58); `e≥17,77`; `P=1,5`; polni navoj; `a≤4,5`; `l=35` | Fuller / fasteners.eu ISO 4017 |
| `legacy_din` | DIN 934 | M10 | `s=17`; `m=8` | mercura / maedler DIN 934 |
| `legacy_din` | DIN 933 | M10×35 | `s=17`; `k=6,4` | fabory DIN 933 M10×35 |

**Provenanca (obvezno polje):** za vsako vrstico `source` (ime/URL vira, kot javno dostopen), `accessed` (datum preverjanja/zapisa, npr. 2026-04-11), in po potrebi `note`. Vgrajujejo se le vrstice z jasno javno provenanco in dopustnimi pogoji uporabe.

## 3. BOM — pravila izpeljave

- **Vir:** `AssemblyDef.items` + `PartDef`.
- **`find_no`:** na unikatni del/pozicijo po dogovoru sestava (v primeru vijacnik 1–6).
- **Količina:** `qty` iz instance; agregacija po enakem `part_ref` kjer je smiselno (sicer po instanci/poziciji glede na konvencijo risbe).
- **Vrstni red:** izdelani (`custom`) → standardni.
- **Stolpci:** poz. / kos / naziv / material / standard / opomba (+ `masa` samo če znana).
- **`incomplete` (npr. 1–2):** vrstica v BOM obstaja (naziv/material/kos znani), geometrija/detajl ne; označeno kot placeholder/incomplete.
- **Primer (vijacnik):** 6 vrstic, kot v `mechanical/examples/vijacnik.yaml`.

## 4. Validate — pravila

- **Popolnost:** preveri `status` delov (`complete`/`incomplete`/`placeholder`).
- **Reference:** skladnost `part_ref`, `items`, `bom_ref`, `standard_ref`.
- **Standardi:** veljavnost preko resolverja (uspešna razrešitev v izbranem profilu) ali eksplicitna napaka.
- **Enote:** konsistentne (mm) in prisotne kjer zahtevano.
- **Manjkajoče mere/obvezna polja:** napaka ali opozorilo po pravilih gatinga.
- **Gating matrika:**
  - `complete` → detajl dovoljen
  - `incomplete` → detajl blokiran; sestav le z eksplicitnim placeholder
  - `placeholder` → vidno označen
- **Rezultat:** poročilo v **JSON** + **človeško berljiva** oblika.
- **Za poz. 1–2 (vijacnik):** poročilo našteje manjkajoča polja (gabariti, izvrtine, navojni sedež, rebra, tolerance, datum/csys za 1; dolžine/premeri/navoj/konec/tolerance/datum/csys za 2) in blokira detajl.

## 5. Izhodni kriterij F1

- Resolver vrne citirane vrednosti za ciljne vrstice (test proti tabelam/provenanci).
- BOM iz primera vrne 6 vrstic z ustreznim vrstnim redom in oznakami.
- `validate` poroča manjkajoča polja za poz. 1–2 in spoštuje gating.
- Brez ograjnega importa / brez posega v obstoječo ograjno kodo.