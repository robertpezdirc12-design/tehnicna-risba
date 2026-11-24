# Kako izboljšati zaznavo ograje s fotografije

*Raziskava, 24. 11. 2026. Namen: iz evidence (ne iz občutka) ugotoviti, katere
izboljšave so smiselne za `photo_fence_proposal`, koliko stanejo in kaj prinesejo.*

## 1. Diagnoza — kaj točno gre narobe

Preizkus na petih fotografijah z Wikimedie (baročni balkon, hiša s tremi
balkoni, stekleni balkon v 21. nadstropju, dva izreza) je pokazal tri ločene
vzroke, ne enega:

| Vzrok | Dokaz iz preizkusa |
|---|---|
| **Zaznava šteje napačne vertikale** | Baročni baluster = »steber« (19 kosov), stekleni pokončni profili = »stebri« z razmakom 193 mm |
| **Ni modela perspektive** | Ravnina balkona je poševna; merjenje v pikslih po vodoravni osi podceni dolžino za 40–60 % |
| **Ena sama referenca je prešibka** | Če je referenca višina ograje, se napaka višine prenese v dolžino; če je razmak, je dolžina po konstrukciji točna, a le če so stebri pravilno prešteti |

Zato na tujih fotografijah napaka **ni majhna in ni predvidljiva** (−60 % do
+140 %), na sintetičnih prizorih z znano resnico pa ostaja v ±3,9 %. Problem
torej ni aritmetika, ampak **geometrija slike**.

## 2. Pet poti, ki jih ponuja stroka

### 2.1 Eno-posnetkovna metrologija (single view metrology)

Klasična, dokazana pot: iz ene slike lahko izmeriš ravnino, če poznaš **eno**
dolžino v tej ravnini in smeri izginjajočih točk (Criminisi idr. 1999,
*Single View Metrology*). Za `photo_fence_proposal` to pomeni: uporabnik
označi rob ograje (4 točke) ali pa se ravnina določi iz izginjajočih točk
(fasada, tla), nato se slika poravna v **čelni pogled** s homografijo. V
čelnem pogledu je merilo enotno (mm/px), zato:

- dolžina in višina sta odvisni le od ene referenčne mere,
- štetje stebrov postane 1D problem (profil po x),
- risba se ne »zvija« več.

**Cena:** OpenCV `getPerspectiveTransform` + 4 točke (ročno) ali LSD +
RANSAC za izginjajoče točke (samodejno). Brez novih odvisnosti, brez mreže.
**Napaka:** pri ročno označenih 4 točkah je napaka merila ~1–2 % (le
natančnost klika in referenčne mere); pri samodejnih izginjajočih točkah
dodatno 1–3 %.

### 2.2 Ponavljajoče se strukture (periodičnost)

Ograja je po definiciji periodična. Wenzel in Förstner (2008) ter kasnejše
delo o fasadah (ISPRS 2013, RANSAC 2014) kažejo, da se perioda zanesljivo
dobi iz avtokorelacije oziroma FFT profila roba. To ne šteje »vseh vertikal«,
ampak **eno periodo in fazo**, zato lažne zaznave (podboji oken, cevi) ne
povečajo števila stebrov.

**Preizkus (narejen v tem repozitoriju):** na izrezu baročnega balkona
avtokorelacija profila roba da periodo 71 px → **27 elementov**; ročno jih
preštejem 26 (napaka +4 %). Trenutna zaznava na istem izrezu našteje 19
»stebrov«.

Dve pasti, ki sta se pokazali in ju je treba vgraditi:

1. **Harmonik.** Najmočnejši vrh avtokorelacije je pri 32 px (širina
   balustra), ne pri 71 px (razmak). Zato ne smeš vzeti kar `argmax`, ampak
   največji vrh, ki je blizu najvišjemu (≥ 0,6 × max) — osnovna perioda je
   praviloma daljša od harmonika.
2. **Poševni pogled.** Na izrezu hiše s tremi balkoni (poševno) metoda da
   33 px → 30 elementov, a linije očitno ne sledijo balusterom: brez
   poravnave v čelni pogled je rezultat naključen. To je dokaz, da mora
   korak 2 vedno teči **na poravnani sliki** (korak 1), ne na izvirniku.

### 2.3 Marker za merilo (ArUco)

