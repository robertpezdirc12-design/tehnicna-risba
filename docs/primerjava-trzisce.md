# Primerjava: naše tehnične risbe proti najboljšim programom na trgu

*Pregled narejen 2026-11-21 (viri: spletne strani/dokumentacija produktov, spodaj).*
*Vprašanje: „primerjaj, kako generirajo najboljši — kaj je videti na spletu —
z našimi tehničnimi risbami, temeljito.“*

## 1. Kdo je na trgu (štiri skupine)

### A. Specializirani generatorji risb za ograje/vrata/ograje (najbližja konkurenca)
| Produkt | Kaj naredi | Format / cena |
|---|---|---|
| **Ornamental Designer Pro** (ornamentaldesignerpro.com) | risanje vrat/ograij/h ograj brez CAD; „Tig“ asistent nariše iz opisa; mere, kote, koti reza, bend sheet; **logotip na dokumentih** | PDF, DXF, SVG, PNG, JPEG, Excel; brezplačno |
| **CAD60** (cad60.com) | parametrični generator iz kataloga 182 modelov; vpišeš mere → A4 paket: ortogonalni pogledi, kote, cut list „v 60 sekundah“; mere izmerjene z 3D modela | PDF paket; načrt „Fabricator“ = zgradijo tvoje modele |
| **FabCAD** (fabcad.com) | avtomatizacija na AutoCAD jedru; knjižnica **16.000 odlitkov/kovanih kosov** proizvajalcev; BOM s koti reza | vtičnik/paket za izdelovalce |
| **Metronel — Steel fence designer** (metronel.com) | brezplačno: enaka polja, 3D model vsakega polja, cut list, teža; knjižnica 119 kovanih elementov | splet, brezplačno |
| **SteelCalc Pro** (steelcalcpro.com) | 20 kalkulatorjev (od stopnic do nestinga); „live BOM“; izpis DXF na CNC, PDF v delavnico, ponudba stranki — **iz istega posla** | free / Pro |

### B. Industrijsko risanje jeklenih konstrukcij (zgornji razred)
| Produkt | Ključne zmožnosti |
|---|---|
| **Tekla Structures** | „one click“ delavniške risbe, **samodejno upravljanje revizij**, BOM, NC/DSTV za CNC, IFC; revizije usklajene z modelom |
| **Autodesk Advance Steel** | 3D model → avtomatske delavniške risbe, BOM, NC datoteke; integracija z AutoCAD/Revit |
| **SDS/2** | globoka avtomatizacija veznih detajlov |

Njihova filozofija (OD3, 2026): *„en model, mnogo izpisov — ena revizija“*; najpogostejša napaka delavnice ni slab model, ampak **nova risba ob stari NC datoteki**.

### C. Optimizatorji razreza / nestinga
| Produkt | Opomba | Cena |
|---|---|---|
| **CutLogic 1D / 2D** | 1D: palice/cevi/profili; sledenje ostankom, cenovno-ozaveščen rez; 2D: DXF + G-code | 799 $ (1D) / 999 $ (2D) enkrat |
| **MaxCut** | namenjen mizarjem; kalkulacija stroškov | 20 $/mesec |
| **Deepnest** (odprta koda) | 2D nesting nepravilnih kosov; vzdrževan fork deepnest-next | brezplačno |
| **CutOptim / CutForge / EZNESTING** | CSV/XLSX izpisi, PDF načrti rezov, NC1 uvoz | free–naročnina |

### D. Spletne ponudbe/CRM za ograje (prodajni sloj)
FenceBuilder Pro (79 $/mesec), FencePro.ai (99–150 $/mesec, z „AI Visualizer“), FenceTracer (180 CAD/mesec), Dirtface (99 $/mesec), Quote Composer (79–149 $/mesec) — skupno: **blagovne znamke PDF ponudbe**, povezava za stranko (brez prijave), revizije ponudb, davki/depoziti, sledenje strankam.

### E. Odprtokodni generatorji tehničnih risb (zanimivo za nas!)
- **draftwright** (github.com/pzfreo/draftwright) — ISO 7200 naslovni blok, ISO 7573 kosovnica, **determinističen izpis** (isti vhod = isti bajti), `diff` med revizijama z označenimi spremembami, DXF z uredljivim besedilom in atributi.
- **Emirhan-1111/technical-drawing** — ISO 128/129-1/286/5457/7200; vsak list se pred zapisom **samodejno preveri** (prekrivanja besedil, vsebina zunaj okvirja, manjkajoči vnosi) — zelo podobno naši „kontroli pravilnosti“.
- **mechpilot** — 2D risanje po ISO s „preveri ob vsaki spremembi“ (manjkajoče kote, prileganja, prazna polja naslovnega bloka).

