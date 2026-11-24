# Issue #6 — P0 revizija izračunov, razreza in dokumentov

**Stanje:** veja `fix/issue-6-p0-revizija` · naloga: GitHub issue #6
(P0: nepravilni izračuni, trde dimenzije, razrez brez verodostojnega modela).
Dokument povzema ugotovitve, odločitve in dokazila. Izdaja EXE **ni objavljena**
do potrditve rešitve.

## 1. Metoda in koordinacija pod-agentov (§10)

Delo je potekalo po vrstnem redu iz §11 (reprodukcija napak → referenčni
izračuni → popravki → testi → build → neodvisni pregled). Specializirani
pod-agenti (vzporedno, po vlogah iz §10):

| Vloga | Pod-agent | Stanje | Ključne ugotovitve (glavni agent jih je preveril v kodi) |
|---|---|---|---|
| 1 — matematični model, geometrija | `issue6-podag-mat-v1` | opravljen | potrditev napake 120/80; 15 neskladij izpis↔spec; past predloge `pokoncna`; model vrat se fizično ne izide (60+990+60>1000); P6 diagonala 3 različne vrednosti; T1–T12 referenčne vrednosti |
| 2 — proizvodnja, cutting-stock | `issue6-podag-cut-v1` | opravljen | fizični model reza (B) je pravilen; greedy optimizator slabši v 38 % majhnih primerov (dokazni primer: 2 surovca/500 mm odpada); FFD model A namesto B (zavračal 3000 iz 3000); trivialne A5 invariante |
| 3 — QA, testna avtomatizacija | `issue6-podag-qa-v1` | opravljen | 163/163 zelenih; artefakti (PDF/CSV/nalepke/DXF) preverjeni vsebinsko — brez neskladij z internimi izračuni; 14 najdb (2× P1: zastarel dokstring testa, vakuumska asercija — obe odpravljeni), 12 predlogov testov z ročnimi vrednostmi |
| 4 — Windows build/release | `issue6-podag-build-v1` | opravljen | revizija spec/build skripte: headless brez try/except (tveganje modalnega dialoga), manjkajoči Pillow v requirements, brez version info, pravila izdaje (nov tag, draft, nikoli zamenjava assetov), sledljivost commit→zapisnik→release; vse kritično aplicirano (§6) |
| 5 — Python arhitektura | — | izvedeno interno | centralizacija `proizvodni_model` (§2) in `vrata.geometrija_vrat` sta bili presojeni kot najmanj tvegan način; obstoječi vmesniki (cfg ključi) nespremenjeni |

Glavni agent je vsako ključno ugotovitev preveril neposredno v kodi
(reprodukcija, ročni izračuni, testi) — poročila pod-agentov niso bila
sprejeta brez preverbe.

## 2. Napaka vijakov (120 → 80) in kanonični proizvodni model

**Reprodukcija** (20 desk, 3 stebri, 2 stika/desko): tabela SEZNAM
SESTAVNIH DELOV je štela `n_desk·n_stebrov·2 = 120` vijakov, montažni list
in količine pa 4/desko = `80` — paralelne formule v več izpisih.

**Popravek:** `risba.proizvodni_model(c)` — EN vir resnice za tabelo
(sestavni deli), montažni list, količine, kosovnico in naročilo:

- pokončna: deske → kosi (razdeljeni okoli odprtin), `n_stikov` = št. robov
  kosov, ki sovpadejo s stebrom, `vijaki = 2·n_stikov` (B2: 2 vijaka na stik,
  deska se pritrdi na oba sosednja stebra; razrezana deska ohrani robova);
- prečna: `n_stikov = Σ (kosi × nosilci, ki jih prečkajo)`, `vijaki = 2·stikov`
  (odprtine izločijo nosilce brez materiala);
- pritrdila nosilca/stebra = 2 na kos.

Dokazila: `tests/test_proizvodni_model.py` (ročne T-vrednosti 20/40/80,
14/26/52, 19/37/74, 11/44/88, 22/22/44), križanje strani PDF s pypdf
(stran 1 in 2 kažeta 80, „120 kos“ je odsoten), primerjava s štetjem
pik v risbi (40 stikov × 2).

