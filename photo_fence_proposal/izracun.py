"""photo_fence_proposal — predračun iz kosovnice (brez AI, lokalno).

Poveže kosovnico (`material.py`) s cenikom `cene.yaml` iz korena projekta.

PRAVILA POŠTENOSTI (enaka kot v glavnem programu):
- cene se NE izmišljajo: če ključa v ceniku ni ali je prazen, je postavka
  »cena po dogovoru« (znesek None) — nikoli ničla, ki bi bila videti kot cena;
- postavke, ki jih kosovnica ne vsebuje (sidra, osnove, nosilci), se ne
  prištejejo tiho — javijo se kot opozorilo, da jih monter doda ročno;
- količine, izpeljane iz nepotrjenih mer, so označene INFORMATIVNO;
- predračun iz fotografije ni ponudba: dokument to pove v glavi in nogi.

Uporaba:
    import izracun
    p = izracun.sestavi(rezultat, izracun.preberi_cenik("../cene.yaml"))
    izracun.narisi_predracun(p, rezultat, "07-predracun.pdf")
"""
from __future__ import annotations

import csv
import datetime
from dataclasses import dataclass
from pathlib import Path

from model import (IZMERJENO, IZRACUNANO, NEZNANO, OCENJENO, Rezultat)

# ključi iz cene.yaml, ki jih ta modul zna uporabiti
KLJUC_WPC = "wpc_deska_m"      # EUR/m porabe desk
KLJUC_ALU = "alu_m"            # EUR/m profilov (stebri)
KLJUC_VIJAK = "vijak_kos"      # EUR/kos
KLJUC_URE = "dela_ure"         # ure montaže
KLJUC_URA_CENA = "dela_ur_cena"

# enaka hevristika kot material.py: steber + 200 mm za betoniranje
DODATEK_STEBRA_MM = 200.0

STATUSI_POTRJENI = (IZMERJENO, IZRACUNANO)


def preberi_cenik(pot: str | Path | None) -> dict[str, float]:
    """Preberi preprost cenik ``kljuc: vrednost  # komentar``.

    Vrne samo numerične vrednosti > 0; vse ostalo (kometarji, besedilo,
    prazne vrednosti) se preskoči. Manjkajoča datoteka vrne prazen slovar
    — klicatelj mora povedati, da cenika ni (brez tihe ničle).
    """
    if pot is None:
        return {}
    p = Path(pot)
    if not p.is_file():
        return {}
    cenik: dict[str, float] = {}
    for vrstica in p.read_text(encoding="utf-8").splitlines():
        vrstica = vrstica.split("#", 1)[0].strip()
        if not vrstica or ":" not in vrstica:
            continue
        kljuc, vrednost = vrstica.split(":", 1)
        try:
            stevilo = float(vrednost.strip().replace(",", "."))
        except ValueError:
            continue
        if stevilo > 0:
            cenik[kljuc.strip()] = stevilo
    return cenik


@dataclass
class Vrstica:
    """Ena postavka predračuna."""

    naziv: str
    kolicina: float | None
    enota: str
    cena_enote: float | None
    znesek: float | None
    status: str
    opomba: str = ""


@dataclass
class Predracun:
    """Predračun: postavke + seštevki + poštena opozorila."""

    vrstice: list[Vrstica]
    skupaj_material: float
    skupaj_delo: float | None
    manjkajoce_cene: list[str]
    opozorila: list[str]
    informativno: bool

    @property
    def skupaj(self) -> float | None:
        """Skupni znesek ali None, če katera cena manjka (ni izmišljena)."""
        if self.manjkajoce_cene:
            return None
        return self.skupaj_material + (self.skupaj_delo or 0.0)

    def povzetek(self) -> str:
        v = ["PREDRAČUN (iz fotografije — informativno):"]
        for r in self.vrstice:
            kol = f"{r.kolicina:.2f} {r.enota}" if r.kolicina is not None else "??"
            cena = (f"{r.cena_enote:.2f} EUR/{r.enota}"
                    if r.cena_enote is not None else "cena po dogovoru")
            znesek = f"{r.znesek:.2f} EUR" if r.znesek is not None else "—"
            v.append(f"  {r.naziv}: {kol} · {cena} · {znesek} [{r.status}]")
        skupaj = (f"{self.skupaj:.2f} EUR" if self.skupaj is not None
                  else "ni izračunan (manjkajoče cene: "
                       + ", ".join(self.manjkajoce_cene) + ")")
        v.append(f"  SKUPAJ: {skupaj}")
        if self.informativno:
            v.append("  OZNAKA: INFORMATIVNO — mere iz fotografije niso potrjene.")
        for o in self.opozorila:
            v.append(f"  opozorilo: {o}")
        return "\n".join(v)


