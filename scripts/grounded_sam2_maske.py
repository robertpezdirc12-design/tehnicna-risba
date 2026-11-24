# -*- coding: utf-8 -*-
"""Grounded SAM 2 → maske JSON (ZUNANJE, neobvezno orodje; NI v izdelku).

NEPREVERJENO V TEM OKOLJU: uteži in paketi niso nameščeni, zato je to
ogrodje + navodilo, ne dokaz kakovosti. Vrata F2 iz
`docs/nacrt-draftwright-pro.md` ostajajo ODPRTA, dokler se ne izmeri
napaka štetja na resničnih fotografijah.

Namestitev (ločeno okolje, ~1 GB):

    git clone https://github.com/IDEA-Research/Grounded-SAM-2
    python -m pip install torch torchvision
    python -m pip install -e Grounded-SAM-2/grounding_dino
    python -m pip install -e Grounded-SAM-2
    # uteži: GroundingDINO Swin-B + SAM 2 tiny/hiera-large (glej README
    # projekta; vsaka utež ima svojo licenco — preveri pred distribucijo)

Uporaba:

    python scripts/grounded_sam2_maske.py --preveri
    python scripts/grounded_sam2_maske.py foto.jpg --izhod maske.json \
        --grounding-weights weights/groundingdino_swinb_cogcoor.pth \
        --sam2-weights weights/sam2.1_hiera_large.pt

Nato v izdelku:

    python photo_fence_proposal/zazeni.py --fotografija foto.jpg \
        --izhod izhod/ --vogali … --marker-mm 150 --maske maske.json

Licence: koda Grounded-SAM-2 / GroundingDINO / SAM 2 je Apache-2.0, uteži
pa imajo lastne pogoje — ta skript jih NE dobavlja in jih ne vgrajuje.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

NAVODILO = (
    "Za Grounded SAM 2 manjkajo paketi ali uteži. Ta skript je "
    "neobvezen most — namesti ga v LOČENO okolje po navodilu v glavi "
    "datoteke (git clone Grounded-SAM-2 + pip install -e + uteži). "
    "Izdelek in njegov EXE ostaneta brez torch/uteži in delujeta naprej."
)

PRAG_BOX = 0.30
PODNAPIS = "fence post. fence slat."


def _manjka() -> list[str]:
    """Kateri od neobveznih paketov niso v tem okolju."""
    manjka = []
    for modul in ("torch", "torchvision", "groundingdino", "sam2"):
        try:
            __import__(modul)
        except Exception:                      # noqa: BLE001 — vsak uvoz
            manjka.append(modul)
    return manjka


def _poligon(maska, epsilon: float = 1.5):
    """Binarna maska → zunanji poligon (approxPolyDP, brez lukenj)."""
    import cv2
    import numpy as np

    m = (np.asarray(maska).astype(np.uint8) * 255)
    konture, _ = cv2.findContours(m, cv2.RETR_EXTERNAL,
                                  cv2.CHAIN_APPROX_SIMPLE)
    if not konture:
        return None
    najvecja = max(konture, key=cv2.contourArea)
    priblizen = cv2.approxPolyDP(najvecja, epsilon, True)
    if len(priblizen) < 3:
        return None
    return [[float(p[0][0]), float(p[0][1])] for p in priblizen]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="grounded-sam2-maske",
        description="Grounded SAM 2 → JSON z maskami za Draftwright "
                    "(zunanje orodje, neobvezno)")
    p.add_argument("foto", nargs="?", help="fotografija")
    p.add_argument("--izhod", default="maske.json")
    p.add_argument("--preveri", action="store_true",
                   help="samo preveri, ali so paketi nameščeni")
    p.add_argument("--prag", type=float, default=PRAG_BOX)
    p.add_argument("--grounding-weights", default=None)
    p.add_argument("--grounding-config", default=None)
    p.add_argument("--sam2-weights", default=None)
    p.add_argument("--sam2-config", default=None)
    args = p.parse_args(argv)

    manjka = _manjka()
    if args.preveri:
        print(f"Manjka: {', '.join(manjka) if manjka else 'nič'}")
        return 0 if not manjka else 2
    if manjka:
        print(NAVODILO, file=sys.stderr)
        print(f"Manjkajoči paketi: {', '.join(manjka)}", file=sys.stderr)
        return 2
    if not args.foto:
        print("NAPAKA: podaj fotografijo (ali --preveri).", file=sys.stderr)
        return 2

    # --- prava pot (zahteva nameščene pakete in uteži) -----------------
    import json

    import numpy as np
    import torch
    from groundingdino.util.inference import load_image, load_model, predict
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    pot = pathlib.Path(args.foto)
    slika_rgb, slika_bgr = load_image(str(pot))
    visina, sirina = slika_rgb.shape[:2]
    model = load_model(args.grounding_config, args.grounding_weights)
    boxes, logits, _ = predict(
        model=model, image=slika_rgb, caption=PODNAPIS, box_threshold=args.prag,
        text_threshold=args.prag, device="cuda" if torch.cuda.is_available()
        else "cpu")
    napovedovalec = SAM2ImagePredictor(
        build_sam2(args.sam2_config, args.sam2_weights, device="cpu"))
    napovedovalec.set_image(slika_bgr)
    maske = []
    for box, zaupanje in zip(boxes, logits):
        x0, y0, x1, y1 = (box.numpy() * np.array([sirina, visina,
                                                 sirina, visina]))
        vnos = np.array([x0, y0, x1, y1])[None, :]
        izrezane, _, _ = napovedovalec.predict(box=vnos,
                                               multimask_output=False)
        poligon = _poligon(izrezane[0],)
        if poligon is None:
            continue
        sir_box = max(1.0, abs(float(x1 - x0)))
        vis_box = abs(float(y1 - y0))
        oznaka = "steber" if vis_box / sir_box >= 2.0 else "lamela"
        maske.append({"oznaka": oznaka, "zaupanje": float(zaupanje),
                      "poligon": poligon})

    # zapis prek istega vmesnika, kot ga bere izdelek (ena oblika, ena
    # validacija — zato uvoz iz photo_fence_proposal)
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]
                           / "photo_fence_proposal"))
    import maske_ai

    maske_ai.shrani(
        maske_ai.Maske(slika=str(pot), sirina_px=sirina, visina_px=visina,
                       maske=tuple(
                           maske_ai.Maska(m["oznaka"],
                                          tuple(map(tuple, m["poligon"])),
                                          m["zaupanje"])
                           for m in maske),
                       vir="grounded-sam-2"),
        args.izhod)
    print(json.dumps({"maske": len(maske), "izhod": args.izhod},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