Namesto »predpostavimo, da je ograja visoka 1000 mm« se na ograjo pripne
natisnjen marker A4 (ArUco). Knjižnica je **že nameščena** (`cv2.aruco`,
OpenCV 4.11) in zazna marker tudi pod kotom; iz njegove velikosti v pikslih
sledi mm/px na tisti ravnini. Literatura o merjenju z ArUco markerji poroča o
napakah reda 1–3 % pri dobri osvetlitvi in kotu < 60°.

**Cena:** ~0,5 dni (generator markerja + branje + navodilo v README).
**Pridobitev:** uporabniku ni treba poznati nobene mere; merilo je v sliki.

### 2.4 Učeni modeli — kaj je res na voljo

Preverjeno pri virih (ne iz blogov):

| Model | Licenca | Velikost (deploy) | Kaj da | Uporabno za |
|---|---|---|---|---|
| Depth Anything V2 Small (ONNX) | Apache-2.0 | **98,8 MB** `model.onnx_data` + 127 kB graf | relativna/metricna globina | pomožna ocena ravnine, ne merilo |
| SAM 2 (hiera-tiny, ONNX) | Apache-2.0 | 134,3 MB encoder + 20,6 MB decoder | maska objekta iz točke | izrez ograje iz scene |
| GroundingDINO | Apache-2.0 | ~700 MB (Swin-B) | detekcija iz besedila (»fence«) | najdi ograjo v kadru |
| DeepLSD | **MIT** | ~100 MB | natančne daljice (boljše od Cannyja) | izginjajoče točke, ravnanje |
| YOLO-World | GPL-3.0 | ~25–50 MB | zero-shot detekcija | ⚠ licenca |
| Ultralytics YOLO (v8/11) | **AGPL-3.0** | 6–50 MB | seg/detekcija | ⚠ licenca za zaprt izdelek |

Pomembna ugotovitev: **Open Images V7 nima razreda `Fence` niti `Balcony`**
(preverjeno v uradnem seznamu 600 razredov: obstajata le `Porch` in
`Stairs`). Prav tako ni pripravljenega modela za ograje v COCO. Roboflow
Universe ima zbirke za ograje, a so majhne (npr. *Fence Segmentation*, v1:
**56 slik**) — premalo za zanesljiv model brez lastnega označevanja.

**Sklep:** učeni modeli so smiselni za *izrez območja* in *kakovost daljic*,
ne pa za merjenje. Meritev ostane geometrijska.

### 2.5 Globina (Depth Anything V2)

Globina iz ene slike da *relativno* razdaljo; za mm je spet potrebna
referenca. Metrične različice (V2 Metric Indoor/Outdoor, Apache-2.0) so
učene na notranjih prizorih oziroma KITTI, ne na fasadah, zato so za balkon
manj zanesljive kot homografija ravnine. **Ni priporočena pot** za ta
problem; ostaja kot eksperiment.

## 3. Kaj je v projektu že na voljo (preverjeno v okolju)

```
opencv 4.11.0 (aruco: da, LSD: da — 4488 daljic v 0,46 s na 1920×1280)
numpy 1.26.4 | skimage 0.26.0 | scipy 1.17.1
onnxruntime 1.22.1 | torch 2.14.1 (CPU)
```

Torej: **nobena od predlaganih izboljšav ne zahteva novega paketa**, razen
če bi dodali učeni model (takrat `onnxruntime` + 20–150 MB uteži).

## 4. Priporočeni načrt (po razmerju pridobitev/cena)

| # | Korak | Delo | Nove odvisnosti | Izmerjena napaka | Stanje |
|---|---|---|---|---|---|
| 1 | **Čelni pogled**: 4 točke, homografija (`rektifikacija.iz_vogalov`) | 0,5 dneva | ne | višina: ~1 %; **širina: neizmerljiva** (glej 4.1) | **narejeno v 1.5.16** |
| 2 | **Periodično štetje** (`perioda.py`, svetilnost + avtokorelacija) | 1 dan | ne | 0 % na sintetičnih, −1…−3 elementa na tujih | **narejeno v 1.5.16** |
| 3 | **ArUco merilo** (`marker.py`) | 0,5 dneva | ne | 0,03 % čelno; 1–3 % poševno (marker ≥ 120 px) | **narejeno v 1.5.16** |
| 3b | **Vgradnja v okno** (`vmesnik.py`: koti + marker + tiskanje lista; `avtomatska_skica` meri z markerjem) | 0,5 dneva | ne | ista kot 1–3 (ista koda); izpeljana mera brez markerja zdaj `ocenjeno` | **narejeno v 1.5.17** |
| 3c | **Soglasje več posnetkov** (`vec_posnetkov.py`, `--dodatna`, polje v oknu): dve meritvi iste ograje → mediana ali jasno opozorilo | 0,5 dneva | ne | 2 sintetični perspektivi: 5925 in 5980 mm (razpršenost 0,9 %); 6 % napačni koti padejo na prag 2 % | **narejeno v 1.5.18** |
| 4 | Samodejne izginjajoče točke (LSD + RANSAC) namesto klika | 3–5 dni | ne | +1–3 % | odprto |
| 5 | (neobvezno) SAM2/GroundingDINO za samodejni izrez | 1–2 tedna | onnxruntime + 30–150 MB | ne izboljša mer | odprto |