def _cena(cenik: dict[str, float], kljuc: str) -> float | None:
    v = cenik.get(kljuc)
    return v if v and v > 0 else None


def _vrstica(naziv: str, kolicina: float | None, enota: str,
             cena_enote: float | None, status: str,
             opomba: str = "") -> Vrstica:
    znesek = (kolicina * cena_enote
              if (kolicina is not None and cena_enote is not None) else None)
    return Vrstica(naziv, kolicina, enota, cena_enote, znesek, status, opomba)


def _dolzina_kosa_mm(rezultat: Rezultat) -> float | None:
    """Dolžina ene lamele: pri vodoravnih = dolžina ograje, sicer višina."""
    mere = rezultat.mere
    kljuc = ("dolzina_ograje"
             if rezultat.parametri.tip == "wpc_vodoravne_lamele"
             else "visina_ograje")
    mera = mere.get(kljuc)
    return mera.vrednost_mm if mera and mera.vrednost_mm else None


def sestavi(rezultat: Rezultat, cenik: dict[str, float]) -> Predracun:
    """Sestavi predračun iz kosovnice in cenika (brez izmišljanja cen)."""
    vrstice: list[Vrstica] = []
    manjkajoce: list[str] = []
    opozorila: list[str] = []

    def dodaj(naziv, kolicina, enota, kljuc, status, opomba="",
              faktor_mm=None):
        """Dodaj postavko; pri faktor_mm je količina = kos × mm / 1000."""
        kol = (kolicina * faktor_mm / 1000.0
               if (kolicina is not None and faktor_mm) else kolicina)
        cena = _cena(cenik, kljuc)
        if cena is None:
            manjkajoce.append(kljuc)
        vrstice.append(_vrstica(naziv, kol, enota, cena, status, opomba))
        return vrstice[-1]

    lamela = next((p for p in rezultat.kosovnica
                   if p.naziv == "WPC lamela/deska"), None)
    steber = next((p for p in rezultat.kosovnica
                   if p.naziv == "Steber"), None)
    vijaki = next((p for p in rezultat.kosovnica
                   if p.naziv == "Vijaki M8×70"), None)

    if lamela is not None:
        kos_mm = _dolzina_kosa_mm(rezultat)
        if kos_mm and lamela.kolicina:
            dodaj("WPC lamele", lamela.kolicina, "m", KLJUC_WPC,
                  lamela.status_mer,
                  f"{lamela.kolicina:.0f} kos × {kos_mm:.0f} mm",
                  faktor_mm=kos_mm)
        else:
            dodaj("WPC lamele", None, "m", KLJUC_WPC, NEZNANO,
                  "dolžina kosa ni znana")
    else:
        opozorila.append("Kosovnica nima postavke lamel — materiala ni "
                         "mogoče ovrednotiti.")

    if steber is not None:
        vis = rezultat.mere.get("visina_ograje")
        vis_mm = (vis.vrednost_mm + DODATEK_STEBRA_MM) if (
            vis and vis.vrednost_mm) else None
        if vis_mm and steber.kolicina:
            dodaj("Aluminijasti stebri", steber.kolicina, "m",
                  KLJUC_ALU, steber.status_mer,
                  f"{steber.kolicina:.0f} kos × {vis_mm:.0f} mm",
                  faktor_mm=vis_mm)
        else:
            dodaj("Aluminijasti stebri", None, "m", KLJUC_ALU, NEZNANO,
                  "višina stebra ni znana")

    if vijaki is not None and vijaki.kolicina:
        dodaj("Vijaki M8×70", vijaki.kolicina, "kos", KLJUC_VIJAK,
              vijaki.status_mer, vijaki.opomba)

    opozorila.append(
        "Sidra, osnove stebrov, nosilci in zaključni profili niso v "
        "kosovnici — dodaj jih ročno, preden predračun pošlješ stranki.")

    delo = None
    ur, cena_ure = _cena(cenik, KLJUC_URE), _cena(cenik, KLJUC_URA_CENA)
    if ur and cena_ure:
        vrstice.append(_vrstica("Delo — montaža", ur, "h", cena_ure,
                                OCENJENO, "ocena ur iz cenika"))
        delo = ur * cena_ure
    else:
        opozorila.append("Cenik ne vsebuje ur/ure dela — delo ni "
                         "obračunano.")

    material = sum(v.znesek for v in vrstice
                   if v is not None and v.znesek is not None
                   and v.naziv != "Delo — montaža")
    informativno = (not rezultat.vse_kljucne_mere_potrjene
                    or any(r.status not in STATUSI_POTRJENI for r in vrstice))
    # zaznava, ki ji ne verjamemo (zavržene mere, napačen razmak), ne sme
    # zgledati kot uporaben izračun — tudi če so cene iz cenika
    nezanesljiva = any(("ni fizično verodostojna" in o.lower())
                       or ("niso stebri" in o.lower())
                       for o in rezultat.opozorila)
    if nezanesljiva:
        informativno = True
        opozorila.append("Zaznava ni uporabna — znesek je le groba ocena, "
                         "ni podlaga za ponudbo.")
    if informativno:
        opozorila.append("Mere iz fotografije niso potrjene — znesek je "
                         "informativne narave, ne ponudba.")
    return Predracun(vrstice, material, delo, sorted(set(manjkajoce)),
                     opozorila, informativno)


