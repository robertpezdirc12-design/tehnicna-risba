# Temeljit preizkus GUI-ja (smoke test)

> Nastalo po zahtevi „testiraj vse temeljito“. Ponovljiv preizkus vseh
> glavnih funkcij programa — z resničnim GUI-jem in preverjanjem VSEBIN
> izhodov (ne le odsotnosti izjeme).

## Zagon

```
python scripts/preizkusi_gui.py
```

Izhod: vrstica `OK …` za vsako preveritev, na koncu `SKUPAJ: N | NAPAK: 0`
(izhodna koda 0). Porabljeno: ~3 minute. Uporabi **generirano** testno
sliko (1600×1200) — zasebnih fotografij ne potrebuje.

## Kaj preveri (55 kontrol)

| Področje | Preveritve |
|---|---|
| Scena | vstavi sliko, namera-vidna, rotacija levo/desno, foto v projekt, odložišče (prazno), odstrani |
| Merilo / merjenje | 2 klika + znana mera → px/mm, meritev v mm, status „izmerjeno po sliki“ |
| Projekt | shrani `.yaml` → odpri → krožno potovanje; odpri sliko prek „Odpri projekt…“ |
| Risba | NARIŠI RISBO (ograja + pokončna) — **pypdf** preveri besedilo: `SPREDNJI POGLLED`, `T1`, `▲ VRH`, `ISO 2768`, `KONTROLNI SEZNAM` |
| Izvozi | DXF (**ezdxf** preveri ISO 13567 plasti), CNC (CSV + G-code), naročilo (odložišče), ponudba (PDF) |
| Revizije / status | nova revizija (diff), statusni tok V DELU → ZA POTRDITEV → IZVEDENO |
| Orodja | živi povzetek, preprosti/napredni način, statika, primerjava načrtov razreza, odpis ostankov, 3D, nova vrsta, čarovnik, O programu, tema, vrstica stanja, undo/redo, pomoč |
| Merjenje s slike | kalibracija, izračun scale, meritev (mm), območje, zaznaj lamele, zaznaj vijake, pobriši, shrani `.yaml` (yaml se prebere) |
| Terenski | validacija dokumenta, vstavi sliko/besedilo, zavrti 45°, undo/redo, shrani/odpri, PDF |

## Pasti, ki jih skripta obvladuje (in zakaj)

- **Nariši risbo je asinhrono** (nit) — skripta izbriše ciljno datoteko,
  počaka na **konec niti** in šele nato bere; branje „na hitro“ bere
  staro/prazno datoteko (kar je povzročilo lažne napake v razvoju).
- **Modalni dialogi** (`wait_window`) se samodejno zaprejo (avtomatski
  klik na potrditveni gumb), sicer klici obtičijo.
- **`StringVar`-ji** se nastavljajo s `.set()`, ne z `setattr` —
  `orodje` v terenskem je `StringVar`, ne niz!
- `terenski_list.preveri_dokument` VRŽE `ValueError` pri napaki in vrne
  `True` pri veljavnem dokumentu.

## Najdba iz preizkusa (edina prava)

`tests/test_vmesnik.py::test_meri_slike_dvojna_korenina` je uporabljal
majhno sliko (200×120); plan-15 opozorilo „mala slika“ odpre **modalni
`messagebox`**, ki je v testih blokiral izvajanje (v celotnem paketu se
je test obesil na ~86 %). Popravek: test nadomesti `messagebox` s
prazno funkcijo (`monkeypatch`) — v pravem GUI-ju opozorilo ostane.

## Omejitev (iskreno)

Skripta preverja funkcije programa; NE preverja izgleda (screenshotov)
— za vizualne preveritve ostaja ročni ogled ali ločene slikovne
preveritve. Tudi tiskanja v fizični tiskalnik ne izvaja.