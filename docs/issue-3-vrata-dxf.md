# Issue #3 — vrata, prehodi, segmenti, DXF: odločitve in izvedba

Ta dokument beleži arhitekturne odločitve implementacije issue #3.
Osnova: stabilno jedro iz issue #2 (74/74 testov, PR #4).

## Vir resnice za geometrijo

`vrata.py: geometrija_vrat()` / `geometrija_prehoda()` sta **edini** izračun
geometrije vrat/prehodov. Porabniki:

- risba (obe predlogi: `narisi_ogrado`, `narisi_pokoncna` → `narisi_odprtine_in_vrata`),
- količine in kosovnica (`narisi_montazni_list`, `narisi_montazni_pokoncna`),
- DXF izvoz (`dxf_izvoz.py`),
- GUI validacija (`vmesnik.py: _vrata_preveri`).

Isti `elementi_vrat()`/`elementi_prehoda()` primitivi se narišejo v matplotlib
in zapišejo v DXF — vizualni prikaz in izvoz se ne moreta raziti.

## Geometrijske odločitve (dokumentirane, brez skritih privzetkov)

- **Veriga širin**: `r_bok + w_1 + r_med + … + r_bok = S_o` (natanko, 1e-9).
  Privzete reže: tla 50 mm, bok 5 mm, med kriloma 10 mm, zgoraj 5 mm;
  pri pasjih vratih ni reže med kriloma (obe polovici enaki).
- **Višina krila**: `h_k = H_o − r_tla − r_zg`.
- **Odprtina**: širina = `vrata.sirina`, višina = `vrata.visina` iz konfiguracije.
  `visina + odcep > visina ograje` je **NAPAKA** (blokira PDF in DXF) —
  vrata ne smejo segati izven ograje.
- **Tečaji (P1)**: h_k ≤ 1200 → 2; ≤ 2100 → 3; ≤ 2500 → 4; sicer 5;
  +1 če je krilo širše od 1200 mm; `skriti` → max(3, izračun).
- **Vijaki (P2)**: 4/6/8 na tečaj (2/3/4 peresov).
- **Okvir (P4)**: 2 stojali + 2 prečki; krilo: 2 stojali + 2 vodoravni letvi.
- **Prečke (P5)**: 2 + (h > 2000) + (h > 2800) — dodatne prečke na krilu.
- **Diagonala (P6)**: hipotenuza notranjih mer krila, zaokroženo navzgor
  na 5 mm (`ceil5`) — proizvodni odrez.
- **Ročaj/ključavnica**: višina 1050 mm (če je krilo krajše od 1000 mm: sredina).
- **Prehod (P7)**: odprtina brez kril; količine: 2 zaključna stebra,
  2 zaključna profila, 4 sidra M10 (2 na steber); brez tečajev/zaklepov.

## Vpliv odprtin na polnilo in razrez

- Prečna: lamele, ki jih seka odprtina, se razrežejo na kose okoli odprtine
  (`razdeli_po_odprtinah`); kosi gredo v rez prek `razrez.razrez_kosov`
  (FFD, kos po kos), ker so različnih dolžin.
- Pokončna: deske znotraj odprtine odpadejo, delno prekrite se razrežejo;
  število kosov (`n_eff`) vpliva na vijake in nabavo.
- Kosi okvirjev/kril vrat gredo v ločen rez (različni profili), kupljeni
  deli (tečaji, ključavnice, ročaji) **ne** gredo v rezalni načrt.

## Količine / kosovnica

Vratne postavke so v `kolicine["postavke"]` (5-tuple format iz issue #2:
`naziv, kol_str, enota, kljuc_cene, num`) — novi ključi cenikov:
`tecaj_kos`, `zapah_kos`, `kljucavnica_kos`, `cilinder_kos`, `rocaj_vrata_par`,
`talni_zatic_kos`, `zapiralo_kos`, `povezovalna_plosca_kos`, `kotnik_kos`,
`vijak_vrata_kos`, `matica_kos`, `podlozka_kos`, `zakljucni_steber_kos`,
`zakljucni_profil_kos`, `sidro_m10_kos`. Obstaja ločen oddelek
»VRATA/PREHODI« v potrebščinah in naročilu montažnega lista.

## Katalog komponent

`vrata.py: KATALOG` (razširljiv prek `nalozi_katalog(pot)` z YAML datoteko —
ni trdo kodiran v risbah). Katalog vsebuje le opisne podatke (oznaka, vrsta,
opis, enota) — **brez** izmišljenih nosilnostnih/statičnih podatkov
(odgovornost: issue §10 — risba NI statični izračun).

## YAML shema v2 in migracija

- v2 doda `shema: 2` in `segmenti` (seznam: ime, tip, mere, kot, vrata, prehodi);
  obstoječa polja ostanejo nedotaknjena (enosegmentni projekt = v1 ekvivalent).
- `migracija.py`: migracija v1→v2 je **idempotentna**, ohranja neznana polja
  (round-trip brez izgube) in **ne piše nazaj** v izvirno datoteko
  (shranjevanje je eksplicitno).

## Koordinacija pod-agentov (zahteva issue #3)

Vzporedno koordiniranih 5 specializiranih pod-agentov (vsak z analizo
repozitorija, brez sprememb datotek):

1. **CAD/geometrija** — model odprtin/kril/rež, veriga širin, pravila
   tečajev; ročni kontrolni izračuni v testih.
2. **Konstrukcija/proizvodnja** — katalog komponent, pravila količin P1–P7,
   vključitev v kosovnico (ohranjeni formati 5-tuple).
3. **DXF/CAD/CNC** — specifikacija plasti/enot/kontur/audit (docs/dxf-specifikacija.md).
4. **UX** — GUI tok (4 obvezna polja, Treeview, dialog, validacija
   napake/opozorila, DXF dialog s potrditvijo prepisa).
5. **QA** — testni načrt (ročno izračunane vrednosti, pypdf štetje strani,
   ezdxf round-trip, YAML round-trip, nedotaknjenih 74 testov).

Odločitve, kjer so se poročila razhajala, je rešil orkestrator in so
zapisane zgoraj (npr. diagonala: notranje mere + ceil5; odprtina: višina
iz konfiguracije z omejitvijo višine ograje).

## Regresija in testi

- **Obstoječih 74 testov NI bilo spremenjenih** (git diff tests/ je prazen
  za stare datoteke) — jedro issue #2 ostaja nespremenjeno.
- Novi testi: `test_vrata.py` (28), `test_dxf.py` (15), `test_projekt.py` (18).
- Merila: matematične vrednosti so ročno izračunane (veriga, tečaji, vijaki,
  diagonala), PDF se preverja s pypdf (št. strani + velikost + vsebina),
  DXF z ezdxf round-tripom, YAML z migracijskim round-tripom.

## Znane omejitve / načrtovane razširitve

- Vogali (koti) med segmenti: podatkovni model (`kot`) in validacija sta
  vključena; risba segmentov je v1 v skupni ravnini (razmak 1000 mm) —
  tlorisna postavitev vogalov je načrtovana razširitev.
- `razrez_kosov` (FFD) za kose različnih dolžin ne uporablja skladišča
  ostankov za porabo (nove ostanke ≥ 100 mm pa evidentira) — izmenjava
  ostankov med različnimi dolžinami je načrtovana optimizacija.
- Kote v DXF so statične (ne asociativne DIMENSION entitete).