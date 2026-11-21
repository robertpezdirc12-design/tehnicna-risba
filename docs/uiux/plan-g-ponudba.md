# Plan G — Dokument ponudbe (Good/Better/Best)

## Vir (raziskava UI/UX)
- Visual Fence Pro: blagovna ponudba z opcijami Good/Better/Best
- Paper2Quote/Cobuild: predloge ponudb, client preview

## Problem
Imamo predračun (PDF stran 3, CSV), a ne dokumenta PONUDBE za stranko
z več izvedbenimi možnostmi.

## Cilj
`ponudba.py` — PDF PONUDBA z:
- glavo (podjetje, stranka, objekt, datum, veljavnost 30 dni),
- tabelo vključenih količin (iz `proizvodnja.izracunaj_kolicine`),
- tremi karticami OSNOVNA / PRIPOROČENA / PREMIUM (Good/Better/Best),
- poštenimi opombami (brez DDV, mere se preverijo na objektu, brez
  statičnega izračuna).

## POŠTENOST (projektna pravila)
Cene se NE izmišljajo z množitelji! Varianti `cene_osnovna`/`cene_premium`
sta iz konfiguracije (YAML); če ju ni, je znesek kartice **„cena po
dogovoru“** — brez izmišljene številke.

## Spremembe
- `ponudba.py`: `sestavi_moznosti(c)`, `narisi_ponudbo(pot_pdf, c)`
- `vmesnik.py`: gumb „PONUDBA (PDF)“ → poleg risbe izdela še ponudbo.

## Testi / verifikacija
1. Brez variant: 1 izračunana opcija, drugi dve „po dogovoru“ (brez številk).
2. Z variantami: vsi trije zneski iz `predracun_znesek` (ročno preverjeno).
3. PDF vsebuje PONUDBO, imena opcij, „brez DDV“ (pypdf).

## Zunaj obsega (iskreno)
- E-podpis / plačila (zahteva zunanji servis).
- Samodejno oblikovanje po merilah stranke (barve, logotip) — v prihodnje.