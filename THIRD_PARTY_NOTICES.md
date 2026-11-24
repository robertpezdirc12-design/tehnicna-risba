# Obvestila tretjih komponent (third-party notices)

Ta program (`TehnicnaRisba`) je lasten projekt pod licenco MIT (glej
`LICENSE`). Ker pa samostojna izvršilna datoteka **vsebuje tudi kodo
tretjih oseb**, so spodaj navedene njihove licence in razlog, zakaj so
vključene.

Zakaj je to potrebno: PyInstaller sam opozarja, da je izdelek mogoče
distribuirati pod poljubno licenco le, **če so izpolnjene licence
odvisnosti** (<https://pyinstaller.org/en/latest/license.html>), in
znano je, da PyInstaller med gradnjo odreže priložena licenčna besedila
(<https://github.com/pyinstaller/pyinstaller/issues/5666>). Zato
obvestila hranimo tukaj, v repozitoriju.

Tabelo vzdržuje skript in je strojno preverjena:

```bash
python scripts/preveri_licence.py --preveri   # 0 = usklajeno z okoljem
python scripts/preveri_licence.py --zapisi    # osveži tabelo
```

<!-- ZACETEK-TABELE -->
| Paket | Različica | Licenca | V EXE | Opomba |
|---|---|---|---|---|
| flask | 3.1.3 | BSD-3-Clause | ne | samo `api/index.py` (spletni API), ni v GUI build |
| matplotlib | 3.11.2 | Python Software Foundation License | da | risanje PDF |
| PyYAML | 6.0.3 | MIT License | da | konfiguracije in katalogi |
| numpy | 1.26.4 | BSD License | da | geometrija in slike |
| ezdxf | 1.4.5 | MIT License | da | DXF izvoz (pin 1.4.5) |
| Pillow | 13.0.0 | MIT-CMU | da | slike in Tk |
| ttkbootstrap | 2.2.7 | MIT AND (Apache-2.0 OR BSD-2-Clause) | da | teme GUI (neobvezno) |
| opencv-python | 4.11.0.86 | Apache Software License | ne | `TehnicnaRisba.spec` izključi `cv2`; foto/QR dela samo v Python različici |
| PyInstaller (bootloader) | 6.22.3 | GPL-2.0 z izjemo za vgrajevanje | da | orodje, ne knjižnica izdelka |
<!-- KONEC-TABELE -->

## Opombe k posameznim licencam

- **matplotlib** je pod lastno licenco, ki temelji na PSF (združljiva z
  MIT/BSD); ob razširjanju je treba ohraniti obvestilo o avtorskih
  pravicah. Zahteva tudi pisave, ki jih prinese matplotlib (lastne
  licence, priložene v paketu).
- **Pillow** je pod MIT-CMU (HPND); obvestilo je treba ohraniti.
- **ezdxf** je MIT.
- **PyYAML** je MIT.
- **numpy** je BSD-3-Clause.
- **ttkbootstrap** je „MIT AND (Apache-2.0 OR BSD-2-Clause)“.
- **PyInstaller** (bootloader v vsakem izdelanem EXE) je GPL-2.0 **z
  izjemo**, ki dovoljuje vgrajevanje tudi v lastniške izdelke; naša koda
  zato ostane MIT. Brez te izjeme vgrajevanja ne bi smeli izvajati.
- **OpenCV** (Apache-2.0) je v `requirements-build.txt`, a ga
  `TehnicnaRisba.spec` **izključi** (`cv2`), zato v privzetem EXE ni
  vgrajen: foto merjenje in QR oznake delujeta v Python različici.

## Česa namenoma ne vgrajujemo

`cadquery`/`OCP` (OpenCASCADE LGPL-2.1, `casadi` LGPL-3.0), `gmsh`
(GPL-2.0+), `pymeshlab` (GPL-3.0) in modeli OCR niso del izdelka. Razlogi
in pogoji, pod katerimi bi se to lahko spremenilo, so v
`docs/odlocitev-3d-in-ocr.md`.
