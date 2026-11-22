# Načrt 7 — Revizijska tabela + diff povzetek

*Izboljšava 1 s prednostne lestvice (primerjava-risbe.md). Cilj: „en model —
ena revizija“ — profesionalni revizijski postopek (register + diff), prilagojen
našemu programu.*

## Stanje pred spremembo
- `risba.tabela_revizij` ŽE riše revizijsko tabelo (spodaj levo) iz
  `cfg["revizije"]` = `[[rev, datum, opis, izdelal], ...]`; naslovni blok kaže
  `REV. {zadnja oznaka}`. **GUI pa tega polja NI NIKOLI napolnil** — vedno le
  privzeta „A / Prva izdaja“.
- Ni diff povzetka: uporabnik ne ve, kaj se je med revizijama spremenilo
  (industrijska bolečina: „revision clouds spregledajo spremembe“ — Operon).

## Rešitev
1. **Nov modul `revizija.py`** (knjižnica, brez GUI):
   - `REVIZIJSKE_CRKE = "ABCDEFGHJKLMNPQRSTUVWXYZ"` — ISO 7200: I in O se ne
     uporabljata (zamenljiva z 1 in 0).
   - `naslednja_oznaka(obstojoce)` → prazno = „A“, sicer naslednja črka po
     zadnji (H→J, N→P); čez Z → AA, AB …
   - `snapshot(cfg)` → globoka kopija „oblikovalsko relevantnih“ polj
     (izločeni: revizije, rev_snapshot, izhod, datum, status_dokumenta —
     ti se spreminjajo brez spremembe izdelka).
   - `diff_povzetek(staro, novo)` → slovenski seznam sprememb
     („širina: 3000 → 3100“, „vrata: dodano enokrilna 900×1500 @200“),
     z zemljevidom imen polj; pri vratih primerja posamezne elemente.
   - `nova_revizija(cfg, opis, izdelal)` → doda `[oznaka, datum, opis, izdelal]`
     v `cfg["revizije"]`, osveži `cfg["rev_snapshot"]`; če je opis prazen, se
     uporabi diff povzetek.
2. **`jedro.preveri_cfg`**: oblika revizij se preveri (4-elementni vnosi).
3. **`vmesnik.py`**:
   - stanje `self.revizije` + `self.rev_snapshot` (v `_zberi_cfg`, iz
     `_nalozi_cfg_v_polja` — deli shranjevanje/odpiranje projekta samodejno);
   - meni Datoteka → „Nova revizija…“ (Ctrl+R): dialog pokaže **diff povzetek**
     proti zadnji reviziji + polje za opis (predizpolnjeno z diffom), potrdi
     zapis revizije.
4. **`risba.py`**: brez sprememb — tabela in `REV.` se napolnita iz cfg.

## Preverjanje
- testi: naslednja oznaka (preskok I/O, AA), diff (spremenjeno/nespremenjeno/
  vrata), krožni tok revizij, validacija, PDF vsebuje vrstice revizij + REV. B;
- realni GUI: meni, dialog z diffom, revizija vidna na izrisanem PDF (screenshot).

## Zavestno izven obsega
- status ZA POTRDITEV → IZVEDENO tok (izboljšava 5, ločeno);
- revizijski oblaki na risbi („clouds spregledajo spremembe“ — diff je zanesljivejši);
- transmittal/registro izdaj (če bo potreba, ločen načrt).