def _eur(v: float | None) -> str:
    """Znesek v slovenskem zapisu (1 234,56)."""
    if v is None:
        return "—"
    return f"{v:,.2f}".replace(",", " ").replace(".", ",")


def izvozi_csv(p: Predracun, pot: str | Path) -> str:
    """Zapiši predračun v CSV."""
    with open(pot, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Naziv", "Kolicina", "Enota", "Cena_enote_EUR",
                    "Znesek_EUR", "Status", "Opomba"])
        for r in p.vrstice:
            w.writerow([r.naziv,
                        "" if r.kolicina is None else f"{r.kolicina:.2f}",
                        r.enota,
                        "" if r.cena_enote is None else f"{r.cena_enote:.2f}",
                        "" if r.znesek is None else f"{r.znesek:.2f}",
                        r.status, r.opomba])
        w.writerow([])
        w.writerow(["Material skupaj", "", "", "",
                    f"{p.skupaj_material:.2f}", "", ""])
        if p.skupaj_delo is not None:
            w.writerow(["Delo skupaj", "", "", "",
                        f"{p.skupaj_delo:.2f}", "", ""])
        w.writerow(["SKUPAJ", "", "", "",
                    "" if p.skupaj is None else f"{p.skupaj:.2f}",
                    "informativno" if p.informativno else "potrjeno",
                    ", ".join(p.manjkajoce_cene)])
    return str(pot)


