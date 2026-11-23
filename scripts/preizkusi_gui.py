# -*- coding: utf-8 -*-
"""TEMELJIT preizkus celega GUI-ja (smoke test). Zaženi: python scripts/preizkusi_gui.py

Vsako funkcijo pravega GUI-ja sprožimo v try/except, preverimo pa tudi
VSEBINO izhodov (PDF besedilo prek pypdf, DXF plasti prek ezdxf, CSV,
YAML) — ne le odsotnost izjeme.
"""
import os
import sys
import traceback

import tempfile

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo)
os.chdir(repo)

OUT = os.path.join(tempfile.gettempdir(), "pi_preizkus_gui")
os.makedirs(OUT, exist_ok=True)

# Generirana testna slika — zasebnih fotografij NE uporabljamo.
POT_SLIKE = os.path.join(OUT, "testna_slika.png")
from PIL import Image, ImageDraw  # noqa: E402

if not os.path.isfile(POT_SLIKE):
    slika = Image.new("RGB", (1600, 1200), (140, 130, 120))
    risar = ImageDraw.Draw(slika)
    for x in range(100, 1500, 120):
        risar.line([(x, 150), (x, 1050)], fill=(80, 60, 40), width=14)
    risar.rectangle([150, 900, 1450, 1080], outline=(30, 30, 30), width=8)
    slika.save(POT_SLIKE)

REZULTATI = []


