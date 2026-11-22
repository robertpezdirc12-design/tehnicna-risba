# -*- coding: utf-8 -*-
"""Načrt 7: revizijska tabela + diff povzetek ('en model — ena revizija')."""
import tkinter as tk

import yaml
from pypdf import PdfReader

import jedro
import revizija
from conftest import osnovni_cfg


# ---------- oznake (ISO 7200: brez I in O) ----------

def test_naslednja_oznaka():
    assert revizija.naslednja_oznaka([]) == "A"
    assert revizija.naslednja_oznaka([["A", "d", "o", "i"]]) == "B"
    assert revizija.naslednja_oznaka([["H", "d", "o", "i"]]) == "J"   # preskok I
    assert revizija.naslednja_oznaka([["N", "d", "o", "i"]]) == "P"   # preskok O
    assert revizija.naslednja_oznaka([["Z", "d", "o", "i"]]) == "AA"


# ---------- diff povzetek ----------

def test_diff_povzetek_spremembe():
    staro = {"mere": {"sirina": 3000, "visina": 1850}, "barva": "RAL 7016",
             "vrata": []}
    novo = {"mere": {"sirina": 3100, "visina": 1850}, "barva": "Siva",
            "vrata": [{"tip": "enokrilna", "x": 200, "sirina": 900,
                       "visina": 1500}]}
    d = revizija.diff_povzetek(staro, novo)
    assert any("širina: 3000 → 3100" in v for v in d)
    assert any("barva: RAL 7016 → Siva" in v for v in d)
    assert any("vrata: dodano:" in v and "enokrilna 900×1500 @200" in v
               for v in d)
    # nespremenjenega ni v povzetku
    assert not any("višina" in v for v in d)


def test_diff_povzetek_brez_sprememb():
    cfg = {"mere": {"sirina": 3000}, "vrata": []}
    assert revizija.diff_povzetek(revizija.snapshot(cfg),
                                  revizija.snapshot(cfg)) == []


def test_diff_izloci_volatilne_kljuce():
    """Izhod, datum in status niso spremembe izdelka."""
    a = {"mere": {"sirina": 3000}, "izhod": "a.pdf", "datum": "1.1.2026",
         "status_dokumenta": "V DELU"}
    b = {"mere": {"sirina": 3000}, "izhod": "b.pdf", "datum": "2.2.2026",
         "status_dokumenta": "IZVEDENO"}
    assert revizija.diff_povzetek(revizija.snapshot(a),
                                  revizija.snapshot(b)) == []


# ---------- nova revizija ----------

def test_nova_revizija_krog():
    cfg: dict = {"ime": "T", "izdelal": "RP",
                 "mere": {"sirina": 3000, "visina": 1850}, "vrata": []}
    v1, p1 = revizija.nova_revizija(cfg)
    assert v1[0] == "A" and v1[3] == "RP"
    assert v1[2] == "Prva izdaja"
    assert cfg["rev_snapshot"] is not None
    # sprememba -> nova revizija z diff opisom
    cfg["mere"]["sirina"] = 3100
    v2, p2 = revizija.nova_revizija(cfg)
    assert v2[0] == "B"
    assert any("širina" in v for v in p2)
    assert "širina" in v2[2]           # diff je tudi v opisu revizije
    assert len(cfg["revizije"]) == 2


def test_nova_revizija_lastni_opis():
    cfg: dict = {"mere": {"sirina": 3000}, "vrata": []}
    revizija.nova_revizija(cfg)
    cfg["mere"]["sirina"] = 3100
    v, _ = revizija.nova_revizija(cfg, opis="Stranka želi širše polje")
    assert v[2] == "Stranka želi širše polje"


def test_preveri_cfg_revizije():
    cfg = osnovni_cfg("x.pdf")
    cfg["revizije"] = [["A", "01.01.2026", "Prva", "RP"]]
    assert jedro.preveri_cfg(cfg) == []
    cfg["revizije"] = [["", "d", "o", "i"]]
    assert any("Revizija 1" in e for e in jedro.preveri_cfg(cfg))
    cfg["revizije"] = "napačno"
    assert any("revizije" in e for e in jedro.preveri_cfg(cfg))


def test_revizije_v_pdf(tmp_path):
    """Revizije so vidne na listu: tabela + REV. v naslovnem bloku."""
    cfg = osnovni_cfg(str(tmp_path / "r.pdf"))
    cfg["revizije"] = [["A", "01.01.2026", "Prva izdaja", "RP"],
                       ["B", "15.02.2026", "širina: 3000 → 3100", "RP"]]
    pdf, _png, _dod, _kol = __import__("risba").generiraj(cfg, dpi_png=30)
    bes = "".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
    assert "REV. B" in bes
    assert "Prva izdaja" in bes
    assert "širina: 3000 → 3100" in bes


def test_revizije_yaml_roundtrip(tmp_path):
    cfg = osnovni_cfg(str(tmp_path / "y.pdf"))
    revizija.nova_revizija(cfg)
    cfg["mere"]["visina"] = 2000
    revizija.nova_revizija(cfg)
    pot = tmp_path / "projekt.yaml"
    pot.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    nalozen = yaml.safe_load(pot.read_text(encoding="utf-8"))
    assert [v[0] for v in nalozen["revizije"]] == ["A", "B"]
    assert isinstance(nalozen["rev_snapshot"], dict)


# ---------- GUI: meni + dialog z diffom ----------

def _najdi_gumb(w, label):
    for c in w.winfo_children():
        try:
            if str(c.cget("text")) == label:
                return c
        except tk.TclError:
            pass
        najden = _najdi_gumb(c, label)
        if najden is not None:
            return najden
    return None


def test_vmesnik_nova_revizija(monkeypatch):
    import vmesnik

    try:
        u = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        u.withdraw()
        u.update_idletasks()
        # sprememba polja -> diff mora biti viden v dialogu
        u.v["sirina"].set("3100")
        videno = {}

        def auto(self):
            b = _najdi_gumb(self, "Shrani revizijo")
            assert b is not None, "gumb 'Shrani revizijo' ni najden"
            videno["gumb"] = True
            b.invoke()

        monkeypatch.setattr(tk.Toplevel, "wait_window", auto)
        u._nova_revizija()
        assert videno.get("gumb")
        assert [v[0] for v in u.revizije] == ["A"]
        assert u.rev_snapshot is not None
        cfg = u._zberi_cfg()
        assert cfg["revizije"] and cfg["revizije"][0][0] == "A"
        assert cfg["rev_snapshot"] is not None
        # druga sprememba -> revizija B z diff opisom
        u.v["visina"].set("2000")
        u._nova_revizija()
        assert [v[0] for v in u.revizije] == ["A", "B"]
        assert "višina" in u.revizije[1][2]
    finally:
        u.destroy()


def test_vmesnik_meni_vsebuje_revizijo():
    import vmesnik
    try:
        u = vmesnik.App()
    except tk.TclError:
        pytest.skip("Tk okolje ni na voljo")
    try:
        u.withdraw()
        u.update_idletasks()
        meni = u.nametowidget(u.cget("menu"))
        najden = False
        for i in range(meni.index("end") + 1):
            if meni.type(i) != "cascade":
                continue
            m = u.nametowidget(meni.entrycget(i, "menu"))
            for j in range(m.index("end") + 1):
                if m.type(j) == "command" and "revizij" in str(
                        m.entrycget(j, "label")).lower():
                    najden = True
        assert najden, "meni Datoteka nima postavke 'Nova revizija…'"
    finally:
        u.destroy()
