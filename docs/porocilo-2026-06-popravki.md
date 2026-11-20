# Popravki izračunov, PDF izpisa in skladišča ostankov (issue #2)

Kratke odločitve in rešitve potrjenih napak. Vsaka točka ima regresijski
test v `tests/` (povezava: ime testne datoteke).

## A1 / P0 — življenjski cikel `PdfPages`

**Napaka:** nalepke (`fig4`) so bile z `pdf.savefig(...)` shranjene PO
zaprtju konteksta `PdfPages`. matplotlib >= 3.10.7 pri tem *tiho* (brez
izjeme) ponovno odpre datoteko in jo prepiše v 0 B / 0 strani.

**Odločitev:** vse strani PDF se zapišejo v ENEM ciklu `PdfPages`
(vrstni red: risba, montažni list, predračun, nalepke). Figure se
zaprejo v `finally`. Če posamezni list odpove, se to zabeleži v
`ZADNJA_OPOZORILA` + stderr, dokument pa ni tiho označen kot popoln
(CLI vrne kodo 2). Zaznavanje NI na podlagi izjem — testi preverjajo
dejansko število strani s `pypdf`.

Testi: `tests/test_pdf_ciklus.py`.

## A2 — kontrola dejanske dolžine kosa

**Napaka:** za prečno predlogo je kontrola kosov preverjala višino lamel
(`lamela_v`), ne dejanske dolžine kosa (širina ograje). Kos 2500 mm je
tako »preverila« s 120 mm.

**Odločitev:** `preveri_cfg` uporablja enotno dolžino kosa:
prečna = `sirina`, pokončna = `visina - rocaj_v - odcep` (enako kot
razrez). Preveri se tudi, da vsaj ena nabavna dolžina zadošča kosu +
kerf, ter da ročaj/stebri ne presegajo tovarniške dolžine palice.

Testi: `tests/test_validacija.py`.

## A3/A5 — nepopoln razrez ni uspeh

Optimizator nima skritih omejitev (stara različica je po 500 kosih
odnehala). `razrez_podatki` preveri celovitost: če izdelanih kosov ni
enako zahtevanim, vrže napako z manjkajočim številom. Kontrola
`V = n·k + kerf_skupaj + ostanek` velja za vse trakove. Kosovnica,
montažni list in naročilo uporabljajo ISTI izračun (`razrez_podatki`).

Testi: `tests/test_razrez.py`.

## A4 — kote in količine prikazujejo dejanske lege

**Napaka:** kotirala se je zahtevana vrednost `razmak_nosilcev` (npr.
1000 mm), dejanski razmak nosilcev pa je bil drugačen (npr. 767 mm pri
širini 2500). Tloris in čelni pogled nista bila usklajena.

**Odločitev:** skupna funkcija `pozicije_nosilcev(sir, raz)` določa lege
in dejanski razmak za vse liste; kotira se dejanski razmak, omejitev
(„razmak ≤ X mm“) ostane vidna v potrebščinah.

Testi: `tests/test_kolicine.py`.

## A6 — izklop optimizacije ni podprt

Zahteve po izklopu optimizacije/združevanja (`brez_optimizacije`,
`optimizacija_rezov=false`, …) se zavrnejo z obrazložitvijo —
neoptimiziranega izpisa nikoli ne označimo kot optimiziranega.

Testi: `tests/test_validacija.py`.

## A8 — informativni predračun

Začasni cenik vsebuje `0.00` PRIMER vrednosti. Dokument s količinami
ostane, predračun pa je pri vseh ničelnih cenah označen
„INFORMATIVEN — BREZ VELJAVNEGA CENIKA“, zneski so „ni obračunano“
(brez zavajajočih „0,00 EUR“). Delno manjkajoče cene so označene
posamično, skupaj pa „delno“.

Testi: `tests/test_predracun.py`.

## A10 — normalizacija konfiguracije

`generiraj()` konfiguracijo normalizira (`zdruzi` dopolni manjkajoče
ključe iz `PRIVZETO`). `kerf` mora biti nenegativno število, `dolzine_deske`
neprazen seznam pozitivnih števil. Neznana predloga je jasna napaka.
`uporabi_ostanke` ima privzeto vrednost `false` (varno).

