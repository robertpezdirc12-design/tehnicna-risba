# Načrt 14 — Delovni prostor „scena“: vstavi sliko → vprašaj namero → meri → potrdi

*Avtor: razvojna analiza ob uporabnikovi opazki (2026-11-22): „Vstavil sem
sliko in je ni — morala bi se prikazati v delovnem prostoru in vprašati,
kaj želim z njo narediti.“*

---

## 1. Izhodišče in problem

Delovni prostor glavnega okna (načrt 13) je danes **prikaz risbe**. Slika,
ki jo uporabnik vstavi (Orodja → Izberi fotografijo …), se shrani le v
polje `foto` obrazca — v delovnem prostoru se **ne pojavi** in program
**nič ne vpraša**. Uporabnik pričakuje logiko, ki je standard v najboljših
orodjih:

> slika se pojavi v prostoru → program vpraša „kaj želite narediti s to
> sliko?“ → izbrani ukaz → rezultat → **potrditev**.

Cilj načrta: to logiko narediti **temeljito, lokalno (brez AI) in pošteno**
(vsaka številka z oznako izvora).

---

## 2. Raziskava trga — kdo to že dela dobro

### 2.1 Neposredni konkurenti (ograje / gradbeni takeoff)

| Produkt | Kaj dela | Vzorec za nas | Vir |
|---|---|---|---|
| **FenceSpec** (AU) | „Turn site photos, hand-drawn plans and measured designs into fencing proposals“ — koraki 01 Ujemi (fotomere), 02 Načrtuj (2D teki, stebri, vrata, elevacije), 03 Prikaži (slogi/barve), 04 Ponudba | Cel tok **slika → mere → risba → ponudba** je industrijski standard; „upload a hand-drawn plan … review the extracted measurements and details, then apply them“ = **preglej, preden uporabiš** | fencespec.com.au |
| **FenceFlow** | „Trace the line — on a survey, blank grid or satellite photo — and every post, panel, bag of concrete and gate latch is counted and priced from the geometry“ | **Sledenje čez sliko** → samodejno štetje iz geometrije (ne iz besedila) | fenceflowapp.com |
| **FenceEstimatePro** | „Photo and sketch input … extract proposed runs and gates. **Check the result against your field measurements before applying it**“ | Izlučeno **nikoli tiho** — obvezna potrditev; tudi „marked survey PDF“ kot vhod | fenceestimatepro.com |
| **ArcSite** | Risba na terenu po tleh objekta, fotografije pripete risbam in ponudbam, AR-skan mej | Fotografija kot **dokazilo** ob risbi/ponudbi | arcsite.com |
| **Fence Pro** | GPS mere po satelitski sliki, točke shranjene z ograjo | Slika kot **podlaga za merjenje** | fencepro.app |

### 2.2 Merjenje in kalibracija s slike

| Produkt | Kaj dela | Vzorec za nas | Vir |
|---|---|---|---|
| **SolidWorks – Sketch Picture** | Slika se ob vstavitvi pojavi v risalnem polju in **samodejno pokaže orodje za merilo** (konstrukcijska črta z ročkama) — postaviš jo na znano dolžino, vpišeš vrednost, slika se skalira; čez sliko se riše | **Merilo takoj po vstavitvi**; opozorilo strokovnjakov: „perspective, lens distortion and unknown scale introduce error … verify final dimensions against a physical measurement“ — natanko naša poštenostna pravila | my.solidworks.com (Inserting and Resizing Sketch Pictures) · mechanitec.ca · cati.com |
| **Onshape – Insert Image** | Slika se postavi v skico z miško; **prva kota/mera, ki jo določiš, raztegne sliko na pravo mero** | „Prva znana mera določi merilo“ — kalibracija brez posebnih dialogov | cad.onshape.com/help (Insert Image) · onshape.com tech-tip |
| **ImageMeter** | Na sliki narišeš **referenčni pravokotnik z znanimi stranicami** (ali preprosto referenčno mero/perspektivno referenco) in izmeriš karkoli v isti ravnini; obstaja namizna različica (Win/macOS/Linux) | Referenčni pravokotnik (okno, plošča) kot **alternativa 2 točkama**; „reference does not have to exist physically — four points forming an imagined rectangle work“ | imagemeter.com/manual |
| **Scale Rule / FloorFigures** | Merjenje s fotografije načrta; **perspektivna korekcija** (4 kote znanega pravokotnika), opozorila: „one calibration can't be true everywhere“ | Iskreno opozorilo: eno merilo ne odpravi perspektive — vrednosti označimo z zaupanjem | scalerule.app · floorfigures.com |
| **HOVER** | 8 fotografij objekta → oblak → 3D model + mere → izvoz (PDF/Excel) → oblikovanje | Industrijski **tok** (slika → proces → pregled mer → oblikovanje → izvoz); za nas **nesprejemljivo**: AI + oblak (naš pogoj: brez AI, lokalno) | hover.to · help.hover.to |
| **CamToPlan / magicplan** | AR merjenje; magicplan „import and draw“: **rišeš čez uvoženo sliko**, fotografije gredo v poročilo/PDF | Slika kot **podlaga za risanje** + fotografija kot **dokazilo v PDF** | help.magicplan.app · apps.apple.com |

