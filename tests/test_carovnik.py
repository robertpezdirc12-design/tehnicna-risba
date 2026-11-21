# -*- coding: utf-8 -*-
"""UI/UX Plan E: čarovnik po korakih (voden vnos).

Vzor Metrologist: jasni koraki z napredkom. Čarovnik ureja ISTE
spremenljivke kot obrazec — zato delujeta živi povzetek in undo/redo.
"""
import pytest

tk = pytest.importorskip("tkinter")

import vmesnik


@pytest.fixture
def datoteka(tmp_path, monkeypatch):
    p = str(tmp_path / "zadnje.yaml")
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", p)
    return p


def _app_carovnik():
    try:
        app = vmesnik.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    car = vmesnik.Carovnik(app)
    return app, car


def test_koraki_naprej_nazaj_in_meje(datoteka):
    app, car = _app_carovnik()
    try:
        assert car.lbl_korak.cget("text").startswith("Korak 1/5")
        car._naprej()
        assert car.lbl_korak.cget("text").startswith("Korak 2/5")
        car._nazaj()
        assert car.lbl_korak.cget("text").startswith("Korak 1/5")
        car._nazaj()                             # na začetku — brez napake
        assert car.lbl_korak.cget("text").startswith("Korak 1/5")
    finally:
        app.destroy()


def test_carovnik_deli_spremenljivke_z_obrazcem(datoteka):
    app, car = _app_carovnik()
    try:
        app.v["sirina"].set("3456")               # isti vir kot obrazec
        car._naprej()                            # korak 2: mere
        vrednosti = [e.cget("textvariable") for e in car.vsebina.winfo_children()
                     if isinstance(e, tk.ttk.Entry) or isinstance(e, tk.Entry)]
        assert any(str(v) == str(app.v["sirina"]) for v in vrednosti)
    finally:
        app.destroy()


def test_neveljaven_vnos_blokira_naprej(datoteka):
    app, car = _app_carovnik()
    try:
        car._naprej()                            # korak 2: mere
        app.v["sirina"].set("NI ŠTEVILO")
        car._naprej()                            # NE sme naprej
        assert car.lbl_korak.cget("text").startswith("Korak 2/5")
        assert car.lbl_opozorilo.cget("text"), "manjka obvestilo o napaki"
        app.v["sirina"].set("2500")
        car._naprej()
        assert car.lbl_korak.cget("text").startswith("Korak 3/5")
    finally:
        app.destroy()


def test_zakljucek_zapre_okno(datoteka):
    app, car = _app_carovnik()
    try:
        for _ in range(4):
            car._naprej()
        assert car.lbl_korak.cget("text").startswith("Korak 5/5")
        assert "Dokončaj" in car.btn_naprej.cget("text")
        car._naprej()                            # zaključi
        assert not car.winfo_exists()
    finally:
        app.destroy()