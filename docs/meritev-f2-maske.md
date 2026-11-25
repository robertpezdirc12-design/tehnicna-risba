# Meritev F2: Grounded SAM 2 na tujih fotografijah (24. 11. 2026)

**Vrata F2 (iz `docs/nacrt-draftwright-pro.md`): napaka štetja ±10 % na
5 tujih fotografijah in ≤ 30 s/sliko na CPU.**

**Izid: vrata NISO dosežena — napaka 20–98 %, čas 41–45 s/sliko.** Zato
AI ostaja zunaj izdelka; ostane le bralnik mask (`maske_ai.py`), ki lahko
naše štetje potrdi ali ovrže, če masko prinese boljše orodje.

## Okolje meritve

| Sestavina | Vrednost |
|---|---|
| Stroj | Windows, CPU (brez CUDA), Python 3.11.9 |
| torch / torchvision | 2.14.1+cpu / 0.29.2+cpu |
| GroundingDINO | Swin-B (`groundingdino_swinb_cogcoor.pth`, 938 MB) |
| SAM 2.1 | hiera-small (`sam2.1_hiera_small.pt`, 184 MB) |
| Prompt | `fence post. fence slat. picket.` |
| Prag | 0,30 (poskusi tudi 0,15 in 0,20) |
| Koda | `Grounding-SAM-2` (Apache-2.0); uteži ločeno, niso v izdelku |
| Namestitev | `.test/venv-ai` (ločen venv, `--system-site-packages`), uteži v `.test/utezi/` |

Vse je v `.test/`, ki je v `.gitignore` — v repo ne gre nobena utež.

## Fotografije in licence

| # | Datoteka | Vir (Wikimedia Commons) | Licenca |
|---|---|---|---|
| 1 | `c08.jpg` — bela letvasta ograja | `File:Chingford Cricket Club boundary picket fence, Chingford, Essex 2.jpg` | CC BY-SA 4.0 |
| 2 | `c05.jpg` — stara lesena palisada | `File:Palisade structure of Fort Fonyód, 2016 Hungary.jpg` | CC BY-SA 3.0 |
| 3 | `c06.jpg` — keltska palisada | `File:St Fagans Celtic village palisade.jpg` | CC BY-SA 3.0 |
| 4 | `k02.jpg` — rustikalna ograja z vrati | `File:Garden fence and gate at Nuthurst, West Sussex, England.jpg` | CC BY-SA 4.0 |
| 5 | `c02.jpg` — dolga palisada ob poti | `File:Archeoparc - Palisade 1.jpg` | CC BY-SA 3.0 |

Fotografije so bile uporabljene samo za meritev in niso del izdelka;
licence zahtevajo navedbo avtorstva ob morebitni objavi izsekov.

## Rezultat (celoten kader, prag 0,30)

Ročno prešteti so vidni vertikalni elementi (deske/stebri) v kadru;
»AI« je število mask, ki jih je orodje označilo kot `steber`.

| # | Fotografija | Ročno | AI `steber` | Napaka | Čas |
|---|---|---|---|---|---|
| 1 | bela letvasta | ≈ 40 | 14 | **−65 %** | 41,7 s |
| 2 | stara palisada | ≈ 12 | 8 | **−33 %** | 43,8 s |
| 3 | keltska palisada | ≈ 18 | 8 | **−56 %** | 41,3 s |
| 4 | rustikalna + vrata | ≈ 5 | 4 | **−20 %** | 43,2 s |
| 5 | dolga palisada | ≈ 50 | 1 | **−98 %** | 44,7 s |

Povprečna napaka ≈ **−54 %**, vsaka fotografija zunaj ±10 %; čas
41–45 s/sliko proti omejitvi 30 s → **oba kriterija padeta**.

## Poskusi, da bi bilo pošteno

| Poskus | Rezultat |
|---|---|
| Prag 0,15, prompt `vertical wooden post.` (palisada) | 18 mask, a le 3 x-skupine — še vedno daleč od 12 |
| 2×2 ploščice, prag 0,20 (palisada) | 49 mask, 148,9 s — natančnost ni boljša, čas 5× čez mejo |
| 2×2 ploščice, prompt `picket.` (bela letvasta) | 6 mask (vse `lamela`) v 140,2 s — slabše od celotne slike |
| Vse oznake skupaj (zgornja meja) | 15 / 7 / 2 / 9 / 11 mask — še vedno pod ročnim štetjem |

## Kaj je šlo narobe (in kaj to pove o uporabi)

1. **GroundingDINO zazna ograjo kot celoto, ne elementov.** Na gosti
   palisadi vrne 1–2 veliki maski (mediana širine 677 px pri sliki
   1280 px), ne 50 desk. Model je učen na »fence«, ne na »vsaka deska«.
2. **Maske se prekrivajo in »krvavijo«** med sosednjimi deskami, zato
   štetje po intervalih z združevanjem prekrivanja ne more ločiti desk
   (pri beli letvasti se 14 mask zlepi v 1 skupino).
3. **Ločevanje steber/deska po razmerju stranic** je prešibko: pri beli
   letvasti je 14 od 15 mask označenih kot `steber`, čeprav so to deske.
4. **CPU je počasen**: 42 s/sliko samo za inferenco, brez nalaganja
   modelov (53 s) in brez pisanja PDF.

## Kar ostane v izdelku (in kar ne)

- **Ostane** `maske_ai.py`: strogo branje mask + deterministično štetje
  (popravljeno v 1.5.20: združuje le močno prekrivajoče se maske, ne
  sosednjih desk) in `--maske`, ki naše štetje **potrdi ali ovrže**.
- **Ne pride** torch, GroundingDINO ali SAM 2 v `requirements.txt`,
  v EXE ali v kakšen samodejni tok. EXE ostane 52,7 MB in brez AI.

## Kako ponoviti

```powershell
python -m venv .test/venv-ai --system-site-packages
.test/venv-ai/Scripts/python.exe -m pip install torchvision --index-url https://download.pytorch.org/whl/cpu
.test/venv-ai/Scripts/python.exe -m pip install transformers addict timm supervision pycocotools yapf hydra-core iopath tqdm
git clone --depth 1 https://github.com/IDEA-Research/Grounded-SAM-2 .test/Grounded-SAM-2
# uteži: HF ShilongLiu/GroundingDINO + facebook/sam2.1-hiera-small
.test/venv-ai/Scripts/python.exe .test/meritev_f2.py "fence post. fence slat. picket." foto.jpg
```

Skripta `.test/meritev_f2.py` ni v repu (`.test/` je v `.gitignore`), ker
vsebuje poti do lokalnih uteži; postopek zgoraj je dovolj za ponovitev.

## Sklep

Grounded SAM 2 za to nalogo **ni uporaben**: ne šteje ponavljajočih se
elementov in na CPU ni dovolj hiter. Vrata F2 so zaprta z negativnim
izidom — to je enako vredno kot pozitiven: AI pot se ne vgradi, pregled
`docs/nacrt-draftwright-pro.md` pa F2 označi kot *preizkušeno in padlo*.
