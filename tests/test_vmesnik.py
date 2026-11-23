# -*- coding: utf-8 -*-
"""B5 in regresija 4 (GUI): shranjevanje/nalaganje nastavitev.

Napaki: (1) `_zberi_cfg` je shranil ključ 'pritrditev', `_nalozi_zadnje` pa
bral 'pritrditev_nacin' — nastavitev se ni obnovila; (2) main je po
nalaganju z `_privzeti()` prepisal vse naložene vrednosti s privzetimi.
"""
import pytest

tk = pytest.importorskip("tkinter")

import vmesnik


def _app():
    try:
        app = vmesnik.App()
    except Exception as e:                       # pragma: no cover
        pytest.skip(f"Tk okolja ni mogoče zagnati: {e}")
    app.withdraw()
    return app


@pytest.fixture
def datoteka(tmp_path, monkeypatch):
    p = str(tmp_path / "zadnje.yaml")
    monkeypatch.setattr(vmesnik, "DAT_ZADNJE", p)
    return p


def test_zberi_cfg_vkljucuje_pravilna_kljuca(datoteka):
    app = _app()
    try:
        app.v["pritrditev_nacin"].set("vrh")
        cfg = app._zberi_cfg()
    finally:
        app.destroy()
    assert cfg["pritrditev"] == "vrh"            # ključ za risbo (naslovnica)
    assert cfg["pritrditev_nacin"] == "vrh"      # ključ za shranjevanje/branje


def test_pritrditev_se_pravilno_shrani_in_obnovi(datoteka):
    app = _app()
    try:
        app.v["pritrditev_nacin"].set("vrh")
        app._shrani_zadnje()
    finally:
        app.destroy()
    app2 = _app()                                # ob zagonu _nalozi_zadnje
    try:
        assert app2.v["pritrditev_nacin"].get() == "vrh"
    finally:
        app2.destroy()


def test_zagon_ne_pripise_privzetih_cez_nalozene(datoteka):
    """Regresija 4: zagon ne sme prepisati naloženih nastavitev s privzetimi."""
    app = _app()
    try:
        app.v["objekt"].set("MOJ OBJEKT")
        app.v["stranka"].set("Stranka d.o.o.")
        app.v["risba_st"].set("PO-777")
        app.v["pritrditev_nacin"].set("bočno")
        app._shrani_zadnje()
    finally:
        app.destroy()
    app2 = _app()
    try:
        assert app2.v["objekt"].get() == "MOJ OBJEKT"
        assert app2.v["stranka"].get() == "Stranka d.o.o."
        assert app2.v["risba_st"].get() == "PO-777"
        assert app2.v["pritrditev_nacin"].get() == "bočno"
    finally:
        app2.destroy()


def test_privzeta_uporaba_ostankov_je_izklopljena(datoteka):
    """A3/A5: ob zagonu je 'Uporabi ostanke' privzeto izklopljeno (varno)."""
    app = _app()
    try:
        assert app.st_ost.get() is False
    finally:
        app.destroy()


def test_gumb_odpisi_ostanke_je_sam_ob_spremembi(datoteka):
    """B1: gumb je omogočen le, ko dejansko obstaja sprememba skladišča."""
    app = _app()
    try:
        assert str(app.btn_ost["state"]) == "disabled"
    finally:
        app.destroy()

# ---------------------------------------------------------------- Plan 4
def test_preklop_teme():
    """Plan 4: preklop teme (ttkbootstrap) deluje ali pošteno javi, da
    paket ni nameščen; aplikacija deluje v obeh primerih."""
    import tkinter as tk
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        assert app._tema in ("svetla", None)
        app._preklopi_temo()
        if app._ttkb is None:
            assert "namesti ttkbootstrap" in app.status.cget("text")
        else:
            assert app._tema == "temna"
            app._preklopi_temo()
            assert app._tema == "svetla"
    finally:
        app.destroy()


def test_statika_pregled_gumb():
    """Plan 6: gumb STATIČNI PREGLED pripravi povzetek brez napake
    (dialog se odpre le z interakcijo — tu preverimo izračun)."""
    import statika
    import tkinter as tk
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        cfg = app._zberi_cfg()
        m = cfg.get("mere", {})
        razmak = (m.get("razmak_stebrov") or m.get("razmak_nosilcev")
                  or 1500.0)
        t = statika.povzetek(float(razmak),
                             max(float(m.get("visina", 1100.0))
                                 - float(m.get("odcep", 0) or 0), 1.0))
        assert "NI STATIČNI IZRAČUN" in t
    finally:
        app.destroy()


