# Odločitve B1/B13 — zaklep (licenca, distribucija, uskladitev)

**Status:** zaklenjeno  
**Datum:** 2026-04-11  
**Podlaga:** potrditev lastnika repozitorija za profesionalno izbiro licence (MIT).

## B1 — Licenca

- **Izbrana licenca:** MIT (SPDX: `MIT`).
- **Utemeljitev:** repozitorij je javen, javno je distribuiran EXE, uporabniški vmesnik/stran sta že navajala odprtokodnost, odvisnosti so permisivne in združljive (ezdxf MIT, PyYAML MIT, numpy BSD-3-Clause, matplotlib permisivna/PSF-slog). MIT je najprimernejša permisivna izbira za uskladitev pravnega stanja z dejansko javno distribucijo.
- **Uveljavitev:** dodana kanonična datoteka `LICENSE` (MIT, copyright 2026 r.pezdirc).
- **Pravno stanje pred tem:** brez datoteke `LICENSE` je veljalo privzeto "vse pravice pridržane"; navedba odprtokodnosti v `index.html` ni bila pravno podprta. S tem zaklepom je stanje usklajeno.

## B13 — Uskladitev artefaktov in distribucijska drža

- **`README.md`:** usklajen na MIT (odstranjeno "Za notranjo uporabo", dodan sklic na `LICENSE`).
- **`index.html`:** usklajen na MIT (eksplicitna navedba licence v nogi, odstranjena generična/zavajajoča povezava brez vira licence).
- **Javni EXE:** distribucija ostaja skladna z MIT (permisivna licenca ne prepoveduje distribucije binarnih artefaktov ob spoštovanju pogojev licence).
- **Ograjna koda:** v tem koraku ni bil izveden noben poseg v obstoječo ograjno kodo (`risba.py`, `vmesnik.py`, `razrez.py`, `merjenje.py`, `api/` ipd.); spremembe so aditivne ali uskladitvene (licenca/dokumentacija/cenik-primer).

## Poslovno zaupni podatki (obvezno, neodvisno od licence)

- **`cene.yaml`:** realne cene so odstranjene iz javnega repozitorija in zamenjane z zgledi/placeholder vrednostmi (`0.00`, označeno kot PRIMER). Licenca ureja ponovno uporabo kode, ne zaupnosti poslovnih podatkov; realen cenik ne sodi v javni repo pri nobeni licenci.

## Katalogski podatki in provenanca (B4)

- **Načelo:** vgrajujejo se le podatki z jasno javno provenanco (javni proizvajalčevi/standardni viri), pri čemer vsaka vrstica nosi vir in datum dostopa/preverjanja. Viri, katerih pogoji ne dovoljujejo ponovne uporabe, se ne vgrajujejo.
- **Ciljne referenčne vrstice (F1):** ISO 4032 M10, ISO 4017 M10×35 (profil `iso`) ter DIN 934 M10, DIN 933 M10×35 (profil `legacy_din`) — dimenzije in javni viri so navedeni v specifikaciji F1 (`docs/f1-specifikacija.md`) in ustreznih katalogskih datotekah pod `mechanical/catalog/` (z provenanco).
- **Ločitev profilov:** `iso` in `legacy_din` sta strogo ločena; resolver ne meša profilov.

## Gate

- Licenčni gate za B4 (vgrajevanje podatkovnih datotek s provenanco), B13 (uskladitev) in distribucijsko držo je **odprt/zaklenjen z MIT**.
- F0 (shema/konvencije) in F1 (logika resolver/BOM/validate) sta licenčno nevtralna in se formalno začneta s tem zaklepom (specifikaciji v `docs/`, primeri/podatki v `mechanical/`), brez posega v ograjno kodo.
