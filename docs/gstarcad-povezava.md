# GstarCAD 2027 → naš projekt (povezava, ne kopiranje)

> Pobuda uporabnika: „preveri, če lahko iz C:\Users\admin\Documents\gstarcad\
> GstarCAD 2027 kaj vzameš in dodaš v naš projekt.“

## Kaj je v mapi (pregledano)

| Vsebina | Kaj je | Uporabno za nas? |
|---|---|---|
| `gcad.exe`, `GcLauncher.exe` | izvršilni program GstarCAD 2027 | ✅ **DA** — vanj odpiramo naše DXF-je |
| `pdftodxf/` (`pdftocad.grx`) | vtičnik PDF → DWG/DXF | ⚠️ ločen pretvornik v GstarCAD-u; naš program risbe GENERIRA, ne uvaža PDF — ni nam potrebno; uporabnik ga lahko uporabi sam |
| `Support/` (`.lsp`, `.fas`) | LISP rutine GstarCAD | ❌ **lastniška koda — NE kopiramo** |
| `Fonts/` (SHX) | pisave | ❌ lastniške — ne kopiramo; naš DXF uporablja standardni tekst |
| `UserDataCache/Template/` (`gcadiso.dwt`, Title Block DWG) | vzorčne predloge/naslovni bloki | ❌ vzorci GstarCAD — ne kopiramo; naš naslovni blok je ISO 7200 (lasten) |
| `ExtendCmd/*.dwg` | bloki vtičnika Undet (točkovni oblaki) | ❌ nepomembno za ograje |
| `*.dll`, `*.grx`, `*.gdx` | knjižnice | ❌ lastniške binarne datoteke |

**Pravilo:** v odprtokodni repozitorij NE gredo lastniške datoteke GstarCAD.
Smemo pa **integrirati** (zagnati nameščen program, odpreti našo datoteko
vanj) in upoštevati **kompatibilnostne konvencije**.

## Kaj dodajamo v projekt

1. **`dxf_izvoz.najdi_cad()`** — zazna nameščen CAD: `GCAD_EXE`/`GSTARCAD_EXE`
   okoljska spremenljivka → `%ProgramFiles%\GstarCAD*\gcad.exe` →
   `~\Documents\gstarcad\*\gcad.exe` (uporabnikova postavitev!) → AutoCAD
   `acad.exe`. Vrne `(pot, iskren opis)`.
2. **`dxf_izvoz.odpri_v_cad(pot)`** — odpre DXF/DWG z zaznanim CAD-om
   (`subprocess.Popen([cad, pot])`); če CAD ni zaznan, uporabi privzeto
   sistemsko povezavo (`os.startfile`) in to **iskreno pove**.
3. **Meni Datoteka → „Odpri DXF v CAD-u“** + vprašanje „Odprem v CAD-u?“
   po uspešnem DXF izvozu (isti vzorec kot terenski PDF odpre ogledovalnik).
4. **Kompatibilnost:** naš DXF je R2010 (AC1024), mm (`$INSUNITS=4`),
   ISO 13567 plasti, ACI barve — GstarCAD 2027 to odpre brez pretvorbe.
   (Dokaz: strukturni test + zagon `gcad.exe` z našim DXF.)

## Iskrene meje

- Zagon `gcad.exe` pokaže, da se program **zažene** z našo datoteko;
  vizualne vsebine ne moremo potrditi brez uporabnikovega zaslona
  (lastniški CAD ni avtomatiziran kot naš GUI test).
- DWG izpisa ne izvajamo neposredno (DWG je lastniški format) — GstarCAD
  odpre naš DXF in ga lahko uporabnik sam shrani kot DWG. Če bi kdaj
  potrebovali avtomatski DWG, bi to šlo prek ODA Teigha (ločena licenca).