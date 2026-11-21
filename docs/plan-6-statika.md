# Plan 6 — Poenostavljen statični pregled (EN 1991 obtežbe)

## Vir (raziskava)
- BS 6180:2011 tabela 2 (prek Balconette): bivalno 0.74 kN/m / 1.0
  kN/m² / 0.5 kN; javno 1.5 / 1.5 / 1.5.
- DIN EN 1991-1-1/NA (prek ChallengingGlass): 0.5 / 1.0 / 2.0 kN/m po
  kategoriji.
- PD 6688-1-1 tabela 3 (UK/IE): 0.36–1.50 kN/m po kategoriji.
- EN 1991-1-4: veter (uporabnik vnese tlačni pritisk — NI avtomatizirano).

## Načelo (iskreno — najpomembnejši del)
Modul izračuna **POTOVANJE (demand)**: zahtevani W (uporni prerez) in I
(vztrajnostni moment) ročaja/stebra pri znani obtežbi. **NE preverja
zmogljivosti** konkretnega profila — brez certificiranih lastnosti
materiala, varnostnih faktorjev γ, utrujenosti, spojev in sidranja tega
ni mogoče pošteno storiti. Izpis je označen z „INFORMATIVNI PREGLED —
NI STATIČNI IZRAČUN“ in NI nadomestilo za pooblaščenega inženirja.

## Fizika (zapisana v modulu, revizijsko)
- ročaj (preprosto podrt nosilec): M = q·L²/8; W_pot = M/f;
  I_pot (uklon L/200) = 5·q·L³·200/(384·E)
- steber (konsolno nosilo): M = q·L·h; W_pot = M/f

## Spremembe
- `statika.py` (nov): `OBTEZBE` (s VIRI), `pregled_rocaj`, `pregled_steber`,
  `povzetek` (opozorilo + vse kategorije), CLI.
- `vmesnik.py`: gumb **STATIČNI PREGLED** — dialog s povzetkom iz
  trenutnih mer (razmak stebrov, višina ročaja).

## Omejitve (označene tudi v izpisu)
- vrednosti obtežb so iz TUJIH virov; slovenskega nacionalnega dodatka
  (SI NA) NISMO preverjali — uporabnik mora preveriti;
- privzeti f = 235 MPa je za S235 JEKLO — za aluminij/kompozit mora
  uporabnik vnesti pravo vrednost (ni trditev o materialu ograje);
- brez: dinamike, utrujenosti, lokalnih učinkov, spojev, sidranja,
  vetra (EN 1991-1-4 je ločena vhodna obtežba, če jo uporabnik vnese).

## Verifikacija
- `tests/test_statika.py` (6): ročno izračunane vrednosti (M = 0.125 kNm
  pri L=1000/q=1; steber M = 1.65 kNm pri h=1100/L=1500), napake,
  skaliranje (2×q → 2×M, 2×L → 4×M, 8×I), viri v OBTEZBAH, opozorilo
  v povzetku.
- `tests/test_vmesnik.py`: gumb/povzetek iz trenutnih mer.
- ruff, mypy baseline, celotna suita.