### 2.3 Vmesniški vzorci (splošno)

| Vir | Vzorec |
|---|---|
| **Figma** (Place Image, drag&drop, Ctrl+V) | Slika je predmet na platnu; ukazi se pojavijo ob izbiri; „Place Image“ = več slik zapored, vsako postaviš z miško |
| **Bluebeam Revu** (Image markup) | Slika je **predmet dokumenta**; tri poti vstavljanja (datoteka / kamera / skener) + drag&drop; isto obnašanje ne glede na vir |
| **UX Patterns Guide** (Toolbar, Context menu, Drag-and-drop upload) | Kontekstualna ukazna vrstica je **pripeta izbranemu predmetu**; meni se preoblikuje po stanju izbire; drop cona z jasnim vabilom + **enakovredna pot z gumbom** (dostopnost) |
| **Eleken (contextual menu), Linear, Canva dev** | „Scope the menu tightly to its target“ — le ukazi za izbrani predmet; **nič se ne zamenja brez jasne namere** (Canva: preview + potrditev namesto tihe zamenjave) |
| **SAP Fiori, Visa, Dropbox** (empty states) | Prazno stanje = **vabilo** (drop cona, gumb „Naloži prvo datoteko“), ne prazen ekran |

### 2.4 Skupni imenovalec vseh najboljših
1. **Vstavi → predmet se takoj vidi** (nikoli tiho v nek skriti žep).
2. **Takojšnje vprašanje po nameni** oz. kontekstualni ukazi za izbrano.
3. **Merilo/kalibracija pred merjenjem** (2 točki + znana dolžina ali referenčni pravokotnik).
4. **Rezultat se nariše preko slike** in ga uporabnik **pregleda ter potrdi**.
5. **Poštenost**: slika ni natančna — vrednosti preveri na objektu.

---

## 3. Arhitektura rešitve (za našo aplikacijo)

Delovni prostor postane **scena** s predmeti. V prvi fazi je predmet lahko
ena **slika** (kasneje tudi risba/skica — izven obsega tega načrta).

### 3.1 Podatkovni model (stanje scene v `vmesnik.App`)

```python
self.scena = {
    "pot":        None,   # izvorna datoteka slike (nikoli ne spreminjamo)
    "delovna":    None,   # začasna datoteka po rotaciji (kar prikažemo)
    "merilo":     None,   # px na mm — None = NI nastavljeno (NEZNANO)
    "merilo_vir": "",     # "2 točki + znana dolžina" | "referenčni pravokotnik"
    "merilo_opozorilo": "",  # npr. "perspektiva ni odpravljena"
}
```

Pravilo: `merilo = None` → vsaka razdalja iz slike se izpiše kot
**NEZNANO — merilo ni nastavljeno** (nikoli izmišljena številka).

### 3.2 Stanja delovnega prostora

