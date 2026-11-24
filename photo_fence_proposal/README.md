# photo_fence_proposal — predlog nove ograje iz fotografije stare (ADD-ON)

**Samostojen, neobvezen dodatek (issue #8).** Ne spreminja in ne uvaža ničesar
iz obstoječega programa (`risba.py`, `razrez.py`, `vrata.py`, `vmesnik.py` …).
Vse obdelave so **lokalne** (CPU, Windows 10, brez GPU) in **brez AI modelov** —
klasični OpenCV (kolonski temni profil, Canny, Hough) + deterministična pravila.

## Zagon

```bash
cd photo_fence_proposal
pip install -r requirements.txt

python zazeni.py --fotografija ..\slike\moja_ograja.jpg --izhod izhod/
    --tip wpc_vodoravne_lamele --barva antracit
    --referenca razmak_stebrov=2000     # ena znana referenčna mera (mm)
    --visina 1800 --dolzina 6000        # neobvezno: ročno potrjene mere
    --podjetje "Mojster d.o.o." --stranka "Naročnik" --objekt "Terasa"
    # --cene ..\cene.yaml (privzeto se najde sam) · --brez-predracuna
```

Testi (samostojni, ne vplivajo na obstoječo `tests/`):

```bash
python -m pytest testi_pfp.py -q
```

## Kaj naredi

1. **Zazna** stebre, polja in vodoravne letve na fotografiji (klasični OpenCV)
   in jih označi čez fotografijo (`01-zaznava.png`).
2. **Kalibrira** z eno referenčno mero uporabnika (najmanjši ročni poseg).
3. **Izpelje mere s statusi**: `izmerjeno` / `izracunano` / `ocenjeno` /
   `neznano` — neznane mere so vedno `?? (neznano — potrdi)`, nikoli izmišljene.
4. **Vizualni predlog** (`02-vizualni-predlog.png`) — vizualizacija nove ograje
   na fotografiji, označena kot *ni dokaz mer*.
5. **Tehnična dokumentacija** (`03-tehniska-risba.pdf`, `04-kosovnica.csv`) —
   risba s kotiranjem + statusi, kosovnica, informativni razrez/odpad.
   Dokument je **INFORMATIVNI PREDLOG**, dokler ključne mere niso potrjene;
   šele potem je označen kot *pripravljeno za izdelavo*.
6. **Predračun** (`07-predracun.pdf`, `08-predracun.csv`) — kosovnica,
   ovrednotena s cenikom `cene.yaml` iz korena projekta (ali `--cene`).
   Cene se **ne izmišljajo**: manjkajoč ključ = »cena po dogovoru«, znesek
   ostane prazen in skupni znesek NI izračunan. Postavke, ki jih kosovnica
   ne vsebuje (sidra, osnove, nosilci, zaključni profili), se ne prištejejo
   tiho — dokument jih našteje kot opozorilo za monterja. Dokler ključne
   mere niso potrjene, je predračun označen **INFORMATIVNO** in ni ponudba.

## Poštene omejitve (pomembno)

- Ena fotografija **ne more** zanesljivo dati vseh mer: perspektiva, zakritja
  in odsotnost merila omejujejo natančnost. Kalibracija predpostavlja čeln
  pogled; pod kotom so mere slabše.
- Merjena napaka na **sintetičnih** testnih prizorih (5 prizorov, znane mere):
  dolžina **±0 mm** pri kalibraciji na razmak stebrov (to ni "čarovnija" — dolžina
  je (n−1)×razmak iz istih zaznanih središč stebrov; zato je pravi preizkus
  napake **navzkrižna kalibracija** na višino → napaka dolžine **0,2–3,9 %**),
  višina **0,2–3,8 %** (merjena iz središč zunanjih letvi; glej `testi_pfp.py`,
  izpis `NAPAKA MER`).
- **Faza 4 — realne fotografije** (`testni_primeri_realni/`, 5 fotografij starih
  ograj z Wikimedie, viri in licence v `VIRA.txt`): **prekomerna zaznava**
  (12–22 "stebrov" namesto dejanskih — deske, drevesa, robovi), opozorilo
  »razmaki neenakomerni / zaznava negotova« se sproži na vseh; absurdne
  kalibrirane vrednosti so **javno zavrnjene** (npr. višina 11760 mm →
  `neznano`). **Sklep: prototip na realnih fotografijah NI zanesljiv vir
  mer** — uporaben kot vizualna pomoč in priprava osnutka, vse mere
  zahtevajo potrditev/merjenje na objektu.
- Parametri nove ograje (širina lamele, razmak) so `ocenjeno`, dokler jih
  uporabnik ne potrdi.
- Razrez je informativna hevristika (standardne 6000 mm palice, kerf 3 mm).
  Kos, daljši od 6000 mm, iz ene palice ni izvedljiv — program tega **ne**
  izračuna (brez negativnega odpada), ampak javi, da je potrebno spajanje palic.
- Ročni vnosi `--visina` / `--dolzina` morajo biti pozitivne vrednosti v mm
  (negativne ali ničelne so zavrnjene z jasno napako).

## Datoteke

| Datoteka | Vloga |
|---|---|
| `model.py` | podatkovni model + statusi mer (Mera, Zaznava, Rezultat …) |
| `zaznavanje.py` | klasično zaznavanje (OpenCV) |
| `kalibracija.py` | kalibracija z referenco + izpeljava mer |
| `predlog.py` | vizualni predlog na fotografiji (A) |
| `tehniska_risba.py` | tehnična risba s kotiranjem in statusi (B) |
| `material.py` | kosovnica + informativni razrez/odpad |
| `izracun.py` | predračun iz kosovnice + cenika (`cene.yaml`), PDF/CSV |
| `zazeni.py` | CLI (celoten tok) |
| `napravi_testne_slike.py` | generator sintetičnih prizorov z znanimi merami |
| `testi_pfp.py` | samostojni testi (32) |

Nič v tej mapi se ne priklopi v glavni program brez izrecne odobritve uporabnika.
## Avtomatska skica (P1) — fotografija → A3 risba

Modula `avtomatska_skica.py` + `rektifikacija.py` iz fotografije narišeta
profesionalno A3 skico v slogu referenčne tehnične risbe: sprednji pogled z
dimenzijsko verigo, prečni prerez A-A, detajl 'B', dokazno (rektificirano)
fotografijo, kosovnico s statusi in naslovni blok.

- **Metrična rektifikacija**: točke izginjanja iz robov (RANSAC, robustno na
  motnje) → čeln pogled ravnine ograje; izpad → homografija iz 4 klikanih
  vogalov.
- **P1 (klik + referenca)**: `--interaktivno` (klik 4 vogalov v oknu) ali
  `--vogali "x1,y1 x2,y2 x3,y3 x4,y4"` + `--referenca visina_ograje=1050`.
  S klikanimi vogali in referenco so mere `izracunano` iz trdne geometrije.
- **Poštenost**: brez reference vse mere `ocenjeno` (standardna lamela);
  neverodostojne vrednosti so javno zavrnjene (`neznano`) z opozorilom;
  dokument z negotovo zaznavo NI "pripravljen za izdelavo".
- **Brez AI modelov**: vse klasični OpenCV + linearna algebra (omejitev #8).

Primer:
`python avtomatska_skica.py foto.png --izhod skica.pdf --lokacija "Balkon" --referenca visina_ograje=1050 --vogali "0,520 1920,280 1920,830 0,950"`
