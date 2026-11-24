# Analiza paketov — kaj namestiti in kdaj

> **Status:** odločitev o paketni strategiji (2026-04-11).
> Dejstva o paketih: PyPI JSON API in licenčne datoteke (delegirana raziskava, 2026-04-11),
> preverjeno še lokalno (`pip show`, uvozi). Nepreverjeno je označeno.
> Kontekst: Python 3.11, Windows, MIT licenca, distribucija prek PyInstaller EXE
> (`requirements-build.txt`), CI GitHub Actions windows-latest.

## 1. Izhodišče — kaj projekt že uporablja

| Paket | V kodi | Kje deklariran | Vloga |
|---|---|---|---|
| numpy | da | `requirements.txt` | računanje geometrije |
| matplotlib | da | `requirements.txt` | risanje PDF (A4/A3) |
| ezdxf | da | `requirements.txt` (pin 1.4.5) | DXF izvoz |
| PyYAML | da | `requirements.txt` | YAML konfiguracija / `mechanical/` katalog |
| Pillow | da | `requirements.txt` | slike |
| opencv-python | da (`merjenje`, `photo_fence_proposal`) | `requirements-build.txt` (pin 4.11.0.86) | terensko merjenje s fotografij (brez AI modelov) |
| flask | da (`api/index.py`) | `requirements.txt` | API |
| ttkbootstrap | da (neobvezno) | `requirements.txt` | teme GUI |
| pypdf | da (testi) | `requirements-dev.txt` | preverjanje PDF |
| **torch, transformers, shapely, networkx, sympy** | **ne** | **nič** | samo v okolju (podedovano) — koda jih ne uvozi |
| **scikit-image, scipy** | **da (foto sloj)** | photo_fence_proposal | `detekcija.py` (robova kontrola ritma, 2026-11-23) — NE v EXE |

Nameščeno v tem krogu (2026-04-11): **`scipy 1.17.1`, `trimesh 5.2.2`, `meshio 5.3.5`**.
**3D in QR (2026-11-23):** `tridim/` (mreža, STL/OBJ/GLB) in `oznake.py`
(QR) **ne dodata nobene odvisnosti** — GLB pišemo sami, QR bere OpenCV, ki
je že v foto sloju. `cadquery`/`OCP`/`casadi` namenoma niso vgrajeni
(LGPL); glej `docs/odlocitev-3d-in-ocr.md`.

`numpy` ostaja 1.26.4 (nedotaknjen). V `requirements.txt` jih **ne dodamo, dokler jih koda
ne uvozi** — da EXE ostane suh. Navodila za namestitev so spodaj (§5).

## 2. Kandidati — dejstva in odločitev

Velikosti = nameščen odtis paketa brez odvisnosti (vir: delegirana raziskava, PyPI wheel).
Licence so odločilne, ker distribuiramo **MIT EXE s PyInstaller** (knjižnice so zvezane v bundle).

### 2.1 Jedro — dovoljeno in koristno (BSD/MIT, majhno)

| Paket | Velikost | Licenca | Konkretna vloga v projektu | Odločitev |
|---|---|---|---|---|
| scipy | ~110 MB | BSD-3 | filtri/optimizacija v `merjenje` in `photo_fence_proposal`, statistične kontrole; pogoj za `scikit-image` | **nameščeno** |
| shapely | ~5 MB | BSD-3 | robustni zamiki zaprtih kontur (npr. postavitev lamel v `razrez`/`dxf_izvoz`), boolska geometrija 2D | na voljo v okolju; v `requirements` ob prvi uporabi |
| networkx | ~7 MB | BSD-3 | graf sestave/BOM (`mechanical.bom`), odvisnosti delov, detekcija ciklov v sestavih | na voljo v okolju |
| trimesh | ~2 MB | MIT | lahka 3D mreža (STL/OBJ), prihodnji predogled `mechanical` delov; `[easy]` vleče manifold3d (Apache-2.0) | **nameščeno** |
| meshio | ~0,5 MB | MIT | pretvorba mrežnih formatov (`.msh`), komplementarno `trimesh` | **nameščeno** |
| sympy | ~27 MB | BSD-3 | simbolni izpeljavi formul v `statika.py` (revizijsko sledljiv izpis `M = q·L²/8`) | na voljo v okolju; uporaba neobvezna |
| scikit-image | ~22 MB | BSD-3 | detekcija robov (Canny) v `photo_fence_proposal/detekcija.py` — robova kontrola lamelnega ritma | **v rabi** (foto sloj, 2026-11-23) |

### 2.2 Težki sloji — namestiti šele ob konkretni funkciji