*Opomba: uporabnik ima v Downloads mapi `draftwright-demo` — očitno ga že preizkuša.*

---

## 2. Primerjalna matrika (naš TehnicnaRisba proti najboljšim)

| Zmožnost | Najboljši na trgu | Naš TehnicnaRisba | Ocena |
|---|---|---|---|
| **Vnos**: parametrične mere | ✓ vse (CAD60, FabCAD, SteelCalc) | ✓ ograja + pokončna + vrata | = |
| **Vnos**: fotografija → risba | redko; FencePro.ai „AI Visualizer“ (nevronske mreže!) | ✓ klasični CV **brez AI modelov**, mere z zaupanjem (izmerjeno/izračunano/ocenjeno) | **MI BOLJE (poštenost)** |
| **Terenske skice** | ✗ (ločene aplikacije) | ✓ vgrajen urejevalnik + vstavljanje slik | **MI BOLJE** |
| **Delavniški paket PDF** | ✓ (Tekla: risbe + seznami) | ✓ A3: risba + montažni + predračun + nalepke | = |
| **Kote / standardi risanja** | Tekla/Imge: ISO 128/129, GD&T, detajli, prerezi | osnovne kote, ISO 7200 naslovni blok (STATUS) | **ONI BOLJE** |
| **DXF** | ✓ (plasma/laser; „layer mapping must match the nest“) | ✓ ISO 13567 plasti, konture za CAM | = |
| **DWG** | ✓ (FabCAD na AutoCAD) | ✗ | ONI BOLJE |
| **NC/DSTV za stroje** | Tekla/Advance: DSTV/NC1 (a „dialect varies by maker“) | △ informativen G-code + cutlist CSV | ONI BOLJE |
| **Razrez 1D** | CutLogic: ostanki, cenovno-ozaveščen, sledenje zalogi | ✓ optimizator + **odpisi ostankov** + primerjava z ročnim rezom | **MI BOLJE (metrika odpada)** |
| **Kosovnica / BOM** | ✓ vse | ✓ CSV + nalepke | = |
| **Ponudba / ceniki** | SaaS: blagovne znamke, revizije, strankina povezava | ✓ PDF ponudba (3 variant), „cena po dogovoru“ brez izmišljanja | ONI (prodajni sloj) / MI (poštenost) |
| **Revizije / asociativnost** | Tekla: „one model, one revision“; draftwright `diff` | ✗ STATUS polje, brez zgodovine revizij | **ONI BOLJE** |
| **3D prikaz** | ✓ povsod (CAD60 mere iz 3D modela) | △ 3D predogled (informativen) | ONI BOLJE |
| **Knjižnice kovanih kosov** | FabCAD 16.000; Metronel 119 | △ `mechanical/` katalog vijakov (nepopoln) | ONI BOLJE |
| **Statika** | Scia/Tekla: polni izračuni | △ INFORMATIVNI pregled (povpraševanje W/I, ne nosilnost) — pošteno označeno | namerno |
| **Označevanje zaupanja meritev** | ✗ nihče ne oglašuje | ✓ (izmerjeno/izračunano/ocenjeno/nezno, † ‡ ≈ ??) | **MI EDINI** |
| **Zavrnitev nevzdržnih meritev** | ✗ | ✓ (javno zavrne „NEZNANO“) | **MI EDINI** |
| **Testi / kakovost kode** | zaprta koda | ✓ 314 testov, ruff/mypy/coverage vrata | **MI BOLJE (preglednost)** |
| **Cena** | 79–180 $/mesec SaaS **ali** 799–999 $ enkrat | brezplačno (EXE, deluje brez povezave) | **MI BOLJE** |
| **Delo brez povezave / zasebnost** | SaaS = oblak | ✓ popolnoma lokalno; fotografije ne zapustijo računalnika | **MI BOLJE** |
| **Blagovna znamka (logo) na dokumentih** | ✓ Ornamental Designer Pro | △ besedilna polja podjetja, brez slike logotipa | ONI BOLJE |
| **Povezava za stranko / CRM** | ✓ FenceBuilder Pro ipd. | ✗ (ni namen) | ONI (izven našega obsega) |

---

## 3. Kaj delajo NAJBOLJE — in kaj se iz tega lahko naučimo

1. **„Risba = načrt = cut list = ponudba“ iz enega klika** (Ornamental Designer Pro,
   SteelCalc Pro: „All of it comes from the same job“). Mi to *že imamo* (en vir
   resnice: `proizvodnja.izracunaj_kolicine`) — a je treba to jasneje prikazati.
2. **Revizije in asociativnost** (Tekla, draftwright `diff`): sprememba modela mora
   preliti vse izpise hkrati; največja napaka je „nova risba ob stari NC datoteki“.
   Mi: osvežitev = novi izpisi, brez zgodovine revizij. **Naša največja vrzel.**