def narisi_predracun(p: Predracun, rezultat: Rezultat, pot_pdf: str | Path,
                     *, podjetje: str = "", stranka: str = "",
                     objekt: str = "", datum: str | None = None) -> str:
    """Nariši A4 predračun (matplotlib) — brez izmišljenih cen."""
    import textwrap

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(8.27, 11.69))      # A4 pokončno
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_xlim(0, 210)
    ax.set_ylim(0, 297)
    ax.axis("off")

    datum = datum or datetime.date.today().strftime("%d.%m.%Y")
    podjetje_txt = podjetje or "—"
    stranka_txt = stranka or "—"
    objekt_txt = objekt or "—"

    # ---- glava ----
    ax.add_patch(plt.Rectangle((12, 266), 186, 22, facecolor="#eceff1",
                               edgecolor="#90a4ae", lw=0.8))
    ax.text(16, 281, podjetje_txt, fontsize=13, fontweight="bold",
            va="center")
    ax.text(16, 272, "PREDRAČUN — INFORMATIVNI IZRAČUN IZ FOTOGRAFIJE",
            fontsize=9, va="center", color="#37474f")
    ax.text(194, 281, f"Datum: {datum}", fontsize=9, ha="right",
            va="center")
    oznaka_mer = ("INFORMATIVNE" if p.informativno else "potrjene")
    ax.text(194, 272, f"Mere: {oznaka_mer}", fontsize=8, ha="right",
            va="center", color="#546e7a")

    ax.text(12, 258, f"Stranka: {stranka_txt}", fontsize=9)
    ax.text(12, 252, f"Objekt: {objekt_txt}", fontsize=9)

    # ---- tabela ----
    glava_y = 240.0
    ax.text(16, glava_y, "Postavka", fontsize=8, fontweight="bold")
    ax.text(96, glava_y, "Količina", fontsize=8, fontweight="bold",
            ha="right")
    ax.text(110, glava_y, "Enota", fontsize=8, fontweight="bold")
    ax.text(140, glava_y, "Cena/eno", fontsize=8, fontweight="bold",
            ha="right")
    ax.text(172, glava_y, "Znesek", fontsize=8, fontweight="bold",
            ha="right")
    ax.text(176, glava_y, "Status", fontsize=8, fontweight="bold")
    ax.plot([12, 198], [glava_y - 2, glava_y - 2], color="#90a4ae", lw=0.7)

    y = glava_y - 9
    for r in p.vrstice:
        ax.text(16, y, r.naziv, fontsize=8)
        ax.text(96, y, _eur(r.kolicina) if r.kolicina is not None else "??",
                fontsize=8, ha="right")
        ax.text(110, y, r.enota, fontsize=8)
        ax.text(140, y,
                (_eur(r.cena_enote) + " EUR") if r.cena_enote is not None
                else "po dogovoru", fontsize=8, ha="right")
        ax.text(172, y, _eur(r.znesek), fontsize=8, ha="right",
                fontweight="bold")
        ax.text(176, y, r.status, fontsize=7, color="#546e7a")
        if r.opomba:
            ax.text(16, y - 3.6, r.opomba, fontsize=6.5, color="#607d8b")
            y -= 9.0
        else:
            y -= 7.0

    y -= 2
    ax.plot([12, 198], [y, y], color="#90a4ae", lw=0.7)
    y -= 8
    ax.text(140, y, "Material skupaj:", fontsize=9, ha="right")
    ax.text(172, y, _eur(p.skupaj_material), fontsize=9, ha="right",
            fontweight="bold")
    if p.skupaj_delo is not None:
        y -= 6
        ax.text(140, y, "Delo skupaj:", fontsize=9, ha="right")
        ax.text(172, y, _eur(p.skupaj_delo), fontsize=9, ha="right",
                fontweight="bold")
    y -= 9
    ax.add_patch(plt.Rectangle((104, y - 5), 94, 10, facecolor="#e8f5e9",
                               edgecolor="#2e7d32", lw=0.8))
    ax.text(140, y, "SKUPAJ:", fontsize=10, ha="right", fontweight="bold")
    if p.skupaj is None:
        ax.text(172, y, "cena po dogovoru", fontsize=9, ha="right",
                fontweight="bold")
    else:
        ax.text(172, y, _eur(p.skupaj) + " EUR", fontsize=10, ha="right",
                fontweight="bold")

    # ---- opozorila ----
    y_op = y - 18
    ax.text(12, y_op, "OPOZORILA IN STATUSI", fontsize=8,
            fontweight="bold", color="#b71c1c")
    y_op -= 5
    for o in p.opozorila:
        for i, vrstica in enumerate(textwrap.wrap(o, width=94)):
            ax.text(12, y_op, ("• " if i == 0 else "   ") + vrstica,
                    fontsize=7, color="#37474f")
            y_op -= 3.6
        y_op -= 1.2

    ax.text(12, 16, "Cene: cene.yaml (vnesel uporabnik). Predračun iz "
            "fotografije ni ponudba — mere potrdi na objektu.", fontsize=7,
            color="#546e7a")
    ax.text(12, 11, "Podpis izvajalca: ______________        "
            "Potrditev stranke: ______________", fontsize=7)

    fig.savefig(pot_pdf)
    plt.close(fig)
    return str(pot_pdf)
