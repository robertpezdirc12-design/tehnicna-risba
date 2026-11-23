# GstarCAD 2027 → naš projekt (konvencije, NE povezave)

> Pobuda uporabnika: „preveri, če lahko iz C:\Users\admin\Documents\gstarcad\
> GstarCAD 2027 kaj vzameš in dodaš v naš projekt.“
> Nato jasna zahteva: **„nesme biti povezano z gcad.exe — naš program;
> vzemi, kaj lahko vzameš.“**

## Odločitev (upoštevana)

Naš program **NI in NE BO povezan z `gcad.exe`** ali katerim koli
lastniškim CAD-om — nobenega zagona zunanjih programov, nobene
odvisnosti. Začasna integracija „odpri DXF v GstarCAD“ je bila
**odstranjena** (commit zanjo je razveljavljen z naslednjim).

Namesto tega smo iz CAD-sveta vzeli **odprte risalne konvencije** in jih
**vgradili samostojno** v naš program (lastna koda, brez kopiranja):

| Vzeta konvencija | Standard | Vgrajeno v naš program |
|---|---|---|
| **Šrafura prereza (45° tanke črte)** — prerezane površine so v CAD risbah vedno šrafirane (ANSI31) | ISO 128-50 | `risba.sachiranje` razširjen (lw/barva) + uporabljen v DETAJL 2 (obe predlogi) za prerez deske/lamele |
| **Šrafura betona (drobci + trikotniki)** | ISO 128-50 | `risba.srafura_betona` — DETAJL 1 (SIDRANJE), osnova |
| **Črtne vrste**: vidno polno, osi verižne (CENTER) | ISO 128-20 | že prej v DXF plasteh (`M-ANNO-CLIN` = CENTER) |
| **ISO 13567 plasti, ACI barve, mm 1:1** | ISO 13567 | že prej v DXF izvozu |
| **ISO 3098 višine besedila** | ISO 3098 | naše višine besedila (7/6/5 pt ≈ 2,5/2,1/1,8 mm) so v seriji — brez sprememb |

## Kaj NE vzamemo (in zakaj)

| Vsebina mape | Razlog |
|---|---|
| `gcad.exe`, DLL, `.grx`, `.gdx` | lastniške binarne datoteke — **ne kopiramo in ne kličemo** |
| `Support/` (`.lsp`, `.fas`) | lastniška koda |
| `Fonts/` (SHX pisave) | lastniške; naš DXF uporablja standardni tekst |
| `UserDataCache/Template/` (`gcadiso.dwt`, Title Block) | vzorci GstarCAD; naš naslovni blok je lasten ISO 7200 |
| `pdftodxf/` (PDF→DWG) | vtičnik znotraj GstarCAD; naš program risbe generira, ne uvaža |

## Iskrena meja

- Program ostaja **samostojen**: deluje brez nameščenega CAD-a.
- DWG ne izpisujemo (lastniški format); naš DXF odpre vsak CAD
  (tudi GstarCAD), če ga uporabnik želi uporabiti — **svoj ročno**,
  naš program ga ne kliče.