```
PRAZEN  ──vstavi sliko──►  SLIKA (izbrana)  ──izberi namero──►  DELOVANJE
   ▲                            │                                  │
   └───────── odstrani ─────────┴────────── rezultat ──────────────┘
                                        (prikaz + potrditev)
```

- **PRAZEN** — drop cona z vabilom (obstoječe `sporocilo`, dopolnjeno).
- **SLIKA** — slika v prostoru + **vrstica namera** (glej 3.4).
- **DELOVANJE** — načini klikanja na sliki (merilo 2 točki, merjenje 2 točki).

### 3.3 Vstavljanje (vse poti vodijo v isto metodo `_scena_nalozi`)

| Pot | Ukaz | Opomba |
|---|---|---|
| Meni | **Vstavi → Sliko v prostor… (Ctrl+I)** | nova |
| Meni | **Vstavi → Sliko iz odložišča (Ctrl+V)** | `PIL.ImageGrab.grabclipboard()`; Ctrl+V vezan **samo na delovni prostor** (v vnosnih poljih ostane običajno lepljenje besedila!) |
| Meni | Orodja → Izberi fotografijo… | obstoječe — nastavi `foto`, **in** odloži v sceno (dopolnitev) |
| Miška | **drag & drop** datoteke na prostor | odvisno od `tkinterdnd2` — če ni nameščen, pot ostane v meniju (brez trde odvisnosti) |

### 3.4 Vrstica „Kaj želite narediti s to sliko?“ (namera)

Pojavi se **samo, ko je slika v sceni** (kontekstualno — ni lebdeči nered).
Vsak ukaz ima svojo pot tudi v meniju **Vstavi** (pravilo „vse v opravilni
vrstici“ ostaja).

| Ukaz | Kaj naredi | Obstaja že? |
|---|---|---|
| **Meri s slike** | odpre `merjenje.App` s sliko iz scene | da (`_meri_slike`) — dopolni z vhodom |
| **Avtomatska skica** | `photo_fence_proposal.avtomatska_skica` (klasični OpenCV) | da (`_avtomatska_skica`) — dopolni z vhodom |
| **Nastavi merilo (2 točki)** | način klikanja: 2 točki na sliki → vprašanje „znana dolžina (mm)“ → `merilo` + vir | **novo** |
| **Izmeri v prostoru (2 točki)** | brez merila → NEZNANO; z merilom → mm + „izmerjeno po sliki“ | **novo** |
| **Fotografija v projekt** | `v["foto"] = pot` (foto v PDF / terenski list) | delno (`_brskaj_foto`) |
| **Obrni levo / desno** | rotacija 90° (PIL), delovna datoteka | **novo** |
| **Odstrani sliko** | počisti sceno, prostor spet prazen | **novo** |

### 3.5 Potrjevanje rezultatov („Uporabi / Zavrzi“)
- Ukazi, ki **jih sproži uporabnik sam** (nastavi fotografijo projekta,
  rotiraj) = sama izbira je potrditev — brez odvečnih dialogov.
- Kar program **izluči iz slike** (avtomatska skica, mere), se **nikoli ne
  prenese v projektna polja samodejno**. Avtomatska skica izda PDF z
  oznakami zaupanja + opozorilo „PREVERI na objektu“ (že tako); če bi
  kdaj predlagala vrednosti za polja, šele po potrditvi (Canva-pattern:
  „replace content only with clear intent“).

---

## 4. Poštenostna pravila (obvezna, merilo celotnega projekta)

1. `merilo = None` → razdalje iz slike: **NEZNANO — merilo ni nastavljeno**.
2. Z merilom: izpis **„izmerjeno po sliki (± perspektiva) — preveri na
   objektu“**; oznaka `izmerjeno` velja za *pikselsko razdaljo*, ne za
   objekt — zato vedno s pripisom.
3. Predlog iz slike (avtomatska skica) — oznake `izmerjeno/izračunano/
   ocenjeno` (že v `photo_fence_proposal`) se NE spreminjajo.
