"""photo_fence_proposal — model podatkov (issue #8).

Samostojen dodatek: fotografija stare ograje → zaznana geometrija →
vizualni predlog + tehnična dokumentacija + informativni izračun materiala.
BREZ AI modelov — klasična obdelava slik (OpenCV) in deterministična pravila.

Statusi mer (vsaka mera v izhodu MORA imeti status):
- ZAZNANO    — vidna geometrija v slikovnih pikah (brez merila)
- IZMERJENO  — kalibrirano z uporabnikovo referenčno mero
- IZRACUNANO — izpeljano iz kalibriranih mer (npr. število polj × razmak)
- OCENJENO   — hevristična ocena (npr. standardna širina deske) — NI potrjeno
- NEZNANO    — ni določljivo iz fotografije — zahteva potrditev uporabnika
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------- statusi mer

ZAZNANO = "zaznano"
IZMERJENO = "izmerjeno"
IZRACUNANO = "izracunano"
OCENJENO = "ocenjeno"
NEZNANO = "neznano"

STATUSI = (ZAZNANO, IZMERJENO, IZRACUNANO, OCENJENO, NEZNANO)

# Statusi, ki veljajo za "potrjene" mere (dokument je lahko za izdelavo).
POTRJENI_STATUSI = (IZMERJENO, IZRACUNANO)


@dataclass
class Mera:
    """Mera z zanesljivostjo — jedro poštene komunikacije (issue #8)."""
    vrednost_mm: float | None
    status: str
    opis: str
    napaka_mm: float | None = None     # znana napaka (samo kalibrirani primeri)
    vir: str = ""                      # npr. "referenca uporabnika", "zaznano: stebri"
    enota: str = "mm"

    def __post_init__(self):
        if self.status not in STATUSI:
            raise ValueError(f"Neznan status mere {self.status!r} — dovoljeni: {STATUSI}")
        if self.status == NEZNANO and self.vrednost_mm is not None:
            raise ValueError("Neznana mera ne sme imeti izmišljene vrednosti!")
        if self.status != NEZNANO and self.vrednost_mm is None:
            raise ValueError(f"Mera s statusom {self.status!r} mora imeti vrednost")
        if self.vrednost_mm is not None and self.vrednost_mm < 0:
            raise ValueError(
                f"Mera ne sme biti negativna (prejeto: {self.vrednost_mm})")

    @property
    def je_potrjena(self):
        return self.status in POTRJENI_STATUSI

    @property
    def oznaka(self):
        """Oznaka za izpis: vrednost + status (nikoli slepa številka)."""
        if self.status == NEZNANO:
            return f"?? {self.enota} (neznano — potrdi)"
        znak = {"izmerjeno": "†", "izracunano": "‡", "ocenjeno": "≈",
                "zaznano": "px"}[self.status]
        v = f"{self.vrednost_mm:.0f}" if self.vrednost_mm is not None else "??"
        return f"{v} {self.enota} [{self.status} {znak}]"

    def v_json(self):
        return asdict(self)


@dataclass
class Slika:
    """Vhodna fotografija (lokalno, brez pošiljanja kamorkoli)."""
    pot: str
    sirina_px: int
    visina_px: int


@dataclass
class Element:
    """Zaznan konstrukcijski element stare ograje (slikovne koordinate)."""
    vrsta: str            # "steber", "polje", "precka", "letv", "rob"
    tocke_px: list        # [(x, y), ...]
    zaupanje: float       # 0..1 (deterministična ocena, ne verjetnost modela)
    opis: str = ""


@dataclass
class Zaznava:
    """Rezultat zaznavanja na eni sliki."""
    slika: Slika
    elementi: list = field(default_factory=list)
    obmocje_ograje_px: list = field(default_factory=list)  # vogali (quad)
    opozorila: list = field(default_factory=list)


@dataclass
class Kalibracija:
    """Ena referenčna mera uporabnika → slikovne pike v mm (single-view).

    OMEJITEV (pošteno): predpostavka je ortogonalen/čeln pogled brez perspektive.
    Pri pogledu pod kotom so mere zmeraj slabše — status OCENJENO ali NEZNANO.
    """
    dolzina_px: float
    dolzina_mm: float
    opis: str = ""

    @property
    def mm_na_px(self):
        return self.dolzina_mm / self.dolzina_px

    def v_mere(self, dolzina_px: float, opis: str, status=IZMERJENO) -> Mera:
        return Mera(vrednost_mm=dolzina_px * self.mm_na_px, status=status,
                    opis=opis, vir="kalibracija: " + self.opis)


# ------------------------------------------------------------------ parametri

TIP_OGRAJE = ("wpc_vodoravne_lamele", "wpc_pokoncne_deske")


@dataclass
class ParametriNove:
    """Uporabnik izbere samo osnovne lastnosti — NE riše skice."""
    tip: str = "wpc_vodoravne_lamele"
    barva: str = "antracit"          # antracit | rjava | siva | bela
    sirina_lamele_mm: float = 165.0  # OCENJENO, dokler uporabnik ne potrdi
    razmak_mm: float = 15.0
    visina_ograje_mm: float | None = None   # None → NEZNANO (dokler ni kalibracije)
    dolzina_ograje_mm: float | None = None

    def __post_init__(self):
        if self.tip not in TIP_OGRAJE:
            raise ValueError(f"Neznan tip ograje {self.tip!r} — dovoljeni: {TIP_OGRAJE}")
        if self.sirina_lamele_mm <= 0 or self.razmak_mm < 0:
            raise ValueError("Neveljavne dimenzije lamel")


BARVE_BGR = {
    "antracit": (63, 63, 70),
    "rjava": (70, 90, 110),
    "siva": (140, 140, 140),
    "bela": (225, 225, 225),
}


@dataclass
class PostavkaKosovnice:
    naziv: str
    material: str
    dimenzija: str
    kolicina: float
    enota: str
    status_mer: str        # najšibkejši status vpletenih mer
    opomba: str = ""


@dataclass
class Rezultat:
    """Celovit izhod: A (vizualni predlog) + B (tehnična dokumentacija)."""
    zaznava: Zaznava | None
    parametri: ParametriNove
    mere: dict = field(default_factory=dict)      # ime → Mera
    kosovnica: list = field(default_factory=list)  # PostavkaKosovnice
    razrez: list = field(default_factory=list)
    odpad_mm: float | None = None
    opozorila: list = field(default_factory=list)

    @property
    def vse_kljucne_mere_potrjene(self) -> bool:
        kljucne = ("dolzina_ograje", "visina_ograje")
        return all(self.mere.get(k) is not None and self.mere[k].je_potrjena
                   for k in kljucne)

    @property
    def oznaka_dokumenta(self) -> str:
        # Poštenost (test z realnimi fotografijami): potrjene mere ŠE NE
        # pomenijo pripravljenosti — če je zaznava negotova (opozorila),
        # dokument ostane predlog za potrditev na objektu.
        if self.vse_kljucne_mere_potrjene:
            blokirajoce = [o for o in self.opozorila
                           if any(z in o.lower() for z in
                                  ("negotov", "neenakomern", "ni zanesljivo"))]
            if blokirajoce:
                return ("PREDLOG ZA POTRDITEV (mere potrjene, a zaznava je "
                        "negotova — obvezno preveri na objektu)")
            return "PRIPRAVLJENO ZA IZDELAVO (vse ključne mere potrjene)"
        return "INFORMATIVNI PREDLOG (ključne mere niso potrjene)"

    def povzetek(self) -> str:
        vrstice = [self.oznaka_dokumenta, ""]
        vrstice.append("MERE:")
        for ime, m in sorted(self.mere.items()):
            vrstice.append(f"  {ime}: {m.oznaka} ({m.opis})")
        if self.opozorila:
            vrstice.append("")
            vrstice.append("OPOZORILA:")
            vrstice.extend(f"  - {o}" for o in self.opozorila)
        return "\n".join(vrstice)

    def v_json(self) -> str:
        return json.dumps({
            "oznaka_dokumenta": self.oznaka_dokumenta,
            "parametri": asdict(self.parametri),
            "mere": {k: m.v_json() for k, m in self.mere.items()},
            "kosovnica": [asdict(p) for p in self.kosovnica],
            "razrez": self.razrez,
            "odpad_mm": self.odpad_mm,
            "opozorila": self.opozorila,
        }, ensure_ascii=False, indent=2)