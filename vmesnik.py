#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vmesnik.py — grafični vmesnik za generator tehničnih risb (risba.py).

Zagon:  python vmesnik.py   (ali dvoklik nanj)
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yaml

# v exe načinu se nastavitve shranjujejo poleg programa (ne v začasni mapi)
if getattr(sys, "frozen", False):
    _AP_DIR = os.path.dirname(sys.executable)
else:
    _AP_DIR = os.path.dirname(os.path.abspath(__file__))

import risba

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
        self.st_preprost = tk.BooleanVar(value=True)   # preprosti način
        self._zgradi()
        self._preklopi_nacin()
        self._nalozi_zadnje()
        self._izpolni_privzete()

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
            variable=self.st_ost)
        cb_ost.grid(row=4, column=2, columnspan=2, sticky="w")
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

        # ---- GUMBI ----
        fb = ttk.Frame(zg, padding=(0, 10))
        fb.grid(row=4, column=0, sticky="ew")
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
        self.btn_cel = ttk.Button(fb, text="CEL ZASLON", state="disabled",
                                  command=self._cel_zaslon)
        self.btn_cel.pack(side="right", padx=10)
        self.status = tk.Label(fb, text="Pripravljen.", fg="#555555",
                               font=("Segoe UI", 9))
        self.status.pack(side="right", padx=14)

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
              "dolzina_palice", "uporabi_ostanke",
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
    app = App()
    # OPOMBA: privzetih vrednosti tukaj NE pišemo čez app.v — nalaganje
    # zadnjih nastavitev (App.__init__ -> _nalozi_zadnje) mora ostati
    # veljavno (regresija: pisanje čez naložene nastavitve).
    app.mainloop()
