# Plan I — 3D predogled ograje

## Vir (raziskava UI/UX)
- Visual Fence Pro: „vrtljiv 3D model ogrje v ponudbi, plast za plastjo“
- magicplan: 3D prikaz tlorisa

## Cilj
Gumb **3D PREDGLED** odpre okno s shematskim 3D prikazom ograje:
- lamele/deske (skatle), zgornji/spodnji profili, nosilci/stebri,
- odprtine (vrata/prehodi) kot praznine z okvirjem,
- interaktivno vrtenje/povečava (matplotlib 3D).

## Iskreno o obsega
To NI fotorealistični vizualizator (kot AI Fence Visualizer — tisti je
izrecno izven naših pravil #8: brez AI) in NI konstrukcijski model.
Je **shematski 3D prikaz** za lažjo predstavo; mere so iz istega
`cfg` kot risba (en vir resnice).

## Spremembe
- `tridimenzionalno.py`: `sestavi_3d(cfg)` (Figure), `narisi_3d_png`,
  `pokazi_3d(cfg, master)` (Toplevel z vgrajenim canvasom).
- `vmesnik.py`: gumb „3D PREDGLED“.

## Testi / verifikacija
1. `sestavi_3d` za obe predlogi vrne figuro s skatlicami (kolekcije > 0).
2. Z vrati deluje (odprtine nariše okvir).
3. `narisi_3d_png` zapiše PNG z vsebino.
4. Celotna suita zelena.

## Zunaj obsega (iskreno)
- Fotorealistični prikaz, teksture, okolica.
- Izvoz 3D (STL/GLTF) — možno v prihodnje.