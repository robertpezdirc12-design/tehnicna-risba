# Plan H — Vleci-za-premik na predogledu

## Vir (raziskava UI/UX)
- magicplan: „direct manipulation — vleci, povečaj, premikaj“
- TakeOn/Plankore: vlečenje izbranih elementov, kolešček = povečava

## Problem
Glavni predogled je bil statična slika (Label) — brez povečave in premika.
Celozaslonski način je imel zoom/pan, navadni ne.

## Cilj
`PredogledCanvas` v glavnem oknu:
- kolešček = povečava (0,05×–5×),
- **vleci-za-premik** pogleda,
- dvoklik = prilagodi oknu, desni klik = ponastavi,
- klik (brez premika) = obstoječi ukaz (cel zaslon, če je vklopljen).

## Iskreno o obsegu
Vlečenje premika POGLED, NE geometrije risbe. Urejanje geometrije z
vlečenjem (kot v CAD) bi zahtevalo popoln interaktivni risalnik — to je
ločen večji projekt in NI del tega plana.

## Spremembe
- `vmesnik.py`: `PredogledCanvas` (PIL resize + create_image),
  `_pokazi_predogled` → `predogled.nastavi(png)`.

## Testi / verifikacija
1. Prikaz slike na platnu (find_all ni prazen).
2. Povečava (kolešček gor/dol) in premik (ox/oy).
3. Klik brez premika sproži ukaz; vlečenje NE.
4. Ponastavi/prilagodi resetirata pogled.

## Zunaj obsega (isknano)
- Urejanje geometrije risbe z vlečenjem (CAD urejevalnik).
- Zoom do neskončnosti z vzorčenjem (omejeno 5×).