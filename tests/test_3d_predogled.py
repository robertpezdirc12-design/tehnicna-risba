# -*- coding: utf-8 -*-
"""UI/UX Plan I: shematski 3D predogled ograje.

ISKRENO: ni fotorealistično (AI vizualizator je izven pravil #8), ni
konstrukcijski model — shematski prikaz iz istega cfg kot risba.
"""
import os


from conftest import osnovni_cfg, cfg_pokoncna

import tridimenzionalno as t3


def test_sestavi_3d_ograda():
    cfg = osnovni_cfg("x.pdf")
    fig = t3.sestavi_3d(cfg)
    ax = fig.axes[0]
    assert len(ax.collections) > 5, "premalo skatlic v 3D prikazu"
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_sestavi_3d_pokoncna():
    cfg = cfg_pokoncna("x.pdf")
    fig = t3.sestavi_3d(cfg)
    ax = fig.axes[0]
    assert len(ax.collections) > 5
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_sestavi_3d_z_vrati():
    cfg = osnovni_cfg(
        "x.pdf",
        vrata=[{"tip": "enokrilna", "x": 200, "sirina": 900, "visina": 1500,
                "smer": "desno-navzven"}])
    fig = t3.sestavi_3d(cfg)
    assert len(fig.axes[0].collections) > 5
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_narisi_3d_png(tmp_path):
    cfg = osnovni_cfg("x.pdf")
    pot = str(tmp_path / "3d.png")
    t3.narisi_3d_png(cfg, pot)
    assert os.path.getsize(pot) > 1000


def test_razdeli_okoli_odprtin():
    # interval 0..1000 z odprtino 200..400 -> dva kosa
    kosi = t3._razdeli(0, 1000, [(200, 400, "V1")])
    assert kosi == [(0.0, 200.0), (400.0, 1000.0)]
    # če odprtina pokrije vse -> ni kosov
    assert t3._razdeli(0, 100, [(0, 100, "V1")]) == []