Vrstni red je bil pravilen, a z eno pomembno korekcijo: **korak 1 sam po
sebi ne more izmeriti širine** (dokaz v 4.1). Šele marker iz koraka 3 naredi
širino merljivo — zato sta 1 in 2 skupaj vredna natanko toliko, kolikor jim
doda 3. Učeni modeli ostajajo najdražji in za točnost mer najmanj koristni.

### 4.1 Zakaj štirje koti ograje ne zadostujejo za širino

Homografija ima 8 prostostnih stopenj, štirje koti pa dajo 8 enačb — zato
je rešitev natanko ena, **a le za izbrano razmerje stranic ciljnega
pravokotnika**. Pravokotnik 6:1, gledan od daleč, in pravokotnik 3:1,
gledan pod drugim kotom, dasta praktično isto sliko. Iz samih kotov je
torej merljivo le razmerje, ki ga vnaprej predpišemo.

Izmerjeno na sintetični sceni 6000 × 1000 mm (koti znani do piksla):
`rektifikacija.iz_vogalov` vrne sliko z razmerjem **2,2 : 1** namesto
6 : 1; ob znani višini 1000 mm iz tega nastane dolžina **2164 mm**
(−64 %). To ni napaka kode, ampak lastnost geometrije — zato je merilo
(marker) nujno, ne le 'lepa dodatna oprema'.

### 4.2 Kaj je v 1.5.16 dejansko narejeno

| Modul | Naloga |
|---|---|
| `photo_fence_proposal/perioda.py` | perioda in število elementov iz svetilnostnega profila (CLAHE + odstranjen trend), avtokorelacija, izbor **najmanjšega** lokalnega maksimuma ≥ 0,6 × maksimuma z izostritvijo ±4 px; štetje z lokalno normalizacijo in kontrolo popolnosti (`pricakovano = round(širina / perioda)`) |
| `photo_fence_proposal/marker.py` | A4 list z 150-mm ArUco markerjem (300 dpi, 100-mm kontrolna črta), zaznava s podpikselnim izostritvom kotov, meritev pravokotnika v mm prek homografije markerja |
| `photo_fence_proposal/vnos.py` | skupno razčlenjevanje vnosa kotov (`x,y;x,y;x,y;x,y`) — ena implementacija za CLI in okno |
| `vmesnik.py` (okno *Predlog mer*) | polji *Koti ograje* in *Marker (mm)*, gumb *Natisni marker …*; kliče `avtomatska_skica.izracunaj_mere_pot(vogali=…, marker_mm=…)` |
| `photo_fence_proposal/zazeni.py` | `--vogali "x,y;x,y;x,y;x,y"` (poravnava + štetje), `--marker-mm` (merilo), marker se išče na izvirniku, koti se preslikajo v mm; vsaka mera dobi status `IZRACUNANO`/`OCENJENO` in opozorilo |

Če markerja ni, program **ne ugiba širine**: izpiše opozorilo, da je iz
samih kotov ni mogoče izračunati, in uporabi ročni `--dolzina`, če je podan.

### 4.3 Izmerjeno (testi, ne občutek)