4. Nič se ne zapiše v `cfg` brez izrecne uporabnikove akcije.
5. Merilo **ne odpravi perspektive** — to je povedano ob kalibraciji
   (vir: Scale Rule / FloorFigures / ImageMeter docs).

---

## 5. Implementacija

### 5.1 `vmesnik.py`
- `PredogledCanvas.slika_koordinate(e)` → (x, y) v koordinatah slike ali
  `None` (če klik zunaj) — preslikava:
  `ix = (e.x − (cw/2 + ox − W/2)) / faktor`, podobno `iy`.
- `App` stanje scene (3.1) + metode:
  `_scena_nalozi(pot)`, `_scena_iz_odlozisca()`, `_scena_obrni(kot)`,
  `_scena_pocisti()`, `_merilo_zacni()` / `_merilo_klik(e)`,
  `_merjenje_zacni()` / `_merjenje_klik(e)`, `_namera_pokazi/skrij()`.
- Meni **Vstavi** (nova kaskada): Sliko v prostor… (Ctrl+I),
  Sliko iz odložišča (Ctrl+V), — , Nastavi merilo (2 točki),
  Izmeri v prostoru (2 točki), — , Fotografija v projekt,
  Obrni sliko levo, Obrni sliko desno, Odstrani sliko iz prostora.
- Vrstica namera: `ttk.Frame` pod platnom v oknu prostora; gumbi kličejo
  iste metode kot meni; prikaz/skritje prek `pack/pack_forget`.
- `_meri_slike(pot=None)` in `_avtomatska_skica(pot=None)`: neobvezni vhod
  (scene) — obstoječe vedenje brez argumenta ostane.

### 5.2 Omejitve / tveganja
- `tkinterdnd2` ni v `requirements.txt` → drag&drop je **odvisnostno
  pogojen** (če manjka, ostanejo menijske poti; brez napake).
- `ImageGrab.grabclipboard()` vrača `None`, če odložišče ni slika → vljudno
  obvestilo, ne napaka.
- Klik na platno že pomeni „cel zaslon“ (`st_klik`) — načini merila
  **začasno** prevzamejo `na_klik` in ga po koncu povrnejo.

---

## 6. Testni načrt (`tests/test_scena_namera.py`)

1. `_scena_nalozi` → `scena.pot` nastavljen, platno prikazuje sliko
   (`_izvirna` ni `None`), vrstica namera vidna.
2. `_scena_pocisti` → vrstica skrita, stanje prazno.
3. Kalibracija: 2 točki + 1500 mm → `merilo ≈ px/mm`; **brez merila je
   razdalja NEZNANO** (metoda vrne `None`, ne številke).
4. Izmeri z merilom: znana razdalja v px → mm znotraj tolerance.
5. „Fotografija v projekt“ → `v["foto"]` = pot scene.
6. Rotacija: `delovna` se zavrti, `pot` ostane nespremenjena.
7. Meni Vstavi vsebuje vse ukaze (`test_meni_popolnost` PRICAKOVANO).
8. Brez tihe uporabe: `_scena_*` metode ne pišejo v `cfg` razen izrecne
   akcije „Fotografija v projekt“.

---

## 7. Izven obsega (potrjeno z analizo, a ne v tem načrtu)
- HOVER-podobno: AI + oblak (prepovedano z našimi pravili).
- Perspektivna korekcija s 4 koti (možna razširitev; ImageMeter vzorec).
- Več predmetov v sceni (slika + risba + skica hkrati) — naslednji korak.
- Risba čez sliko („import and draw“ kot magicplan) — CAD urejevalnik,
  izven obsega.

## 8. Merila sprejemljivosti
- [ ] Vstavljena slika se **takoj** pokaže v delovnem prostoru.
- [ ] Program **takoj vpraša** „Kaj želite narediti s to sliko?“.
- [ ] Brez merila NI izmišljenih številk (NEZNANO).
- [ ] Vsi ukazi dosegljivi iz menija **Vstavi** (ni skritih funkcij).
- [ ] Nič se ne zapiše v projekt brez izrecne akcije.
- [ ] Vsi testi zeleni + ruff + mypy brez novih napak.