| Paket | Odtis sklada | Licenca | Kaj bi odprl | Pogoji / pasti |
|---|---|---|---|---|
| cadquery + cadquery-ocp | ~650–750 MB | Apache-2.0 vezave; OCCT LGPL-2.1 **z OCCT izjemo** (dovoli distribucijo objektne kode z vidnim obvestilom) | pravi 3D parametrski deli iz `mechanical` (`valj`, `izvrtina`, `navoj`) → ortogonalne projekcije v PDF prilogo | ⚠ trda odvisnost **casadi (LGPL-3.0)** brez izjeme → pred distribucijo pravni pregled ali izključitev; obvezno obvestilo "uporablja Open CASCADE" v EXE/dokumentaciji |
| pyvista + vtk | ~315 MB | MIT / BSD-3 | interaktivni 3D predogled | za PDF priloge zadošča matplotlib — **zaenkrat odveč** |
| open3d | ~273 MB | MIT | registracija točkovnih oblakov, rekonstrukcija mrež (če bi merili s 3D skenerjem) | počasno vzdrževanje release-ov; potrebe ni |
| paddleocr + paddlepaddle | ≥500 MB | Apache-2.0 | OCR natisnjenih meritev s fotografij | `paddleocr` je le ovojnica; pogon (`paddlepaddle`, 377 MB) se namesti ročno; `paddlex` pin-a `numpy<2.4` (zdaj 1.26 — OK, a pri nadgradnji numpy pozor) |
| torch + transformers | ~580 MB | BSD-3 / Apache-2.0 | ML (npr. TrOCR namesto PaddleOCR, detekcija objektov na fotografijah) | v okolju **že nameščeno**, a koda ju ne uporablja; PyInstaller + torch je boleč (skriti uvozi, velikost) |

### 2.3 Zavrnjeno — licenca ali logistika

| Paket | Razlog zavrnitve |
|---|---|
| **gmsh** | **GPL-2.0+** — zvezan v PyInstaller bundle bi "okužil" MIT EXE z obveznostjo objave izvorne kode. Dovoljen ločeno orodje, ne v distribuiranem EXE. |
| **pymeshlab** | **GPL-3.0** — isti razlog. Permissivna alternativa za popravilo mrež: `manifold3d` (Apache-2.0, prek `trimesh[easy]`). |
| **pythonocc-core** | **Sploh ni pip-namestljiv** (PyPI brez datotek; samo conda-forge) **+ LGPL-3.0-or-later** na vezavah + v celoti podvojeno s `cadquery-ocp`. |

## 3. Podvajanja (ne nameščati dveh rešitev za isti problem)

- **CAD:** `cadquery` in `pythonocc-core` sta oba ovitka nad OCCT → vedno samo eden (cadquery).
- **Mreže:** `trimesh` (I/O + lahka geometrija) ⊂ `open3d` (registracija/vizualizacija) ⊃ `meshio` (le pretvorbe). Za naš 2D/2.5D obseg zadostujeta `trimesh` + `meshio`.
- **OCR:** PaddleOCR (+377 MB) ≈ TrOCR prek transformers (+torch 484 MB) → izbrati največ enega, ali nič (zaenkrat: ročni vnos + kalibrirana fotografija).
- **3D vizualizacija:** `pyvista`/vtk (307 MB) proti matplotlib, ki ga aplikacija **že ima** — za ortogonalne projekcije v PDF matplotlib zadošča.
- **Numerika:** numpy / scipy / sympy so komplementarni sloji, ne konkurenti.

## 4. Vpliv na kakovostna vrata

- **EXE (PyInstaller):** nič novega v bundle, dokler koda ne uvozi paketov. Ob vključitvi kateregakoli težkega sloja: `requirements-build.txt` + `TehnicnaRisba.spec` + obvezno obvestilo o licencah (OCCT izjema!). `torch` je znan po težavah s PyInstallerjem.
- **CI (windows-latest):** namestitev težkih slojev bi podaljšala CI za minute in GB — zato so v `requirements-dev`/`build` samo tisti, ki jih testi res potrebujejo.
- **mypy:** `cv2`/`tkinter`/`ezdxf`/`numpy` so že vir šuma v `.mypy-baseline`; vsak nov težek paket brez stubov prinese nov šum → baseline ratchet varuje, a ne odpiraj front po nepotrebnem.
- **Testi:** nove knjižnice ne smejo postati pogoj za obstoječe teste; uporabljati jih je treba prek neobveznih uvozov (kot `ttkbootstrap`).

## 5. Odločitev — kaj in kdaj

1. **Zdaj (izvedeno):** `scipy`, `trimesh`, `meshio` — lahki, permissivni, odpravijo vrzel v jedru.
   ```
   python -m pip install "scipy<1.18" trimesh meshio
   ```
   (`scipy<1.18` = zadnja vrstica s kolesi za Python 3.11.)
