# Plan 16 — Statična priloga (revizijsko sledljiv izračunski list)

## Odločitev (P4 „statični izračun“)
Celovitega statičnega izračuna **ne avtomatiziramo** — brez certificiranih
lastnosti materiala, varnostnih faktorjev, sidranja in SI NA bi bil to
lažen občutek varnosti. Namesto tega program sestavi **statično prilogo**:
pregledno, revizijsko sledljivo podlago, ki jo montažer preda
pooblaščenemu inženirju. Priloga torej dopolnjuje načrt 6 (povpraševanje),
ga ne razglaša za izračun.

## Vsebina priloge (A4, ena stran)
1. **Glava** — projekt, št. risbe, stranka, objekt, datum (iz konfiguracije).
2. **Opozorilo** (rdeče) — „INFORMATIVNI PREGLED — NI STATIČNI IZRAČUN …“.
3. **Vhodni podatki** — L (razmak stebrov), h (višina ročaja = visina − odcep),
   mere ograje, material (f, E) z opozorilom, če je f privzet S235.
4. **Obtežbe in zahteve (povpraševanje — demand)** — po kategorijah
   (bivalno/javno, viri iz načrta 6): ročaj M/W≥/I≥, steber F/M/W≥.
   Neobvezno: veter s **uporabnikovim tlakom** `statika.veter_kN_m2`
   (q = p·h) — jasno označeno kot vhod, NE izračun po EN 1991-1-4.
5. **Formule** — zapisane za revizijo (M = q·L²/8 …).
6. **Odprto za pooblaščenega inženirja** — kontrolni seznam ([ ]): zmogljivost
   prereza, γ/kombinacije, sidranje, veter EN 1991-1-4, dinamika/utrujenost,
   SI NA, dejanski razmak.
7. **Pritrdila iz konfiguracije** (vijaka, podlaga) + **opombe inženirja**
   (črte za ročne zapise) + **podpisni blok** (izdelal / pregledal / odobril).

## Spremembe
- `statika.py`: `priloga_podatki(cfg)` (JSON-prijazno), `pripis_priloge()`
  (berljivo), `narisi_prilogo(pot_pdf, cfg)` (A4), CLI
  `python statika.py --priloga projekt.yaml [-o STAT-priloga.pdf]`;
  blok `cfg["statika"]`: `f_MPa`, `E_MPa`, `veter_kN_m2`.
- `vmesnik.py`: meni **Orodja → Statična priloga (PDF)** (shranjevanje PDF).
- `tests/test_statika_priloga.py` (14): struktura, ročno preverjene zahteve,
  veter (enote p·h), opozorilo o S235, JSON, PDF z eno stranjo, kataloška
  pritrdila (dimenzije + dokazilo + eksplicitne napake).

## Pritrdila iz kataloga `mechanical/` (dopolnitev)

Neobvezni seznam `cfg["pritrdila_katalog"]` — vsak vnos `designation`,
`standard`, `profil` (+ `vloga`) se razreši prek `mechanical.resolver.razresi`
in v prilogi izpiše kot **dimenzije Z dokazilom** (standard, oznaka, mere iz
kataloga, vir + datum dostopa, status, katalogska datoteka). Prosta polja
(`pritrditev`, `vijak_lamela`, `vijak_nosilec`) ostanejo, a so označena kot
**brez kataloškega vira**. Neznana/manjkajoča vrstica je eksplicitna napaka
(`NapakaKataloga` s podrazredi) — mere se nikoli ne izmislijo.

## Omejitve (označene tudi v prilogi)
- priloga je **povpraševanje (demand)** — nikoli ne trdi o zmogljivosti;
- obtežbe so tujih virov (BS 6180 / PD 6688 / EN 1991-1-1 NA), SI NA ni
  preverjen; veter NI avtomatiziran;
- f = 235 MPa je privzeto za S235 JEKLO — za aluminij/kompozit mora
  uporabnik vnesti pravo vrednost (`statika.f_MPa`).