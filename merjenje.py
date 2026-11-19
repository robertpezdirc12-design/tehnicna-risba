#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merjenje.py — pomožno merjenje s fotografije (kalibracija + zaznavanje).

Kako deluje (pošteno):
  1. Odpri fotografijo ograje.
  2. KALIBRACIJA: klikni 2 točki na ZNANI dimenziji (privzeto širina WoodCore
     deske = 67 mm; lahko tudi meter ali merilo v kadru) — nastavi se merilo.
  3. MERI: klikni 2 točki na neznani dimenziji — izpiše mm; poimenuj meritve
     (npr. "sirina", "visina", "razmak_vijakov") za prenos v risbo.
  4. ZAZNAJ LAMELE: samodejno poišče svetlo/temne pasove (vrste lamel) in
     predlaga število, višino in vrzel (potrdi z merilom!).
  5. ZAZNAJ VIJAKE/LUKNJE: samodejno poišče okrogle pike (vijaki, luknje)
     in izračuna tipičen razmak (potrdi z merilom!).

Zagon: python merjenje.py [slika.jpg]
Test brez okna: python merjenje.py slika.jpg --test
"""

import math
import os
import sys

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageTk

try:
    import cv2
    IMA_CV = True
except ImportError:
    IMA_CV = False

TIPKE_MERE = ("sirina", "visina", "globina", "razmak_nosilcev")


# ---------------------------------------------------------------- zaznavanje
def _obrez(roi, w, h):
    """roi = (x0, y0, x1, y1) ali None -> celotna slika."""
    if not roi:
        return 0, 0, w, h
    return (max(0, int(min(roi[0], roi[2]))), max(0, int(min(roi[1], roi[3]))),
            min(w, int(max(roi[0], roi[2]))), min(h, int(max(roi[1], roi[3]))))


def vrhovi(x, sep, thr):
    """Lokalni maksimumi z najmanjšim razmakom sep in pragom thr."""
    idx = []
    for i in range(1, len(x) - 1):
        if x[i] >= x[i - 1] and x[i] >= x[i + 1] and x[i] >= thr:
            if idx and i - idx[-1] < sep:
                if x[i] > x[idx[-1]]:
                    idx[-1] = i
            else:
                idx.append(i)
    return idx


def _najboljsi_periodicni(prof, ofs=0):
    """Najde najbolj reden periodični vzorec v 1-D profilu svetlosti.

    Kandidati: temni pasovi / svetle vrzeli / robovi (gradient).
    Vrne (rel_odklon, pasovi [(a, b)], info) ali None.
    """
    n = len(prof)
    k = max(1, int(n * 0.003) | 1)
    sm = np.convolve(prof, np.ones(k) / k, mode="same")
    meja = (float(sm.max()) + float(sm.min())) / 2.0

    def teki(maska):
        out = []
        zac = None
        for y, t in enumerate(maska):
            if t and zac is None:
                zac = y
            elif not t and zac is not None:
                if y - zac > 2:
                    out.append((zac, y))
                zac = None
        if zac is not None:
            out.append((zac, len(maska)))
        return out

    kand = []
    for tip, maska in (("temne", sm < meja), ("svetle", sm >= meja)):
        teki_r = teki(maska)
        if 3 <= len(teki_r) <= 300:
            pitch = [teki_r[i + 1][0] - teki_r[i][0]
                     for i in range(len(teki_r) - 1)]
            if pitch:
                povp = sum(pitch) / len(pitch)
                std = (sum((p - povp) ** 2 for p in pitch) / len(pitch)) ** 0.5
                rel = std / max(povp, 1e-9)
                tr = [(a + ofs, b + ofs) for a, b in teki_r]
                if tip == "svetle":
                    vrzeli = [b - a for a, b in tr]
                    deb = [p - v for p, v in zip(pitch, vrzeli)] or None
                    centri = [(a + b) / 2 for a, b in tr]
                    pasovi = [(c - 1, c + 1) for c in centri]
                    lam = len(tr) + 1
                else:
                    vrzeli = [tr[i + 1][0] - tr[i][1]
                              for i in range(len(tr) - 1)]
                    deb = [b - a for a, b in tr] or None
                    pasovi = tr
                    lam = len(tr)
                info = {"stevilo": lam,
                        "debelina_px": float(np.mean(deb)) if deb else None,
                        "vrzel_px": float(np.mean(vrzeli)) if vrzeli else None,
                        "pitch_px": float(np.mean(pitch)), "tip": tip}
                kand.append((rel, pasovi, info))

    # kandidat: robovi (gradient svetlosti) — deluje tudi pri nizkem kontrastu
    grad = np.abs(np.diff(sm))
    k2 = max(1, int(n * 0.002) | 1)
    grad = np.convolve(grad, np.ones(k2) / k2, mode="same")
    sep = max(6, int(n * 0.008))
    thr = float(grad.mean() + 0.8 * grad.std())
    vr = vrhovi(grad, sep, thr)
    if len(vr) >= 4:
        razlike = np.diff(np.array(vr))
        med = float(np.median(razlike))
        if 5 <= med <= n * 0.4:
            blizu = razlike[(razlike > 0.5 * med) & (razlike < 1.5 * med)]
            if len(blizu):
                mad = float(np.mean(np.abs(blizu - med)))
                pasovi_g = [(v + ofs - 1, v + ofs + 1) for v in vr]
                info = {"stevilo": int(round((vr[-1] - vr[0]) / med)) + 1,
                        "debelina_px": None, "vrzel_px": None,
                        "pitch_px": med + 1, "tip": "robovi"}
                kand.append((mad / med, pasovi_g, info))

    if not kand:
        return None
    kand.sort(key=lambda t: t[0])
    return kand[0]


def zaznaj_lamele(pot, roi=None):
    """Zazna VODORAVNE pasove lamel (prečna ograja) znotraj obmečja.

    Zaznavanje smeri (pokončna ograja) je preskušeno in nezanesljivo na
    dejanskih fotografijah, zato ni vključeno — za to uporabi klik-merjenje.

    Vrne (pasovi [(y0, y1)], info).
    """
    img = cv2.imread(pot)
    if img is None:
        raise ValueError(f"Slike ni mogoče odpreti: {pot}")
    H, W = img.shape[:2]
    bx0, by0, bx1, by1 = _obrez(roi, W, H)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[by0:by1, bx0:bx1]
    h, w = g.shape
    if h < 20 or w < 20:
        raise ValueError("Območje je premajhno — označi večje območje ograje.")
    x0, x1 = int(w * 0.2), int(w * 0.8)
    r = _najboljsi_periodicni(g[:, x0:x1].mean(axis=1), by0)
    if not r:
        return [], {"stevilo": 0, "debelina_px": None, "vrzel_px": None,
                    "pitch_px": None}
    _, pasovi, info = r
    return pasovi, info


def zaznaj_vijake(pot, roi=None, y_range=None):
    """Zazna okrogle pike (vijaki/luknje) — temne in svetle (znotraj območja,
    po možnosti samo na višinskem območju ograje).

    Vrne (pike [(x, y, r)] v koordinatah cele slike, informacije dict).
    """
    img = cv2.imread(pot)
    if img is None:
        raise ValueError(f"Slike ni mogoče odpreti: {pot}")
    H, W = img.shape[:2]
    bx0, by0, bx1, by1 = _obrez(roi, W, H)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[by0:by1, bx0:bx1]
    h, w = g.shape
    if h < 20 or w < 20:
        raise ValueError("Območje je premajhno — označi večje območje ograje.")
    pike = []
    for barva in (0, 255):
        p = cv2.SimpleBlobDetector_Params()
        p.minThreshold, p.maxThreshold, p.thresholdStep = 10, 240, 12
        p.filterByArea = True
        p.minArea = max(20, w * h * 2e-7)
        p.maxArea = max(500, w * h * 3e-4)
        p.filterByCircularity = True
        p.minCircularity = 0.65
        p.filterByConvexity = False
        p.filterByInertia = False
        p.blobColor = barva
        det = cv2.SimpleBlobDetector_create(p)
        for kp in det.detect(g):
            y_abs = kp.pt[1] + by0
            if y_range and not (y_range[0] <= y_abs <= y_range[1]):
                continue
            pike.append((kp.pt[0] + bx0, y_abs, kp.size / 2))
    # razmak: mediana najbližjega soseda
    raz = []
    for i, (x, y, _) in enumerate(pike):
        naj = min((math.hypot(x - x2, y - y2)
                   for j, (x2, y2, _) in enumerate(pike) if j != i),
                  default=None)
        if naj:
            raz.append(naj)
    info = {
        "stevilo": len(pike),
        "razmak_px": float(np.median(raz)) if raz else None,
    }
    return pike, info


def oznaci_sliko(pot, pasovi, pike, izhod, roi=None):
    """Shrani označeno sliko (kroga/pike/pasovi) — za preverjanje."""
    img = Image.open(pot).convert("RGB")
    dr = ImageDraw.Draw(img)
    if roi:
        dr.rectangle([roi[0], roi[1], roi[2], roi[3]],
                     outline=(255, 140, 0), width=4)
    for (a, b) in pasovi:
        dr.line([(0, (a + b) / 2), (img.width, (a + b) / 2)],
                fill=(0, 200, 255), width=3)
    for (x, y, r) in pike:
        dr.ellipse([x - r - 4, y - r - 4, x + r + 4, y + r + 4],
                   outline=(0, 220, 80), width=3)
    img.save(izhod)


# ---------------------------------------------------------------- okno
class App(tk.Tk):
    def __init__(self, pot=None):
        super().__init__()
        self.title("Merjenje s fotografije — kalibracija + zaznavanje")
        self.geometry("1280x860")
        try:
            self.state("zoomed")
        except Exception:
            pass
        self.img = None
        self.w_px = self.h_px = 0
        self.png_pot = None
        self.scale = None          # px na mm
        self.zoom = 1.0
        self.off = [0.0, 0.0]
        self.prev = None
        self._tk_img = None
        self.klik = []             # trenutni par točk (koordinate slike)
        self.prev_premik = None
        self.meritve = []          # [(ime, mm_ali_None, px)]
        self.det_pasovi = []
        self.det_pike = []
        self.roi = None            # označeno območje ograje (x0, y0, x1, y1)
        self._zgradi()
        if pot and os.path.isfile(pot):
            self._odpri_pot(pot)

    # ------------------------------------------------------------- vmesnik
    def _zgradi(self):
        levi = ttk.Frame(self, padding=10)
        levi.pack(side="left", fill="y")

        ttk.Label(levi, text="MERJENJE S SLIKE", font=("Segoe UI", 13, "bold")
                  ).pack(anchor="w")
        ttk.Button(levi, text="ODPRI SLIKO…", command=self._odpri)\
            .pack(fill="x", pady=4)

        f1 = ttk.LabelFrame(levi, text="1. KALIBRACIJA (znana dimenzija)",
                            padding=6)
        f1.pack(fill="x", pady=6)
        ttk.Label(f1, text="Znana dolžina (mm):").pack(anchor="w")
        self.v_ref = tk.StringVar(value="67")   # širina WoodCore deske
        ttk.Entry(f1, width=12, textvariable=self.v_ref).pack(anchor="w")
        ttk.Label(f1, text="WoodCore deska: ROMB 67 → 67 mm; POLNA 128 → 128 mm",
                  foreground="#888888", wraplength=210, font=("Segoe UI", 7)
                  ).pack(anchor="w")
        self.btn_ref = ttk.Button(f1, text="KALIBRIRAJ (2 klika)",
                                  command=lambda: self._nastavi_nacin("ref"))
        self.btn_ref.pack(fill="x", pady=2)

        f2 = ttk.LabelFrame(levi, text="2. MERJENJE (2 klika)", padding=6)
        f2.pack(fill="x", pady=6)
        ttk.Label(f2, text="Ime meritve (sirina/visina/…):").pack(anchor="w")
        self.v_ime = tk.StringVar()
        ttk.Entry(f2, width=20, textvariable=self.v_ime).pack(anchor="w")
        self.btn_meri = ttk.Button(f2, text="MERI (2 klika)",
                                   state="disabled",
                                   command=lambda: self._nastavi_nacin("meri"))
        self.btn_meri.pack(fill="x", pady=2)
        self.lst = tk.Listbox(f2, height=8, font=("Segoe UI", 8))
        self.lst.pack(fill="x", pady=2)
        ttk.Button(f2, text="POBRIŠI MERITVE",
                   command=self._pobrisi_meritve).pack(fill="x")

        f3 = ttk.LabelFrame(levi, text="3. SAMODEJNO ZAZNAVAJANJE", padding=6)
        f3.pack(fill="x", pady=6)
        ttk.Label(f3, text="Najprej označi območje ograje (2 klika):",
                  wraplength=210, font=("Segoe UI", 7)).pack(anchor="w")
        self.btn_roi = ttk.Button(f3, text="OZNAČI OBMOČJE (2 klika)",
                                  state="disabled",
                                  command=lambda: self._nastavi_nacin("roi"))
        self.btn_roi.pack(fill="x", pady=2)
        ttk.Button(f3, text="POBRIŠI OBMOČJE",
                  command=self._pobrisi_roi).pack(fill="x", pady=2)
        self.btn_lam = ttk.Button(f3, text="ZAZNAJ LAMELE (pasovi)",
                                  state="disabled", command=self._zaznaj_lam)
        self.btn_lam.pack(fill="x", pady=2)
        self.btn_vij = ttk.Button(f3, text="ZAZNAJ VIJAKE / LUKNJE",
                                  state="disabled", command=self._zaznaj_vij)
        self.btn_vij.pack(fill="x", pady=2)
        ttk.Label(f3, text="Deluje najbolje na fotografiji iz blizu, pravokotno "
                           "na ograjo. Rezultate VEDNO potrdi z merilom!",
                  foreground="#b00020", wraplength=210, font=("Segoe UI", 7)
                  ).pack(anchor="w", pady=2)

        f4 = ttk.LabelFrame(levi, text="4. IZVOZ", padding=6)
        f4.pack(fill="x", pady=6)
        ttk.Button(f4, text="SHRANI KOT PROJEKT (.yaml)",
                   command=self._shrani).pack(fill="x", pady=2)

        self.status = tk.Label(levi, text="Odpriti moraš sliko.", fg="#555555",
                               wraplength=220, font=("Segoe UI", 8),
                               justify="left")
        self.status.pack(anchor="w", pady=8)

        desni = ttk.Frame(self)
        desni.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(desni, bg="#222222", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._narisi())
        self.canvas.bind("<Button-1>", self._klik)
        self.canvas.bind("<MouseWheel>", self._kolesce)
        self.canvas.bind("<Button-3>", self._desno)
        self.nacin = None

    # ------------------------------------------------------------- slika
    def _odpri(self):
        pot = filedialog.askopenfilename(
            filetypes=[("Slike", "*.jpg *.jpeg *.png *.bmp"),
                       ("Vse datoteke", "*.*")])
        if pot:
            self._odpri_pot(pot)

    def _odpri_pot(self, pot):
        self.img = Image.open(pot).convert("RGB")
        self.w_px, self.h_px = self.img.size
        self.png_pot = pot
        self.zoom = 1.0
        self.off = [0.0, 0.0]
        self.scale = None
        self.klik = []
        self.meritve = []
        self.det_pasovi = []
        self.det_pike = []
        self.roi = None
        for b in (self.btn_meri, self.btn_lam, self.btn_vij, self.btn_roi):
            b.config(state="normal")
        self.status.config(text=f"Slika: {self.w_px}×{self.h_px} px — "
                                "najprej KALIBRACIJA (2 klika na znano "
                                "dimenzijo).")
        self._narisi()

    # ------------------------------------------------------------- canvas
    def _osn(self):
        W = max(self.canvas.winfo_width(), 800)
        H = max(self.canvas.winfo_height(), 600)
        return W, H, min(W / self.w_px, H / self.h_px)

    def _narisi(self):
        if self.img is None:
            return
        W, H, s0 = self._osn()
        sc = s0 * self.zoom
        scx = self.w_px / 2 - self.off[0] / sc
        scy = self.h_px / 2 - self.off[1] / sc
        pw, ph = W / (2 * sc), H / (2 * sc)
        x0, y0 = max(0.0, scx - pw), max(0.0, scy - ph)
        x1, y1 = min(float(self.w_px), scx + pw), min(float(self.h_px),
                                                      scy + ph)
        if x1 <= x0 or y1 <= y0:
            return
        crop = self.img.crop((int(x0), int(y0), int(x1), int(y1)))
        dw = min(5000, max(1, int((x1 - x0) * sc)))
        dh = min(5000, max(1, int((y1 - y0) * sc)))
        crop = crop.resize((dw, dh), Image.BILINEAR)
        dr = ImageDraw.Draw(crop)

        def S(sx, sy):
            """slika-px -> točka na obrežanem izrezu."""
            return ((sx - x0) * sc, (sy - y0) * sc)

        for (a, b) in self.det_pasovi:
            py = S(0, (a + b) / 2)[1]
            dr.line([0, py, dw, py], fill=(0, 200, 255), width=2)
        for (x, y, r) in self.det_pike:
            px, py = S(x, y)
            rr = max(6, r * sc)
            dr.ellipse([px - rr, py - rr, px + rr, py + rr],
                       outline=(0, 220, 80), width=2)
        # meritve
        for ime, mm, (p1, p2) in self.meritve:
            a, b = S(*p1), S(*p2)
            dr.line([a, b], fill=(255, 210, 0), width=3)
            dr.ellipse([a[0] - 6, a[1] - 6, a[0] + 6, a[1] + 6],
                       fill=(255, 210, 0))
            dr.ellipse([b[0] - 6, b[1] - 6, b[0] + 6, b[1] + 6],
                       fill=(255, 210, 0))
            napis = f"{ime}: {mm:.0f} mm" if mm else f"{ime}: {math.hypot(p2[0]-p1[0], p2[1]-p1[1]):.0f} px"
            dr.text(((a[0] + b[0]) / 2 + 8, (a[1] + b[1]) / 2 - 8), napis,
                    fill=(255, 210, 0),
                    font=ImageFont_nalozi(16))
        # označeno območje
        if self.roi:
            a, b = S(self.roi[0], self.roi[1]), S(self.roi[2], self.roi[3])
            dr.rectangle([a, b], outline=(255, 140, 0), width=3)
        # trenutni klik-par
        for (sx, sy) in self.klik:
            px, py = S(sx, sy)
            dr.ellipse([px - 7, py - 7, px + 7, py + 7],
                       outline=(255, 60, 60), width=2)
            dr.line([px - 10, py, px + 10, py], fill=(255, 60, 60), width=2)
            dr.line([px, py - 10, px, py + 10], fill=(255, 60, 60), width=2)
        if len(self.klik) == 1 and self.prev_premik:
            a, b = S(*self.klik[0]), S(*self.prev_premik)
            dr.line([a, b], fill=(255, 120, 120), width=2)

        self._tk_img = ImageTk.PhotoImage(crop)
        self.canvas.delete("all")
        self.canvas.create_image(W / 2 + (x0 - scx) * sc + self.off[0],
                                 H / 2 + (y0 - scy) * sc + self.off[1],
                                 anchor="nw", image=self._tk_img)
        self.canvas.create_text(
            W / 2, H - 24,
            text="kolešček = povečava • desni klik = ponastavi klik • "
                 "ESC = izhod",
            fill="#aaaaaa", font=("Segoe UI", 9))

    def _klik_src(self, cx, cy):
        """točka platna -> koordinata slike (px)."""
        W, H, s0 = self._osn()
        sc = s0 * self.zoom
        return (self.w_px / 2 - self.off[0] / sc + (cx - W / 2) / sc,
                self.h_px / 2 - self.off[1] / sc + (cy - H / 2) / sc)

    def _klik(self, e):
        if self.img is None or not self.nacin:
            return
        sx, sy = self._klik_src(e.x, e.y)
        self.klik.append((sx, sy))
        if len(self.klik) >= 2:
            p1, p2 = self.klik[:2]
            d_px = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if self.nacin == "ref":
                try:
                    znano = float(str(self.v_ref.get()).replace(",", "."))
                except ValueError:
                    messagebox.showerror("Napaka", "Znana dolžina mora biti "
                                                  "število (mm).")
                    self.klik = []
                    return
                if d_px < 5 or znano <= 0:
                    self.klik = []
                    return
                self.scale = d_px / znano
                self.status.config(text=f"Merilo: {self.scale:.2f} px/mm — "
                                        "zdaj lahko MERIŠ in zaznavaš.")
                self.nacin = None
            elif self.nacin == "roi":
                self.roi = (min(p1[0], p2[0]), min(p1[1], p2[1]),
                            max(p1[0], p2[0]), max(p1[1], p2[1]))
                self.status.config(text="Območje označeno — zdaj ZAZNAJ "
                                        "LAMELE / VIJAKE.")
                self.nacin = None
            else:
                ime = self.v_ime.get().strip() or f"M{len(self.meritve) + 1}"
                mm = d_px / self.scale if self.scale else None
                self.meritve.append((ime, mm, (p1, p2)))
                self.lst.insert("end",
                                f"{ime}: {mm:.0f} mm" if mm
                                else f"{ime}: {d_px:.0f} px (brez merila)")
                self.v_ime.set("")
            self.klik = []
        self.prev_premik = None
        self._narisi()

    def _desno(self, e):
        self.klik = []
        self._narisi()

    def _kolesce(self, e):
        if self.img is None:
            return
        f = 1.25 if e.delta > 0 else 0.8
        W, H, s0 = self._osn()
        nz = max(0.5, min(15.0, self.zoom * f))
        if nz == self.zoom:
            return
        ux = (e.x - W / 2 - self.off[0]) / (s0 * self.zoom)
        uy = (e.y - H / 2 - self.off[1]) / (s0 * self.zoom)
        self.off[0] = e.x - W / 2 - ux * s0 * nz
        self.off[1] = e.y - H / 2 - uy * s0 * nz
        self.zoom = nz
        self._narisi()

    def bind(self, *a, **k):        # ESC
        super().bind(*a, **k)

    # ------------------------------------------------------------- dejanja
    def _nastavi_nacin(self, nacin):
        if nacin == "meri" and not self.scale:
            messagebox.showwarning(
                "Brez merila", "Najprej KALIBRACIJA (2 klika na znano "
                               "dimenzijo) — sicer so mm nesmiseln.")
            return
        self.nacin = nacin
        self.klik = []
        self.status.config(text="Klikni 2 točki na sliki …"
                                if nacin else "Pripravljen.")

    def _pobrisi_meritve(self):
        self.meritve = []
        self.lst.delete(0, "end")
        self._narisi()

    def _pobrisi_roi(self):
        self.roi = None
        self._narisi()

    def _zaznaj_lam(self):
        if not self.png_pot:
            return
        try:
            pasovi, info = zaznaj_lamele(self.png_pot, self.roi)
        except ValueError as e:
            messagebox.showerror("Napaka", str(e))
            return
        self.det_pasovi = pasovi
        self.det_info = info
        if self.scale and info["pitch_px"]:
            pitch = info["pitch_px"] / self.scale
            deb = (info["debelina_px"] or 0) / self.scale
            vr = (info["vrzel_px"] or 0) / self.scale
            self.status.config(
                text=f"Zaznanih pasov: {info['stevilo']} • pitch ≈ {pitch:.0f}"
                     f" mm • lamela ≈ {deb:.0f} mm • vrzel ≈ {vr:.0f} mm "
                     "(preveri z merilom!)")
            self.v_ime.set("razmak_lamel")
        else:
            self.status.config(text=f"Zaznanih pasov: {info['stevilo']} "
                                    "(brez merila — najprej kalibracija).")
        self._narisi()

    def _zaznaj_vij(self):
        if not self.png_pot:
            return
        if not self.det_pasovi:          # najprej območje ograje (pasovi)
            self._zaznaj_lam()
        try:
            y_range = None
            if len(self.det_pasovi) >= 2:
                centri = [(a + b) / 2 for a, b in self.det_pasovi]
                pitch = ((max(centri) - min(centri)) / (len(centri) - 1)
                         if len(centri) > 1 else 100)
                y_range = (min(centri) - 2 * pitch, max(centri) + 2 * pitch)
            pike, info = zaznaj_vijake(self.png_pot, self.roi, y_range)
        except ValueError as e:
            messagebox.showerror("Napaka", str(e))
            return
        self.det_pike = pike
        if self.scale and info["razmak_px"]:
            self.status.config(
                text=f"Zaznanih pik (vijaki/luknje): {info['stevilo']} • "
                     f"tipičen razmak ≈ {info['razmak_px'] / self.scale:.0f} "
                     "mm (preveri z merilom!)")
        else:
            self.status.config(text=f"Zaznanih pik: {info['stevilo']} "
                                    "(brez merila — najprej kalibracija).")
        self._narisi()

    def _shrani(self):
        if self.img is None:
            return
        cfg = {
            "predloga": "ograda",
            "ime": "NOVA OGRAJA (iz fotografije)",
            "risba_st": "NOVA-01",
            "izdelal": "", "stranka": "", "objekt": "",
            "datum": "", "merilo": "auto", "format": "A3",
            "izhod": "NOVA-01.pdf", "foto": self.png_pot or "",
            "barva": "Antracit", "profil": "ROMB 67",
            "material": "Aluminij (prašno barvano)",
            "material_lamel": "WPC lesni kompozit",
            "deli": None, "opombe": None, "revizije": None,
            "mere": {"sirina": 3000, "visina": 1200, "globina": 1200,
                     "odcep": 60, "profil_v": 40, "lamela_v": 60,
                     "debelina": 20, "lamele": 13, "razmak_nosilcev": 1000},
            "meritve_iz_slike": [f"{ime}: {mm:.0f} mm" if mm else
                                 f"{ime}: px" for ime, mm, _ in self.meritve],
        }
        # prenesi poimenovane meritve v mere
        for ime, mm, _ in self.meritve:
            if mm and ime.strip().lower() in TIPKE_MERE:
                cfg["mere"][ime.strip().lower()] = round(mm)
        # zaznane lamele (če merilo obstaja)
        info = getattr(self, "det_info", None) or {}
        if self.scale and info.get("stevilo", 0) >= 3:
            cfg["mere"]["lamele"] = info["stevilo"]
            if info.get("debelina_px"):
                cfg["mere"]["lamela_v"] = round(
                    info["debelina_px"] / self.scale)
        pot = filedialog.asksaveasfilename(
            defaultextension=".yaml", initialfile="projekt_iz_slike.yaml",
            filetypes=[("YAML", "*.yaml")])
        if not pot:
            return
        with open(pot, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        messagebox.showinfo(
            "Shranjeno",
            f"Projekt shranjen:\n{pot}\n\nGeneriraj risbo:\n"
            f"python risba.py {os.path.basename(pot)}\n"
            "(nato še popravljaj mere v vmesniku — zaznave so pomožne).")


def ImageFont_nalozi(velikost):
    from PIL import ImageFont
    try:
        return ImageFont.truetype("arial.ttf", velikost)
    except Exception:
        try:
            return ImageFont.load_default(size=velikost)
        except Exception:
            return ImageFont.load_default()


# ---------------------------------------------------------------- glavno
def test_headless(pot, roi=None):
    """Preverjanje zaznavanja brez okna: python merjenje.py slika.jpg --test
    [--roi x0,y0,x1,y1]"""
    pasovi, li = zaznaj_lamele(pot, roi)
    pike, vi = zaznaj_vijake(pot, roi)
    print(f"Slika: {pot} | območje: {roi or 'celotna slika'}")
    fp = lambda v: f"{v:.0f} px" if v else "—"
    print(f"Pasovi (lamele): {li['stevilo']} | debelina ≈ {fp(li['debelina_px'])} | "
          f"pitch ≈ {fp(li['pitch_px'])}")
    print(f"Pike (vijaki/luknje): {vi['stevilo']} | razmak ≈ {fp(vi['razmak_px'])}")
    izhod = os.path.splitext(pot)[0] + "-oznaceno.png"
    oznaci_sliko(pot, pasovi, pike, izhod, roi)
    print(f"Označena slika: {izhod}")


def main():
    pot = None
    roi = None
    test = "--test" in sys.argv
    argv = list(sys.argv[1:])
    if "--roi" in argv:
        i = argv.index("--roi")
        vred = argv[i + 1]
        roi = tuple(float(x) for x in vred.split(","))
        del argv[i:i + 2]
    for a in argv:
        if os.path.isfile(a):
            pot = a
    if test and pot:
        test_headless(pot, roi)
        return
    app = App(pot)
    app.bind("<Escape>", lambda e: app.destroy())
    app.mainloop()


if __name__ == "__main__":
    main()