**Past predloge:** `proizvodni_model` je za neznano predlogo (npr. ASCII
`pokoncna`) tiho uporabil prečno vejo (160 namesto 80 vijakov). Zdaj vrže
jasno `ValueError` (test T11).

## 3. Model reza in kerf (§5)

**Fizični model (dokumentiran, enoten):** `n` kosov dolžine `k` iz traku `B`
potrebuje `n−1` rezov, če se zadnji kos konča ob robu (flush), sicer `n`
rezov (zadnji loči ostanek). Kapaciteta:
`kos_iz_vira(B, k, w) = (B + w) // (k + w)` ⇔ največje `n` z `n·k + (n−1)·w ≤ B`.
Ostanek: `max(0, B − n·(k + w))` — šprica < kerf se vknjiži v porabo žage.
Mejni primer iz naloge: 3 kosi 500 mm, kerf 2, surovca [1002, 1552].

| | greedy (pred) | DP (zdaj) | optimalno |
|---|---|---|---|
| trakovi | `[(1002,2),(1002,1)]` | `[(1552,3)]` | `[(1552,3)]` |
| surovci | 2 | **1** | 1 |
| skupni odpad | 500 mm | **46 mm** | 46 mm |

Popravki:
1. `optimiziraj_zalogo` → **dinamično programiranje** (globalno optimalno
   za enake kose); kriterij (leksikografsko): (1) najmanjša skupna
   nabavljena dolžina, (2) najmanj trakov, (3) najmanj odpada.
   *Razširitev:* če bi bil `MIN_OSTANKA` vrednostno pomemben, bi bil
   optimalni problem NP-težek (bin packing z ohranjanjem ostankov);
   trenutno so ostanki le evidenca, zato je DP dopusten — dokumentirano.
2. `razrez_kosov` (FFD, mešane dolžine) usklajen z modelom B (prej je
   vsak kos plačal svoj kerf in zavračal kose, ki fizično gredo —
   3000 iz traku 3000), + best-fit surovec + konsolidacija trakov.
   Za mešane dolžine je algoritem hevrističen (BFD + konsolidacija),
   poimenovan in dokumentiran kot tak; za majhne primere so rezultati
   preverjeni z neodvisnim reševalnikom.
3. `ostanek_po_rezih`: prekoračitev kapacitete vrže `ValueError`
   (prej tiho 0); A5 invariante v `razrez_podatki` so dejavne
   (`kol ≤ kapaciteta`, `(n−1)·w ≤ poraba kerfa ≤ n·w`).

**Neodvisna verifikacija:** `tests/test_rez_model.py` vsebuje ločen
referenčni reševalnik (izčrpna kombinatorična enumeracija polnitev) in
primerja (ΣB, št. trakov) s produkcijo na fiksni mreži 10 primerov —
10/10 ujemanj. Robni primeri, dolga serija (600 kosov), mešane dolžine
z invariantami.

## 4. Vrata in model okvirja (P0)

Pod-agent 1 je dokazal fizično neskladje: kosovnica je rezala okvirna
stojala široka 60 mm (`prečka = S_o − 2·60`), geometrija pa je štela le
5 mm režo (`w_k = S_o − 2·5`) → 60 + 990 + 60 = 1150 > 1000 mm.

**Nov model (dokumentiran, edini):** okvirna stojala stojijo znotraj
odprtine; vodoravna veriga:

```
2·SIRINA_OKVIRJA + r_bok + Σw_k + (n_kril−1)·r_med + r_bok = S_o
```

| primer | prej w_k | zdaj w_k | veriga |
|---|---|---|---|
| enokrilna 1000 | 990 | **870** | 60+5+870+5+60 = 1000 |
| dvokrilna 3000 | 1490 | **1430** | 60+5+1430+10+1430+5+60 = 3000 |
| pasja 700 | 345 | **285** | 60+5+285+285+5+60 = 700 |

Ostalo: **P6 diagonala** je zdaj hipotenuza NOTRANJIH mer krila
`ceil5(hypot(w_k−2·40, h_k−2·40))` pri vseh treh (spec, koda, risba —
prej tri različne vrednosti; 1000×2100 → 2120); `tecaji_skriti` se zdaj
pravilno prenaša v kosovnico (prej vedno TEČ-STD); `preveri_odrtine`
preverja dejanske višine odprtin (prej višino ograje — kontrola mrtva);
krilo, manjše od profilov, je zavrnjeno z jasno napako.

