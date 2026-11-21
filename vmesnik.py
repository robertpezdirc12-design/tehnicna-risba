#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vmesnik.py — grafični vmesnik za generator tehničnih risb (risba.py).

Zagon:  python vmesnik.py   (ali dvoklik nanj)
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yaml

import proizvodnja

# v exe načinu se nastavitve shranjujejo poleg programa (ne v začasni mapi)
if getattr(sys, "frozen", False):
    _AP_DIR = os.path.dirname(sys.executable)
else:
    _AP_DIR = os.path.dirname(os.path.abspath(__file__))

import risba
import vrata as vrat

try:
    from PIL import Image, ImageTk
    IMA_PIL = True
except ImportError:
    IMA_PIL = False

NAPISI = {
    "ime": "Ime projekta", "risba_st": "Številka risbe", "izdelal": "Izdelal",
    "podjetje": "Podjetje", "pregledal": "Pregledal", "odobril": "Odobril",
    "sirina": "Širina ograje", "visina": "Višina od tal do vrha",
    "globina": "Globina / stranska dolžina", "lamele": "Število lamel",
    "lamela_v": "Višina lamel", "debelina": "Debelina lamel",
    "odcep": "Odcep od tal", "material": "Material",
    "razmak_nosilcev": "Razmak nosilcev", "profil": "Profil / model deske",
    "stranka": "Naročnik / stranka", "objekt": "Objekt (lokacija)",
    "podlaga": "Podlaga", "pritrditev_nacin": "Način pritrditve",
    "vijak_lamela": "Vijak lamela↔profil", "vijak_nosilec": "Vijak nosilec↔podlaga",
    "material_lamel": "Material lamel", "dobavitelj": "Dobavitelj",
    "vrzel": "Vrzel med deskami", "kerf": "Kerf (širina rezila)",
    "dolzine_deske": "Dolžine desk v nabavi",
    "dolzina_palice": "Tovarniška dolžina alu palice",
    "foto": "Pot do fotografije", "izhod": "Ime izhodne datoteke",
}

# cene za predračun (stran 3 PDF) — ključi so enaki kot v yaml 'cene:'
CENE_KLJUCI = ("wpc_deska_m", "alu_m", "rocaj_kos", "nosilec_kos",
               "vijak_kos", "fasadni_kos", "anker_kos", "osnova_kos",
               "dela_ure", "dela_ur_cena")

CENE_NAPISI = {
    "wpc_deska_m": "WPC deska (EUR/m):",
    "alu_m": "Alu profil (EUR/m):",
    "rocaj_kos": "Ročaj (EUR/kos):",
    "nosilec_kos": "Nosilec (EUR/kos):",
    "vijak_kos": "Vijak (EUR/kos):",
    "fasadni_kos": "Fasadni vijak (EUR/kos):",
    "anker_kos": "Anker M10 (EUR/kos):",
    "osnova_kos": "Osnova za steber (EUR/kos):",
    "dela_ure": "Delo (ure):",
    "dela_ur_cena": "Delo (EUR/h):",
}

# Samodejno shranjevanje zadnjih nastavitev (ob vsaki risbi, naloži ob zagonu)
DAT_ZADNJE = os.path.join(_AP_DIR, "zadnje_nastavitve.yaml")


# namigi ob prehodu miške (UI/UX Plan F)
NAMIGI = {
    "sirina": "Skupna širina ograje v mm (vodoravna dolžina). "
              "Vpliva na število polj, nosilcev in dolžino ročaja.",
    "visina": "Višina ograje od tal do vrha v mm. V višino so všteti "
              "odcep, lamele/deske in profili (preveri izračun na "
              "montažnem listu).",
    "globina": "Globina oz. stranska dolžina ograje v mm (za 3D/DXF).",
    "odcep": "Razmik od tal do spodnjega roba ograje v mm.",
    "lamele": "Število lamel/desk v polju (prečna predloga) oz. desk "
              "(pokončna).",
    "lamela_v": "Višina lamel (prečna) oz. širina deske (pokončna) v mm.",
    "debelina": "Debelina lamele/deske v mm (npr. WPC 21 mm).",
    "vrzel": "Razmik med sosednjima deskama v mm — vpliva na porabo in "
             "videz.",
    "razmak_nosilcev": "Največji dovoljen razmak nosilcev/stebrov v mm; "
                       "dejanski razmak se porazdeli enakomerno (glej "
                       "montažni list).",
    "kerf": "Širina reza (žaginega lista) v mm — upoštevana pri razrezu "
            "in izračunu ostankov.",
    "dolzine_deske": "Razpoložljive tovarniške dolžine desk v mm, "
                     "ločene z ; (npr. 5800; 4200). Optimizer izbere "
                     "najboljšo kombinacijo.",
    "dolzina_palice": "Tovarniška dolžina alu palice v mm (npr. 6000).",
    "vijak_lamela": "Opis vijaka za pritrditev lamele/deske — pride v "
                    "kosovnico in naročilo.",
    "vijak_nosilec": "Opis vijaka/ankerja za pritrditev nosilca na "
                     "podlago.",
    "pritrditev_nacin": "Način pritrditve (bočno/vrh) — prikazan na "
                        "detajlu pritrjevanja.",
    "material_lamel": "Material lamel/desk (npr. WPC) — opisno.",
    "profil": "Profil/model deske (npr. ROMB 67) — vpliva na opise v "
              "kosovnici.",
    "uporabi_ostanke": "Če je vklopljeno, razrez uporabi ostanke iz "
                       "skladišča (zmanjša odpad).",
}


class Namig:
    """Namig ob prehodu miške čez widget (UI/UX Plan F)."""

    def __init__(self, widget, besedilo, zamik=500):
        self.widget = widget
        self.besedilo = besedilo
        self.zamik = zamik
        self._id = None
        self._okno = None
        widget.bind("<Enter>", self._zacetek)
        widget.bind("<Leave>", self._konec)
        widget.bind("<ButtonPress>", self._konec)

    def _zacetek(self, _e=None):
        self._konec()
        self._id = self.widget.after(self.zamik, self._prikazi)

    def _konec(self, _e=None):
        if self._id is not None:
            try:
                self.widget.after_cancel(self._id)
            except Exception:
                pass
            self._id = None
        if self._okno is not None:
            try:
                self._okno.destroy()
            except Exception:
                pass
            self._okno = None

    def _prikazi(self):
        if self._okno is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._okno = tk.Toplevel(self.widget)
        self._okno.wm_overrideredirect(True)
        self._okno.wm_geometry(f"+{x}+{y}")
        tk.Label(self._okno, text=self.besedilo, bg="#fff8c4", fg="#333333",
                 relief="solid", borderwidth=1, wraplength=300,
                 font=("Segoe UI", 8), justify="left").pack(ipadx=4, ipady=2)


