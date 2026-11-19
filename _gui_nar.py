# -*- coding: utf-8 -*-
"""Popravek narocilo spojev + GUI gumba (naročilo kopiraj, odpisi ostankov)."""
NL = chr(10)      # pravi premik v novo vrstico
BS = chr(92)      # backslash

# ============================ risba.py ============================
pot = "risba.py"
k = open(pot, encoding="utf-8").read()

staro = ('    "narocilo": "' + NL + '".join(nar),')
novo = ('    "narocilo": "' + BS + 'n".join(nar),')
print("pokvarjenih spojev:", k.count(staro))
assert k.count(staro) == 2, "pričakovana 2 pokvarjena spoja"
k = k.replace(staro, novo)

open(pot, "w", encoding="utf-8").write(k)
print("risba.py: spoji popavljeni")

# ============================ vmesnik.py ============================
pot = "vmesnik.py"
k = open(pot, encoding="utf-8").read()

# gumba v vrstico gumbov (fb)
staro = '''        ttk.Button(fb, text="SHRANI PROJEKT (.yaml)",
                   command=self._shrani_projekt).pack(side="right")'''
novo = '''        self.btn_nar = ttk.Button(fb, text="NAROČILO (kopiraj)",
                                  state="disabled", command=self._narocilo_kopiraj)
        self.btn_nar.pack(side="right", padx=8)
        self.btn_ost = ttk.Button(fb, text="ODPIŠI OSTANKE", state="disabled",
                                  command=self._odpisi_ostanke)
        self.btn_ost.pack(side="right")
        ttk.Button(fb, text="SHRANI PROJEKT (.yaml)",
                   command=self._shrani_projekt).pack(side="right")'''
assert staro in k, "gumbi fb"
k = k.replace(staro, novo)

# stanje + shranjevanje kolicin iz _narisi_nit/_koncano
staro = '''    def _narisi_nit(self, cfg):
        try:
            izhod, png, _png2 = risba.generiraj(cfg, dpi_png=120)
        except ValueError as e:
            self.after(0, self._napaka, str(e))
            return
        except Exception as e:
            self.after(0, self._napaka, f"Nepričakovana napaka: {e}")
            return
        self.after(0, self._koncano, izhod, png)'''
novo = '''    def _narisi_nit(self, cfg):
        try:
            izhod, png, dodatni, kolicine = risba.generiraj(cfg, dpi_png=120)
        except ValueError as e:
            self.after(0, self._napaka, str(e))
            return
        except Exception as e:
            self.after(0, self._napaka, f"Nepričakovana napaka: {e}")
            return
        self.after(0, self._koncano, izhod, png, dodatni, kolicine)'''
assert staro in k, "_narisi_nit"
k = k.replace(staro, novo)

staro = '''    def _koncano(self, izhod, png):
        self.pdf_pot = izhod
        self.png_pot = png
        self.btn_pdf.config(state="normal")
        self.btn_cel.config(state="normal")
        self.btn_narisi.config(state="normal", text="NARIŠI RISBO")'''
novo = '''    def _koncano(self, izhod, png, dodatni, kolicine):
        self.pdf_pot = izhod
        self.png_pot = png
        self.kolicine = kolicine
        self.btn_pdf.config(state="normal")
        self.btn_cel.config(state="normal")
        if kolicine and kolicine.get("narocilo"):
            self.btn_nar.config(state="normal")
            self.btn_ost.config(state="normal")
        self.btn_narisi.config(state="normal", text="NARIŠI RISBO")'''
assert staro in k, "_koncano"
k = k.replace(staro, novo)

# dodatni dokumenti v statusni vrstici
staro = '''        self.status.config(text=f"Napisano: {os.path.basename(izhod)} "
                                f"• nastavitve samodejno shranjene",
                           fg="#1b5e20")
        self._shrani_zadnje()'''
novo = '''        dok = " + ".join(os.path.basename(p) for p in dodatni)
        self.status.config(text=f"Napisano: {os.path.basename(izhod)} • {dok} "
                                f"• nastavitve samodejno shranjene",
                           fg="#1b5e20")
        self._shrani_zadnje()'''
assert staro in k, "status dodatni"
k = k.replace(staro, novo)

# obdelovalne metode
staro = '''    def _odpri_pdf(self):
        if self.pdf_pot:
            os.startfile(self.pdf_pot)'''
novo = '''    def _narocilo_kopiraj(self):
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
            risba.shrani_ostanke(self.kolicine["ostanki_posodobitev"])
        except Exception as e:
            messagebox.showerror("Ostanki", f"Napaka pri shranjevanju: {e}")
            return
        self.kolicine["ostanki_posodobitev"] = None
        self.btn_ost.config(state="disabled")
        messagebox.showinfo(
            "Ostanki", "Porabljeni ostanki so odpisani iz ostanki.yaml "
            "(v mapi programa).")

    def _odpri_pdf(self):
        if self.pdf_pot:
            os.startfile(self.pdf_pot)'''
assert staro in k, "metode"
k = k.replace(staro, novo)

# stanje na začetku
staro = '''        self.pdf_pot = None
        self.png_pot = None'''
novo = '''        self.pdf_pot = None
        self.png_pot = None
        self.kolicine = None'''
assert staro in k, "stanje"
k = k.replace(staro, novo)

open(pot, "w", encoding="utf-8").write(k)
print("vmesnik.py: gumba NAROČILO/ODPIŠI OSTANKE OK")