Testi: `tests/test_validacija.py`.

## B1 — skladišče ostankov (in regresija dvojnega odštevanja)

**Napaka (regresija 1):** po porazdelitvi kosov iz ostanka je bil ostanek
v tabeli prikazan `0` (podatkovna struktura je bila mutirana in nato
odštetja še enkrat) — pravilno 994 mm (3000 − 2×(1000+3)).

**Odločitve:**

- model reza je enoten povsod: `n × (k + kerf)` zasede trak; ostanek se
  izračuna ENKRAT in se nikoli ne odšteje dvakrat (tudi v montažnih
  listih),
- `porazdeli_z_ostanki` ne mutira vhodnega seznama; vsak ostanek je
  porabljen največ enkrat; mešanje barv/profilov ni dovoljeno,
- novi ostanki iz nabavnih desk se evidentirajo tudi, ko je uporaba
  starih ostankov izklopljena,
- generiranje **nikoli** ne piše v skladišče; odpis je izrecen
  (CLI `--potrosi-ostanke`, GUI gumb „ODPIŠI OSTANKE“) in ob odpisu se
  naredi varnostna kopija (`.bak`) ter atomičen zapis (`os.replace`),
- metapodatki ostankov (barva, profil, opomba) se ohranijo,
- lokacija skladišča: `TEHNICNA_RISBA_DATA` ali `%APPDATA%\TehnicnaRisba`
  (Windows) / `~/.local/share/TehnicnaRisba`; stara datoteka iz delovne
  mape se varno migrira (vir ostane nedotaknjen).

Testi: `tests/test_ostanki.py`, `tests/test_razrez.py`.

## B2/B3/B4 — pokončna predloga (in regresiji 2 in 3)

**Napake:** vrzel med deskami je bila izračunana iz celotne širine
(43,16 namesto uporabnikovih 20 mm), agregatna formula za palice je
podcenjevala (9 × 1200 mm → 2 namesto 3 palic), vijaki so bili
prešteti (`n_d × n_s × 2` = 120 namesto 80).

**Dokumentirana konstrukcijska geometrija:** stebri so v enakomernih
legah; deske potekajo po poljih med stebri (se ne prekrivajo s stebri) in
so pritrjene na oba sosednja stebra — 2 vijaka na stik = **4 na desko**.
Uporabnikova `vrzel` se uporabi NATANČNO; če se deske ne prilegajo v
polje, je to jasna napaka (brez tihega prilagajanja). Palice se štejejo
po kosih na palico (`stevilo_palic`), ne po agregatni dolžinski formuli.

Testi: `tests/test_pokoncna.py`, `tests/test_razrez.py`.

## B5 — GUI (in regresija 4)

**Napaki:** (1) nastavitev „Pritrditev“ se po ponovnem zagonu ni
obnovila (shranjen ključ `pritrditev`, bran ključ `pritrditev_nacin`);
(2) zagon je po nalaganju zadnjih nastavitev z `_privzeti()` preko njih
zapisal privzete vrednosti.

**Odločitev:** `cfg` vsebuje oba ključa, `_nalozi_zadnje` bere
`pritrditev_nacin` s povratnim `pritrditev`; zagon ne prepisuje
naloženih vrednosti. Gumb „ODPIŠI OSTANKE“ je omogočen le ob dejanski
spremembi skladišča, po odpisu onemogočen. Pot skladišča je vidna v GUI.

Testi: `tests/test_vmesnik.py`.

## D — poimenovanje listov

Risalna lista sta dva (1/2 risba, 2/2 montažni list); predračun in
nalepke sta označeni kot prilogi („ni risalni list“) in ne štejeta
kot lista.

## E — poštene navedbe

Testi so tekli na Windows 11 / Python 3.11.9 / matplotlib 3.11.2.
EXE v tem popravku ni bil ponovno zgrajen; Vercel objavlja le statično
stran (web generator ni aktiven). README to izrecno navaja.