class CelZaslon(tk.Toplevel):
    """Celozaslonski predogled: kolešček miške = povečava, vlečenje = premik."""

    def __init__(self, master, png_pot):
        super().__init__(master)
        self.title("Predogled — cel zaslon (ESC ali dvoklik = izhod)")
        self.configure(bg="black")
        self.attributes("-fullscreen", True)
        self.img = Image.open(png_pot).convert("RGB")
        self.w_px, self.h_px = self.img.size
        self.zoom = 1.0
        self.off = [0.0, 0.0]
        self.prev = None
        self._tk_img = None
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._narisi())
        self.canvas.bind("<MouseWheel>", self._kolesce)
        self.canvas.bind("<Button-1>", self._dol)
        self.canvas.bind("<B1-Motion>", self._vleci)
        self.canvas.bind("<Double-Button-1>", lambda e: self.destroy())
        self.canvas.bind("<Triple-Button-1>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(60, self._narisi)

    def _osn(self):
        W = max(self.canvas.winfo_width(), 800)
        H = max(self.canvas.winfo_height(), 600)
        return W, H, min(W / self.w_px, H / self.h_px)

    def _narisi(self):
        W, H, s0 = self._osn()
        sc = s0 * self.zoom
        scx = self.w_px / 2 - self.off[0] / sc      # središče vidnega območja
        scy = self.h_px / 2 - self.off[1] / sc
        pw, ph = W / (2 * sc), H / (2 * sc)
        x0, y0 = max(0.0, scx - pw), max(0.0, scy - ph)
        x1, y1 = min(float(self.w_px), scx + pw), min(float(self.h_px), scy + ph)
        if x1 <= x0 or y1 <= y0:
            return
        crop = self.img.crop((int(x0), int(y0), int(x1), int(y1)))
        dw = min(4000, max(1, int((x1 - x0) * sc)))
        dh = min(4000, max(1, int((y1 - y0) * sc)))
        crop = crop.resize((dw, dh), Image.BILINEAR)
        self._tk_img = ImageTk.PhotoImage(crop)
        self.canvas.delete("all")
        self.canvas.create_image(W / 2 + (x0 - scx) * sc + self.off[0],
                                 H / 2 + (y0 - scy) * sc + self.off[1],
                                 anchor="nw", image=self._tk_img)
        self.canvas.create_text(
            W / 2, H - 26,
            text="ESC ali dvoklik = zapri  •  kolešček miške = povečava  •  "
                 "vleci z levim gumbom = premik",
            fill="#9a9a9a", font=("Segoe UI", 10))

    def _kolesce(self, e):
        f = 1.25 if e.delta > 0 else 0.8
        W, H, s0 = self._osn()
        nz = max(0.6, min(12.0, self.zoom * f))
        if nz == self.zoom:
            return
        ux = (e.x - W / 2 - self.off[0]) / (s0 * self.zoom)
        uy = (e.y - H / 2 - self.off[1]) / (s0 * self.zoom)
        self.off[0] = e.x - W / 2 - ux * s0 * nz
        self.off[1] = e.y - H / 2 - uy * s0 * nz
        self.zoom = nz
        self._narisi()

    def _dol(self, e):
        self.prev = (e.x, e.y)

    def _vleci(self, e):
        if self.prev:
            self.off[0] += e.x - self.prev[0]
            self.off[1] += e.y - self.prev[1]
            self.prev = (e.x, e.y)
            self._narisi()


class Carovnik(tk.Toplevel):
    """Voden vnos po korakih (UI/UX Plan E).

    Ureja ISTE spremenljivke kot glavni obrazec — živi povzetek (Plan A)
    in undo/redo (Plan D) zato delujeta samodejno.
    """

    KORAKI = (
        ("Vrsta in ime", ("predloga", "ime")),
        ("Mere ograje (mm)", ("sirina", "visina", "globina", "odcep")),
        ("Lamele / deske (mm)", ("lamele", "lamela_v", "debelina", "vrzel")),
        ("Vrata in prehodi (neobvezno)", None),
        ("Pregled in zaključek", ()),
    )

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Čarovnik za vnos — korak za korakom")
        self.resizable(False, False)
        self.i = 0
        tk.Label(self, text="ČAROVNIK — voden vnos",
                 font=("Segoe UI", 12, "bold")).pack(pady=(10, 2))
        self.lbl_korak = tk.Label(self, text="", font=("Segoe UI", 10))
        self.lbl_korak.pack(anchor="w", padx=14)
        self.pb = ttk.Progressbar(self, maximum=100, length=400)
        self.pb.pack(fill="x", padx=14, pady=4)
        self.vsebina = ttk.Frame(self, padding=(14, 6))
        self.vsebina.pack(fill="both", expand=True)
        self.lbl_opozorilo = tk.Label(self, text="", fg="#b00020",
                                      wraplength=400, justify="left")
        self.lbl_opozorilo.pack(anchor="w", padx=14)
        dno = ttk.Frame(self, padding=12)
        dno.pack(fill="x")
        ttk.Button(dno, text="✕ Prekliči", command=self.destroy).pack(side="left")
        self.btn_naprej = ttk.Button(dno, text="Naprej →", command=self._naprej)
        self.btn_naprej.pack(side="right")
        self.btn_nazaj = ttk.Button(dno, text="← Nazaj", command=self._nazaj)
        self.btn_nazaj.pack(side="right", padx=(0, 6))
        self._pokazi()

    def _pokazi(self):
        for w in self.vsebina.winfo_children():
            w.destroy()
        self.lbl_opozorilo.config(text="")
        naslov, polja = self.KORAKI[self.i]
        n = len(self.KORAKI)
        self.lbl_korak.config(text=f"Korak {self.i + 1}/{n}: {naslov}")
        self.pb["value"] = (self.i + 1) / n * 100
        if polja:
            for j, k in enumerate(polja):
                ttk.Label(self.vsebina,
                          text=NAPISI.get(k, "Predloga:") .rstrip(":") + ":"
                          ).grid(row=j, column=0, sticky="e", padx=(0, 6),
                                 pady=3)
                if k == "predloga":
                    ttk.Combobox(
                        self.vsebina, width=14, state="readonly",
                        textvariable=self.app.v[k],
                        values=["ograda", "pokončna"]).grid(
                            row=j, column=1, sticky="w", pady=3)
                else:
                    ttk.Entry(self.vsebina, width=16,
                              textvariable=self.app.v[k]).grid(
                                  row=j, column=1, sticky="w", pady=3)
        elif self.i == 3:
            ttk.Label(
                self.vsebina,
                text="Dodaj vrata/prehode ali preskoči ta korak.",
                wraplength=380, justify="left").grid(
                    row=0, column=0, columnspan=2, sticky="w")
            ttk.Button(self.vsebina, text="Dodaj vrata/prehod …",
                       command=self.app._vrata_dodaj).grid(
                           row=1, column=0, sticky="w", pady=4)
            ttk.Button(self.vsebina, text="Odstrani zadnja",
                       command=self.app._vrata_odstrani).grid(
                           row=1, column=1, sticky="w", padx=6)
            tk.Label(
                self.vsebina,
                text=f"Trenutno: {len(self.app.vrata_sez)} vrat/prehodov",
                fg="#555555").grid(row=2, column=0, columnspan=2, sticky="w")
        else:
            ttk.Label(self.vsebina, text=self._pregled(), justify="left",
                      wraplength=400).grid(row=0, column=0, sticky="w")
        self.btn_nazaj.config(
            state="normal" if self.i > 0 else "disabled")
        self.btn_naprej.config(
            text="Dokončaj ✓" if self.i == n - 1 else "Naprej →")

    def _pregled(self):
        try:
            cfg = self.app._zberi_cfg()
        except ValueError as e:
            return f"Pregled ni na voljo — {e}"
        m = cfg["mere"]
        return (f"Projekt: {cfg['ime']}  ({cfg['risba_st']})\n"
                f"Predloga: {cfg['predloga']}\n"
                f"Ograja: {m['sirina']:g} × {m['visina']:g} mm\n"
                f"Lamele/deske: {m['lamele']:g} × {m['lamela_v']:g} mm, "
                f"debelina {m['debelina']:g} mm\n"
                f"Vrata/prehodi: {len(cfg['vrata'])}\n"
                f"Izhod: {cfg['izhod']}\n\n"
                "Dokončaj — vnos ostane v obrazcu "
                "(živi povzetek, undo/redo delujeta naprej).")

    def _veljavno(self):
        polja = self.KORAKI[self.i][1]
        if polja is None or polja == ():
            return True
        try:
            self.app._preberi_mere()
            return True
        except ValueError as e:
            self.lbl_opozorilo.config(text=str(e))
            return False

    def _naprej(self):
        if not self._veljavno():
            return
        if self.i >= len(self.KORAKI) - 1:
            self.destroy()
            return
        self.i += 1
        self._pokazi()

    def _nazaj(self):
        if self.i > 0:
            self.i -= 1
            self._pokazi()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generator tehničnih risb — balkonska ograja")
        self.geometry("920x820")
        self.minsize(860, 760)
        try:
            self.state("zoomed")          # odpri povečano (celo okno)
        except Exception:
            pass
        self.pdf_pot = None
        self.png_pot = None
        self.kolicine = None
        self._slika = None            # referenca (sicer GC uniči sliko)
        self.v = {}
        self.polja = {}               # referenca polj za skrivanje/prikaz
        self.namigi = {}              # Plan F: namigi ob prehodu miške
        self.vrata_sez = []           # vrata/prehodi (issue #3)
        self.st_preprost = tk.BooleanVar(value=True)   # preprosti način
        # UI/UX Plan A: živi povzetek (debounce osveževanje)
        self.st_zivo = tk.BooleanVar(value=True)
        self._zivi_id = None
        # UI/UX Plan D: zgodovina (undo/redo)
        self._zgodovina = []
        self._zgodovina_i = -1
        self._zgodovina_id = None
        self._obnavljam = False
        self._zgradi()
        self._preklopi_nacin()
        self._nalozi_zadnje()
        self._izpolni_privzete()
        self._zgodovina_zabelezi()   # začetno stanje (po nalaganju!)

    # ------------------------------------------------------------- gradnja
    def _zgradi(self):
        tk.Label(self, text="GENERATOR TEHNIČNE RISBE",
                 font=("Segoe UI", 15, "bold")).pack(pady=(12, 0))
        tk.Label(self, text="Balkonska ograja iz lamel — vpiši mere in nariši (A3 PDF za tisk)",
                 fg="#555555").pack(pady=(0, 4))
        fr_p = ttk.Frame(self)
        fr_p.pack(fill="x", padx=14, pady=(0, 4))
        if "predloga" not in self.v:
            self.v["predloga"] = tk.StringVar(value="ograja")
        ttk.Label(fr_p, text="Predloga:").pack(side="left", padx=(0, 4))
        self.cb_pred = ttk.Combobox(fr_p, width=12, state="readonly",
                                    textvariable=self.v["predloga"],
                                    values=["ograja", "pokončna"])
        self.cb_pred.pack(side="left")
        self.cb_pred.bind("<<ComboboxSelected>>",
                          lambda e: self._preklopi_predlogo())
        ttk.Checkbutton(fr_p, text="Preprosti način — pokaži samo osnovno "
                        "(mere, fotografija, NARIŠI)",
                        variable=self.st_preprost,
                        command=self._preklopi_nacin).pack(side="right")
        # Plan D: undo/redo
        self.btn_ponovi = ttk.Button(fr_p, text="↪ Ponovi",
                                     command=self._ponovi, width=9)
        self.btn_ponovi.pack(side="right", padx=(0, 6))
        self.btn_razveljavi = ttk.Button(fr_p, text="↩ Razveljavi",
                                         command=self._razveljavi, width=11)
        self.btn_razveljavi.pack(side="right", padx=(0, 2))
        ttk.Button(fr_p, text="✦ ČAROVNIK",
                   command=self._carovnik).pack(side="right", padx=(0, 8))

        zg = ttk.Frame(self, padding=(14, 4))
        zg.pack(fill="x")
        zg.columnconfigure(0, weight=1)

        # ---- PROJEKT ----
        f1 = ttk.LabelFrame(zg, text="PROJEKT", padding=8)
        f1.grid(row=0, column=0, sticky="ew")
        self._polje(f1, 0, 0, "ime", 34)
        self._polje(f1, 0, 1, "risba_st", 12)
        self._polje(f1, 0, 2, "izdelal", 14)
        self._polje(f1, 1, 0, "material", 30)
        self._polje(f1, 1, 1, "profil", 14)
        self._polje(f1, 1, 2, "material_lamel", 22)
        self._polje(f1, 1, 3, "dobavitelj", 14)
        if "barva" not in self.v:
            self.v["barva"] = tk.StringVar()
        lbl_b = ttk.Label(f1, text="Barva lamel:")
        lbl_b.grid(row=2, column=0, sticky="e", padx=(0, 4), pady=2)
        self.cb_barva = ttk.Combobox(
            f1, width=24, state="readonly", textvariable=self.v["barva"],
            values=list(risba.WPC_BARVE) + ["Po dogovoru"])
        self.cb_barva.grid(row=2, column=1, columnspan=2, sticky="w", pady=2)
        op_b = tk.Label(f1, text="(odtenek vedno potrdi s vzorcem proizvajalca)",
                        fg="#888888")
        op_b.grid(row=2, column=3, sticky="w")
        self.polja.setdefault("barva", []).extend([lbl_b, self.cb_barva, op_b])
        self._polje(f1, 3, 0, "podjetje", 30)
        self._polje(f1, 3, 1, "pregledal", 14)
        self._polje(f1, 3, 2, "odobril", 14)
        self._polje(f1, 4, 0, "stranka", 30)
        self._polje(f1, 4, 1, "objekt", 34)

        # ---- MERE ----
        f2 = ttk.LabelFrame(zg, text="MERE (mm)", padding=8)
        f2.grid(row=1, column=0, sticky="ew", pady=6)
        self._polje(f2, 0, 0, "sirina", 10)
        self._polje(f2, 0, 1, "visina", 10)
        self._polje(f2, 0, 2, "globina", 10)
        self._polje(f2, 1, 0, "lamele", 10)
        self._polje(f2, 1, 1, "lamela_v", 10)
        self._polje(f2, 1, 2, "debelina", 10)
        self._polje(f2, 2, 0, "odcep", 10)
        self._polje(f2, 2, 1, "vrzel", 10)
        self._polje(f2, 3, 0, "razmak_nosilcev", 10)
        self._polje(f2, 3, 1, "kerf", 10)
        self._polje(f2, 4, 0, "dolzine_deske", 22)
        self._polje(f2, 4, 1, "dolzina_palice", 10)
        self.st_ost = tk.BooleanVar(value=False)
        cb_ost = ttk.Checkbutton(
            f2, text=f"Uporabi skladišče ostankov ({risba.pot_ostanki()})",
            variable=self.st_ost, command=self._zivi_sprememba)
        cb_ost.grid(row=4, column=2, columnspan=2, sticky="w")
        self.namigi["uporabi_ostanke"] = Namig(cb_ost, NAMIGI["uporabi_ostanke"])
        self.polja.setdefault("uporabi_ostanke", []).append(cb_ost)
        tk.Label(f2, text="(višina zgornjega/spodnjega profila je 40 mm; "
                         "razmak nosilcev se samodejno izračuna)",
                 fg="#888888").grid(row=5, column=0, columnspan=6, sticky="w")

        # ---- PRITRDITEV ----
        f4 = ttk.LabelFrame(zg, text="PRITRDITEV", padding=8)
        f4.grid(row=2, column=0, sticky="ew")
        self._polje(f4, 0, 0, "podlaga", 14)
        self._polje(f4, 0, 1, "pritrditev_nacin", 14)
        self._polje(f4, 0, 2, "vijak_lamela", 30)
        self._polje(f4, 1, 0, "vijak_nosilec", 30)
        tk.Label(f4, text="(vijak: prosto — npr. „RF M8×70 Inox“, "
                         "„anker M12“, „fasadni Ø8×80 + tipli“ …)",
                 fg="#888888").grid(row=1, column=1, columnspan=2, sticky="w")

        # ---- FOTO + IZHOD ----
        f3 = ttk.LabelFrame(zg, text="FOTOGRAFIJA IN IZHOD", padding=8)
        f3.grid(row=3, column=0, sticky="ew")
        self._polje(f3, 0, 0, "foto", 52)
        ttk.Button(f3, text="Prebrskaj…", command=self._brskaj_foto)\
            .grid(row=0, column=2, sticky="w", padx=4)
        self._polje(f3, 1, 0, "izhod", 52)
        btn_m = ttk.Button(f3, text="MERI S SLIKE (pomožno merjenje)",
                           command=self._meri_slike)
        btn_m.grid(row=1, column=2, sticky="w", padx=4)
        self.polja.setdefault("meri_slike", []).append(btn_m)

        # ---- CENE (predračun) ----
        f5 = ttk.LabelFrame(zg, text="CENE (EUR — neobvezno; doda stran 3 "
                                     "PREDRAČUN k PDF)", padding=8)
        f5.grid(row=3, column=0, sticky="ew", pady=6)
        self.polja.setdefault("cene_okvir", []).append(f5)
        for i, ck in enumerate(CENE_KLJUCI):
            self._polje(f5, i // 3, i % 3, "cene_" + ck, 11,
                        napis=CENE_NAPISI[ck])
        tk.Label(f5, text="(prazno = postavka ni v predračunu; pokončna "
                          "ograja uporablja iste cene)", fg="#888888"
                 ).grid(row=3, column=0, columnspan=6, sticky="w")

        # ---- VRATA IN PREHODI (issue #3) ----
        self.fv = ttk.LabelFrame(zg, text="VRATA IN PREHODI (neobvezno)",
                                 padding=8)
        self.fv.grid(row=4, column=0, sticky="ew", pady=6)
        self.polja.setdefault("vrata_okvir", []).append(self.fv)
        stolpci = ("st", "tip", "x", "sirina", "visina", "smer")
        self.tv_vrata = ttk.Treeview(self.fv, columns=stolpci,
                                     show="headings", height=4)
        for sk, nas in zip(stolpci, ("Št.", "Tip", "x (mm)", "Širina (mm)",
                                     "Višina (mm)", "Smer")):
            self.tv_vrata.heading(sk, text=nas)
            self.tv_vrata.column(sk, width=100 if sk != "tip" else 120,
                                 anchor="w")
        self.tv_vrata.grid(row=0, column=0, columnspan=4, sticky="ew")
        fb_v = ttk.Frame(self.fv)
        fb_v.grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Button(fb_v, text="Dodaj vrata/prehod",
                   command=self._vrata_dodaj).pack(side="left")
        ttk.Button(fb_v, text="Uredi",
                   command=self._vrata_uredi).pack(side="left", padx=6)
        ttk.Button(fb_v, text="Odstrani", command=self._vrata_odstrani)\
            .pack(side="left")
        self.lbl_vrata = tk.Label(self.fv, text="", fg="#b26a00",
                                  wraplength=620, justify="left")
        self.lbl_vrata.grid(row=2, column=0, columnspan=4, sticky="w")

        # ---- GUMBI ----
        fb = ttk.Frame(zg, padding=(0, 10))
        fb.grid(row=5, column=0, sticky="ew")
        self.btn_narisi = tk.Button(
            fb, text="NARIŠI RISBO", command=self._narisi,
            bg="#2e7d32", fg="white", activebackground="#1b5e20",
            activeforeground="white", font=("Segoe UI", 11, "bold"),
            padx=18, pady=6, relief="flat", cursor="hand2")
        self.btn_narisi.pack(side="left")
        self.btn_pdf = tk.Button(
            fb, text="ODPRI PDF", command=self._odpri_pdf, state="disabled",
            font=("Segoe UI", 10, "bold"), padx=14, pady=6, cursor="hand2")
        self.btn_pdf.pack(side="left", padx=10)
        self.btn_nar = ttk.Button(fb, text="NAROČILO (kopiraj)",
                                  state="disabled",
                                  command=self._narocilo_kopiraj)
        self.btn_nar.pack(side="right", padx=8)
        self.btn_ost = ttk.Button(fb, text="ODPIŠI OSTANKE", state="disabled",
                                  command=self._odpisi_ostanke)
        self.btn_ost.pack(side="right")
        ttk.Button(fb, text="SHRANI PROJEKT (.yaml)",
                   command=self._shrani_projekt).pack(side="right")
        ttk.Button(fb, text="IZVOZI DXF", command=self._izvozi_dxf)\
            .pack(side="right", padx=(0, 6))
        self.btn_cel = ttk.Button(fb, text="CEL ZASLON", state="disabled",
                                  command=self._cel_zaslon)
        self.btn_cel.pack(side="right", padx=10)
        self.status = tk.Label(fb, text="Pripravljen.", fg="#555555",
                               font=("Segoe UI", 9))
        self.status.pack(side="right", padx=14)

        # ---- ŽIVI POVZETEK (UI/UX Plan A) ----
        fz = ttk.LabelFrame(zg, text="ŽIVI POVZETEK", padding=8)
        fz.grid(row=0, column=1, rowspan=6, sticky="n", padx=(12, 0))
        fr_z = ttk.Frame(fz)
        fr_z.pack(fill="x")
        ttk.Checkbutton(fr_z, text="Živo osveževanje",
                        variable=self.st_zivo).pack(side="left")
        ttk.Button(fr_z, text="Osveži",
                   command=self._zivi_osvezi).pack(side="right")
        self.zivi_platno = tk.Canvas(fz, width=324, height=210,
                                     bg="white", highlightthickness=1,
                                     highlightbackground="#cccccc")
        self.zivi_platno.pack(pady=(6, 4))
        self.zivi_vrstice = tk.Label(
            fz, text="—", justify="left", font=("Segoe UI", 9), anchor="w")
        self.zivi_vrstice.pack(fill="x")
        self.zivi_cena = tk.Label(
            fz, text="—", justify="left", font=("Segoe UI", 10, "bold"),
            anchor="w")
        self.zivi_cena.pack(fill="x", pady=(4, 0))
        self.zivi_status = tk.Label(
            fz, text="", fg="#555555", font=("Segoe UI", 8), anchor="w",
            wraplength=310, justify="left")
        self.zivi_status.pack(fill="x")
        tk.Label(fz, text="(shematski prikaz in živa cena — natančna "
                          "risba ostane gumb NARIŠI RISBO)",
                 fg="#888888", font=("Segoe UI", 8), wraplength=310,
                 justify="left").pack(fill="x", pady=(4, 0))

        # ---- PREDGLED ----
        self.fp = ttk.LabelFrame(self, text="PREDGLED RISBE", padding=6)
        self.fp.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.st_klik = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.fp, text="Klik na risbo odpre cel zaslon",
                        variable=self.st_klik).pack(side="top", anchor="e",
                                                    padx=6)
        self.predogled = tk.Label(self.fp, fg="#999999",
                                  text="\n\nKlikni »NARIŠI RISBO« — tukaj se prikaže risba.\n"
                                       "(cel zaslon: gumb »CEL ZASLON« ali kljukica zgoraj)",
                                  font=("Segoe UI", 10))
        self.predogled.pack(fill="both", expand=True)
        self.predogled.bind("<Button-1>", self._klik_predogled)

        # živo osveževanje: ob vsaki spremembi polja (debounce 600 ms)
        for _var in self.v.values():
            _var.trace_add("write", self._zivi_sprememba)
        self.after(300, self._zivi_osvezi)

        # Plan D: bližnjici undo/redo (delujeta tudi iz vnosnih polj)
        self.bind_all("<Control-z>", self._razveljavi)
        self.bind_all("<Control-y>", self._ponovi)
        self.bind_all("<Control-Shift-Z>", self._ponovi)
        # Plan F: bližnjice
        self.bind_all("<Control-n>", lambda e: self._narisi())
        self.bind_all("<Control-p>", lambda e: self._odpri_pdf())
        self.bind_all("<Control-s>", lambda e: self._shrani_projekt())
        self.bind_all("<Control-e>", lambda e: self._izvozi_dxf())
        self.bind_all("<F1>", lambda e: self._pomoc())

    def _polje(self, star, vrsta, stolpec, kljuc, sirina, napis=None):
        if kljuc not in self.v:
            self.v[kljuc] = tk.StringVar()
        if napis is None:
            napis = NAPISI[kljuc] + ":"
        lbl = ttk.Label(star, text=napis)
        lbl.grid(row=vrsta, column=stolpec * 2, sticky="e", padx=(0, 4),
                 pady=2)
        ent = ttk.Entry(star, width=sirina, textvariable=self.v[kljuc])
        ent.grid(row=vrsta, column=stolpec * 2 + 1, sticky="w",
                 padx=(0, 12), pady=2)
        self.polja.setdefault(kljuc, []).extend([lbl, ent])
        if kljuc in NAMIGI:                       # Plan F: namig
            self.namigi[kljuc] = Namig(ent, NAMIGI[kljuc])
            Namig(lbl, NAMIGI[kljuc])

    # --------------------------------------------- živi povzetek (Plan A)
    def _carovnik(self):
        """Odpri voden vnos po korakih (Plan E)."""
        Carovnik(self)

    def _pomoc(self):
        """F1: pomoč z bližnjicami in legendo (Plan F)."""
        messagebox.showinfo(
            "Pomoč — bližnjice",
            "Bližnjice:\n"
            "  Ctrl+N — NARIŠI RISBO\n"
            "  Ctrl+P — ODPRI PDF\n"
            "  Ctrl+S — SHRANI PROJEKT (.yaml)\n"
            "  Ctrl+E — IZVOZI DXF\n"
            "  Ctrl+Z — razveljavi • Ctrl+Y / Ctrl+Shift+Z — ponovi\n"
            "  F1 — to sporočilo\n\n"
            "Namigi: postavi miško na polje za razlago.\n"
            "Merjenje s slike: vedno preveri mere na objektu!")

    def _zivi_sprememba(self, *_):
        """Sproži osvežitev živega povzetka z debounce (600 ms)."""
        self._zgodovina_odlozi()          # Plan D: zgodovina sprememb
        if not self.st_zivo.get():
            return
        if self._zivi_id is not None:
            try:
                self.after_cancel(self._zivi_id)
            except Exception:
                pass
        self._zivi_id = self.after(600, self._zivi_osvezi)

    def _zivi_osvezi(self):
        """Izračunaj in prikaži živo kosovnico/ceno ter shematski prikaz."""
        self._zivi_id = None
        if not hasattr(self, "zivi_cena"):
            return
        try:
            cfg = self._zberi_cfg()
        except ValueError as e:
            self.zivi_status.config(text=f"Vnos ni veljaven — {e}",
                                    fg="#b00020")
            return
        try:
            kol = proizvodnja.izracunaj_kolicine(cfg)
            znesek = proizvodnja.predracun_znesek(cfg.get("cene"),
                                                   kol["postavke"])
        except Exception as e:                      # ne sme sesuti GUI-ja
            self.zivi_status.config(text=f"Izračun ni mogoč — {e}",
                                    fg="#b00020")
            return
        po = {}
        for _n, _ks, _e, kljuc, num in kol["postavke"]:
            if kljuc:
                po[kljuc] = po.get(kljuc, 0.0) + float(num or 0)
        st_vrat = len(cfg.get("vrata") or [])
        nos = po.get("nosilec_kos", 0) + po.get("osnova_kos", 0)
        vij = (po.get("vijak_kos", 0) + po.get("fasadni_kos", 0)
               + po.get("anker_kos", 0))
        self.zivi_vrstice.config(text=(
            f"WPC: {po.get('wpc_deska_m', 0):.1f} m   "
            f"Alu: {po.get('alu_m', 0):.1f} m\n"
            f"Nosilci/stebri: {nos:.0f}   Vijaki: {vij:.0f}\n"
            f"Vrata/prehodi: {st_vrat}"))
        if znesek["vse_nic"]:
            self.zivi_cena.config(
                text="SKUPAJ: ni obračunano (cene so PRIMER)", fg="#8a6d3b")
        elif znesek["delno"]:
            self.zivi_cena.config(
                text=f"SKUPAJ (delno, brez DDV): {znesek['skupaj']:.2f} EUR",
                fg="#b26a00")
        else:
            self.zivi_cena.config(
                text=f"SKUPAJ (brez DDV): {znesek['skupaj']:.2f} EUR",
                fg="#1b5e20")
        if znesek["manjkajoce_cene"]:
            self.zivi_status.config(
                text="Manjka cena (ni vštetih v seštevek): "
                     + ", ".join(znesek["manjkajoce_cene"]), fg="#b26a00")
        else:
            self.zivi_status.config(
                text="Povzetek se osveži samodejno ob vnosu.", fg="#555555")
        self._zivi_narisi(cfg)

    def _zivi_narisi(self, cfg):
        """Shematski prikaz ograje (NI tehnična risba — ta je gumb NARIŠI)."""
        c = self.zivi_platno
        c.delete("all")
        try:
            m = cfg["mere"]
            sir = float(m["sirina"] or 0)
            vis = float(m["visina"] or 0)
        except Exception:
            return
        if sir <= 0 or vis <= 0:
            return
        W, H, x0, y0 = 300, 170, 12, 16
        c.create_rectangle(x0, y0, x0 + W, y0 + H, outline="#666666",
                           fill="#fafafa")
        n = max(int(m.get("lamele") or 0), 1)
        for i in range(1, n):
            y = y0 + H - i * H / n
            c.create_line(x0, y, x0 + W, y, fill="#9a9a9a")
        razmak = float(m.get("razmak_nosilcev") or 0)
        if razmak > 0:
            st = int(sir // razmak)
            for i in range(st + 1):
                x = x0 + min(W, W * i * razmak / sir)
                c.create_line(x, y0, x, y0 + H, fill="#2e5d9f", width=2)
        try:
            vp = proizvodnja.vrata_podatki(cfg)
            for od in vp["odprtine"]:
                xa = x0 + W * float(od[0]) / sir
                xb = x0 + W * float(od[1]) / sir
                c.create_rectangle(xa, y0, xb, y0 + H, fill="#e3f2fd",
                                   outline="#1565c0", dash=(3, 2))
        except Exception:
            pass
        c.create_text(x0 + W / 2, y0 + H + 12, text=f"{sir:g} mm",
                      font=("Segoe UI", 8))
        c.create_text(x0 - 4, y0 + H / 2, text=f"{vis:g} mm",
                      font=("Segoe UI", 8), angle=90)

    # --------------------------------------------- zgodovina: undo/redo (Plan D)
    MAX_ZGODOVINA = 50

    def _zgodovina_stanje(self):
        return {
            "v": {k: var.get() for k, var in self.v.items()},
            "vrata": [dict(v) for v in self.vrata_sez],
            "ost": bool(self.st_ost.get()),
            "preprost": bool(self.st_preprost.get()),
        }

    def _zgodovina_odlozi(self):
        """Zabeleži stanje zamaknjeno (700 ms) — en vnos na vnosni cikel."""
        if self._obnavljam:
            return
        if self._zgodovina_id is not None:
            try:
                self.after_cancel(self._zgodovina_id)
            except Exception:
                pass
        self._zgodovina_id = self.after(700, self._zgodovina_zabelezi)

    def _zgodovina_zabelezi(self, *_):
        self._zgodovina_id = None
        if self._obnavljam:
            return
        stanje = self._zgodovina_stanje()
        if (self._zgodovina
                and self._zgodovina[self._zgodovina_i] == stanje):
            return
        del self._zgodovina[self._zgodovina_i + 1:]   # odreži vejo naprej
        self._zgodovina.append(stanje)
        if len(self._zgodovina) > self.MAX_ZGODOVINA:
            self._zgodovina.pop(0)
        self._zgodovina_i = len(self._zgodovina) - 1
        self._zgodovina_gumbi()

    def _zgodovina_obnovi(self, i):
        self._zgodovina_zabelezi_hitro_ali_pobrisi()
        self._obnavljam = True
        try:
            stanje = self._zgodovina[i]
            for k, var in self.v.items():
                var.set(stanje["v"].get(k, var.get()))
            self.vrata_sez[:] = [dict(v) for v in stanje["vrata"]]
            self.st_ost.set(stanje["ost"])
            self.st_preprost.set(stanje["preprost"])
            self._vrata_osvezi()
            self._preklopi_nacin()
            self._zivi_osvezi()
        finally:
            self._obnavljam = False
        self._zgodovina_i = i
        self._zgodovina_gumbi()

    def _zgodovina_zabelezi_hitro_ali_pobrisi(self):
        """Pred preskokom v zgodovini zaključi čakajoči debounce vnos."""
        if self._zgodovina_id is not None:
            try:
                self.after_cancel(self._zgodovina_id)
            except Exception:
                pass
            self._zgodovina_id = None

    def _zgodovina_gumbi(self):
        if not hasattr(self, "btn_razveljavi"):
            return
        self.btn_razveljavi.config(
            state="normal" if self._zgodovina_i > 0 else "disabled")
        self.btn_ponovi.config(
            state="normal" if self._zgodovina_i < len(self._zgodovina) - 1
            else "disabled")

    def _razveljavi(self, _ev=None):
        if self._zgodovina_i > 0:
            self._zgodovina_obnovi(self._zgodovina_i - 1)
        return "break"

    def _ponovi(self, _ev=None):
        if self._zgodovina_i < len(self._zgodovina) - 1:
            self._zgodovina_obnovi(self._zgodovina_i + 1)
        return "break"

    def _privzeti(self):
        p = risba.PRIVZETO
        m = p["mere"]
        return {
            "ime": p["ime"], "risba_st": p["risba_st"], "izdelal": p["izdelal"],
            "podjetje": p["podjetje"], "pregledal": p["pregledal"],
            "odobril": p["odobril"], "stranka": p["stranka"],
            "objekt": p["objekt"], "podlaga": p["podlaga"],
            "pritrditev_nacin": p["pritrditev"],
            "vijak_lamela": p["vijak_lamela"], "vijak_nosilec": p["vijak_nosilec"],
            "material": p["material"], "profil": p["profil"],
            "barva": p["barva"], "foto": "", "izhod": p["izhod"],
            "sirina": f"{m['sirina']:g}", "visina": f"{m['visina']:g}",
            "globina": f"{m['globina']:g}", "lamele": str(m["lamele"]),
            "lamela_v": f"{m['lamela_v']:g}", "debelina": f"{m['debelina']:g}",
            "odcep": f"{m['odcep']:g}",
            "razmak_nosilcev": f"{m['razmak_nosilcev']:g}",
            "vrzel": f"{m.get('vrzel', 20.0):g}",
            "kerf": f"{p.get('kerf', 3.0):g}",
            "dolzine_deske": "; ".join(f"{d:g}" for d in
                                       p.get("dolzine_deske", [5800])),
            "dolzina_palice": f"{p.get('dolzina_palice', 6000):g}",
            "material_lamel": p.get("material_lamel") or "",
            "dobavitelj": p.get("dobavitelj") or "",
        }

    # ------------------------------------------------------------- akcije
    def _brskaj_foto(self):
        pot = filedialog.askopenfilename(
            title="Izberi fotografijo",
            filetypes=[("Slike", "*.jpg *.jpeg *.png *.bmp"),
                       ("Vse datoteke", "*.*")])
        if pot:
            self.v["foto"].set(pot)

    def _meri_slike(self):
        """Odpri pomožno merjenje s fotografije (kalibracija + zaznavanje)."""
        pot = self.v["foto"].get().strip()
        if not pot or not os.path.isfile(pot):
            pot = filedialog.askopenfilename(
                title="Izberi fotografijo za merjenje",
                filetypes=[("Slike", "*.jpg *.jpeg *.png *.bmp"),
                           ("Vse datoteke", "*.*")])
            if not pot:
                return
            self.v["foto"].set(pot)
        try:
            import merjenje
        except ImportError:
            messagebox.showerror(
                "Manjka OpenCV",
                "Za merjenje s slike namesti OpenCV:\n\n"
                "python -m pip install opencv-python")
            return
        merjenje.App(pot)

    def _preberi_mere(self):
        def stev(kljuc, tip=float):
            raw = self.v[kljuc].get().strip().replace(",", ".")
            try:
                vred = tip(raw)
            except ValueError:
                raise ValueError(f"Polje »{NAPISI.get(kljuc, kljuc)}« mora "
                                 f"biti število (vpisano: "
                                 f"{self.v[kljuc].get().strip()!r}).")
            if vred <= 0:
                raise ValueError(f"Polje »{NAPISI.get(kljuc, kljuc)}« mora "
                                 "biti pozitivno število.")
            return vred

        return {
            "sirina": stev("sirina"), "visina": stev("visina"),
            "globina": stev("globina"), "lamele": stev("lamele", int),
            "lamela_v": stev("lamela_v"), "debelina": stev("debelina"),
            "odcep": stev("odcep"), "profil_v": 40.0,
            "razmak_nosilcev": stev("razmak_nosilcev"),
            "deska_sirina": stev("lamela_v"), "deska_debelina": stev("debelina"),
            "vrzel": stev("vrzel"), "rocaj_v": 40.0,
            "razmak_stebrov": stev("razmak_nosilcev"),
            "steber_sirina": 60.0, "steber_debelina": 40.0,
        }

    def _zberi_cfg(self):
        m = self._preberi_mere()
        cene = {}
        for ck in CENE_KLJUCI:
            raw = self.v["cene_" + ck].get().strip().replace(",", ".")
            if raw:
                try:
                    cene[ck] = float(raw)
                except ValueError:
                    raise ValueError(f"Polje »{CENE_NAPISI[ck]}« mora biti "
                                     f"število ali prazno (vpisano: {raw!r}).")
        def dec(kljuc, priv):
            raw = self.v[kljuc].get().strip().replace(",", ".")
            if not raw:
                return priv
            try:
                return float(raw)
            except ValueError:
                raise ValueError(f"Polje »{NAPISI.get(kljuc, kljuc)}« mora "
                                 f"biti število ali prazno (vpisano: "
                                 f"{raw!r}).")
        dl_dolzine = []
        for x in (self.v["dolzine_deske"].get().strip()
                  .replace(";", ",").split(",")):
            if x.strip():
                try:
                    dl_dolzine.append(float(x.strip().replace(",", ".")))
                except ValueError:
                    raise ValueError(f"Polje »{NAPISI['dolzine_deske']}« mora "
                                     f"biti števila, ločena z ; (vpisano: "
                                     f"{self.v['dolzine_deske'].get()!r}).")
        ime = self.v["ime"].get().strip() or "BALKONSKA OGRAJA"
        izhod = self.v["izhod"].get().strip() or "BO-001.pdf"
        foto = self.v["foto"].get().strip()
        if foto and not os.path.isfile(foto):
            raise ValueError(f"Fotografija ne obstaja: {foto}")
        cfg = {
            "predloga": self.v["predloga"].get() or "ograja", "ime": ime,
            "risba_st": self.v["risba_st"].get().strip() or "BO-001",
            "izdelal": self.v["izdelal"].get().strip() or "",
            "stranka": self.v["stranka"].get().strip() or None,
            "objekt": self.v["objekt"].get().strip() or None,
            "podjetje": self.v["podjetje"].get().strip() or None,
            "pregledal": self.v["pregledal"].get().strip() or None,
            "odobril": self.v["odobril"].get().strip() or None,
            "datum": "", "merilo": "auto", "format": "A3",
            "izhod": izhod, "foto": foto,
            "barva": self.v["barva"].get() or None,
            "profil": self.v["profil"].get().strip() or None,
            "material_lamel": self.v["material_lamel"].get().strip() or None,
            "dobavitelj": self.v["dobavitelj"].get().strip() or None,
            "kerf": dec("kerf", 3.0),
            "dolzina_palice": dec("dolzina_palice", 6000.0),
            "dolzine_deske": (dl_dolzine or None),
            "uporabi_ostanke": bool(self.st_ost.get()),
            "material": self.v["material"].get().strip() or "Aluminij",
            "podlaga": self.v["podlaga"].get().strip() or None,
            "pritrditev": self.v["pritrditev_nacin"].get().strip() or None,
            "pritrditev_nacin": self.v["pritrditev_nacin"].get().strip() or None,
            "vijak_lamela": self.v["vijak_lamela"].get().strip() or None,
            "vijak_nosilec": self.v["vijak_nosilec"].get().strip() or None,
            "deli": None, "opombe": None, "mere": m,
            "klik_cel_zaslon": bool(self.st_klik.get()),
            "preprost_nacin": bool(self.st_preprost.get()),
            "vrata": [dict(v) for v in self.vrata_sez],
        }
        if cene:
            cfg["cene"] = cene
        return cfg

    def _narisi(self):
        try:
            cfg = self._zberi_cfg()
        except ValueError as e:
            messagebox.showerror("Napaka pri vnosu", str(e))
            return
        self.btn_narisi.config(state="disabled", text="NARISUJEM…")
        self.status.config(text="Narišem risbo…", fg="#555555")
        threading.Thread(target=self._narisi_nit, args=(cfg,),
                         daemon=True).start()

    def _narisi_nit(self, cfg):
        try:
            izhod, png, dodatni, kolicine = risba.generiraj(cfg, dpi_png=120)
        except ValueError as e:
            self.after(0, self._napaka, str(e))
            return
        except Exception as e:                     # nepričakovana napaka
            self.after(0, self._napaka, f"Nepričakovana napaka: {e}")
            return
        self.after(0, self._koncano, izhod, png, dodatni, kolicine)

    def _napaka(self, sporocilo):
        self.btn_narisi.config(state="normal", text="NARIŠI RISBO")
        self.status.config(text="Napaka.", fg="#b00020")
        messagebox.showerror("Napaka", sporocilo)

    def _koncano(self, izhod, png, dodatni, kolicine):
        self.pdf_pot = izhod
        self.png_pot = png
        self.kolicine = kolicine
        self.btn_pdf.config(state="normal")
        self.btn_cel.config(state="normal")
        if kolicine and kolicine.get("narocilo"):
            self.btn_nar.config(state="normal")
        # Gumb za odpis ostankov je omogočen LE ob dejanski sprememb
        # skladišča (B1) — po odpisu ga _odpisi_ostanke onemogoči.
        if kolicine and kolicine.get("ostanki_posodobitev") is not None:
            self.btn_ost.config(state="normal")
        else:
            self.btn_ost.config(state="disabled")
        self.btn_narisi.config(state="normal", text="NARIŠI RISBO")
        dok = " + ".join(os.path.basename(p) for p in dodatni)
        opozorila = list(getattr(risba, "ZADNJA_OPOZORILA", []))
        self.status.config(text=f"Napisano: {os.path.basename(izhod)} • {dok} "
                                f"• nastavitve samodejno shranjene",
                           fg="#1b5e20")
        if opozorila:
            self.status.config(text="Napisano z OPOZORILI — PDF ni popoln "
                                    "(glej sporočilo).", fg="#b26a00")
            messagebox.showwarning(
                "Opozorila", "PDF je nastal, a ni popoln:\n\n"
                + "\n\n".join(opozorila))
        self._shrani_zadnje()
        self._pokazi_predogled(png)

    # napredna polja — skrita v preprostem načinu
    ADVANS = ("podjetje", "pregledal", "odobril", "stranka", "objekt",
              "material", "profil", "razmak_nosilcev", "barva", "meri_slike",
              "podlaga", "pritrditev_nacin", "vijak_lamela", "vijak_nosilec",
              "material_lamel", "dobavitelj", "vrzel", "kerf", "dolzine_deske",
              "dolzina_palice", "uporabi_ostanke", "vrata_okvir",
              "cene_wpc_deska_m", "cene_alu_m", "cene_rocaj_kos",
              "cene_nosilec_kos", "cene_vijak_kos", "cene_fasadni_kos",
              "cene_anker_kos", "cene_dela_ure", "cene_dela_ur_cena")

    def _preklopi_predlogo(self):
        """Prilagodi napise polj predlogi (ograda / pokončna)."""
        pok = self.v["predloga"].get() == "pokončna"
        if "lamele" in self.polja:
            self.polja["lamele"][0].config(
                text="Število desk:" if pok else "Število lamel:")
        if "lamela_v" in self.polja:
            self.polja["lamela_v"][0].config(
                text="Širina desk (mm):" if pok else "Višina lamel (mm):")
        if "debelina" in self.polja:
            self.polja["debelina"][0].config(
                text="Debelina desk (mm):" if pok else "Debelina lamel (mm):")
        if "razmak_nosilcev" in self.polja:
            self.polja["razmak_nosilcev"][0].config(
                text="Razmak stebrov (mm):" if pok else "Razmak nosilcev (mm):")

    def _preklopi_nacin(self):
        """Preprosti način: skrije napredna polja, pokaže samo osnovno."""
        preprost = self.st_preprost.get()
        for kljuc in self.ADVANS:
            for w in self.polja.get(kljuc, []):
                if preprost:
                    w.grid_remove()
                else:
                    w.grid()
        for f in self.polja.get("cene_okvir", []):
            if preprost:
                f.grid_remove()
            else:
                f.grid()
        if preprost:
            self.status.config(text="Preprosti način — kljukica zgoraj "
                                    "prikaže napredne možnosti.")
        self._zgodovina_odlozi()          # Plan D

    # ------------------------------------------------- vrata in prehodi (issue #3)
    def _vrata_mere(self):
        """Osnovne mere ograje za validacijo vrat (brez napak v drugih poljih)."""
        def stev(kljuc, priv):
            try:
                return float(self.v[kljuc].get().strip().replace(",", ".")
                             or priv)
            except (ValueError, KeyError, AttributeError):
                return priv
        return stev("sirina", 0.0), stev("visina", 0.0), stev("odcep", 0.0)

    def _vrata_preveri(self):
        """Preveri vrate/prehode in prikaže napake (rdeče) / opozorila (oranžno)."""
        napake = []
        opozorila = []
        sir, vis, odcep = self._vrata_mere()
        odprtine = []
        for i, v in enumerate(self.vrata_sez, start=1):
            try:
                g = vrat.geometrija_vrat(v, v.get("sirina", 900),
                                         float(v.get("visina") or 0))
            except (ValueError, TypeError) as e:
                napake.append(f"Vrata {i}: {e}")
                continue
            if g["odprtina"]["visina"] + odcep > vis + 1e-9:
                napake.append(f"Vrata {i}: višina z odcepom presega višino "
                              f"ograje ({risba.fmt(vis)} mm).")
            odprtine.append((g["x"], g["odprtina"]["sirina"], vis,
                              f"Vrata {i}"))
            if g["tip"] == "enokrilna" and g["odprtina"]["sirina"] > 1000:
                opozorila.append(f"Vrata {i}: enokrilna nad 1000 mm se "
                                 "lahko povesijo.")
        if sir > 0:
            napake += vrat.preveri_odprtine(odprtine, sir, vis)
        besedilo = ""
        if napake:
            besedilo = "✖ " + "\n✖ ".join(napake)
        elif opozorila:
            besedilo = "⚠ " + "\n⚠ ".join(opozorila)
        self.lbl_vrata.config(text=besedilo,
                              fg="#b00020" if napake else "#b26a00")
        return napake

    def _vrata_osvezi(self):
        self.tv_vrata.delete(*self.tv_vrata.get_children())
        for i, v in enumerate(self.vrata_sez, start=1):
            self.tv_vrata.insert("", "end", iid=str(i - 1), values=(
                i, v.get("tip", ""), v.get("x", ""), v.get("sirina", ""),
                v.get("visina", ""), v.get("smer", "—")))
        self._vrata_preveri()
        self._zivi_sprememba()

    def _vrata_dialog(self, vnos=None):
        """Modalni dialog za vnos/urejanje vrat ali prehoda."""
        d = tk.Toplevel(self)
        d.title("Vrata / prehod")
        d.grab_set()
        polja = {}
        vrsta_tip = tk.StringVar(value=(vnos or {}).get("tip", "enokrilna"))
        ttk.Label(d, text="Tip:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        cb = ttk.Combobox(d, textvariable=vrsta_tip, state="readonly", width=16,
                          values=list(vrat.VRSTE_VRAT))
        cb.grid(row=0, column=1, sticky="w", pady=4)
        for vr, (kljuc, privzeto) in enumerate((
                ("x", "0"), ("sirina", "900"), ("visina", "1500")), start=1):
            ttk.Label(d, text={"x": "Položaj x (mm):", "sirina": "Širina (mm):",
                               "visina": "Višina (mm):"}[kljuc]).grid(
                row=vr, column=0, sticky="e", padx=6, pady=4)
            e = ttk.Entry(d, width=12)
            e.insert(0, str((vnos or {}).get(kljuc, privzeto)))
            e.grid(row=vr, column=1, sticky="w", pady=4)
            polja[kljuc] = e
        ttk.Label(d, text="Smer:").grid(row=4, column=0, sticky="e", padx=6)
        v_smer = tk.StringVar(value=(vnos or {}).get("smer", "desno-navzven"))
        ttk.Combobox(d, textvariable=v_smer, state="readonly", width=16,
                     values=list(vrat.SMERI)).grid(row=4, column=1, sticky="w")
        v_diag = tk.BooleanVar(value=bool((vnos or {}).get("diagonala")))
        ttk.Checkbutton(d, text="Diagonala", variable=v_diag).grid(
            row=5, column=1, sticky="w")
        napaka_lbl = tk.Label(d, text="", fg="#b00020", wraplength=280,
                              justify="left")
        napaka_lbl.grid(row=6, column=0, columnspan=2, sticky="w", padx=6)
        rezultat = {}

        def potrdi():
            try:
                v = vrat.normaliziraj_vrata({
                    "tip": vrsta_tip.get(),
                    "x": polja["x"].get(),
                    "sirina": polja["sirina"].get(),
                    "visina": polja["visina"].get(),
                    "smer": v_smer.get(),
                    "diagonala": bool(v_diag.get()),
                })
                vrat.geometrija_vrat(v, v["sirina"], v["visina"])
            except ValueError as e:
                napaka_lbl.config(text=str(e))
                return
            rezultat.update(v)
            d.destroy()

        ttk.Button(d, text="V redu", command=potrdi).grid(row=7, column=1,
                                                          sticky="e", padx=6,
                                                          pady=8)
        ttk.Button(d, text="Prekliči", command=d.destroy).grid(
            row=7, column=0, sticky="w", padx=6, pady=8)
        d.wait_window()
        return rezultat or None

    def _vrata_dodaj(self):
        v = self._vrata_dialog()
        if v:
            self.vrata_sez.append(v)
            self._vrata_osvezi()

    def _vrata_uredi(self):
        izbira = self.tv_vrata.selection()
        if not izbira:
            messagebox.showinfo("Uredi vrata", "Najprej izberi vrstico v seznamu.")
            return
        i = int(izbira[0])
        v = self._vrata_dialog(self.vrata_sez[i])
        if v:
            self.vrata_sez[i] = v
            self._vrata_osvezi()

    def _vrata_odstrani(self):
        izbira = self.tv_vrata.selection()
        if not izbira:
            messagebox.showinfo("Odstrani vrata",
                                "Najprej izberi vrstico v seznamu.")
            return
        i = int(izbira[0])
        v = self.vrata_sez[i]
        if not messagebox.askyesno(
                "Odstrani vrata",
                f"Ali res želiš odstraniti vrata #{i + 1} "
                f"({v.get('tip')}, x={v.get('x')} mm)?\n"
                "Tega dejanja ni mogoče razveljaviti."):
            return
        del self.vrata_sez[i]
        self._vrata_osvezi()

    def _izvozi_dxf(self):
        """Izvoz projekta v DXF za CAD/CNC (ezdxf)."""
        try:
            import dxf_izvoz
        except ImportError:
            messagebox.showerror(
                "Manjka ezdxf",
                "Za DXF izvoz namesti knjižnico:\npython -m pip install ezdxf")
            return
        try:
            cfg = self._zberi_cfg()
        except ValueError as e:
            messagebox.showerror("Napaka pri vnosu", str(e))
            return
        zacetna = os.path.splitext(cfg.get("izhod") or "projekt.pdf")[0] + ".dxf"
        pot = filedialog.asksaveasfilename(
            defaultextension=".dxf", initialfile=os.path.basename(zacetna),
            filetypes=[("DXF (CAD/CNC)", "*.dxf")])
        if not pot:
            return
        if os.path.exists(pot):
            if not messagebox.askyesno(
                    "Datoteka obstaja",
                    f"{pot} že obstaja.\nAli jo prepišem?"):
                return
        try:
            dxf_izvoz.izvozi_dxf(cfg, pot)
        except Exception as e:
            messagebox.showerror("Napaka pri DXF izvozu", str(e))
            return
        messagebox.showinfo("DXF izvoz",
                            f"DXF zapisan: {pot}\n"
                            "Konture so nominalne (brez kompenzacije "
                            "orodja/kerfa); DXF ne vsebuje G-code.")

    def _klik_predogled(self, e=None):
        """Klik na predogled odpre cel zaslon samo, če je kljukica označena."""
        if self.st_klik.get():
            self._cel_zaslon()

    def _cel_zaslon(self):
        if not self.png_pot:
            return
        if IMA_PIL:
            CelZaslon(self, self.png_pot)
        else:
            t = tk.Toplevel(self)
            t.title("Predogled — cel zaslon (ESC = izhod)")
            t.configure(bg="black")
            t.attributes("-fullscreen", True)
            t.bind("<Escape>", lambda e: t.destroy())
            img = tk.PhotoImage(file=self.png_pot, subsample=3)
            tk.Label(t, image=img, bg="black").pack(expand=True)
            t._img = img

    def _shrani_zadnje(self):
        """Samodejno shrani trenutne nastavitve (tiho, brez obvestil)."""
        try:
            cfg = self._zberi_cfg()
            with open(DAT_ZADNJE, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        except Exception:
            pass

    def _izpolni_privzete(self):
        """Prazna polja izpolni s privzetimi vrednostmi (prvi zagon)."""
        for kljuc, vred in self._privzeti().items():
            if kljuc in self.v and not self.v[kljuc].get().strip():
                self.v[kljuc].set(str(vred))

    def _nalozi_zadnje(self):
        """Naloži zadnje nastavitve, če obstajajo (ob zagonu okna)."""
        try:
            with open(DAT_ZADNJE, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            return
        if not isinstance(cfg, dict):
            return

        def nast(kljuc, vrednost):
            if vrednost is not None and kljuc in self.v:
                self.v[kljuc].set(str(vrednost))

        for k in ("ime", "risba_st", "izdelal", "podjetje", "pregledal",
                  "odobril", "stranka", "objekt", "material", "profil",
                  "barva", "izhod", "foto", "podlaga",
                  "vijak_lamela", "vijak_nosilec", "material_lamel",
                  "dobavitelj", "kerf", "dolzina_palice"):
            nast(k, cfg.get(k))
        # "Pritrditev" — krog shranjevanja/preverjanja (B5): zapisujemo
        # oba ključa, beremo "pritrditev_nacin" s povratnim "pritrditev"
        nast("pritrditev_nacin",
             cfg.get("pritrditev_nacin", cfg.get("pritrditev")))
        for k in ("sirina", "visina", "globina", "lamele", "lamela_v",
                  "debelina", "odcep", "razmak_nosilcev", "vrzel"):
            nast(k, (cfg.get("mere") or {}).get(k))
        if cfg.get("dolzine_deske"):
            nast("dolzine_deske", "; ".join(f"{d:g}"
                                            for d in cfg["dolzine_deske"]))
        if "uporabi_ostanke" in cfg:
            self.st_ost.set(bool(cfg["uporabi_ostanke"]))
        if "klik_cel_zaslon" in cfg:
            self.st_klik.set(bool(cfg["klik_cel_zaslon"]))
        if "preprost_nacin" in cfg:
            self.st_preprost.set(bool(cfg["preprost_nacin"]))
            self._preklopi_nacin()
        if isinstance(cfg.get("vrata"), list):
            self.vrata_sez = [dict(v) for v in cfg["vrata"]
                              if isinstance(v, dict)]
            self._vrata_osvezi()
        if "predloga" in cfg:
            pl = str(cfg["predloga"]).strip().lower()
            self.v["predloga"].set("pokončna" if pl == "pokončna" else "ograja")
            self._preklopi_predlogo()
        for ck in CENE_KLJUCI:
            nast("cene_" + ck, (cfg.get("cene") or {}).get(ck))

    def _pokazi_predogled(self, png):
        if IMA_PIL:
            img = Image.open(png)
            okvir_w = max(self.fp.winfo_width() - 20, 400)
            okvir_h = max(self.fp.winfo_height() - 20, 300)
            merilo = min(okvir_w / img.width, okvir_h / img.height, 1.0)
            img = img.resize((max(1, int(img.width * merilo)),
                              max(1, int(img.height * merilo))),
                             Image.LANCZOS)
            self._slika = ImageTk.PhotoImage(img)
        else:
            self._slika = tk.PhotoImage(file=png, subsample=4)
        self.predogled.config(image=self._slika, text="", fg="#999999")

    def _narocilo_kopiraj(self):
        if not (self.kolicine and self.kolicine.get("narocilo")):
            return
        self.clipboard_clear()
        self.clipboard_append(self.kolicine["narocilo"])
        messagebox.showinfo(
            "Naročilo kopirano",
            "Naročilo je kopirano v odložišče — prilepi v e-pošto "
            "dobavitelju (npr. Roksal).")

    def _odpisi_ostanke(self):
        if not (self.kolicine and
                self.kolicine.get("ostanki_posodobitev") is not None):
            return
        try:
            pot, backup = risba.shrani_ostanke(
                self.kolicine["ostanki_posodobitev"])
        except Exception as e:
            messagebox.showerror("Ostanki", f"Napaka pri shranjevanju: {e}")
            return
        self.kolicine["ostanki_posodobitev"] = None
        self.btn_ost.config(state="disabled")
        sporocilo = f"Ostanki so odpisani iz skladišča:\n{pot}"
        if backup:
            sporocilo += f"\n\nVarnostna kopija pred prepisom:\n{backup}"
        messagebox.showinfo("Ostanki", sporocilo)

    def _odpri_pdf(self):
        if self.pdf_pot:
            os.startfile(self.pdf_pot)

    def _shrani_projekt(self):
        try:
            cfg = self._zberi_cfg()
        except ValueError as e:
            messagebox.showerror("Napaka pri vnosu", str(e))
            return
        pot = filedialog.asksaveasfilename(
            defaultextension=".yaml", initialfile="projekt.yaml",
            filetypes=[("YAML", "*.yaml")], title="Shrani projekt kot")
        if not pot:
            return
        with open(pot, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        messagebox.showinfo(
            "Shranjeno",
            f"Nastavitve shranjene:\n{pot}\n\nIsto risbo narediš tudi iz "
            f"ukazne vrstice:\npython risba.py {os.path.basename(pot)}")


if __name__ == "__main__":
    # Neinteraktivni način (issue #6, §9 — smoke test zgrajenega programa):
    #   TehnicnaRisba.exe --brez-zaslona <config.json|config.yaml>
    #   TEHNICNA_RISBA_HEADLESS=1 TehnicnaRisba.exe <config.yaml>
    # izvede generiranje PDF brez odpiranja GUI in konča z izhodno kodo.
    _args = [a for a in sys.argv[1:]]
    # Terenski list (issue #9/#10) — ločen urejevalnik skice v istem paketu:
    #   TehnicnaRisba.exe --terenski            (odpre urejevalnik)
    #   TehnicnaRisba.exe --terenski-smoke X.pdf (headless demo izpis)
    if "--terenski" in _args:
        import terenski_gui
        terenski_gui.zazeni()
        sys.exit(0)
    if "--terenski-smoke" in _args:
        try:
            import terenski_list
            _i = _args.index("--terenski-smoke")
            _kandidat = _args[_i + 1] if _i + 1 < len(_args) else ""
            _pot = (_kandidat if _kandidat and not _kandidat.startswith("--")
                    else "terenski-smoke.pdf")
            _st = terenski_list.izvozi_pdf(terenski_list._demo_dokument(), _pot)
            print(f"OK: {_pot} ({_st} strani)")
            sys.exit(0)
        except Exception as _e:
            print(f"NAPAKA: {_e}", file=sys.stderr)
            sys.exit(1)
    _headless = (os.environ.get("TEHNICNA_RISBA_HEADLESS") == "1"
                 or "--brez-zaslona" in _args)
    if _headless:
        try:
            _args = [a for a in _args if a != "--brez-zaslona"]
            if not _args:
                print("Uporaba: TehnicnaRisba --brez-zaslona <config.json|config.yaml>",
                      file=sys.stderr)
                sys.exit(2)
            with open(_args[0], "r", encoding="utf-8") as _f:
                _cfg = (json.load(_f) if _args[0].lower().endswith(".json")
                        else yaml.safe_load(_f))
            _izhod, _png, _dod, _kol = risba.generiraj(_cfg)
            print(f"Izdelano: {_izhod}")
            sys.exit(0)
        except Exception as _e:   # v windowed EXE bi sicer PyInstaller odprl modalni dialog
            print(f"NAPAKA: {_e}", file=sys.stderr)
            sys.exit(1)

    app = App()
    # OPOMBA: privzetih vrednosti tukaj NE pišemo čez app.v — nalaganje
    # zadnjih nastavitev (App.__init__ -> _nalozi_zadnje) mora ostati
    # veljavno (regresija: pisanje čez naložene nastavitve).
    app.mainloop()
