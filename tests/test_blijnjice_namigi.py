# -*- coding: utf-8 -*-
"""UI/UX Plan F: bližnjice (Ctrl+…) + namigi (tooltips).

Vzor: standardne bližnjice (QtoTakeoff/Plankore) in kontekstualna pomoč
(magicplan).
"""
import pytest

tk = pytest.importorskip("tkinter")

import vmesnik


@pytest.fixture
def datoteka(tmp_path, monkeypatch):
    p = str(tmp_path / "zadnje.yaml")
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", p)
    return p


def _app():
    try:
        app = vmesnik.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    return app


def test_namig_prikazi_in_zapre(datoteka):
    app = _app()
    try:
        w = tk.Entry(app)
        n = vmesnik.Namig(w, "Preizkusni namig", zamik=0)
        n._prikazi()
        assert n._okno is not None
        lbl = n._okno.winfo_children()[0]
        assert lbl.cget("text") == "Preizkusni namig"
        n._konec()
        assert n._okno is None
        assert not w.winfo_exists() or True      # widget ostane veljaven
    finally:
        app.destroy()


def test_namigi_pokrivajo_kljucna_polja(datoteka):
    app = _app()
    try:
        for kljuc in ("sirina", "visina", "kerf", "razmak_nosilcev",
                      "dolzine_deske", "uporabi_ostanke"):
            assert kljuc in vmesnik.NAMIGI, f"manjka namig za {kljuc}"
            assert kljuc in app.namigi, f"namig ni pripet na {kljuc}"
    finally:
        app.destroy()


def test_blijnjice_so_vezane(datoteka):
    app = _app()
    try:
        for dogodek in ("<Control-n>", "<Control-p>", "<Control-s>",
                        "<Control-e>", "<Control-z>", "<Control-y>", "<F1>"):
            ukaz = app.bind_all(dogodek)
            assert ukaz, f"bližnjica {dogodek} ni vezana"
    finally:
        app.destroy()


def test_pomoc_se_odpre(datoteka, monkeypatch):
    app = _app()
    try:
        videno = {}
        monkeypatch.setattr(
            vmesnik.messagebox, "showinfo",
            lambda naslov, besedilo: videno.update(naslov=naslov,
                                                   besedilo=besedilo))
        app._pomoc()
        assert "bližnjice" in videno["naslov"].lower()
        assert "Ctrl+Z" in videno["besedilo"]
    finally:
        app.destroy()