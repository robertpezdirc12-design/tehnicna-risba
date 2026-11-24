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

## Trajno brezplačne alternative (preverjeno 2026-11-24)

**Pollinations.ai** — odprtokodna platforma (Berlin), klasični API je brez
prijave in brez ključa: `https://image.pollinations.ai/prompt/<povpraševanje>?width=768&height=768&seed=5`.
Preizkušeno: klic deluje (HTTP 200, JPEG z logotipom v kotu), vendar so
**omejitve trde** — ena slika na 45 s na IP (drugi klic v isti minuti vrne
HTTP 402 z `Retry-After`), največ 768×768, „best effort“ brez garancije.
Kakovost je neenakomerna: preprosto povpraševanje („rdeče jabolko“) je
zadeto, pri povpraševanju o ograji pa je model trikrat vrnil povsem
nepovezane podobe. Za občasno sliko da, za zanesljivo uporabo ne.

**Cloudflare Workers AI** — trajno brezplačna kvota **10.000 nevronov/dan**
(ponastavitev ob 00:00 UTC), model `@cf/black-forest-labs/flux-1-schnell`
(≈ 4,8 nevrona na ploščico 512×512 na korak). Zahteva brezplačen račun
Cloudflare in žeton; brez logotipa, komercialna raba dovoljena. To je
najbolj resen trajno brezplačen API, ki ne oglašuje in ne zahteva kartice.

**Bing Image Creator / Microsoft Designer** — brezplačno s katerim koli
Microsoftovim računom, kakovost DALL·E-razreda, dnevne kvote; spletni
vmesnik, uradnega API-ja ni, slika nosi oznako. Trajno brezplačno.

**Craiyon** — klasičen oglasno financiran brezplačni generator; kakovost
nizka, za resno rabo ne.

**Lokalno (ComfyUI + SDXL/FLUX)** — trajno brezplačno in brez omrežja, a
zahteva GPU z ≈ 8 GB VRAM; edina možnost, ki se ujema s pravilom „brez
omrežja“ v tem repozitoriju.

Sklep: trajno brezplačne možnosti **obstajajo** (Pollinations, Cloudflare
kvota, Bing), a nobena ni hkrati brez omejitev, brez računa in zanesljive
kakovosti. Za občasno marketinško sliko zadošča Pollinations ali Bing; za
produkt pa odločitev ostaja ista — slik ne vgrajujemo.
