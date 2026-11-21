"""Urejevalnik terenske skice (Tkinter) — prazno platno, prostoročno risanje,
sestavljanje elementov in tisk A4/A3.

Ločen vmesnik za dokumentni tip "skica" (terenski_list). Ne uvaža risba/vrata/
razrez — ročne mere so anotacije, nikoli potrjene proizvodne mere.
"""
from __future__ import annotations

import os
import tempfile
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog
from tkinter import ttk

import terenski_list as tl

ORODJA = [
    ("izberi", "Izberi / premakni"),
    ("prostorocno", "Prostoročno"),
    ("radirka", "Radirka"),
    ("crta", "Črta"),
    ("puscica", "Puščica"),
    ("pravokotnik", "Pravokotnik"),
    ("elipsa", "Elipsa"),
    ("besedilo", "Besedilo"),
    ("mera", "Ročna mera"),
    ("kocka", "Izometrična kocka"),
    ("kvader", "Izometrični kvader"),
]

BARVE_KANVAS = {
    "crna": "#000000", "siva": "#777777", "rdeca": "#b22222",
    "modra": "#1f4e9c", "zelena": "#1e7a1e",
}


class Urejevalnik(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Terenski list — skica")
        self.geometry("1150x820")
        self.minsize(900, 650)

        self.dok = tl.nov_dokument()
        self.zgodovina = tl.Zgodovina(self.dok)
        self.pot = None
        self.umazano = False
        self.orodje = tk.StringVar(value="izberi")
        self.barva = tk.StringVar(value="crna")
        self.izbran = None

        # pogled: px na mm in odmik
        self.lestvica = 3.0
        self.ox = 40.0
        self.oy = 760.0
        self._zacetna_tocka = None
        self._zacetni_element = None
        self._zadnja_tocka = None

        self._zgradi_ui()
        self._narisi()
        self.protocol("WM_DELETE_WINDOW", self._zapri)

    # ------------------------------------------------------------------ UI
    def _zgradi_ui(self):
        pas = tk.Frame(self)
        pas.pack(side="top", fill="x", padx=4, pady=2)
        tk.Label(pas, text="Orodje:").pack(side="left")
        for oznaka, opis in ORODJA:
            tk.Radiobutton(pas, text=opis, value=oznaka, variable=self.orodje,
                           indicatoron=False, width=12, pady=2,
                           command=self._zamenjaj_orodje).pack(side="left", padx=1)

        pas2 = tk.Frame(self)
        pas2.pack(side="top", fill="x", padx=4, pady=2)
        tk.Label(pas2, text="Barva:").pack(side="left")
        ttk.Combobox(pas2, textvariable=self.barva, values=list(tl.BARVE),
                     width=8, state="readonly").pack(side="left")
        tk.Button(pas2, text="Razveljavi", command=self._razveljavi).pack(side="left", padx=2)
        tk.Button(pas2, text="Ponovi", command=self._ponovi).pack(side="left")
        tk.Button(pas2, text="Podvoji", command=self._podvoji).pack(side="left", padx=2)
        tk.Button(pas2, text="Zavrti 45°", command=self._zavrti).pack(side="left")
        tk.Button(pas2, text="Večje", command=lambda: self._spremeni(1.25)).pack(side="left", padx=2)
        tk.Button(pas2, text="Manjše", command=lambda: self._spremeni(0.8)).pack(side="left")
        tk.Button(pas2, text="Izbriši", command=self._izbrisi).pack(side="left", padx=2)

        pas3 = tk.Frame(self)
        pas3.pack(side="top", fill="x", padx=4, pady=2)
        tk.Label(pas3, text="Stran:").pack(side="left")
        self.stran = tk.StringVar(value=self.dok["nastavitve"]["stran"])
        ttk.Combobox(pas3, textvariable=self.stran, values=list(tl.STRANI),
                     width=5, state="readonly").pack(side="left")
        tk.Label(pas3, text="Orientacija:").pack(side="left")
        self.orientacija = tk.StringVar(value=self.dok["nastavitve"]["orientacija"])
        ttk.Combobox(pas3, textvariable=self.orientacija, values=list(tl.ORIENTACIJE),
                     width=10, state="readonly").pack(side="left")
        tk.Label(pas3, text="Merilo:").pack(side="left")
        self.merilo = tk.StringVar(value=self.dok["nastavitve"]["merilo"])
        ttk.Combobox(pas3, textvariable=self.merilo, values=list(tl.MERILA),
                     width=10, state="readonly").pack(side="left")
        self.mreza = tk.BooleanVar(value=False)
        self.vodila = tk.BooleanVar(value=False)
        self.okvir = tk.BooleanVar(value=False)
        tk.Checkbutton(pas3, text="Mreža", variable=self.mreza,
                       command=self._nastavitve).pack(side="left")
        tk.Checkbutton(pas3, text="Vodila", variable=self.vodila,
                       command=self._nastavitve).pack(side="left")
        tk.Checkbutton(pas3, text="Okvir", variable=self.okvir,
                       command=self._nastavitve).pack(side="left")

        pas4 = tk.Frame(self)
        pas4.pack(side="top", fill="x", padx=4, pady=2)
        for bes, ukaz in [("Nova", self._nova), ("Odpri…", self._odpri),
                          ("Shrani", self._shrani), ("Shrani kot…", self._shrani_kot),
                          ("PDF…", self._pdf), ("Predogled", self._predogled),
                          ("Tiskaj", self._tiskaj)]:
            tk.Button(pas4, text=bes, command=ukaz).pack(side="left", padx=2)

        self.platno = tk.Canvas(self, bg="white", highlightthickness=1,
                                highlightbackground="#888888")
        self.platno.pack(fill="both", expand=True, padx=4, pady=4)
        self.platno.bind("<ButtonPress-1>", self._na_pritisk)
        self.platno.bind("<B1-Motion>", self._na_premik)
        self.platno.bind("<ButtonRelease-1>", self._na_oddajo)
        self.platno.bind("<MouseWheel>", self._na_kolesce)
        self.platno.bind("<Button-2>", self._na_pritisk_premik)
        self.platno.bind("<B2-Motion>", self._na_premik_premik)

        self.status = tk.Label(self, anchor="w",
                               text="Ročne mere so anotacije skice — niso potrjene "
                                    "proizvodne mere. Ctrl+Z razveljavi.")
        self.status.pack(side="bottom", fill="x")
        self.bind("<Control-z>", lambda e: self._razveljavi())
        self.bind("<Control-y>", lambda e: self._ponovi())
        self.bind("<Delete>", lambda e: self._izbrisi())

    def _zamenjaj_orodje(self):
        self.izbran = None
        self._narisi()

    # ------------------------------------------------------------ koordinate
    def _v_svet(self, sx, sy):
        return ((sx - self.ox) / self.lestvica, (self.oy - sy) / self.lestvica)

    def _v_platno(self, x, y):
        return (self.ox + x * self.lestvica, self.oy - y * self.lestvica)

    # --------------------------------------------------------------- risanje
    def _narisi(self):
        p = self.platno
        p.delete("all")
        nast = self.dok["nastavitve"]
        s, v = tl.dimenzije_strani(nast["stran"], nast["orientacija"])
        x0, y0 = self._v_platno(0, 0)
        x1, y1 = self._v_platno(s, v)
        p.create_rectangle(x0, y1, x1, y0, outline="#444444", fill="#fdfdfd")
        if nast.get("mreza"):
            for gx in tl.frange(0, s, tl.MREZA_MM):
                a, b = self._v_platno(gx, 0)
                _, c = self._v_platno(gx, v)
                p.create_line(a, b, a, c, fill="#e4e4e4")
            for gy in tl.frange(0, v, tl.MREZA_MM):
                a, b = self._v_platno(0, gy)
                c, _ = self._v_platno(s, gy)
                p.create_line(a, b, c, b, fill="#e4e4e4")
        if nast.get("vodila"):
            a, b = self._v_platno(s / 2, 0)
            _, c = self._v_platno(s / 2, v)
            p.create_line(a, b, a, c, fill="#99bbdd", dash=(4, 4))
            a, b = self._v_platno(0, v / 2)
            c, _ = self._v_platno(s, v / 2)
            p.create_line(a, b, c, b, fill="#99bbdd", dash=(4, 4))
        if nast.get("okvir"):
            p.create_rectangle(self._v_platno(5, v - 5)[0], self._v_platno(5, v - 5)[1],
                               self._v_platno(s - 5, 5)[0], self._v_platno(s - 5, 5)[1],
                               outline="#000000")
        for i, el in enumerate(self.dok["elementi"]):
            barva = BARVE_KANVAS.get(el.get("barva", "crna"), "#000000")
            if self.izbran == i:
                barva = "#d05050"
            self._narisi_element(p, el, barva)
        if self.izbran is not None and self.izbran < len(self.dok["elementi"]):
            xmn, ymn, xmx, ymx = tl.element_meje(self.dok["elementi"][self.izbran])
            ax, ay = self._v_platno(xmn, ymx)
            bx, by = self._v_platno(xmx, ymn)
            p.create_rectangle(ax, ay, bx, by, outline="#d05050", dash=(3, 3))

    def _narisi_element(self, p, el, barva):
        tip = el["tip"]
        if tip == "poteza":
            tocke = [t for pt in el["tocke"] for t in self._v_platno(*pt)]
            p.create_line(*tocke, fill=barva, width=max(1, el["sirina"] * self.lestvica),
                          smooth=True)
        elif tip in ("crta", "puscica"):
            ax, ay = self._v_platno(*el["a"])
            bx, by = self._v_platno(*el["b"])
            p.create_line(ax, ay, bx, by, fill=barva,
                          width=max(1, el["sirina"] * self.lestvica))
            if tip == "puscica":
                self._glava(p, ax, ay, bx, by, barva)
        elif tip == "mera":
            ax, ay = self._v_platno(*el["a"])
            bx, by = self._v_platno(*el["b"])
            p.create_line(ax, ay, bx, by, fill=barva, width=1)
            self._glava(p, ax, ay, bx, by, barva)
            self._glava(p, bx, by, ax, ay, barva)
            p.create_text((ax + bx) / 2, (ay + by) / 2 - 12,
                          text=f"{el['vsebina']} {tl.OZNAKA_ROCNO}",
                          fill=barva, font=("TkDefaultFont", 9))
        elif tip == "pravokotnik":
            ax, ay = self._v_platno(el["x"], el["y"] + el["visina"])
            bx, by = self._v_platno(el["x"] + el["sirina"], el["y"])
            p.create_rectangle(ax, ay, bx, by, outline=barva)
        elif tip == "elipsa":
            ax, ay = self._v_platno(el["x"], el["y"] + el["visina"])
            bx, by = self._v_platno(el["x"] + el["sirina"], el["y"])
            p.create_oval(ax, ay, bx, by, outline=barva)
        elif tip == "besedilo":
            ax, ay = self._v_platno(el["x"], el["y"])
            p.create_text(ax, ay, text=el["vsebina"], fill=barva, anchor="sw",
                          font=("TkDefaultFont", int(max(7, el["visina"] * self.lestvica))))
        elif tip in ("kocka", "kvader"):
            a = el["a"]
            b = el.get("b", el["a"])
            c = el.get("c", el["a"])
            for crta_tocke in tl.tocke_kvader_odseki(el["x"], el["y"], a, b, c):
                ax, ay = self._v_platno(*crta_tocke[0])
                bx, by = self._v_platno(*crta_tocke[1])
                p.create_line(ax, ay, bx, by, fill=barva)

    @staticmethod
    def _glava(p, ax, ay, bx, by, barva):
        import math
        dx, dy = bx - ax, by - ay
        d = math.hypot(dx, dy)
        if d == 0:
            return
        u = 8.0
        ux, uy = dx / d, dy / d
        px, py = -uy, ux
        p.create_polygon(ax, ay,
                         ax + ux * u + px * u / 2.5, ay + uy * u + py * u / 2.5,
                         ax + ux * u - px * u / 2.5, ay + uy * u - py * u / 2.5,
                         fill=barva, outline=barva)

    # ------------------------------------------------------------ vnos dogodkov
    def _na_pritisk(self, dog):
        x, y = self._v_svet(dog.x, dog.y)
        orodje = self.orodje.get()
        if orodje == "izberi":
            self.izbran = tl.zadetek(self.dok, x, y)
            self._zacetna_tocka = (x, y)
            if self.izbran is not None:
                self._zacetni_element = self.dok["elementi"][self.izbran]
            self._narisi()
        elif orodje == "radirka":
            zadetek = tl.zadetek(self.dok, x, y)
            if zadetek is not None:
                del self.dok["elementi"][zadetek]
                self._zapomni()
        else:
            self._zacetna_tocka = (x, y)
            self._zadnja_tocka = (x, y)

    def _na_premik(self, dog):
        x, y = self._v_svet(dog.x, dog.y)
        orodje = self.orodje.get()
        if orodje == "izberi" and self.izbran is not None and self._zacetna_tocka:
            dx = x - self._zacetna_tocka[0]
            dy = y - self._zacetna_tocka[1]
            self.dok["elementi"][self.izbran] = tl.premakni(self._zacetni_element, dx, dy)
            self._narisi()
        elif orodje == "prostorocno" and self._zadnja_tocka:
            oris = self.platno
            ax, ay = self._v_platno(*self._zadnja_tocka)
            bx, by = self._v_platno(x, y)
            oris.create_line(ax, ay, bx, by, fill=BARVE_KANVAS[self.barva.get()],
                             width=max(1, 0.5 * self.lestvica))
            if self._zacetna_tocka == self._zadnja_tocka:
                self._zacetna_tocka = [self._zadnja_tocka, (x, y)]
            else:
                self._zacetna_tocka.append((x, y))
            self._zadnja_tocka = (x, y)

    def _na_oddajo(self, dog):
        x, y = self._v_svet(dog.x, dog.y)
        orodje = self.orodje.get()
        zacetek = self._zacetna_tocka
        self._zacetna_tocka = None
        self._zadnja_tocka = None
        if orodje == "izberi":
            if self.izbran is not None:
                self._zapomni()
            self._zacetni_element = None
            return
        if orodje == "prostorocno":
            if isinstance(zacetek, list) and len(zacetek) >= 2:
                self.dok["elementi"].append(
                    tl.poteza(zacetek, barva=self.barva.get()))
                self._zapomni()
            return
        if zacetek is None:
            return
        if abs(x - zacetek[0]) < 0.5 and abs(y - zacetek[1]) < 0.5:
            if orodje == "besedilo":
                vsebina = simpledialog.askstring("Besedilo", "Vsebina:",
                                                 parent=self)
                if vsebina:
                    self.dok["elementi"].append(
                        tl.besedilo(x, y, vsebina, barva=self.barva.get()))
                    self._zapomni()
            return
        try:
            if orodje == "crta":
                self.dok["elementi"].append(
                    tl.crta(zacetek, (x, y), barva=self.barva.get()))
            elif orodje == "puscica":
                self.dok["elementi"].append(
                    tl.puscica(zacetek, (x, y), barva=self.barva.get()))
            elif orodje == "mera":
                vsebina = simpledialog.askstring(
                    "Ročna mera", "Oznaka mere (ročni vnos):", parent=self)
                self.dok["elementi"].append(
                    tl.mera(zacetek, (x, y), vsebina, barva=self.barva.get()))
            elif orodje == "pravokotnik":
                self.dok["elementi"].append(
                    tl.pravokotnik(min(zacetek[0], x), min(zacetek[1], y),
                                   abs(x - zacetek[0]), abs(y - zacetek[1]),
                                   barva=self.barva.get()))
            elif orodje == "elipsa":
                self.dok["elementi"].append(
                    tl.elipsa(min(zacetek[0], x), min(zacetek[1], y),
                              abs(x - zacetek[0]), abs(y - zacetek[1]),
                              barva=self.barva.get()))
            elif orodje == "kocka":
                a = max(abs(x - zacetek[0]), abs(y - zacetek[1])) / 1.5
                self.dok["elementi"].append(
                    tl.kocka(min(zacetek[0], x), min(zacetek[1], y),
                             max(2.0, a), barva=self.barva.get()))
            elif orodje == "kvader":
                self.dok["elementi"].append(
                    tl.kvader(min(zacetek[0], x), min(zacetek[1], y),
                              max(2.0, abs(x - zacetek[0]) / 1.8),
                              max(2.0, abs(x - zacetek[0]) / 3.0),
                              max(2.0, abs(y - zacetek[1])),
                              barva=self.barva.get()))
            else:
                return
            self._zapomni()
        except ValueError as e:
            messagebox.showerror("Element", str(e), parent=self)

    def _na_kolesce(self, dog):
        faktor = 1.1 if dog.delta > 0 else 1 / 1.1
        self.lestvica = max(0.4, min(20.0, self.lestvica * faktor))
        self._narisi()

    def _na_pritisk_premik(self, dog):
        self._zacetna_tocka = (dog.x, dog.y)

    def _na_premik_premik(self, dog):
        if self._zacetna_tocka:
            self.ox += dog.x - self._zacetna_tocka[0]
            self.oy += dog.y - self._zacetna_tocka[1]
            self._zacetna_tocka = (dog.x, dog.y)
            self._narisi()

    # -------------------------------------------------------------- operacije
    def _zapomni(self):
        self.zgodovina.zapomni(self.dok)
        self.umazano = True
        self._narisi()

    def _razveljavi(self):
        stanje = self.zgodovina.razveljavi()
        if stanje is not None:
            self.dok = stanje
            self.izbran = None
            self.umazano = True
            self._narisi()

    def _ponovi(self):
        stanje = self.zgodovina.ponovi()
        if stanje is not None:
            self.dok = stanje
            self.izbran = None
            self.umazano = True
            self._narisi()

    def _izbrani(self):
        if self.izbran is None or self.izbran >= len(self.dok["elementi"]):
            messagebox.showinfo("Izbira", "Najprej izberi element (orodje Izberi).",
                                parent=self)
            return None
        return self.dok["elementi"][self.izbran]

    def _izbrisi(self):
        el = self._izbrani()
        if el is not None:
            del self.dok["elementi"][self.izbran]
            self.izbran = None
            self._zapomni()

    def _podvoji(self):
        el = self._izbrani()
        if el is not None:
            self.dok["elementi"].append(tl.podvoji(el))
            self._zapomni()

    def _zavrti(self):
        el = self._izbrani()
        if el is not None:
            self.dok["elementi"][self.izbran] = tl.zavrti(el, 45.0)
            self._zapomni()

    def _spremeni(self, faktor):
        el = self._izbrani()
        if el is not None:
            self.dok["elementi"][self.izbran] = tl.povecaj(el, faktor)
            self._zapomni()

    def _nastavitve(self):
        nast = self.dok["nastavitve"]
        nast["stran"] = self.stran.get()
        nast["orientacija"] = self.orientacija.get()
        nast["merilo"] = self.merilo.get()
        nast["mreza"] = self.mreza.get()
        nast["vodila"] = self.vodila.get()
        nast["okvir"] = self.okvir.get()
        self.umazano = True
        self._narisi()

    # -------------------------------------------------------------- datoteke
    def _preveri_neshranjeno(self):
        if not self.umazano:
            return True
        odgovor = messagebox.askyesnocancel(
            "Neshranjene spremembe", "Shranim spremembe?", parent=self)
        if odgovor is None:
            return False
        if odgovor:
            return self._shrani()
        return True

    def _nova(self):
        if not self._preveri_neshranjeno():
            return
        self.dok = tl.nov_dokument(self.stran.get(), self.orientacija.get())
        self.zgodovina = tl.Zgodovina(self.dok)
        self.pot = None
        self.umazano = False
        self.izbran = None
        self._narisi()

    def _odpri(self):
        if not self._preveri_neshranjeno():
            return
        pot = filedialog.askopenfilename(
            parent=self, filetypes=[("Skica terenskega lista", "*.yaml *.yml")])
        if not pot:
            return
        try:
            self.dok = tl.nalozi(pot)
        except Exception as e:
            messagebox.showerror("Odpiranje", f"Dokumenta ni mogoče odpreti:\n{e}",
                                 parent=self)
            return
        self.zgodovina = tl.Zgodovina(self.dok)
        self.pot = pot
        self.umazano = False
        self.izbran = None
        self._sinhroniziraj_nastavitve()
        self._narisi()

    def _sinhroniziraj_nastavitve(self):
        nast = self.dok["nastavitve"]
        self.stran.set(nast["stran"])
        self.orientacija.set(nast["orientacija"])
        self.merilo.set(nast["merilo"])
        self.mreza.set(nast.get("mreza", False))
        self.vodila.set(nast.get("vodila", False))
        self.okvir.set(nast.get("okvir", False))

    def _shrani(self):
        if self.pot is None:
            return self._shrani_kot()
        try:
            tl.shrani(self.dok, self.pot)
        except Exception as e:
            messagebox.showerror("Shranjevanje", str(e), parent=self)
            return False
        self.umazano = False
        self.status.config(text=f"Shranjeno: {self.pot}")
        return True

    def _shrani_kot(self):
        pot = filedialog.asksaveasfilename(
            parent=self, defaultextension=".yaml",
            filetypes=[("Skica terenskega lista", "*.yaml")])
        if not pot:
            return False
        self.pot = pot
        return self._shrani()

    def _pdf(self):
        self._nastavitve()
        pot = filedialog.asksaveasfilename(
            parent=self, defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")])
        if not pot:
            return
        try:
            st = tl.izvozi_pdf(self.dok, pot)
        except Exception as e:
            messagebox.showerror("PDF", f"Izvoz ni uspel:\n{e}", parent=self)
            return
        self.status.config(text=f"PDF: {pot} ({st} strani)")
        messagebox.showinfo("PDF", f"Izvoženo: {pot} ({st} strani)", parent=self)

    def _predogled(self):
        self._nastavitve()
        pot = os.path.join(tempfile.gettempdir(), "terenski_predogled.png")
        try:
            tl.predogled_png(self.dok, pot)
        except Exception as e:
            messagebox.showerror("Predogled", str(e), parent=self)
            return
        okno = tk.Toplevel(self)
        okno.title("Predogled strani 1 (isti izris kot PDF)")
        slika = tk.PhotoImage(file=pot)
        oznaka = tk.Label(okno, image=slika)
        oznaka.image = slika
        oznaka.pack()

    def _tiskaj(self):
        self._nastavitve()
        pot = os.path.join(tempfile.gettempdir(), "terenski_tisk.pdf")
        try:
            tl.izvozi_pdf(self.dok, pot)
            tl.tiskaj_pdf(pot)
        except Exception as e:
            messagebox.showerror("Tiskanje", str(e), parent=self)
            return
        self.status.config(
            text=f"Poslano v sistemski tisk: {pot} — preveri tudi fizični izpis.")

    def _zapri(self):
        if self._preveri_neshranjeno():
            self.destroy()


def zazeni():
    app = Urejevalnik()
    app.mainloop()


if __name__ == "__main__":
    zazeni()