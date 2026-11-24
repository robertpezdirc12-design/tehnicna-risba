# Eden AI — brezplačni model slik (preverjeno 2026-11-24)

**Namen:** odgovoriti, ali je Eden AI (in konkretno OVHcloud SDXL) uporaben
za ta projekt — in zapisati dokaz, da odločitev ni ugibanje.

## Kaj je bilo preverjeno

Klican je bil `POST https://api.edenai.run/v3/universal-ai` s telesom
`{"model": ..., "input": {"text": ..., "resolution": ...}}` in veljavnim
ključem (`sk-eden-live-…`). Katalog modelov: `GET /v3/info/image/generation`
(40 modelov).

| Preveritev | Rezultat |
|---|---|
| Ključ deluje | da — overjen, klic se izvede |
| `image/generation/ovhcloud/stable-diffusion-xl-base-v10` | **brezplačen**: `"price": 0.0, "price_unit_type": "free"`; dva klica sta vrnila `"cost":"0E-9"` in veljavno sliko 1024×1024 |
| Ločljivost | **samo 1024×1024** — 512×512 vrne napako providerja (`supports resolution 1024x1024 only`) |
| Plačljivi modeli | **niso brezplačni** in račun trenutno nima kredita: `minimax/image-01` → HTTP 402 „Insufficient AI credit“ |
| Najboljši modeli v katalogu | `openai/gpt-image-2` 0,053 $/sliko, `google` (gemini-3-pro-image, image-1.5) 0,034–0,039 $, `pruna/p-image-ideogram-very-high` 0,033 $, `bytedance/seedream-5-0` 0,035 $ — vsi plačljivi |
| Cenejši plačljivi | `minimax/image-01` 0,0035 $, `pruna/p-image-ideogram-very-low` 0,003 $, `replicate` 0,000225 $/sek izvajanja |
| Poslovni model Eden AI | pay-as-you-go, 5,5 % provizije; ni „neomejeno brezplačno“ — brezplačni so le posamezni modeli (zgoraj) in *sandbox* žetoni (simulirani odgovori) |

## Zakaj tega ne vgrajujemo

1. **Kakovost:** edini brezplačni model je SDXL base 1.0 (2023) pri 1024×1024.
   Za tehnične risbe ni uporaben — te morajo ostati deterministične
   (matplotlib/ezdxf), ne „približno podobne“.
2. **Ni pogodbeno stalno brezplačen:** Eden AI ne jamči trajnosti; cena 0 je
   lastnost trenutnega kataloga. Sklic na „vedno brezplačno“ bi bil trditev,
   ki je ne moremo držati.
3. **Spletna stran prikazuje resnične izdelke programa** (`slike/`), ne
   generiranih podob — vstavljanje AI-slik bi bilo zavajajoče glede na
   načelo poštenih navedb v tem repozitoriju.
4. **Pravilo `photo_fence_proposal`:** modul je „brez AI / lokalno“ in to
   preverja test z AST pregledom uvozov — omrežna odvisnost bi pravilo
   podrla.

## Licenca in pogoji

SDXL base 1.0 je izdan pod CreativeML Open RAIL++-M (dovoljena komercialna
raba z omejitvami uporabe). Poleg tega veljajo pogoji OVHcloud in Eden AI.
Za vsako resno uporabo je treba preveriti pogoje pri ponudniku, ne le
licenco modela.

## Če bi vseeno potrebovali slike

Takrat velja: ključ **samo iz okoljske spremenljivke** (`EDENAI_KEY`),
privzeto izklopljeno, izven EXE-ja, brez zapisa ključa v repozitorij, z
opozorilom ob klicu. Za *marketing* je bolje najeti fotografa ali uporabiti
lastne fotografije izvedenih ograj — te so tudi pravno čiste.
