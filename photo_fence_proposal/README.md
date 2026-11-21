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

## Poštene omejitve (pomembno)

- Ena fotografija **ne more** zanesljivo dati vseh mer: perspektiva, zakritja
  in odsotnost merila omejujejo natančnost. Kalibracija predpostavlja čeln
  pogled; pod kotom so mere slabše.
- Merjena napaka na **sintetičnih** testnih prizorih (5 prizorov, znane mere):
  dolžina **±88–123 mm**, višina **±125–178 mm** (glej `testi_pfp.py`, izpis
  `NAPAKA MER`). Sintetični prizori **niso** nadomestilo za terenske
  fotografije — testiranje na resničnih fotografijah ostaja odprto.
- Parametri nove ograje (širina lamele, razmak) so `ocenjeno`, dokler jih
  uporabnik ne potrdi.
- Razrez je informativna hevristika (standardne 6000 mm palice, kerf 3 mm).

## Datoteke

| Datoteka | Vloga |
|---|---|
| `model.py` | podatkovni model + statusi mer (Mera, Zaznava, Rezultat …) |
| `zaznavanje.py` | klasično zaznavanje (OpenCV) |
| `kalibracija.py` | kalibracija z referenco + izpeljava mer |
| `predlog.py` | vizualni predlog na fotografiji (A) |
| `tehniska_risba.py` | tehnična risba s kotiranjem in statusi (B) |
| `material.py` | kosovnica + informativni razrez/odpad |
| `zazeni.py` | CLI (celoten tok) |
| `napravi_testne_slike.py` | generator sintetičnih prizorov z znanimi merami |
| `testi_pfp.py` | samostojni testi (17) |

Nič v tej mapi se ne priklopi v glavni program brez izrecne odobritve uporabnika.