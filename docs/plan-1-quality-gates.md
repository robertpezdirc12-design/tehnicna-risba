# Plan 1 — Quality gates: ruff + mypy + coverage „ratchet“

## Vir (raziskava)
- Modern Python standard (TS2/TS3): coverage prag v CI, ne v vsakem zagonu
- Python Tooling Stack 2026: ruff + mypy (postopno na obstoječi kodi)
- SQRBOK „Quality Gates“: pragovi z razlogom; coverage „ratchet“ —
  prag = trenutna vrednost zaokrožena NAVZDOL na 5, dviguje se z rastjo
  (ne blokira PR-ja, ki ne spremeni ničesar)

## Cilj
1. **ruff** — statična analiza (napačne reference, neuporabljeni uvozi,
   napake v sintaksi): 0 napak pri izbranih pravilih.
2. **mypy** — postopno: `check_untyped_defs=true`, `ignore_missing_imports`.
   ODLOČITEV (spremenjeno med izvedbo): „0 napak“ ni dosegljivo brez
   popačenja kode s `type: ignore` — večina od 122 najdb je šum nepopolnih
   stubov (cv2, ezdxf, tkinter, numpy). Namesto tega **BASELINE RATCHET**
   (SQRKOB „no new instances“): obstoječe napake so v `.mypy-baseline`,
   nova koda ne sme prinesti NOVE; baseline se s časom MANJŠA.
3. **coverage „ratchet“** — `fail_under` = 65 (trenutna pokritost 70 %
   zaokrožena navzdol na 5, minus rezerva za okoljsko nihanje Tk testov),
   meri se SAMO v CI (ne v navadnem `pytest`).
4. CI koraki: ruff → mypy baseline → pytest s coverage.

## Najdbe med izvedbo (vrednost orodij potrjena!)
- **F821 prava napaka**: `jedro.py` je uporabljal `os.path.isfile` brez
  uvoženega `os` — ob `cfg["foto"]` bi prišlo do `NameError`.
- ruff `--fix` je odstranil **re-exporte fasade** `risba.py` (F2 dogovor) in
  s tem zlomil `api/index.py` in snapshot teste → obnovljeni z PEP 484
  `as` zapisom (ruff jih označi za namerne). Pouk: fasadni moduli
  potrebujejo `X as X` zapis za re-exporte.
- odstranjenih 14 mrtvih spremenljivk (F841) in 26 neuporabljenih uvozov.

## Spremembe
- `pyproject.toml` (nov): [tool.ruff], [tool.mypy], [tool.coverage.*]
- `scripts/preveri_mypy.py` (nov): baseline ratchet
- `.mypy-baseline` (nov): 85 normaliziranih zapisov (122 surovih napak)
- `requirements-dev.txt`: +ruff, mypy, pytest-cov
- `.github/workflows/testi.yml`: +3 koraki
- popravki kode: F821 (jedro), mrtve spremenljivke, F2 re-exporti

## Verifikacija
- `ruff check .` → All checks passed
- `scripts/preveri_mypy.py` → brez novih napak (85 v baseline)
- `pytest --cov` → 270 zelenih, pokritost 70 % ≥ prag 65

## Zunaj obsega (iskreno)
- `ruff format` / preoblikovanje celotne kode (ogromen diff, brez funkcionalne
  koristi).
- `mypy --strict` in tipizacija celotne kode — ločen projekt.
- Mutation testing — predlagan v raziskavi, a precej časa; ločeno.