2. **Ob funkciji (sloj foto-merjenja):** `scikit-image` (+ `scipy`, že notri).
   → **izvedeno 2026-11-23**: `photo_fence_proposal/detekcija.py` — neodvisen
   robovi estimator ritma + kontrola soglasja s profilnim estimatorjem
   (nesoglasje eksplicitno dolja statuse mer).
3. **Ob funkciji (3D deli `mechanical`):** `cadquery` — šele po odločitvi o `casadi` (LGPL) in z OCCT obvestilom:
   ```
   python -m pip install cadquery
   ```
4. **Ob funkciji (OCR):** izbrati PaddleOCR *ali* TrOCR; šele ko bo konkreten primer uporabe.
5. **Nikoli v EXE:** `gmsh`, `pymeshlab`, `pythonocc-core`.

## 6. Analiza treh naslednjih korakov ("naslednjič po moji logiki")

### (a) Kataloške vrstice pritrdil iz `mechanical/` v statično prilogo — **izvedeno 2026-04-11**

Trenutno `statika.py` bere pritrdila kot prosto besedilo (`cfg["pritrditev"]`). Predlog:

- `cfg["pritrditev"]` dobi elemente z `ref: "iso_4017_m10x35"` → `mechanical.resolver.razresi()`
  vrne mere (Ø10 × 35) + **dokazilo** (`source`, `accessed`) → vrstica v prilogi
  »Pritrdila (katalog)« s stolpci: oznaka, standard, mere, vir, dostopano.
- Prosto besedilo ostane dovoljeno, a se izpiše kot **»brez kataloškega vira«** — meritev se
  nikoli ne izmisli (skladno z »brez ugibanja«).
- Smer uvozov je čista: `statika` → `mechanical` je dovoljeno (omejitev velja obratno:
  `mechanical` ne sme uvažati ograjnih modulov).
- Povezava z BOM: `mechanical.bom.izpelji_bom()` že združuje instance po `part_ref` — priloga
  lahko navaja tudi `bom.id` za sledljivost.
- Testi: priloga vsebuje »ISO 4017«, »M10×35«, URL vira in datum dostopa; test za fallback na
  prosto besedilo. **Brez novih paketov** — rešljivo z obstoječim `PyYAML` + `mechanical/`.

### (b) Hitrejša testna zanka (šele po preverjanju vzporedne varnosti)

1. **Preveri vzporedno varnost:** nekateri testi pišejo fiksne izhodne datoteke (`PO-001.png`
   v korenu repozitorija itd.) → pod `pytest-xdist` bi se tekmi prekrivale. Pogoj: izhodi v
   `tmp_path` ali enolična imena. `conftest.py` že izolira `TEHNICNA_RISBA_DATA`, ne pa
   delovnega imenika.
2. Šele nato: `pytest-xdist` (`-n auto`) + `pytest-timeout` (ta reši tudi težavo zataknjenega
   celotnega testiranja, ki smo jo srečali — `pytest` brez timeouta je lahko neskončen).
3. Označi počasne teste (`@pytest.mark.pocasi` — npr. tisti, ki uvažajo matplotlib/cv2) in
   razvojna zanka teče `pytest -m "not pocasi"`. Merilo: `python -X importtime` — na tem
   stroju je sam uvoz `matplotlib` ~40 s, `cv2` ~17 s, kar je okoljsko, ne koda.
4. V CI ostane celoten `pytest tests/ -q --cov` (ratchet za pokritost nespremenjen).

### (c) Dodatni tipi vrat (`vrata.py`)

- Čista 2D geometrija — **brez novih paketov**. Vsak tip = nov podatkovni model + risba +
  DXF + razrez + terenski list, po obstoječem vzorcu testov.
- Vrstni red po vrednosti: (1) drsna vrata, (2) dvokrilna, (3) prehodna vrata v ograjnem polju.
- Edina povezava s paketi: če bodo sestavi vrat dobili 3D predoglede, takrat šele sloj `cadquery`
  (§5.3) — za risbe/DXF ni potrebe.

## 7. Sklep

Seznam iz vprašanja je **pretežek za enkraten vnos** — kot celota bi prinesel ~2,5–3 GB,
dve GPL pasti (gmsh, pymeshlab), enega, ki ga ni mogoče namestiti (pythonocc), in tri podvojene
stekle (CAD, mreže, OCR). Smiselna je **plastna strategija**: lahko jedro (scipy/trimesh/meshio,
izvedeno) → `scikit-image` pri foto-merjenju → `cadquery` pri 3D delih `mechanical` → OCR/ML šele
ob konkretni potrebi. Trije naslednji koraki iz §6 **ne potrebujejo nobenega novega paketa**.