| Preizkus | Resnica | Rezultat | Napaka |
|---|---|---|---|
| perioda, sintetično | 10 / 16 / 8 / 26 elementov | 10 / 16 / 8 / 26 | 0 elementov, perioda ±1 px |
| perioda, `k1-izrez` (tuja fotografija) | 26 elementov (ročno) | 23 | −3; kontrola popolnosti javi 28 pričakovanih → status `OCENJENO` |
| marker, čelni pogled 6000 × 1000 mm | 6000 × 1000 | 5998 × 998 | **−0,03 % / −0,2 %** |
| marker 300 mm (68 px), poševno, 0,5 px/mm | 6000 × 1000 | 5925 × 993 | **−1,3 % / −0,7 %** |
| marker 300 mm (68 px), poševno, 1 px/mm | 6000 × 1000 | 6177 × 1009 | +2,9 % / +0,9 % |
| marker 150 mm (34 px), poševno | 6000 × 1000 | 6336 × 1134 | +5,6 % / +13,4 % (premajhen marker) |

Zato: `MIN_STRANICA_PX = 60` (pod tem se marker zavrne) in opozorilo pod
120 px. Meritev je torej zanesljiva, ko je marker na fotografiji dovolj
velik — kar je fizika, ne nastavitev.

Preverjanje: `python -m pytest photo_fence_proposal/testi_pfp.py -q`
(66 testov, vsi zeleni).

## 5. Kako preveriti, da izboljšava res deluje

Brez merjene resnice ni dokaza. Zato pred vsako izboljšavo:

1. **20 fotografij** (10 frontalnih, 10 poševnih), za vsako ročno izmerjena
   dolžina in višina (metrski trak, zapis v CSV).
2. Za vsako: napaka v mm in % za dolžino, višino, število stebrov.
3. Kriterij sprejema: **MAE ≤ 3 %** za dolžino/višino, **štetje brez napake**
   pri frontalnih in ±1 pri poševnih.
4. Vsaka izboljšava se doda v `testi_pfp.py` kot regresijski test na
   sintetičnem prizoru z znano resnico (kot je že zdaj) in na vsaj dveh
   realnih fotografijah (mehke meje: ±1 steber).

## 6. Licence in tveganja

- **AGPL-3.0** (Ultralytics) in **GPL-3.0** (YOLO-World, XiaohuLu VP): za
  komercialni izdelek nesprejemljivo brez pravnega mnenja. Uporabi Apache-2.0
  (SAM2, GroundingDINO, Depth Anything V2), MIT (DeepLSD) ali čisto OpenCV.
- `photo_fence_proposal` mora ostati **samostojen in brez mreže** (zahteva iz
  številke #8). Vsaka izboljšava mora biti v novih modulih, z `--brez-*`
  stikali, in ne sme uvesti `risba`, `razrez`, `vrata`, `vmesnik`.
- Natečena natančnost **ne sme** spremeniti oznake dokumenta: če meritev ni
  potrjena, ostane »INFORMATIVNO« — tudi ko je algoritem samozavesten.

## 7. Viri

- Criminisi, Reid, Zisserman: *Single View Metrology*, ICCV 1999 —
  https://robots.ox.ac.uk/~vgg/publications/1999/Criminisi99/criminisi99.pdf
- Bazin idr.: *Globally Optimal Line Clustering and Vanishing Point Estimation
  in Manhattan World*, CVPR 2012 — https://people.inf.ethz.ch/~pomarc/pubs/BazinCVPR12.pdf
- Lu idr.: *2-Line Exhaustive Searching for Real-Time Vanishing Point
  Estimation*, WACV 2017 — https://xiaohulugo.github.io/papers/Vanishing_Point_Detection_WACV2017.pdf
- Wenzel, Förstner: *Detection of Repeated Structures in Facade Images*,
  2008 — https://www.ipb.uni-bonn.de/pdfs/Wenzel2008Detection.pdf
- ISPRS Annals: *Automated detection of repeated structures in building
  facades*, 2013 — https://isprs-annals.copernicus.org/articles/II-5-W2/241/2013/isprsannals-II-5-W2-241-2013.pdf
- DeepLSD (MIT) — https://github.com/cvg/DeepLSD
- Depth Anything V2 (Apache-2.0) — https://github.com/DepthAnything/Depth-Anything-V2
- SAM 2 (Apache-2.0) — https://github.com/facebookresearch/sam2
- GroundingDINO (Apache-2.0) — https://github.com/IDEA-Research/GroundingDINO
- OpenCV ArUco — https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html
- Open Images razredi (preverjeno: brez `Fence`/`Balcony`) —
  https://storage.googleapis.com/openimages/v7/oidv7-class-descriptions-boxable.csv
- Roboflow *Fence Segmentation* (56 slik) —
  https://universe.roboflow.com/fence-segmentation/fence-segmentation-rorvi
