# Plan 5 — Podpis EXE + preverjanje posodobitev

## Vir (raziskava)
- „Shipping a Python desktop app“ (dev.to, 2026): nepodpisan EXE sproži
  SmartScreen/AV; **najprej podpiši EXE**, šele nato sestavi namestitev
  (sicer ostane nepodpisan ekstrakt znotraj paketa).
- „How to Code-Sign a PyInstaller EXE“ (2026): **RFC 3161 časovni žig**
  (`/tr`) je obvezen — brez njega podpis umre s potekom certifikata.
- „Code-Sign and Auto-Update“ (Deskifier, 2026): brez preverjanja
  posodobitev uporabniki obtičijo na starih različicah.

## Spremembe
1. `posodobitev.py` (nov): `VERZIJA`, `primerjaj_verziji` (numerično —
   `1.2 < 1.10`), `odpri_zadnjo_izdajo` (omrežni klic, ločen za teste),
   `preveri_posodobitev` → `{novo, verzija, url, napaka}`.
   Politika: aplikacija samo OPOMORI in pokaže povezavo — NE namešča
   posodobitev sama (iskreno: za to bi bil potreben podpisan
   namestitveni paket z verifikacijo).
2. `vmesnik.py`: gumb **⟳ Posodobitev** — preverjanje v niti
   (neblokirajoče); omrežna napaka NI kritična, javi se v statusu.
3. `build_windows.py`: `podpisi()` — `signtool sign /f <cert> /fd sha256
   /tr http://timestamp.digicert.com /td sha256`; geslo se NE izpisuje;
   BREZ certifikata se podpis preskoči z jasnim razlogom v zapisniku.

## Kar mora narediti NAROČNIK (iskreno — to ni avtomatizirano)
- **Kupi certifikat** za podpis kode: standardni (~200 USD/leto) ali EV
  (~200–500 USD/leto, hitrejši SmartScreen ugled). To je naročnikov
  strošek in pogodba s CA — mi tega ne moremo nadomestiti.
- Nastavi okoljski spremenljivki `PODPIS_PFX` (pot do .pfx) in izbirno
  `PODPIS_GESLO` ter `PODPIS_TOOL` (če `signtool.exe` ni na PATH).
- **Vrstni red**: `python build_windows.py --smoke` podpiše EXE po
  gradnji; namestitveni paket (če ga bo) sestavi ŠELE PO podpisu.

## Zunaj obsega
- Trgovinska aplikacija / auto-update odjemalec (npr. Squirrel, MSIX) —
  ločen projekt z lastno infrastrukturo.
- macOS podpis in notarizacija (Apple Developer ID, 99 USD/leto) —
  aplikacija je namenjena Windows.

## Verifikacija
- `tests/test_posodobitev.py` (6): numerična primerjava verzij, nova /
  enaka / starejša izdaja, omrežna napaka, preskok brez certifikata,
  sestava signtool ukaza s časovnim žigom (BREZ omrežja in BREZ resničnega
  certifikata — subprocess nadomeščen).
- `ruff`, `mypy` baseline, celotna suita.