def test_foto_predogled(tmp_path):
    """Pritožba uporabnika: vstavljene slike se ne vidijo. Zdaj vmesnik
    pokaže predogled fotografije (in se pobriše, ko je pot prazen)."""
    import tkinter as tk
    from PIL import Image
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        pot = str(tmp_path / "foto.jpg")
        Image.new("RGB", (320, 240), (30, 90, 160)).save(pot, format="JPEG")
        app.v["foto"].set(pot)          # trace sam pokliče osvežitev
        assert app._foto_tk is not None
        app.v["foto"].set("")
        assert app._foto_tk is None
    finally:
        app.destroy()


def test_meri_slike_dvojna_korenina(tmp_path, monkeypatch):
    """Napaka iz preverjanja vmesnikov: MERI S SLIKE odpre DRUGO Tk-korenino;
    ImageTk.PhotoImage brez master=self se veže na prvo in create_image
    vrne 'image pyimageN doesn't exist'."""
    import tkinter as tk
    import tkinter.messagebox as mb
    # slika je namerno majhna (200x120) -> merjenje javi 'mala slika' s
    # MODALNIM dialogom; v testih ga nadomestimo, sicer test obtiči.
    monkeypatch.setattr(mb, "showwarning", lambda *a, **k: None)
    monkeypatch.setattr(mb, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(mb, "showerror", lambda *a, **k: None)
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        from PIL import Image
        pot = str(tmp_path / "f.jpg")
        Image.new("RGB", (200, 120), (90, 60, 60)).save(pot, format="JPEG")
        import merjenje
        m = merjenje.App(pot)      # brez izjeme tudi ob živi prvi korenini
        m.update()
        assert m._tk_img is not None
        m.destroy()
    finally:
        app.destroy()


def test_odpri_projekt_roundtrip(tmp_path):
    """Projekt je bil doslej mogoče le SHRANITI — vmesnik ga ni mogel
    znova odpreti. Zdaj: _zberi_cfg -> YAML -> _odpri_projekt -> polja."""
    import tkinter as tk
    import tkinter.filedialog as fd
    import tkinter.messagebox as mb
    import yaml
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    stare = (fd.askopenfilename, mb.showinfo)
    try:
        app.v["ime"].set("Projekt X")
        app.v["sirina"].set("3333")
        app.vrata_sez = [{"tip": "enokrilna", "x": 100, "sirina": 900,
                          "visina": 1500, "smer": "desno-navzven",
                          "tip_rocaja": "kljukica",
                          "tip_kljucavnice": "cilinder"}]
        cfg = app._zberi_cfg()
        pot = str(tmp_path / "projekt.yaml")
        with open(pot, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        # "umazan" vnos pred odpiranjem
        app.v["sirina"].set("1111")
        app.v["ime"].set("Drugo")
        app.vrata_sez = []
        fd.askopenfilename = lambda *a, **k: pot
        mb.showinfo = lambda *a, **k: "ok"
        app._odpri_projekt()
        app.update()
        assert app.v["sirina"].get() == "3333", "polja morajo biti obnovljena"
        assert app.v["ime"].get() == "Projekt X"
        assert len(app.vrata_sez) == 1, "vrata morajo biti obnovljena"
    finally:
        fd.askopenfilename, mb.showinfo = stare
        app.destroy()


def test_cnc_izvoz_iz_vmesnika(tmp_path):
    """CNC izvoz (CSV + G-code) iz vmesnika — skupine LOČENE po profilih
    (modul cnc.py je bil prej popolnoma nedosegljiv iz vmesnika)."""
    import os
    import tkinter as tk
    import tkinter.messagebox as mb
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    stare = (mb.showinfo, mb.showerror)
    try:
        base = str(tmp_path / "CNC-001")
        app.v["izhod"].set(base + ".pdf")
        app.v["sirina"].set("3000")
        app.v["visina"].set("1850")
        app.v["odcep"].set("250")
        app.vrata_sez = [{"tip": "enokrilna", "x": 200, "sirina": 900,
                          "visina": 1500, "smer": "desno-navzven",
                          "tip_rocaja": "kljukica",
                          "tip_kljucavnice": "cilinder"}]
        mb.showinfo = lambda *a, **k: "ok"
        mb.showerror = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError(a))
        app._cnc_izvoz()
        app.update()
        for ozn in ("lamele", "vrata"):
            assert os.path.isfile(f"{base}-cnc-{ozn}.csv"), ozn
            assert os.path.isfile(f"{base}-cnc-{ozn}.nc"), ozn
        with open(f"{base}-cnc-lamele.nc", encoding="utf-8") as f:
            nc = f.read()
        assert "G21" in nc, "G-code mora biti v mm"
        assert "informativni" in nc.lower(), "pošteno opozorilo operaterju"
        with open(f"{base}-cnc-vrata.csv", encoding="utf-8") as f:
            vrata = f.read()
        with open(f"{base}-cnc-lamele.csv", encoding="utf-8") as f:
            lamele = f.read()
        assert "V1-" in vrata, "vratni kosi morajo biti v svojem CSV"
        assert "V1-" not in lamele, "profila se NE smeta mešati"
    finally:
        mb.showinfo, mb.showerror = stare
        app.destroy()


def test_nova_vrsta_pilot_okno(tmp_path, monkeypatch):
    """Pilot 'lesena vertikalna' (F4, issue #5) je bil nedosegljiv iz
    vmesnika — zdaj ima okno s polji iz deklarativnih opisov (U3)."""
    import os
    import tkinter as tk
    import tkinter.messagebox as mb
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        import nova_vrsta
        okno = vmesnik.NovaVrstaOkno(app)
        okno.update()
        assert set(okno.v) == {p[0] for p in nova_vrsta.POLJA}, \
            "polja morajo priti iz opisov POLJA"
        sporocila = []
        stare = (mb.showinfo, mb.showerror)

        def _info(*a, **k):
            sporocila.append(str(a[-1]))
            return "ok"

        def _napaka(*a, **k):
            sporocila.append("NAPAKA: " + str(a[-1]))

        mb.showinfo = _info
        mb.showerror = _napaka
        try:
            okno._pokazi_kolicine()
            assert any("Deske:" in s for s in sporocila), "količine morajo priti"
            okno._predogled()
        finally:
            mb.showinfo, mb.showerror = stare
        assert os.path.isfile(os.path.join(os.environ.get("TEMP", "."),
                                           "nova_vrsta_predogled.png"))
    finally:
        app.destroy()


def test_meni_vsebuje_vse_funkcije():
    """Zahteva uporabnika: funkcije v SPUSTNIH MENIJIH, ne razmetane po
    ekranu — a vse morajo ostati dosegljive."""
    import tkinter as tk
    try:
        app = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        meni = app.nametowidget(app.cget("menu"))
        nizi = [meni.entrycget(i, "label")
                for i in range(meni.index("end") + 1)
                if meni.type(i) == "cascade"]
        assert nizi == ["Datoteka", "Urejanje", "Vstavi", "Pogled",
                        "Orodja", "Pomoč"]
        vsebina = {}
        for i in range(meni.index("end") + 1):
            if meni.type(i) != "cascade":
                continue
            pod = app.nametowidget(meni.entrycget(i, "menu"))
            vsebina[meni.entrycget(i, "label")] = [
                pod.entrycget(j, "label")
                for j in range(pod.index("end") + 1)
                if pod.type(j) == "command"]
        nujne = {
            "Datoteka": ["Odpri projekt…", "Shrani projekt (.yaml)",
                         "NARIŠI RISBO", "Odpri PDF", "Izvozi DXF",
                         "CNC (CSV + G-code)", "Naročilo (kopiraj)",
                         "Ponudba (PDF)"],
            "Urejanje": ["Razveljavi", "Ponovi"],
            "Pogled": ["Cel zaslon", "3D predogled", "Preklopi temo"],
            "Orodja": ["Meri s slike (pomožno merjenje)",
                       "Avtomatska skica (iz foto)", "Statični pregled",
                       "Nova vrsta (pilot)…", "Odpiši ostanke"],
            "Pomoč": ["Čarovnik (voden vnos)", "Preveri posodobitev",
                      "O programu"],
        }
        for kljuc, seznam in nujne.items():
            for n in seznam:
                assert n in vsebina[kljuc], f"{kljuc} manjka: {n}"
        # upravljanje stanja deluje prek adapterjev (kot prej pri gumbih)
        assert app.btn_ost["state"] == "disabled"
        app.btn_ost.config(state="normal")
        assert app.btn_ost["state"] == "normal"
        app.btn_ost.config(state="disabled")
    finally:
        app.destroy()