def preveri(area, akcija, fn, tudi=None):
    """Požene akcijo, opcionalno preveri izhod (tudi -> callable -> str/None)."""
    try:
        fn()
        dodatno = tudi() if tudi else None
        if dodatno:
            REZULTATI.append((area, akcija, "NAPAKA-IZHOD", dodatno))
            print(f"  IZHOD-PROBLEM {area} / {akcija}: {dodatno}", flush=True)
        else:
            REZULTATI.append((area, akcija, "OK", ""))
            print(f"  OK {area} / {akcija}", flush=True)
    except Exception as e:
        REZULTATI.append((area, akcija, "NAPAKA", f"{type(e).__name__}: {e}"))
        print(f"  NAPAKA {area} / {akcija}: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc(limit=2)


# ============================================================ priprava
import tkinter as tk  # noqa: E402
from tkinter import filedialog, messagebox, simpledialog, ttk  # noqa: E402
import vmesnik  # noqa: E402
import terenski_gui  # noqa: E402
import terenski_list  # noqa: E402
import merjenje  # noqa: E402

# samodejno zapri modalne dialoge (wait_window), da klici ne obtičijo
_orig_wait = tk.Toplevel.wait_window


def _auto_wait(self):
    def zapri():
        try:
            gumbi = []

            def isci(w):
                for o in w.winfo_children():
                    if isinstance(o, (tk.Button, ttk.Button)):
                        gumbi.append(o)
                    isci(o)

            isci(self)
            potrdi = [g for g in gumbi if str(g.cget("text")).lower() in
                      ("potrdi", "v redu", "shrani", "dodaj", "naprej",
                       "uporabi izbrani načrt", "zaključi", "ok")]
            if potrdi:
                potrdi[-1].invoke()
            else:
                self.destroy()
        except Exception:
            pass

    self.after(250, zapri)
    return _orig_wait(self)


tk.Toplevel.wait_window = _auto_wait  # type: ignore[assignment]

# krmiljenje dialogov
DLG = {"pot": None}
filedialog.askopenfilename = lambda **k: DLG.get("pot") or ""  # type: ignore[assignment]
filedialog.asksaveasfilename = lambda **k: DLG.get("pot") or ""  # type: ignore[assignment]
messagebox.showinfo = lambda *a, **k: None  # type: ignore[assignment]
messagebox.showwarning = lambda *a, **k: None  # type: ignore[assignment]
messagebox.showerror = lambda *a, **k: print(  # type: ignore[assignment]
        "    [showerror]", a[-1][:120],
                                            flush=True)
messagebox.askyesno = lambda *a, **k: True  # type: ignore[assignment]
messagebox.askokcancel = lambda *a, **k: True  # type: ignore[assignment]
simpledialog.askfloat = lambda *a, **k: 1500.0  # type: ignore[assignment]
simpledialog.askstring = lambda *a, **k: "PREIZKUS"  # type: ignore[assignment]

app = vmesnik.App()
app.geometry("1150x780+20+20")
app.update_idletasks()


def osvezi():
    app.update_idletasks()
    app.update()


cfg_pot = os.path.join(OUT, "projekt.yaml")
pdf_pot = os.path.join(OUT, "BO-TEST.pdf")

# realni podatki balkona
app.v["ime"].set("Balkonska ograja — preizkus")
app.v["risba_st"].set("PO-100")
app.v["izdelal"].set("R. Pezdirc")
app.v["sirina"].set("2900")
app.v["visina"].set("1850")
app.v["globina"].set("1200")
app.v["odcep"].set("300")
app.v["izhod"].set(pdf_pot)
app.v["barva"].set("Teak")
for k, val in (("cene_wpc", "10"), ("cene_alu", "10"), ("cene_rocaj", "10"),
               ("cene_nosilec", "10"), ("cene_vijak", "10"),
               ("cene_fasadni_vijak", "10"), ("cene_anker", "10"),
               ("cene_osnova", "10"), ("cene_delo", "10")):
    if k in app.v:
        app.v[k].set(val)

print("=== 1. SCENA (slika) ===", flush=True)
DLG["pot"] = POT_SLIKE
preveri("Scena", "vstavi sliko (meni)", lambda: app._scena_nalozi(POT_SLIKE))
preveri("Scena", "vrstica namera vidna",
        lambda: (_n := app.namera_vrstica.winfo_manager()) == "pack"
        or (_ for _ in ()).throw(AssertionError(f"manager={_n}")))
preveri("Scena", "rotacija levo", lambda: app._scena_obrni_levo())
preveri("Scena", "rotacija desno", lambda: app._scena_obrni_desno())
preveri("Scena", "foto v projekt", lambda: app._scena_foto_v_projekt(),
        tudi=lambda: ("foto ni nastavljen" if app.v["foto"].get() != os.path.abspath(POT_SLIKE) else None))
preveri("Scena", "odložišče (prazno) — vljudno obvestilo",
        lambda: app._scena_iz_odlozisca())
preveri("Scena", "odstrani", lambda: app._scena_pocisti())
preveri("Scena", "znova naloži za nadaljevanje",
        lambda: app._scena_nalozi(POT_SLIKE))

print("=== 2. MERILO / MERJENJE V PROSTORU ===", flush=True)
class D:
    x = 0
    y = 0


class _ev:
    def __init__(self, x, y):
        self.x, self.y = x, y


def klik(x, y):
    d = D()
    d.x, d.y = x, y
    return d


app.predogled.slika_koordinate = lambda e: (float(e.x), float(e.y))
preveri("Merilo", "nastavi merilo (2 točki + 1500 mm)", lambda: (
    app._merilo_zacni(), app._merilo_klik(klik(100, 50)),
    app._merilo_klik(klik(1300, 50))))
preveri("Merilo", "merilo izračunano",
        lambda: abs(app.scena["merilo"] - 1200 / 1500) < 1e-9 or (_ for _ in ()).throw(AssertionError(str(app.scena["merilo"]))))
preveri("Merilo", "izmeri v prostoru (2 točki)", lambda: (
    app._merjenje_zacni(), app._merjenje_klik(klik(0, 0)),
    app._merjenje_klik(klik(240, 0))))
preveri("Merilo", "izpis mm je označen",
        lambda: "izmerjeno po sliki" in str(app.status.cget("text"))
        or (_ for _ in ()).throw(AssertionError(str(app.status.cget("text")))))

print("=== 3. PROJEKT (shramba/nalaganje) ===", flush=True)
DLG["pot"] = cfg_pot
preveri("Projekt", "shrani (.yaml)", lambda: app._shrani_projekt(),
        tudi=lambda: (None if os.path.isfile(cfg_pot) else "datoteke ni"))
preveri("Projekt", "odpri (.yaml)", lambda: app._odpri_projekt())
DLG["pot"] = POT_SLIKE
preveri("Projekt", "odpri sliko prek 'Odpri projekt…'", lambda: app._odpri_projekt())

print("=== 4. RISBA (PDF) — obe predlogi ===", flush=True)


def narisi_in_pocakaj():
    """Generiraj in počakaj na KONEC ozadnje niti (sicer dirka s starim PDF)."""
    import threading
    import time
    if os.path.isfile(pdf_pot):
        os.remove(pdf_pot)
    baza = threading.active_count()
    app._narisi()
    kraj = time.time() + 120
    while time.time() < kraj:
        time.sleep(0.5)
        if threading.active_count() > baza:
            continue
        if os.path.isfile(pdf_pot) and os.path.getsize(pdf_pot) > 0:
            time.sleep(1.0)
            return None
    return "PDF ni končan (120 s)"


preveri("Risba", "NARIŠI RISBO (ograja)", narisi_in_pocakaj)


def pocakaj(pot, timeout=120):
    """Počakaj, da ozadnja nit konča in datoteka končana (velikost stabilna)."""
    import time
    import threading
    kraj = time.time() + timeout
    zadnja = -1
    stabilnih = 0
    while time.time() < kraj:
        if threading.active_count() > 2:   # ozadnja nit še dela
            stabilnih = 0
            time.sleep(0.5)
            continue
        time.sleep(0.5)
        if not os.path.isfile(pot):
            continue
        vel = os.path.getsize(pot)
        if vel > 0 and vel == zadnja:
            stabilnih += 1
            if stabilnih >= 4:      # 2 s nespremenjene velikosti
                return None
        else:
            stabilnih = 0
        zadnja = vel
    return f"datoteka {os.path.basename(pot)} ni končana ({timeout}s)"


def pdf_vsebina(pot, iskano):
    from pypdf import PdfReader
    besedilo = "".join((p.extract_text() or "") for p in PdfReader(pot).pages)
    return None if all(x in besedilo for x in iskano) else f"manjka {iskano}"


preveri("Risba", "PDF vsebuje vsebine (ograja)",
        lambda: None, tudi=lambda: pdf_vsebina(
            pdf_pot, ["SPREDNJI POGLLED", "T1", "▲ VRH", "ISO 2768",
                      "KONTROLNI SEZNAM"]))

app.v["predloga"].set("pokončna")
app._preklopi_predlogo()
preveri("Risba", "NARIŠI RISBO (pokončna)", narisi_in_pocakaj)
preveri("Risba", "PDF vsebuje vsebine (pokončna)",
        lambda: None, tudi=lambda: pdf_vsebina(
            pdf_pot, ["SPREDNJI POGLLED", "T1", "DETAJL 1"]))
app.v["predloga"].set("ograja")
app._preklopi_predlogo()
app._narisi()

print("=== 5. IZVOZI ===", flush=True)
dxf_pot = os.path.join(OUT, "izvoz.dxf")
DLG["pot"] = dxf_pot


def dxf_preveri():
    import ezdxf
    doc = ezdxf.readfile(dxf_pot)
    plasti = {l.dxf.name for l in doc.layers}
    # ISO 13567 plasti (dxf_izvoz.PLASTI)
    manjka = {"M-ELEM-CONT", "M-STEB-CONT", "M-ANNO-DIMS"} - plasti
    return f"DXF manjka plasti: {manjka}" if manjka else None


preveri("Izvoz", "DXF", lambda: app._izvozi_dxf(), tudi=dxf_preveri)
cnc_dir = OUT
preveri("Izvoz", "CNC (CSV + G-code)", lambda: app._cnc_izvoz())
preveri("Izvoz", "Naročilo (kopiraj)", lambda: app._narocilo_kopiraj())
ponudba_pot = os.path.splitext(pdf_pot)[0] + "-ponudba.pdf"   # ob risbo
preveri("Izvoz", "Ponudba (PDF)", lambda: app._ponudba_pdf(),
        tudi=lambda: (None if os.path.isfile(ponudba_pot) else "ni datoteke"))

print("=== 6. REVIZIJE / STATUS / QC ===", flush=True)
preveri("Revizije", "nova revizija (diff)", lambda: app._nova_revizija())
preveri("Status", "tok V DELU → ZA POTRDITEV → IZVEDENO",
        lambda: (app.v["status_dokumenta"].set("ZA POTRDITEV"),
                 app.v["status_dokumenta"].set("IZVEDENO"),
                 app._status_spremenjen(None),
                 app.v["status_dokumenta"].set("V DELU")))

print("=== 7. Vmesniška orodja ===", flush=True)
preveri("Orodja", "živi povzetek", lambda: app._zivi_osvezi())
preveri("Orodja", "preprosti/napredni način", lambda: (
    app.st_preprost.set(False), app._preklopi_nacin(),
    app.st_preprost.set(True), app._preklopi_nacin()))
preveri("Orodja", "statični pregled", lambda: app._statika_pregled())
preveri("Orodja", "primerjava načrtov razreza", lambda: app._rezni_nacrt_dialog())
preveri("Orodja", "odpiši ostanke", lambda: app._odpisi_ostanke())
preveri("Orodja", "3D predogled", lambda: app._3d_predogled())
preveri("Orodja", "nova vrsta (pilot)", lambda: app._nova_vrsta_okno())
preveri("Orodja", "čarovnik", lambda: app._carovnik())
preveri("Orodja", "O programu", lambda: app._o_programu())
preveri("Orodja", "preklop teme", lambda: app._preklopi_temo())
preveri("Orodja", "vrstica stanja", lambda: (
    app.st_status.set(False), app._preklopi_status_vrstico(),
    app.st_status.set(True), app._preklopi_status_vrstico()))
preveri("Orodja", "undo/redo", lambda: (
    app._zgodovina_zabelezi(), app._razveljavi(None), app._ponovi(None)))
preveri("Orodja", "pomoč (F1)", lambda: app._pomoc())

print("=== 8. MERJENJE S SLIKE (celo okno) ===", flush=True)
import tkinter.messagebox as mb  # noqa: E402
mb.showwarning = lambda *a, **k: None  # type: ignore[assignment]
m = merjenje.App(POT_SLIKE)
m.update_idletasks()


def klik2(x, y):
    d = D()
    d.x, d.y = x, y
    return d


preveri("Merjenje", "kalibracija (2 klika + 2900 mm)", lambda: (
    m.v_ref.set("2900"), setattr(m, "nacin", "ref"),
    m._klik(klik2(100, 300)), m._klik(klik2(900, 300))))
preveri("Merjenje", "scale izračunan",
        lambda: m.scale and 0 < m.scale < 5 or (_ for _ in ()).throw(AssertionError(str(m.scale))))
preveri("Merjenje", "meritev (2 klika)", lambda: (
    setattr(m, "nacin", "meri"), m.v_ime.set("visina"),
    m._klik(klik2(400, 200)), m._klik(klik2(400, 600))))
preveri("Merjenje", "meritev zapisana (mm)",
        lambda: m.meritve and m.meritve[0][1] and 0 < m.meritve[0][1] < 10000
        or (_ for _ in ()).throw(AssertionError(str(m.meritve))))
preveri("Merjenje", "označi območje (2 klika)", lambda: (
    setattr(m, "nacin", "roi"), m._klik(klik2(100, 100)),
    m._klik(klik2(800, 700))))
preveri("Merjenje", "zaznaj lamele (pasovi)", lambda: m._zaznaj_lam())
preveri("Merjenje", "zaznaj vijake/luknje", lambda: m._zaznaj_vij())
preveri("Merjenje", "pobriši meritve", lambda: m._pobrisi_meritve())
merjenje_pot = os.path.join(OUT, "merjenje.yaml")
DLG["pot"] = merjenje_pot
preveri("Merjenje", "shrani projekt (.yaml)", lambda: m._shrani(),
        tudi=lambda: (None if os.path.isfile(merjenje_pot) else "ni datoteke"))
def _yaml_ok():
    import yaml
    podatki = yaml.safe_load(open(merjenje_pot, encoding="utf-8"))
    return None if podatki else "yaml je prazen"


preveri("Merjenje", "yaml se prebere", _yaml_ok)
m.destroy()

print("=== 9. TERENSKI LIST / UREDNIK ===", flush=True)
def _validen():
    # preveri_dokument VRŽE ValueError pri neveljavnem; True = veljaven
    try:
        terenski_list.preveri_dokument(terenski_list.nov_dokument())
    except ValueError as e:
        raise AssertionError(f"ni veljaven: {e}")
    return None


preveri("Terenski", "nov dokument + validacija", _validen)

try:
    u = terenski_gui.Urejevalnik()
    u.update_idletasks()
    preveri("Terenski", "vstavi sliko (meni)", lambda: (u.orodje.set('slika'), u._vstavi_sliko()))
    def _vstavi_besedilo():
        u.orodje.set("besedilo")
        u._na_pritisk(_ev(60, 60))
        u._na_oddajo(_ev(60, 60))
        if not u.dok["elementi"]:
            raise AssertionError("element ni nastal")

    preveri("Terenski", "vstavi besedilo (orodje)", _vstavi_besedilo)
    preveri("Terenski", "zavrti 45°", lambda: u._zavrti())
    preveri("Terenski", "razveljavi / ponovi", lambda: (
        u._razveljavi(), u._ponovi()))
    def _shrani_odpri():
        DLG["pot"] = os.path.join(OUT, "terenski.yaml")
        u._shrani()
        u._odpri()
        return None

    preveri("Terenski", "shrani / odpri (.yaml)", _shrani_odpri)
    ter_pot = os.path.join(OUT, "terenski.pdf")
    DLG["pot"] = ter_pot
    preveri("Terenski", "PDF", lambda: u._pdf(),
            tudi=lambda: (None if os.path.isfile(ter_pot) else "ni datoteke"))
    u.destroy()
except tk.TclError:
    REZULTATI.append(("Terenski", "gradnja okna", "PRESKOČENO", "Tk"))

app.destroy()

print("\n=== POVZETEK ===", flush=True)
slabi = [r for r in REZULTATI if r[2] != "OK"]
for r in REZULTATI:
    print(f"{r[2]:>12} | {r[0]} / {r[1]} {('- ' + r[3]) if r[3] else ''}",
          flush=True)
print(f"\nSKUPAJ: {len(REZULTATI)} | NAPAK: {len(slabi)}", flush=True)
sys.exit(1 if slabi else 0)