**Sprememba testov (utemeljeno):** `tests/test_vrata.py` (4 vrednosti) in
`tests/test_dxf.py` (1 vrednost) so zaklepali prejšnji, fizično neskladen
model — vrednosti so posodobljene z novim modelom in komentarji. Noben
test ni bil prilagojen »da ostane zelen« brez spremembe kode.

## 5. Trde dimenzije in izpisi (§7)

Odstranjene/utemeljene trde dimenzije: `60×40` (steber), `90×90×6`
(osnova), `80×40×3`/`60×40×3` (profili), `50×50×5` (nosilec), kota
„60 mm“ v detajlu, `2100` v razrezni skupini prehoda → vse iz
konfiguracije (`PRIVZETO`: `profil_zg_dim`, `profil_sp_dim`, `nosilec_dim`,
`osnova_dim`) ali imenovanih konstant (`vrata.SIRINA_OKVIRJA` ipd.).
Naročilo prečne zdaj ločeno navaja zgornji in spodnji profil ter nosilne
nosilce (prej so bili spodnji profil in nosilci izpuščeni), imena
vijakov so enotna čez vse strani.

`preveri_cfg`/`proizvodni_model`: neznane predloge vržejo napako;
konfiguracije s preseženimi višinami so zavrnjene (brez tihih sprememb
mer) — velja od issue #2 in se preverja s testi.

## 6. Ponovljiv Windows build (§9)

Orodje: `python build_windows.py --smoke` (enoten, dokumentiran postopek:
različice + git stanje → PyInstaller iz `TehnicnaRisba.spec` → SHA-256/
velikost → funkcionalni smoke prek `--brez-zaslona` / `TEHNICNA_RISBA_HEADLESS=1`
oba načina, hermetično s `TEHNICNA_RISBA_DATA` v temp mapi) — struktura
in pravila: `docs/build.md`.

Popravki po reviziji pod-agenta 4: headless veja z `try/except` (windowed
EXE sicer odpre modalni dialog in visi), `Pillow` v `requirements.txt`
(`merjenje.py` ga uvozi nepogojno) + `requirements-build.txt` (freeze),
spec: `upx=False` (UPX ni nameščen — konsistenten izid), dedup/razširitev
`excludes` (`PIL.ImageQt` ipd. — EXE 198 → 103 MB), `hiddenimports`
zaklepanje (ezdxf, yaml, PIL.ImageTk).

Rezultati in kontrolne vsote: `build-zapisnik.json` (različice, git
commit/veja/dirty, spec sha256, EXE sha256/velikost, smoke: PDF 3 strani
preverjen s pypdf, oba načina zagona). **Omejitev ponovljivosti:**
PyInstaller ne zagotavlja bit-identičnega izida (časovni žigi v PE) —
ponovljivost pomeni isti postopek + iste različice → delujoč EXE z
enako funkcionalnostjo; hash se vodi za sledljivost.

**Sledljivost izdaj:** obstoječa `v1.0`/`v1.1` nimata zapisanega commit
SHA in sta nastali pred tem postopkom; pravilo za naprej (docs/build.md):
nova izdaja = nov tag, objavljena kot DRAFT šele po potrditvi (§9),
nikoli zamenjava assetov obstoječega taga.

**Izdaja NI objavljena** — EXE je samo v `dist/` in ga je treba
objaviti šele po potrditvi (§9/§10). Neobjavljeno je tudi preverjeno na
GitHubu (ni novih release-ov). Znana omejitev: `migracija.py` (shema v2)
ni vključena v EXE — dokumentirano v docs/build.md.

## 7. QA ugotovitve in testni obseg

Pod-agent 3 (QA) je pregledal teste, pokritost in **vsebinsko** preveril
artefakte (5 konfiguracij: PDF strani/besedilo s pypdf, CSV kosovnice s
seštevki, nalepke, DXF+PDF skupaj, dolga serija 60 kosov) — **med
artefakti in internimi izračuni ni neskladij** (vijaki enaki na strani 1,
strani 2 in v naročilu; CSV vrstice = kosovnica; P6 diagonala v kosovnici
in DXF skladna).

Najdbe in odziv glavnega agenta:

| Najdba | Resnost | Rešitev |
|---|---|---|
| dokstring `test_vrata.py` je dokumentiral stare vrednosti (990/1490/345) | P1 | odpravljeno — dokstring opisuje nov model (870/1430/285) |
| vakuumska asercija `"80" in narocilo` (podniz tudi v "Ø8×80") | P1 | odpravljeno — natančna vrstica `"- RF M8×70 Inox — 80 kos"` + `"120 kos" not in` |
| `proizvodni_model` z nepopolnim `mere` vrže surovi `KeyError` | P2 | dokumentirano: javni vstop je `generiraj`/`zdruzi`; neposredni klic je interni API |
| headless način brez testov | P2 | odpravljeno — `tests/test_zagon.py`: kode 0/1/2, branje JSON/YAML, resničen CLI klic (`TEHNICNA_RISBA_HEADLESS=1`) s preverjenim PDF; vstopna točka `vmesnik.zazeni_brez_zaslona` |
| `generiraj({})` tiho piše `BO-001.pdf` v CWD | P2 | odpravljeno (v1.5.2): manjkajoč `izhod` je `ValueError`, v CWD ne nastane nič; `tests/test_validacija_tipov.py` |
| `preveri_cfg` se je sesul na `razmak_stebrov: 0`, napačni obliki `vrata`/`prehodi` in `inf` (fuzz) | P2 | odpravljeno (v1.5.3): vsi primeri so napaka v seznamu; 18 novih testov + CLI brez sledi sklada; fuzz brez izjem |
| nekatere veje (fig3/fig4 degradacija, krajšanje rezalnega načrta, `preveri_cfg` B1–B7, rotacija segmentov v DXF) brez testov | P2/P3 | tipska odpornost `preveri_cfg` pokrita (v1.5.2); CLI `--dxf` in `--potrosi-ostanke` pokrita z resničnim podprocesom (v1.5.4); ostale veje so še vedno znana vrzel — predlogi T1–T12 so zapisani za razširitev testne suite |
| večsegmentni projekt je v PDF tiho izgledal kot en segment | P2 | odpravljeno (v1.5.4): PDF zabeleži opozorilo „več segmentov … samo glavni pogled … DXF“; test v `test_pdf_ciklus.py`; DXF ostaja polni izvoz |
| `predloga: "POKONČNA"` je obšla validacijo pokončne (primerjava z malo začetnico) | P2 | odpravljeno (v1.5.5): `zdruzi` in `preveri_cfg` normalizirata ime; velika začetnica ne obide geometrije, neznana predloga se še vedno zavrne |
| tip segmenta `"OGRAJA"`/tipkarska napaka je v DXF tiho postal pokončna ograja (`else` veja) | P1 | odpravljeno (v1.5.6): tip se normalizira, neznan se zavrne; `preveri_cfg` preveri obliko segmentov in `mere` |
| dve definiciji odpada na montažnem listu (PORABA „odpad“ vključuje kerf, REZ „ostanek“ ga ne) | P3 | konservativnost namerna — zapisano v docs/build.md in poročilu; predlog T10 to zaklene |

- skupaj **163 testov** (74 iz #2 nespremenjenih + 61 iz #3 + 28 novih),
  vsi zeleni; testni program modela reza je neodvisen od produkcijskega;
- preverjanje artefaktov (ne le funkcij): PDF strani/besedilo s pypdf
  (križanje strani 1↔2), CSV kosovnice vsebinsko (vrstice, seštevki),
  DXF okrogla vožnja z ezdxf (že iz #3);
- znane omejitve (poštene, dokumentirane): kotna postavitev segmentov v
  tlorisu je bodoče delo (podatkovni model `kot` obstaja; `generiraj` PDF
  segmentov ne upošteva — DXF jih), ostanki se ne porabljajo čez dolžine
  zalog v `razrez_kosov`, dimenzije v DXF so statične (brez G-kode —
  disclaimers v DXF/README/docs), `migracija.py` ni v EXE.

## 8. Povezave

- `tests/test_rez_model.py` — neodvisni regresijski program modela reza
- `tests/test_proizvodni_model.py` — kanonični model količin (T-vrednosti)
- `docs/dxf-specifikacija.md`, `docs/issue-3-vrata-dxf.md` — spec (usklajeni)
- `build_windows.py` + `build-zapisnik.json` — build in dokazila