3. **Samodejni pregled lista pred izpisom** (Emirhan-1111: prekrivanja, vsebina
   zunaj okvirja, manjkajoča polja). Mi imamo delno („kontrola pravilnosti“ +
   preverjanje DXF) — lahko razširimo na cel list.
4. **Knjižnice katalogov proizvajalcev** (FabCAD 16.000 kosov): kosi so že
   narisani in v BOM. Naš `mechanical/` katalog je začetek v tej smeri.
5. **Izpisi po meri stroja** (DSTV „dialect varies by maker“): profesionalci
   izvažajo za TOČNO določen stroj. Naš G-code je pošteno označen kot
   informativen — prava pot je „profil stroja“ (žaga X: tak format).
6. **Prodajni sloj** (blagovne znamke PDF, povezava za stranko, revizije ponudb).
   Zunaj našega obsega, a logotip na dokumentih je nizko viseče sadje.

## 4. Kaj delamo MI bolje (naše prednosti — ne olepševati!)

1. **Sistem poštenja meritev** (izmerjeno/izračunano/ocenjeno/nezno; zavrnitev
   nevzdržnih vrednosti) — noben komercialni produkt tega ne oglašuje.
   Fotografske mere so pri nas označene s zaupanjem; „AI Visualizer“ pri FencePro.ai
   generira podobe brez merljivosti.
2. **Metrika odpada proti ročnemu rezu** (ne le izkoristek %): poštena primerjava
   po profilih, v vrstnem redu kosovnika.
3. **Brez AI modelov** (zahteva naročnika): klasična geometrija, deluje lokalno.
4. **Preglednost kode**: 314 testov, kakovostna vrata, determinizem.
5. **Cena in zasebnost**: brezplačno, brez povezave, fotografije ostanejo lokalno.
6. **Integrirani terenski urejevalnik** s slikami — konkurenca ima le risanje.

## 5. Prednostna lestvica izboljšav (ponudba — NE obljuba)

| # | Izboljšava | Utemeljitev iz primerjave | Velikost |
|---|---|---|---|
| 1 | **Revizije dokumentov** (št. revizije, zgodovina, „diff“ povzetek sprememb) | najpogostejša napaka pri profesionalcih | srednja |
| 2 | **Kontrola celotnega lista** (prekrivanja, vsebina zunaj okvirja) pred izpisom | Emirhan-1111/draftwright; nadgradi obstoječo kontrolo | srednja |
| 3 | **Logotip podjetja na dokumentih** (PNG/SVG v naslovni blok) | Ornamental Designer Pro; pričakovanje strank | majhna |
| 4 | **Profili strojev** za G-code (nastavljiv format izpisa) | DSTV „dialect“ problem | srednja |
| 5 | **Razširjen `mechanical/` katalog** (vijaki/kovani kosi → BOM) | FabCAD/Metronel knjižnice | velika |
| 6 | DWG izvoz (prek ezdxf ali pretvorba) | FabCAD/AutoCAD okolje | majhna |
| 7 | Večstranski terenski list / glave in noge | profesionalni terenski paketi | majhna |

## 6. Viri (2026-11-21)

- ornamentaldesignerpro.com — risanje vrat/ograij, cut list, izpisi z logotipom
- cad60.com — parametrični paket risb iz kataloga (182 modelov)
- fabcad.com/products — avtomatizirane ograje/vrata, 16.000 kovanih kosov, AutoCAD
- metronel.com/tools — brezplačni steel fence designer (3D, cut list, teža)
- steelcalcpro.com — kalkulatorji → DXF/PDF/ponudba iz istega posla
- tekla.com/solutions/steel-detailing — „one click“ risbe, revizije, BOM, NC
- od3.co.uk — „From Tekla model to workshop“ (NC/DSTV, DXF, revizije)
- origin-team.com / tjsteeldetailers.com — Advance Steel / SDS/2 primerjave
- eznesting.com/blog/best-cut-list-optimizer-software-2026 — CutLogic 799 $, MaxCut 20 $/mes
- tmachines.com/cutlogic-1d — CutLogic 1D (ostanki, cenovno-ozaveščen rez)
- github.com/pzfreo/draftwright — ISO 7200/7573, determinizem, revizijski diff
- github.com/Emirhan-1111/technical-drawing — ISO 128/129/286 + samodejni pregled lista
- fencebuilderpro.com (79 $/mes), fencepro.ai (99–150 $/mes), fencetracer.com (180 CAD/mes), quotecomposer.com (79–149 $/mes)
- cutforge.eu (NC1), cutoptim.com/docs/exports (CSV/XLSX izpisi), klietsch.com (DSTV Assistant)