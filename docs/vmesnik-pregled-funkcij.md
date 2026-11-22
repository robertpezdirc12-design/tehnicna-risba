# Pregled: implementirane funkcije → prikaz v vmesniku

Vprašanje uporabnika: *„preveri, če vse funkcije, ki so narejene, prikazuje
vmesnik.“* Spodaj je sistematičen popis (avtomatizirano križanje klicev iz
`vmesnik.py`/`terenski_gui.py` proti modulom) in stanje po urejanju.

## Vidno v GLAVNEM vmesniku (vmesnik.py)

| Funkcija (modul) | Kje v vmesniku |
|---|---|
| risba.generiraj — PDF (risba + montažni + predračun + nalepke) | NARIŠI RISBO |
| predogled risbe (PNG) | PREDGLED RISBE • klik = CEL ZASLON |
| proizvodnja — naročilo (materialni nalog) | NAROČILO (kopiraj) |
| ponudba.narisi_ponudbo — 3 možnosti | PONUDBA (PDF) |
| dxf_izvoz.izvozi_dxf (ISO 13567 plasti) | IZVOZI DXF |
| **cnc.izvozi_cutlist + izvozi_gcode** | **CNC (CSV + G-code)** — prej nedosegljivo |
| projekti: shranjevanje cfg (YAML) | SHRANI PROJEKT (.yaml) • Ctrl+S |
| **projekti: nalaganje cfg (YAML)** | **ODPRI PROJEKT… • Ctrl+O** — prej nedosegljivo |
| tridimenzionalno (3D predogled) | 3D PREDGLED |
| statika (informativni pregled) | STATIČNI PREGLED |
| **nova_vrsta (pilot: lesena vertikalna, F4)** | **NOVA VRSTA (pilot)** — prej nedosegljivo |
| merjenje (kalibracija + merjenje s foto) | MERI S SLIKE |
| photo_fence_proposal.avtomatska_skica | AVTOMATSKA SKICA (iz foto) |
| fotografija + predogled | FOTOGRAFIJA IN IZHOD (Prebrskaj… + predogled) |
| ostanki (odpis skladišča) | ODPIŠI OSTANKE |
| posodobitev (preverjanje izdaje) | ⟳ Posodobitev |
| vrata (veriga modelov, cene) | VRATA IN PREHODI (tabela) |
| ttkbootstrap teme | ◐ Tema |
| undo/redo, čarovnik, živ povzetek, preprosti način | gumbi/bljižnjice |

Samodejno ob NARIŠI (brez ločenih gumbov): kosovnica CSV, nalepke PNG,
odpis ostankov v kosovnici, opozorila kvalitete.

## Vidno v TERENSKEM urejevalniku (terenski_gui.py)

Vseh 11 vrst elementov iz `terenski_list.VRSTE` ima orodje: poteza
(Prostoročno), črta, puščica, mera, pravokotnik, elipsa, besedilo, kocka,
kvader, **slika** (vstavljanje: orodje „Slika“ → takoj izbira datoteke,
klik na platno tudi s tresljajem miške, gumb „Vstavi sliko…“).
Naprej: premikanje/brisanje/podvajanje/vrtenje 45°/skaliranje, barve,
undo/redo, stran/orientacija/merilo/mreža/vodila/okvir, YAML shramba
(slika vgrajena), PDF izvoz, predogled, tiskanje.

## Ostaja namenoma zunaj vmesnika (iskreno)

| Funkcija | Zakaj / pot |
|---|---|
| `avtomatska_skica.izberi_vogale` (interaktivni klik vogalov) | odpre interaktivno matplotlib okno; na voljo prek CLI (`python photo_fence_proposal/zazeni.py --interaktivno`) |
| `migracija`, `jedro`, `vrata`, `proizvodnja`, `razrez` | knjižnični moduli — uporabljajo jih gumbi zgoraj (ne potrebujejo lastnih gumbov) |
| `terenski_list.preveri_dokument` | kliče se ob nalaganju (varnost), ni uporabniške akcije |
| G-code prilagoditev žagi | informativen izpis — operater prilagodi; zapisano tudi v sami datoteki |

## Ugotovitve pregleda (2026-11-21)

1. **Shranjenega projekta ni bilo mogoče odpreti** — obstajal je le
   „Shrani projekt“; vrnitev je bila le prek ukazne vrstice.
   → dodano: ODPRI PROJEKT… / Ctrl+O (isti cfg → polja kot obnovitev seje).
2. **`cnc.py` (CSV + G-code) ni imel nobene poti v vmesnik** — modul je bil
   v celoti nedosegljiv. → dodano: gumb CNC (CSV + G-code), skupine kosov
   pridejo iz `proizvodnja.izracunaj_kolicine` (`skupine_reza`) — vsak
   profil zase, brez mešanja palic.
3. **`nova_vrsta.py` (pilot F4) ni imel poti v vmesnik** — sedaj okno
   „NOVA VRSTA (pilot)“, ki polja generira iz deklarativnih `POLJA`
   (U3: nič polj brez oznak), količine + PNG predogled.
4. Kozmetika: obnovljena polja so kazala `3333.0` namesto `3333`.
## Drugi pregled (2026-11-22) — vizualni nadzor opravilne vrstice

Vprašanje: *„če so v opravilni vrstici vse funkcije.“* Pregled v živo
(pravi GUI, odprti meniji, posnetki) + statično križanje vseh
`command=self.X` vezavi.

**Najdene vrzeli (6 funkcij je bilo samo na gumbih) → odpravljeno:**

| Funkcija | Prej | Zdaj |
|---|---|---|
| Izberi fotografijo… (`_brskaj_foto`) | samo gumb „Prebrskaj…“ | Orodja → Izberi fotografijo… |
| Dodaj vrata/prehod… (`_vrata_dodaj`) | samo gumb v tabeli | Urejanje |
| Uredi izbrana vrata… (`_vrata_uredi`) | samo gumb | Urejanje |
| Odstrani izbrana vrata (`_vrata_odstrani`) | samo gumb | Urejanje |
| Osveži živ povzetek (`_zivi_osvezi`) | samo gumb | Pogled |
| Preklopi preprosti način (`_preklopi_nacin`) | samo gumb | Pogled |

**Terenski urejevalnik:** vsa orodja (12: izberi, prostoročno, radirka,
črta, puščica, pravokotnik, elipsa, besedilo, ročna mera, kocka, kvader,
slika) so zdaj tudi v meniju **Vstavi** — radijske povezave na ISTI
`self.orodje` vir kot orodna vrstica, zato meni vedno kaže aktivno
orodje (kljukica). Meni Datoteka: dodan „Izhod“.

**Ostaja namenoma zunaj menijev** (preverjeno): notranji gumbi dialogov
(čarovnik: Naprej/Nazaj; Nova vrsta: Količine/Predogled), nastavitve
obrazca (checkbox „Uporabi skladišče ostankov“, „Živo osveževanje“,
„Klik na risbo odpre cel zaslon“, comboboxi Barva/Status) — to so
vnosna polja, ne funkcije.

**Regresijska zaščita:** `tests/test_meni_popolnost.py` — statično
križanje (noben `command=self.X` brez poti v meniju) + realno menijsko
drevo obeh vmesnikov.
