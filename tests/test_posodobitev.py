# -*- coding: utf-8 -*-
"""Plan 5: logika preverjanja posodobitev (BREZ omrežja — klic se
nadomesti)."""
import posodobitev


def test_primerjaj_verziji_numericno():
    assert posodobitev.primerjaj_verziji("1.2", "1.10") == -1   # ne leksikografsko
    assert posodobitev.primerjaj_verziji("1.10", "1.2") == 1
    assert posodobitev.primerjaj_verziji("1.2", "1.2") == 0
    assert posodobitev.primerjaj_verziji("v1.3", "1.3") == 0
    assert posodobitev.primerjaj_verziji("1.2.1", "1.2") == 1
    assert posodobitev.primerjaj_verziji("1.2", "2") == -1


def test_preveri_posodobitev_nova(monkeypatch):
    monkeypatch.setattr(posodobitev, "odpri_zadnjo_izdajo",
                        lambda *a, **k: {"tag_name": "v1.3",
                                         "html_url": "https://example/rel"})
    r = posodobitev.preveri_posodobitev("1.2")
    assert r == {"novo": True, "verzija": "v1.3",
                 "url": "https://example/rel", "napaka": None}


def test_preveri_posodobitev_enaka_in_starejsa(monkeypatch):
    monkeypatch.setattr(posodobitev, "odpri_zadnjo_izdajo",
                        lambda *a, **k: {"tag_name": "v1.2"})
    r = posodobitev.preveri_posodobitev("1.2")
    assert r["novo"] is False and r["napaka"] is None
    monkeypatch.setattr(posodobitev, "odpri_zadnjo_izdajo",
                        lambda *a, **k: {"tag_name": "v0.9"})
    assert posodobitev.preveri_posodobitev("1.2")["novo"] is False


def test_preveri_posodobitev_omrezna_napaka(monkeypatch):
    def _padec(*a, **k):
        raise OSError("ni omrežja")
    monkeypatch.setattr(posodobitev, "odpri_zadnjo_izdajo", _padec)
    r = posodobitev.preveri_posodobitev("1.2")
    assert r["novo"] is False
    assert "OSError" in r["napaka"]


def test_podpis_brez_certifikata_preskoci(monkeypatch, tmp_path):
    """Plan 5: brez PODPIS_PFX se podpis preskoči (brez napake)."""
    import build_windows
    monkeypatch.delenv("PODPIS_PFX", raising=False)
    r = build_windows.podpisi()
    assert r["podpisano"] is False
    assert "PODPIS_PFX" in r["razlog"]


def test_podpis_z_certifikatom_uporabi_signtool(monkeypatch):
    """Plan 5: s certifikatom se kliče signtool s časovnim žigom RFC 3161
    in BEZ izpisa gesla."""
    import build_windows
    klici = []
    monkeypatch.setenv("PODPIS_PFX", "/tmp/test.pfx")
    monkeypatch.setenv("PODPIS_GESLO", "skrivnost123")

    def _run(ukaz, **kw):
        klici.append(ukaz)
        class R:
            returncode = 0
        return R()
    monkeypatch.setattr(build_windows.subprocess, "run", _run)
    r = build_windows.podpisi()
    assert r["podpisano"] is True
    ukaz = klici[0]
    assert ukaz[0] == "signtool" and ukaz[1] == "sign"
    assert "/tr" in ukaz and "http://timestamp.digicert.com" in ukaz
    assert "/td" in ukaz and "sha256" in ukaz
    assert "skrivnost123" in ukaz            # v ukazu JA (za podpis)
