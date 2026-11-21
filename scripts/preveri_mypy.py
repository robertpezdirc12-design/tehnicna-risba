# -*- coding: utf-8 -*-
"""mypy baseline „ratchet“ (Plan 1 — quality gates).

Vzor: SQRKOB „no new instances“ — obstoječe napake so v baseline datoteki,
nova koda pa NE SME prinesti nobene nove. Baseline se s časom MANJŠA
(ročno, ob popravilih), nikoli ne raste.

Uporaba:
    python scripts/preveri_mypy.py            # preveri (izhod 0 = brez novih)
    python scripts/preveri_mypy.py --update   # osveži baseline

Omejitev (iskreno): normalizacija odstrani številke vrstic, zato se
identični sporočili v isti datoteki zložita v en vnos — a nova instanca
istega sporočila v isti datoteki ostane neopažena. Zadosten nadzor za
„no new instances“ politiko.
"""
import pathlib
import re
import subprocess
import sys

KOREN = pathlib.Path(__file__).resolve().parent.parent
BASELINE = KOREN / ".mypy-baseline"

# path:line[:col]: error: msg [code]  ->  path: error: msg [code]
VZOREC = re.compile(r"^(?P<path>[^:]+):\d+(?::\d+)?: (?P<msg>.*)$")


def normaliziraj(vrstice: list[str]) -> set[str]:
    out = set()
    for v in vrstice:
        v = v.strip()
        if not v or not v.endswith("]") and ": error:" not in v:
            continue
        m = VZOREC.match(v)
        if m:
            out.add(f"{m.group('path')}: {m.group('msg')}")
    return out


def zazeni_mypy() -> list[str]:
    p = subprocess.run(
        [sys.executable, "-m", "mypy", "."],
        capture_output=True, text=True, cwd=str(KOREN), encoding="utf-8",
    )
    return [v for v in (p.stdout + p.stderr).splitlines() if ": error:" in v]


def main() -> int:
    napake = zazeni_mypy()
    trenutne = normaliziraj(napake)

    if "--update" in sys.argv:
        BASELINE.write_text(
            "# mypy baseline (Plan 1 — ratchet). Zmanjšuj, ne povečuj!\n"
            + "\n".join(sorted(trenutne)) + "\n",
            encoding="utf-8",
        )
        print(f"baseline osvežen: {len(trenutne)} zapisov -> {BASELINE.name}")
        return 0

    if not BASELINE.exists():
        print("baseline ne obstaja — zaženi najprej z --update", file=sys.stderr)
        return 2
    zabelezeno = {
        v.strip() for v in BASELINE.read_text(encoding="utf-8").splitlines()
        if v.strip() and not v.startswith("#")
    }
    nove = sorted(trenutne - zabelezeno)
    if nove:
        print(f"NOVE mypy napake ({len(nove)}) — nič novih dovoljenih:")
        for v in nove:
            print("  " + v)
        return 1
    print(f"mypy: brez novih napak (v baseline zabeleženih: {len(zabelezeno)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())