# -*- coding: utf-8 -*-
"""UI/UX Plan C: barvni statusi mer v obrazcu (merjenje.py).

Metrologist vzor: „vsak rezultat ima oceno zaupanja — takoj veš, ali
številki verjeti.“ Testi preverjajo statuse, barve zaupanja in obarvan
vnos v seznam meritev.
"""
import pytest

import merjenje


def test_status_meritve_znaki_in_barve():
    zelena, znak, _ = merjenje.status_meritve("izmerjeno")
    assert znak == "†" and zelena == "#1b5e20"
    rdeca, znak, _ = merjenje.status_meritve("neznano")
    assert znak == "?? " .strip() and rdeca == "#b00020"
    # neznani status pade v neznano (ne v zeleno!)
    assert merjenje.status_meritve("bogve")[0] == "#b00020"


def test_barva_zaupanja_meje():
    assert merjenje.barva_zaupanja(0.9) == ("#1b5e20", "ZANESLJIVO")
    assert merjenje.barva_zaupanja(0.5) == ("#b26a00", "PREVERI")
    assert merjenje.barva_zaupanja(0.1) == ("#b00020", "NEGOTOVO")
    assert merjenje.barva_zaupanja(None) == ("#b00020", "NEGOTOVO")


tk = pytest.importorskip("tkinter")


def _app():
    try:
        app = merjenje.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    return app


def test_vstavi_meritev_obarva_vnos():
    app = _app()
    try:
        app._vstavi_meritev("sirina", 1234.0, 2468.0)
        app._vstavi_meritev("visina", None, 500.0)
        prvi = app.lst.get(0)
        drugi = app.lst.get(1)
        assert "1234 mm [†]" in prvi
        assert "500 px [?? — brez merila]" in drugi
        assert app.lst.itemconfig(0, "fg")[-1] == "#1b5e20"   # zeleno
        assert app.lst.itemconfig(1, "fg")[-1] == "#b00020"   # rdeče
    finally:
        app.destroy()